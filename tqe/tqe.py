#!/usr/bin/env python3
"""
tqe/tqe.py
Updated TQE prototype with COMET / COMET-QE integration and TM fuzzy matching.

Key features:
 - Parse XLIFF (1.2/2.0)
 - Fuzzy TM lookup (rapidfuzz) with configurable threshold (default 0.8)
 - COMET (ref-based) & COMET-QE (no-ref) loading & batching (optional)
 - Per-metric metadata (per-model) and aggregated metrics written as XLIFF props
 - GPU + fp16 support (if device=cuda)
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from lxml import etree

# Optional libs
try:
    from bert_score import score as bert_score
    BERTSCORE_AVAILABLE = True
except Exception:
    BERTSCORE_AVAILABLE = False

try:
    from sentence_transformers import SentenceTransformer, util as st_util
    SBERT_AVAILABLE = True
except Exception:
    SBERT_AVAILABLE = False

try:
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False

# COMET (optional)
try:
    from comet import load_from_checkpoint
    COMET_AVAILABLE = True
except Exception:
    COMET_AVAILABLE = False

# ---------- Constants ----------
DEFAULT_MODEL_DIR = "./models"
DEFAULT_COMET_DIR = os.path.join(DEFAULT_MODEL_DIR, "comet")
DEFAULT_COMET_REF_REPO = "Unbabel/wmt22-comet-da"   # example HF repo (change if needed)
DEFAULT_COMET_QE_REPO = "Unbabel/wmt21-comet-qe"    # example HF repo

# ---------- Utilities ----------
def now_iso():
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"

def safe_get_text(node):
    if node is None:
        return ""
    return (node.text or "").strip()

# ---------- XLIFF parsing ----------
def parse_xliff(xliff_path: str):
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    tree = etree.parse(xliff_path, parser)
    root = tree.getroot()
    tus = []
    trans_units = root.findall(".//{*}trans-unit") + root.findall(".//{*}unit")
    if not trans_units:
        trans_units = root.findall(".//trans-unit") + root.findall(".//unit")
    for tu in trans_units:
        tu_id = tu.get("id") or tu.get("resname") or (tu.get("translate") or "")
        source_node = tu.find(".//{*}source") or tu.find(".//source")
        target_node = tu.find(".//{*}target") or tu.find(".//target")
        src = safe_get_text(source_node)
        tgt = safe_get_text(target_node)
        tus.append({
            "id": tu_id,
            "src": src,
            "tgt": tgt,
            "target_node": target_node,
            "xml_node": tu,
        })
    return tree, tus

# ---------- TMX parsing (simple) ----------
def parse_tmx(tmx_path: str):
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    tree = etree.parse(tmx_path, parser)
    root = tree.getroot()
    tm = {}
    for tu in root.findall(".//{*}tu"):
        # naive mapping: first tuv <> seg considered src, other tuvs as targets
        segs = tu.findall(".//{*}tuv")
        texts = {}
        for tuv in segs:
            lang = tuv.get("{http://www.w3.org/XML/1998/namespace}lang") or tuv.get("lang") or ""
            seg = tuv.find(".//{*}seg")
            if seg is None:
                continue
            texts[lang] = safe_get_text(seg)
        # index each target by the English (or any) source text -- we store all tuv entries
        # For simplicity: put every target under each source text found in tuv set
        for src_lang, src_text in texts.items():
            for tgt_lang, tgt_text in texts.items():
                if src_lang == tgt_lang:
                    continue
                tm.setdefault(src_text, []).append({
                    "target": tgt_text,
                    "tgt_lang": tgt_lang,
                    "creationtool": tu.get("creationtool") or "",
                    "is_human": True  # default true - further heuristics applied later
                })
    return tm

# ---------- Heuristics ----------
def is_human_translation_from_xliff_tu(tu_xml_node: etree._Element) -> bool:
    notes = tu_xml_node.findall(".//{*}note") + tu_xml_node.findall(".//note")
    for n in notes:
        txt = safe_get_text(n).lower()
        if any(k in txt for k in ("machine", "mt", "automatic", "google", "deepl", "nmt", "llm", "translated by", "aws", "azure")):
            return False
    tool = (tu_xml_node.get("creationtool") or tu_xml_node.get("tool") or "")
    if tool:
        t = tool.lower()
        if any(tok in t for tok in ("mt", "machine", "google", "deepl", "nmt", "translate", "llm")):
            return False
        else:
            return True
    # default: treat ambiguous as NOT human (per your instruction)
    return False

# ---------- Fuzzy TM lookup (Levenshtein via rapidfuzz) ----------
def fuzzy_tmx_lookup(src: str, tmx_map: Dict[str, List[Dict]], threshold: float = 0.8) -> Optional[str]:
    """
    Find the best TM entry whose source is fuzzy-similar to the given src.
    threshold is normalized similarity (0..1). Uses rapidfuzz ratio.
    Returns the target text (first best human-marked target) or None.
    """
    if not RAPIDFUZZ_AVAILABLE or not tmx_map:
        return None
    best_score = 0.0
    best_tgt = None
    for tm_src, entries in tmx_map.items():
        # normalized ratio (0..100)
        sim = fuzz.ratio(src, tm_src)
        norm = sim / 100.0
        if norm >= threshold and norm > best_score:
            # pick first human-marked target if present
            for e in entries:
                if e.get("is_human", True):
                    best_score = norm
                    best_tgt = e.get("target")
                    break
            if best_tgt is None and entries:
                best_tgt = entries[0].get("target")
                best_score = norm
    return best_tgt

# ---------- Scoring primitives (same as previous, with additions) ----------
def compute_accuracy_with_reference_bertscore(candidate: str, reference: str, lang: str = "en") -> float:
    if BERTSCORE_AVAILABLE:
        model_type = "xlm-roberta-large" if lang != "en" else "roberta-large"
        P, R, F1 = bert_score([candidate], [reference], lang=lang, model_type=model_type, rescale_with_baseline=True)
        val = float(F1[0])
        return val * 100.0
    elif SBERT_AVAILABLE:
        sbert = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        emb_c = sbert.encode(candidate, convert_to_tensor=True)
        emb_r = sbert.encode(reference, convert_to_tensor=True)
        sim = float(st_util.cos_sim(emb_c, emb_r))
        return max(0.0, min(100.0, sim * 100.0))
    else:
        return 50.0

def compute_accuracy_without_reference_sbert(src: str, candidate: str) -> float:
    if SBERT_AVAILABLE:
        sbert = SentenceTransformer("sentence-transformers/paraphrase-multilingual-mpnet-base-v2")
        emb_src = sbert.encode(src, convert_to_tensor=True)
        emb_c = sbert.encode(candidate, convert_to_tensor=True)
        sim = float(st_util.cos_sim(emb_src, emb_c))
        score = max(0.0, min(100.0, (sim + 1.0) / 2.0 * 100.0))
        return score
    else:
        return 50.0

def compute_fluency_perplexity(candidate: str, lm_model=None, lm_tokenizer=None, device="cpu") -> float:
    if not TRANSFORMERS_AVAILABLE or lm_model is None or lm_tokenizer is None:
        return 50.0
    lm_model.eval()
    with torch.no_grad():
        inputs = lm_tokenizer(candidate, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(device) for k, v in inputs.items()}
        labels = inputs["input_ids"]
        outputs = lm_model(**inputs, labels=labels)
        loss = float(outputs.loss)
    ppl = math.exp(min(loss, 50))
    score = 100.0 * (1.0 - math.tanh(math.log(max(ppl, 1.0)) / 1.5))
    return max(0.0, min(100.0, score))

def compute_tone_score(candidate: str, tone_exemplars: List[str], sbert_model=None) -> float:
    if not SBERT_AVAILABLE or sbert_model is None:
        return 50.0
    emb_c = sbert_model.encode(candidate, convert_to_tensor=True)
    sims = []
    for ex in tone_exemplars:
        emb_e = sbert_model.encode(ex, convert_to_tensor=True)
        sims.append(float(st_util.cos_sim(emb_c, emb_e)))
    if not sims:
        return 50.0
    avg_sim = sum(sims) / len(sims)
    return max(0.0, min(100.0, (avg_sim + 1.0) / 2.0 * 100.0))

# ---------- COMET helpers ----------
def load_comet_model(checkpoint_path: str, device: str = "cpu", fp16: bool = False):
    if not COMET_AVAILABLE:
        raise RuntimeError("COMET python package not available. Install from https://github.com/Unbabel/COMET.git")
    model = load_from_checkpoint(checkpoint_path)
    if device.startswith("cuda"):
        model = model.to(device)
        if fp16:
            try:
                model.half()
            except Exception:
                # some PL wrappers may not accept .half(); continue
                pass
    return model

def run_comet_ref_batch(comet_model, srcs: List[str], hyps: List[str], refs: List[str], batch_size: int = 16, device: str = "cuda"):
    results = []
    for i in range(0, len(srcs), batch_size):
        b_src = srcs[i:i+batch_size]
        b_hyp = hyps[i:i+batch_size]
        b_ref = refs[i:i+batch_size]
        # COMET's predict API returns list of dicts; gpus param is used by PL trainer; set gpus=1 if cuda
        pred = comet_model.predict(b_src, b_hyp, b_ref, batch_size=len(b_src), gpus=1 if device.startswith("cuda") else 0)
        for p in pred:
            # try common keys:
            val = None
            if isinstance(p, dict):
                for k in ("score", "preds", "pred"):
                    if k in p:
                        val = p[k]
                        break
            if val is None:
                # fallback if predict returned scalar in list
                try:
                    val = float(p)
                except Exception:
                    val = 0.0
            results.append(float(val))
    return results

def run_comet_qe_batch(comet_qe_model, srcs: List[str], hyps: List[str], batch_size: int = 16, device: str = "cuda"):
    results = []
    for i in range(0, len(srcs), batch_size):
        b_src = srcs[i:i+batch_size]
        b_hyp = hyps[i:i+batch_size]
        pred = comet_qe_model.predict(b_src, b_hyp, batch_size=len(b_src), gpus=1 if device.startswith("cuda") else 0)
        for p in pred:
            val = None
            if isinstance(p, dict):
                for k in ("score", "preds", "pred"):
                    if k in p:
                        val = p[k]
                        break
            if val is None:
                try:
                    val = float(p)
                except Exception:
                    val = 0.0
            results.append(float(val))
    return results

# Normalization helper (simple linear mapping - placeholder for calibration)
def normalize_comet_score(raw_score: float, raw_min: float = -1.0, raw_max: float = 1.0) -> float:
    # Map raw_score in [raw_min, raw_max] to [0,100]
    if raw_max == raw_min:
        return max(0.0, min(100.0, raw_score))
    norm = (raw_score - raw_min) / (raw_max - raw_min)
    return max(0.0, min(100.0, norm * 100.0))

# ---------- XLIFF metadata helpers ----------
def add_tqe_props_to_tu(tu_node: etree._Element, props: Dict[str, str]):
    pg = tu_node.find(".//{*}prop-group")
    if pg is None:
        pg = etree.SubElement(tu_node, "prop-group")
    for k, v in props.items():
        p = etree.SubElement(pg, "prop")
        p.set("type", k)
        p.text = str(v)

def write_xliff(tree: etree._ElementTree, out_path: str):
    tree.write(out_path, encoding="utf-8", pretty_print=True, xml_declaration=True)

# ---------- Aggregation ----------
def aggregate_scores(acc: float, flu: float, tone: float, uq_halluc: bool=False,
                     weights: Tuple[float, float, float] = (0.6, 0.25, 0.15)) -> Tuple[float, str]:
    w_acc, w_flu, w_tone = weights
    weighted = w_acc * acc + w_flu * flu + w_tone * tone
    if uq_halluc:
        return weighted, "needs_human_revision"
    if weighted >= 85.0:
        return weighted, "accept_auto"
    if weighted >= 70.0:
        return weighted, "accept_with_review"
    return weighted, "needs_human_revision"

# ---------- Engine ----------
class TQEEngine:
    def __init__(self, device="cpu", lm_name=None, sbert_name=None, comet_ref_ckpt=None, comet_qe_ckpt=None, fp16=False, comet_batch=16):
        self.device = device
        self.lm_model = None
        self.lm_tokenizer = None
        self.sbert_model = None
        self.comet_model = None
        self.comet_qe_model = None
        self.fp16 = fp16
        self.comet_batch = comet_batch

        if TRANSFORMERS_AVAILABLE and lm_name:
            try:
                self.lm_tokenizer = AutoTokenizer.from_pretrained(lm_name)
                self.lm_model = AutoModelForCausalLM.from_pretrained(lm_name).to(self.device)
                if fp16 and self.device.startswith("cuda"):
                    try:
                        self.lm_model.half()
                    except Exception:
                        pass
            except Exception as e:
                print("Warning: could not load LM:", e, file=sys.stderr)

        if SBERT_AVAILABLE:
            self.sbert_model = SentenceTransformer(sbert_name or "sentence-transformers/paraphrase-multilingual-mpnet-base-v2")

        if comet_ref_ckpt:
            try:
                self.comet_model = load_comet_model(comet_ref_ckpt, device=self.device, fp16=fp16)
            except Exception as e:
                print("Warning: could not load COMET ref model:", e, file=sys.stderr)
                self.comet_model = None

        if comet_qe_ckpt:
            try:
                self.comet_qe_model = load_comet_model(comet_qe_ckpt, device=self.device, fp16=fp16)
            except Exception as e:
                print("Warning: could not load COMET-QE model:", e, file=sys.stderr)
                self.comet_qe_model = None

    def score_xliff(self, xliff_path: str, candidates: Dict[str, List[str]],
                    tmx_map: Optional[Dict[str, List[Dict]]] = None,
                    uqlm_map: Optional[Dict[str, Dict]] = None,
                    tone_exemplars_map: Optional[Dict[str, List[str]]] = None,
                    out_path: str = "out.xlf",
                    weights: Tuple[float, float, float] = (0.6, 0.25, 0.15),
                    lang: str = "en",
                    fuzzy_threshold: float = 0.8,
                    fuzzy_enable: bool = True):
        tree, tu_list = parse_xliff(xliff_path)
        tmx_map = tmx_map or {}
        uqlm_map = uqlm_map or {}
        tone_exemplars_map = tone_exemplars_map or {}
        for tu in tu_list:
            tu_id = tu["id"]
            src = tu["src"]
            existing_tgt = tu["tgt"]
            xml_node = tu["xml_node"]

            # Identify human reference (prefer TMX fuzzy match, else existing target if flagged human)
            human_ref = None
            if fuzzy_enable and tmx_map:
                human_ref = fuzzy_tmx_lookup(src, tmx_map, threshold=fuzzy_threshold)
            if human_ref is None:
                # use existing target only if marked human
                if existing_tgt and is_human_translation_from_xliff_tu(xml_node):
                    human_ref = existing_tgt

            # Candidate set
            tu_candidates = candidates.get(tu_id) or candidates.get(src) or ([existing_tgt] if existing_tgt else [])
            if not tu_candidates:
                continue

            # Batch precompute COMET inputs if models present
            # We'll perform per-candidate scoring for simplicity (small nbest). For large N, adjust batching.
            best = None
            best_meta = None

            for cand in tu_candidates:
                uq = uqlm_map.get(tu_id) or uqlm_map.get(src) or {}
                uq_halluc = bool(uq.get("hallucination") or uq.get("is_hallucination"))

                # ACCURACY: prefer COMET (ref) if ref available, else COMET-QE if available, else BERTScore or SBERT
                acc_components = {}
                if human_ref and self.comet_model:
                    try:
                        raw = run_comet_ref_batch(self.comet_model, [src], [cand], [human_ref], batch_size=self.comet_batch, device=self.device)[0]
                        acc_components["comet_ref_raw"] = raw
                        acc = normalize_comet_score(raw, raw_min=-1.0, raw_max=1.0)
                        acc_components["comet_ref_norm"] = round(acc, 3)
                    except Exception as e:
                        acc = compute_accuracy_with_reference_bertscore(cand, human_ref, lang=lang)
                elif self.comet_qe_model and not human_ref:
                    try:
                        raw = run_comet_qe_batch(self.comet_qe_model, [src], [cand], batch_size=self.comet_batch, device=self.device)[0]
                        acc_components["comet_qe_raw"] = raw
                        acc = normalize_comet_score(raw, raw_min=-1.0, raw_max=1.0)
                        acc_components["comet_qe_norm"] = round(acc, 3)
                    except Exception as e:
                        acc = compute_accuracy_without_reference_sbert(src, cand)
                else:
                    if human_ref:
                        acc = compute_accuracy_with_reference_bertscore(cand, human_ref, lang=lang)
                        acc_components["bertscore"] = round(acc, 3)
                    else:
                        acc = compute_accuracy_without_reference_sbert(src, cand)
                        acc_components["sbert_no_ref"] = round(acc, 3)

                # Fluency (LM perplexity fallback)
                if self.lm_model and self.lm_tokenizer:
                    flu = compute_fluency_perplexity(cand, lm_model=self.lm_model, lm_tokenizer=self.lm_tokenizer, device=self.device)
                    flu_model = getattr(self.lm_model.config, "_name_or_path", "causal-lm")
                else:
                    flu = 50.0
                    flu_model = "none"

                # Tone
                exemplars = tone_exemplars_map.get(tu_id) or tone_exemplars_map.get("default") or []
                if exemplars and self.sbert_model:
                    tone = compute_tone_score(cand, exemplars, sbert_model=self.sbert_model)
                else:
                    tone = 50.0

                # UQLM penalty
                if uq_halluc:
                    acc = acc * 0.25

                weighted, decision = aggregate_scores(acc, flu, tone, uq_hallucination=uq_halluc, weights=weights)

                meta = {
                    "accuracy": round(float(acc), 2),
                    "fluency": round(float(flu), 2),
                    "tone": round(float(tone), 2),
                    "weighted": round(float(weighted), 2),
                    "decision": decision,
                    "uq_hallucination": bool(uq_halluc),
                    "per_metric_models": {
                        "accuracy_components": acc_components,
                        "fluency_model": flu_model,
                        "tone_model": getattr(self.sbert_model, "name", "sbert") if self.sbert_model else "none",
                    }
                }

                # choose best candidate by weighted, prefer accept_auto
                if best is None or (meta["weighted"] > best_meta["weighted"]) or (meta["decision"] == "accept_auto" and best_meta["decision"] != "accept_auto"):
                    best = cand
                    best_meta = meta

            # Write back target and props
            target_node = tu["target_node"]
            if target_node is None:
                target_node = etree.SubElement(xml_node, "target")
            target_node.text = best

            # Add per-model/per-metric props and aggregate props
            props = {}
            # per-component: expand components dict
            # accuracy components (if any)
            acc_comps = best_meta["per_metric_models"].get("accuracy_components", {})
            for k, v in acc_comps.items():
                props[f"tqe:accuracy.{k}"] = str(v)
            props["tqe:accuracy"] = str(best_meta["accuracy"])
            props["tqe:fluency"] = str(best_meta["fluency"])
            props["tqe:tone"] = str(best_meta["tone"])
            props["tqe:weighted_score"] = str(best_meta["weighted"])
            props["tqe:decision"] = best_meta["decision"]
            props["tqe:uqm_hallucination"] = str(best_meta["uq_hallucination"])
            props["tqe:models_used"] = json.dumps(best_meta["per_metric_models"])
            props["tqe:timestamp"] = now_iso()
            add_tqe_props_to_tu(xml_node, props)

        write_xliff(tree, out_path)
        print(f"Wrote scored XLIFF to {out_path}")

# ---------- CLI ----------
def load_json_optional(path: Optional[str]):
    if not path:
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--xliff", required=True)
    parser.add_argument("--candidates", required=True)
    parser.add_argument("--tmx", help="Optional TMX file for TM lookup")
    parser.add_argument("--uqlm", help="Optional UQLM JSON map")
    parser.add_argument("--tone_exemplars", help="Optional tone exemplars JSON")
    parser.add_argument("--out", default="out.xlf")
    parser.add_argument("--device", default="cuda", choices=["cpu","cuda"])
    parser.add_argument("--lm_model", help="HF causal LM for fluency (optional)")
    parser.add_argument("--sbert_model", help="SentenceTransformer model name (optional)")
    parser.add_argument("--lang", default="en")
    parser.add_argument("--use-comet-ref", help="Path to COMET (ref) checkpoint", default=None)
    parser.add_argument("--use-comet-qe", help="Path to COMET-QE checkpoint", default=None)
    parser.add_argument("--fp16", action="store_true", help="Use fp16 where possible")
    parser.add_argument("--comet-batch-size", default=16, type=int)
    parser.add_argument("--fuzzy-enable", action="store_true", help="Enable fuzzy TM lookup")
    parser.add_argument("--fuzzy-threshold", default=0.8, type=float, help="Fuzzy match threshold (0..1)")
    parser.add_argument("--weights", default="0.6,0.25,0.15", help="Weights for accuracy,fluency,tone")
    args = parser.parse_args(argv)

    candidates = load_json_optional(args.candidates)
    uqlm_map = load_json_optional(args.uqlm) if args.uqlm else {}
    tone_exemplars = load_json_optional(args.tone_exemplars) if args.tone_exemplars else {}
    tmx_map = parse_tmx(args.tmx) if args.tmx else None

    w = tuple(float(x) for x in args.weights.split(","))
    engine = TQEEngine(device=args.device, lm_name=args.lm_model, sbert_name=args.sbert_model,
                       comet_ref_ckpt=args.use_comet_ref, comet_qe_ckpt=args.use_comet_qe,
                       fp16=args.fp16, comet_batch=args.comet_batch_size)
    engine.score_xliff(args.xliff, candidates, tmx_map=tmx_map, uqlm_map=uqlm_map, tone_exemplars_map=tone_exemplars,
                       out_path=args.out, weights=w, lang=args.lang, fuzzy_threshold=args.fuzzy_threshold, fuzzy_enable=args.fuzzy_enable)

if __name__ == "__main__":
    main()
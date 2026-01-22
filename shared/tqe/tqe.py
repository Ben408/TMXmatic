"""
Translation Quality Estimation (TQE) Engine

Main TQE engine for scoring translation candidates.
Integrates with shared infrastructure (model manager, logging, etc.)
"""
import logging
import json
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from lxml import etree

from shared.tqe.scoring import (
    compute_accuracy_with_reference_bertscore,
    compute_accuracy_without_reference_sbert,
    compute_fluency_perplexity,
    compute_tone_score,
    aggregate_scores,
    normalize_comet_score
)
from shared.tqe.xliff_utils import (
    parse_xliff, is_human_translation_from_xliff_tu,
    add_tqe_props_to_tu, write_xliff, now_iso
)
from shared.tqe.tmx_utils import parse_tmx, fuzzy_tmx_lookup
from shared.tqe.comet_utils import (
    load_comet_model, run_comet_ref_batch, run_comet_qe_batch
)
from shared.tqe.uqlm_integration import detect_hallucination
from shared.utils.logging import get_logger

logger = get_logger(__name__)

# Optional imports
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False
    logger.warning("Transformers not available")

try:
    from sentence_transformers import SentenceTransformer
    SBERT_AVAILABLE = True
except Exception:
    SBERT_AVAILABLE = False
    logger.warning("SentenceTransformers not available")

try:
    import torch
except Exception:
    torch = None
    logger.warning("PyTorch not available")


class TQEEngine:
    """
    Translation Quality Estimation Engine.
    
    Scores translation candidates using multiple metrics:
    - Accuracy (COMET, BERTScore, SBERT)
    - Fluency (LM perplexity)
    - Tone (SBERT similarity to exemplars)
    - Hallucination detection (UQLM)
    """
    
    def __init__(self, device: str = "cpu", lm_name: Optional[str] = None,
                 sbert_name: Optional[str] = None, comet_ref_ckpt: Optional[str] = None,
                 comet_qe_ckpt: Optional[str] = None, fp16: bool = False,
                 comet_batch: int = 16):
        """
        Initialize TQE Engine.
        
        Args:
            device: Device to use ('cpu' or 'cuda')
            lm_name: HuggingFace model name for fluency scoring
            sbert_name: SentenceTransformer model name
            comet_ref_ckpt: Path to COMET reference-based checkpoint
            comet_qe_ckpt: Path to COMET-QE checkpoint
            fp16: Use half precision
            comet_batch: Batch size for COMET scoring
        """
        self.device = device
        self.fp16 = fp16
        self.comet_batch = comet_batch
        
        # Models (loaded on demand)
        self.lm_model = None
        self.lm_tokenizer = None
        self.sbert_model = None
        self.comet_model = None
        self.comet_qe_model = None
        
        # Load models if names provided
        if TRANSFORMERS_AVAILABLE and lm_name:
            try:
                self.lm_tokenizer = AutoTokenizer.from_pretrained(lm_name)
                self.lm_model = AutoModelForCausalLM.from_pretrained(lm_name).to(self.device)
                if fp16 and self.device.startswith("cuda") and torch:
                    try:
                        self.lm_model.half()
                    except Exception:
                        pass
                logger.info(f"Loaded LM model: {lm_name}")
            except Exception as e:
                logger.warning(f"Could not load LM model {lm_name}: {e}")
        
        if SBERT_AVAILABLE:
            model_name = sbert_name or "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            try:
                self.sbert_model = SentenceTransformer(model_name)
                logger.info(f"Loaded SBERT model: {model_name}")
            except Exception as e:
                logger.warning(f"Could not load SBERT model: {e}")
        
        if comet_ref_ckpt:
            try:
                self.comet_model = load_comet_model(comet_ref_ckpt, device=self.device, fp16=fp16)
            except Exception as e:
                logger.warning(f"Could not load COMET ref model: {e}")
        
        if comet_qe_ckpt:
            try:
                self.comet_qe_model = load_comet_model(comet_qe_ckpt, device=self.device, fp16=fp16)
            except Exception as e:
                logger.warning(f"Could not load COMET-QE model: {e}")
    
    def score_candidate(self, candidate: str, source: str, reference: Optional[str] = None,
                       tone_exemplars: Optional[List[str]] = None,
                       uqlm_check: bool = True) -> Dict:
        """
        Score a single translation candidate.
        
        Args:
            candidate: Candidate translation
            source: Source text
            reference: Optional reference translation
            tone_exemplars: Optional tone exemplar texts
            uqlm_check: Whether to check for hallucination
        
        Returns:
            Dictionary with scores and metadata
        """
        # UQLM hallucination check
        uq_result = {}
        uq_halluc = False
        if uqlm_check:
            try:
                uq_result = detect_hallucination(candidate, source=source)
                uq_halluc = uq_result.get('hallucination', False) or uq_result.get('is_hallucination', False)
            except Exception as e:
                logger.warning(f"UQLM check failed: {e}")
        
        # Accuracy scoring
        acc_components = {}
        if reference and self.comet_model:
            try:
                raw = run_comet_ref_batch(
                    self.comet_model, [source], [candidate], [reference],
                    batch_size=1, device=self.device
                )[0]
                acc_components["comet_ref_raw"] = raw
                acc = normalize_comet_score(raw, raw_min=-1.0, raw_max=1.0)
                acc_components["comet_ref_norm"] = round(acc, 3)
            except Exception as e:
                logger.warning(f"COMET ref scoring failed: {e}")
                acc = compute_accuracy_with_reference_bertscore(candidate, reference)
                acc_components["bertscore"] = round(acc, 3)
        elif self.comet_qe_model and not reference:
            try:
                raw = run_comet_qe_batch(
                    self.comet_qe_model, [source], [candidate],
                    batch_size=1, device=self.device
                )[0]
                acc_components["comet_qe_raw"] = raw
                acc = normalize_comet_score(raw, raw_min=-1.0, raw_max=1.0)
                acc_components["comet_qe_norm"] = round(acc, 3)
            except Exception as e:
                logger.warning(f"COMET-QE scoring failed: {e}")
                acc = compute_accuracy_without_reference_sbert(source, candidate)
                acc_components["sbert_no_ref"] = round(acc, 3)
        else:
            if reference:
                acc = compute_accuracy_with_reference_bertscore(candidate, reference)
                acc_components["bertscore"] = round(acc, 3)
            else:
                acc = compute_accuracy_without_reference_sbert(source, candidate)
                acc_components["sbert_no_ref"] = round(acc, 3)
        
        # UQLM penalty
        if uq_halluc:
            acc = acc * 0.25
        
        # Fluency scoring
        if self.lm_model and self.lm_tokenizer:
            flu = compute_fluency_perplexity(
                candidate, self.lm_model, self.lm_tokenizer, self.device
            )
            flu_model = getattr(self.lm_model.config, "_name_or_path", "causal-lm")
        else:
            flu = 50.0
            flu_model = "none"
        
        # Tone scoring
        exemplars = tone_exemplars or []
        if exemplars and self.sbert_model:
            tone = compute_tone_score(candidate, exemplars, self.sbert_model)
        else:
            tone = 50.0
        
        # Aggregate scores
        weighted, decision = aggregate_scores(acc, flu, tone, uq_halluc)
        
        return {
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
            },
            "uqlm_result": uq_result
        }
    
    def score_xliff(self, xliff_path: str, candidates: Dict[str, List[str]],
                   tmx_map: Optional[Dict[str, List[Dict]]] = None,
                   uqlm_map: Optional[Dict[str, Dict]] = None,
                   tone_exemplars_map: Optional[Dict[str, List[str]]] = None,
                   out_path: str = "out.xlf",
                   weights: Tuple[float, float, float] = (0.6, 0.25, 0.15),
                   lang: str = "en",
                   fuzzy_threshold: float = 0.8,
                   fuzzy_enable: bool = True):
        """
        Score translation candidates in XLIFF file.
        
        Args:
            xliff_path: Path to input XLIFF file
            candidates: Dictionary mapping TU ID or source -> list of candidate translations
            tmx_map: Optional TMX translation memory map
            uqlm_map: Optional pre-computed UQLM results
            tone_exemplars_map: Optional tone exemplars by TU ID
            out_path: Output XLIFF path
            weights: Weights for (accuracy, fluency, tone)
            lang: Language code
            fuzzy_threshold: Fuzzy match threshold
            fuzzy_enable: Enable fuzzy TM matching
        """
        tree, tu_list = parse_xliff(xliff_path)
        tmx_map = tmx_map or {}
        uqlm_map = uqlm_map or {}
        tone_exemplars_map = tone_exemplars_map or {}
        
        for tu in tu_list:
            tu_id = tu["id"]
            src = tu["src"]
            existing_tgt = tu["tgt"]
            xml_node = tu["xml_node"]
            
            # Find human reference (prefer TMX fuzzy match)
            human_ref = None
            if fuzzy_enable and tmx_map:
                match_result = fuzzy_tmx_lookup(src, tmx_map, threshold=fuzzy_threshold)
                if match_result:
                    human_ref, similarity = match_result
            
            if human_ref is None:
                # Use existing target if marked as human
                if existing_tgt and is_human_translation_from_xliff_tu(xml_node):
                    human_ref = existing_tgt
            
            # Get candidates
            tu_candidates = (candidates.get(tu_id) or candidates.get(src) or 
                           ([existing_tgt] if existing_tgt else []))
            if not tu_candidates:
                continue
            
            # Score all candidates
            best = None
            best_meta = None
            
            for cand in tu_candidates:
                # Get UQLM result if available
                uq = uqlm_map.get(tu_id) or uqlm_map.get(src) or {}
                uq_halluc = bool(uq.get("hallucination") or uq.get("is_hallucination"))
                
                # Get tone exemplars
                exemplars = tone_exemplars_map.get(tu_id) or tone_exemplars_map.get("default") or []
                
                # Score candidate
                meta = self.score_candidate(
                    candidate=cand,
                    source=src,
                    reference=human_ref,
                    tone_exemplars=exemplars,
                    uqlm_check=not uq_halluc  # Skip if already computed
                )
                
                # Override with pre-computed UQLM if available
                if uq_halluc:
                    meta["uq_hallucination"] = True
                    meta["accuracy"] = meta["accuracy"] * 0.25
                    meta["weighted"], meta["decision"] = aggregate_scores(
                        meta["accuracy"], meta["fluency"], meta["tone"], 
                        uq_halluc=True, weights=weights
                    )
                
                # Choose best candidate
                if (best is None or 
                    meta["weighted"] > best_meta["weighted"] or
                    (meta["decision"] == "accept_auto" and 
                     best_meta["decision"] != "accept_auto")):
                    best = cand
                    best_meta = meta
            
            # Write best candidate to target
            target_node = tu["target_node"]
            if target_node is None:
                target_node = etree.SubElement(xml_node, "target")
            target_node.text = best
            
            # Add TQE metadata
            props = {}
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
        logger.info(f"Scored XLIFF written to {out_path}")

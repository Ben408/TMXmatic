#!/usr/bin/env python3
"""
tqe/terminology.py

Helpers to load termbases (CSV or TBX) and to check term presence/matching in candidate translations.
Exports:
 - load_terms_csv(path)
 - load_terms_tbx(path)
 - lookup_exact_term(src_term, src_lang, tgt_lang, term_db)
 - fuzzy_lookup_term(src_term, src_lang, tgt_lang, term_db, threshold=0.8)
 - term_presence_score(candidate_text, expected_term, lang=None)
 - match_terms_in_candidate(src_text, candidate_text, term_db, src_lang, tgt_lang, fuzzy_threshold=0.8)

Notes:
 - This is a pragmatic, language-agnostic helper. For robust handling of compounds (German etc)
   you should add language-specific morphological splitting or compound-splitter libraries.
"""
from typing import Dict, List, Optional, Tuple
import csv
import xml.etree.ElementTree as ET
import re
import json

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False

TermEntry = Dict[str, str]
# term_db structure: mapping keyed by (src_lang, tgt_lang) -> list[ {src:..., tgt:..., approved:bool, variants:[] } ]
TermDB = Dict[Tuple[str, str], List[TermEntry]]

def load_terms_csv(path: str, src_col="source", tgt_col="target", src_lang_col="src_lang", tgt_lang_col="tgt_lang", approved_col="approved") -> TermDB:
    db: TermDB = {}
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            src = row.get(src_col, "").strip()
            tgt = row.get(tgt_col, "").strip()
            src_lang = row.get(src_lang_col, "").strip() or "src"
            tgt_lang = row.get(tgt_lang_col, "").strip() or "tgt"
            approved = row.get(approved_col, "true").strip().lower() in ("1","true","yes","y")
            key = (src_lang, tgt_lang)
            entry = {"src": src, "tgt": tgt, "approved": approved, "variants": row.get("variants","").split("|") if row.get("variants") else []}
            db.setdefault(key, []).append(entry)
    return db

def load_terms_tbx(path: str) -> TermDB:
    # Very small TBX parser: looks for termEntry -> langSet -> tig/term
    db: TermDB = {}
    tree = ET.parse(path)
    root = tree.getroot()
    # TBX can use namespaces; we'll ignore them by using localname
    for termEntry in root.findall(".//termEntry"):
        langs = {}
        for langSet in termEntry.findall(".//langSet"):
            lcode = langSet.attrib.get("xml:lang") or langSet.attrib.get("{http://www.w3.org/XML/1998/namespace}lang") or langSet.attrib.get("lang")
            if not lcode:
                continue
            tig = langSet.find(".//tig")
            if tig is None:
                # sometimes term is directly under langSet
                term_el = langSet.find(".//term")
            else:
                term_el = tig.find(".//term")
            if term_el is None:
                continue
            langs[lcode] = term_el.text.strip()
        # create pairwise entries for all combos
        for src_lang, src_term in langs.items():
            for tgt_lang, tgt_term in langs.items():
                if src_lang == tgt_lang:
                    continue
                key = (src_lang, tgt_lang)
                entry = {"src": src_term, "tgt": tgt_term, "approved": True, "variants": []}
                db.setdefault(key, []).append(entry)
    return db

def lookup_exact_term(src_term: str, src_lang: str, tgt_lang: str, term_db: TermDB) -> Optional[TermEntry]:
    key = (src_lang, tgt_lang)
    for e in term_db.get(key, []):
        if e["src"].strip().lower() == src_term.strip().lower():
            return e
    return None

def fuzzy_lookup_term(src_term: str, src_lang: str, tgt_lang: str, term_db: TermDB, threshold: float = 0.8) -> Optional[Tuple[TermEntry, float]]:
    """
    Return (entry, score) where score in 0..1
    """
    if not RAPIDFUZZ_AVAILABLE:
        return None
    key = (src_lang, tgt_lang)
    best_score = 0.0
    best_entry = None
    for e in term_db.get(key, []):
        s = fuzz.ratio(src_term, e["src"]) / 100.0
        if s >= threshold and s > best_score:
            best_score = s
            best_entry = e
    if best_entry:
        return best_entry, best_score
    return None

def normalize_text_for_matching(t: str) -> str:
    # basic normalization: lower, remove extra whitespace, remove punctuation except internal hyphens
    t = t.lower().strip()
    t = re.sub(r"[^\w\s\-]", " ", t, flags=re.UNICODE)
    t = re.sub(r"\s+", " ", t)
    return t

def candidate_contains_term(candidate: str, expected_term: str) -> bool:
    # Simple exact or substring match on normalized text
    c = normalize_text_for_matching(candidate)
    e = normalize_text_for_matching(expected_term)
    if e in c.split():
        return True
    if e in c:
        return True
    return False

def compound_aware_check(candidate: str, expected_term: str) -> bool:
    """
    Heuristic: checks for expected term appearing as substring fragments of candidate (useful for German compounds).
    Splits expected_term into components (by non-alpha) and checks all components exist in candidate.
    """
    c = normalize_text_for_matching(candidate)
    parts = re.split(r"\W+", expected_term)
    parts = [p for p in parts if p]
    if not parts:
        return False
    for p in parts:
        if p not in c:
            return False
    return True

def term_presence_score(candidate_text: str, expected_term: str) -> float:
    """
    Returns 0..100 score indicating how well expected_term appears in candidate.
    100 = exact or strong match; 0 = not present.
    """
    if candidate_contains_term(candidate_text, expected_term):
        return 100.0
    if compound_aware_check(candidate_text, expected_term):
        return 85.0
    # fuzzier substring match
    if RAPIDFUZZ_AVAILABLE:
        score = fuzz.partial_ratio(candidate_text, expected_term) / 100.0
        return max(0.0, min(100.0, score * 100.0))
    return 0.0

def match_terms_in_candidate(src_text: str, candidate_text: str, term_db: TermDB, src_lang: str, tgt_lang: str, fuzzy_threshold: float = 0.8) -> Dict:
    """
    Finds best term matches (exact or fuzzy) for src_text and returns:
     {found: bool, expected_tgt: str or None, match_score: 0..100, method: 'exact'|'fuzzy'|'compound'|'none'}
    If multiple terms exist, returns the best-scoring one.
    """
    # Try exact lookup
    exact = lookup_exact_term(src_text, src_lang, tgt_lang, term_db)
    if exact:
        score = term_presence_score(candidate_text, exact["tgt"])
        return {"found": score >= 50.0, "expected_tgt": exact["tgt"], "match_score": score, "method": "exact"}
    # Fuzzy source lookup
    fuzzy = fuzzy_lookup_term(src_text, src_lang, tgt_lang, term_db, threshold=fuzzy_threshold)
    if fuzzy:
        entry, s = fuzzy
        # s is similarity on source; now check presence in candidate
        score = term_presence_score(candidate_text, entry["tgt"])
        method = "fuzzy" if s < 0.99 else "exact"
        return {"found": score >= 50.0, "expected_tgt": entry["tgt"], "match_score": score, "method": method}
    # not found
    return {"found": False, "expected_tgt": None, "match_score": 0.0, "method": "none"}

if __name__ == "__main__":
    # quick CLI for manual checks
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--terms_csv")
    parser.add_argument("--src_lang", default="en")
    parser.add_argument("--tgt_lang", default="de")
    parser.add_argument("--src_text", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--fuzzy_threshold", type=float, default=0.8)
    args = parser.parse_args()
    if args.terms_csv:
        db = load_terms_csv(args.terms_csv)
    else:
        print("Provide terms_csv path")
        raise SystemExit(1)
    out = match_terms_in_candidate(args.src_text, args.candidate, db, args.src_lang, args.tgt_lang, fuzzy_threshold=args.fuzzy_threshold)
    print(json.dumps(out, indent=2))
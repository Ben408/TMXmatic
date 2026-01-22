"""
TMX Utilities

Helper functions for parsing TMX files and fuzzy matching.
"""
import logging
from typing import Dict, List, Optional
from lxml import etree

logger = logging.getLogger(__name__)

try:
    from rapidfuzz import fuzz
    RAPIDFUZZ_AVAILABLE = True
except Exception:
    RAPIDFUZZ_AVAILABLE = False
    logger.warning("rapidfuzz not available for fuzzy matching")


def safe_get_text(node) -> str:
    """Safely extract text from XML node."""
    if node is None:
        return ""
    return (node.text or "").strip()


def parse_tmx(tmx_path: str) -> Dict[str, List[Dict]]:
    """
    Parse TMX file and create translation memory map.
    
    Args:
        tmx_path: Path to TMX file
    
    Returns:
        Dictionary mapping source text -> list of translation entries
    """
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    tree = etree.parse(tmx_path, parser)
    root = tree.getroot()
    tm = {}
    
    for tu in root.findall(".//{*}tu"):
        # Get all language variants
        segs = tu.findall(".//{*}tuv")
        texts = {}
        for tuv in segs:
            lang = (tuv.get("{http://www.w3.org/XML/1998/namespace}lang") or 
                   tuv.get("lang") or "")
            seg = tuv.find(".//{*}seg")
            if seg is None:
                continue
            texts[lang] = safe_get_text(seg)
        
        # Create entries for all language pairs
        for src_lang, src_text in texts.items():
            for tgt_lang, tgt_text in texts.items():
                if src_lang == tgt_lang:
                    continue
                tm.setdefault(src_text, []).append({
                    "target": tgt_text,
                    "tgt_lang": tgt_lang,
                    "creationtool": tu.get("creationtool") or "",
                    "is_human": True  # Default true
                })
    
    logger.info(f"Parsed {len(tm)} source entries from TMX")
    return tm


def fuzzy_tmx_lookup(src: str, tmx_map: Dict[str, List[Dict]], 
                     threshold: float = 0.8) -> Optional[tuple[str, float]]:
    """
    Find best fuzzy match in TMX.
    
    Args:
        src: Source text to match
        tmx_map: TMX translation memory map
        threshold: Minimum similarity threshold (0-1)
    
    Returns:
        Tuple of (target_text, similarity_score) or None if no match
    """
    if not RAPIDFUZZ_AVAILABLE or not tmx_map:
        return None
    
    best_score = 0.0
    best_tgt = None
    
    for tm_src, entries in tmx_map.items():
        # Normalized ratio (0-100)
        sim = fuzz.ratio(src, tm_src)
        norm = sim / 100.0
        
        if norm >= threshold and norm > best_score:
            # Prefer human-marked targets
            for e in entries:
                if e.get("is_human", True):
                    best_score = norm
                    best_tgt = e.get("target")
                    break
            
            # Fallback to first entry if no human-marked
            if best_tgt is None and entries:
                best_tgt = entries[0].get("target")
                best_score = norm
    
    if best_tgt:
        return (best_tgt, best_score)
    return None

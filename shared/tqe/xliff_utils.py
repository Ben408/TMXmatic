"""
XLIFF Utilities

Helper functions for parsing and writing XLIFF files.
"""
import logging
from typing import Dict, List, Optional
from lxml import etree
from datetime import datetime

logger = logging.getLogger(__name__)


def safe_get_text(node) -> str:
    """Safely extract text from XML node."""
    if node is None:
        return ""
    return (node.text or "").strip()


def now_iso() -> str:
    """Get current time in ISO format."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def parse_xliff(xliff_path: str) -> tuple[etree._ElementTree, List[Dict]]:
    """
    Parse XLIFF file and extract translation units.
    
    Args:
        xliff_path: Path to XLIFF file
    
    Returns:
        Tuple of (tree, tu_list) where tu_list contains dicts with:
        - id: Translation unit ID
        - src: Source text
        - tgt: Target text
        - target_node: Target XML node
        - xml_node: Translation unit XML node
    """
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    tree = etree.parse(xliff_path, parser)
    root = tree.getroot()
    tus = []
    
    # Find translation units (support both XLIFF 1.2 and 2.0)
    trans_units = root.findall(".//{*}trans-unit") + root.findall(".//{*}unit")
    if not trans_units:
        trans_units = root.findall(".//trans-unit") + root.findall(".//unit")
    
    for tu in trans_units:
        tu_id = tu.get("id") or tu.get("resname") or (tu.get("translate") or "")
        source_node = tu.find(".//{*}source")
        if source_node is None:
            source_node = tu.find(".//source")
        target_node = tu.find(".//{*}target")
        if target_node is None:
            target_node = tu.find(".//target")
        src = safe_get_text(source_node)
        tgt = safe_get_text(target_node)
        tus.append({
            "id": tu_id,
            "src": src,
            "tgt": tgt,
            "target_node": target_node,
            "xml_node": tu,
        })
    
    logger.info(f"Parsed {len(tus)} translation units from {xliff_path}")
    return tree, tus


def is_human_translation_from_xliff_tu(tu_xml_node: etree._Element) -> bool:
    """
    Heuristically determine if translation is human-translated.
    
    Args:
        tu_xml_node: Translation unit XML node
    
    Returns:
        True if appears to be human translation, False otherwise
    """
    # Check notes
    notes = tu_xml_node.findall(".//{*}note") + tu_xml_node.findall(".//note")
    for n in notes:
        txt = safe_get_text(n).lower()
        if any(k in txt for k in ("machine", "mt", "automatic", "google", "deepl", 
                                  "nmt", "llm", "translated by", "aws", "azure")):
            return False
    
    # Check creation tool
    tool = (tu_xml_node.get("creationtool") or tu_xml_node.get("tool") or "")
    if tool:
        t = tool.lower()
        if any(tok in t for tok in ("mt", "machine", "google", "deepl", "nmt", 
                                    "translate", "llm")):
            return False
        else:
            return True
    
    # Default: treat ambiguous as NOT human
    return False


def add_tqe_props_to_tu(tu_node: etree._Element, props: Dict[str, str]):
    """
    Add TQE properties to translation unit.
    
    Args:
        tu_node: Translation unit XML node
        props: Dictionary of property name -> value
    """
    # Find or create prop-group
    pg = tu_node.find(".//{*}prop-group")
    if pg is None:
        pg = etree.SubElement(tu_node, "prop-group")
    
    # Add properties
    for k, v in props.items():
        p = etree.SubElement(pg, "prop")
        p.set("type", k)
        p.text = str(v)


def write_xliff(tree: etree._ElementTree, out_path: str):
    """
    Write XLIFF tree to file.
    
    Args:
        tree: XLIFF element tree
        out_path: Output file path
    """
    tree.write(out_path, encoding="utf-8", pretty_print=True, xml_declaration=True)
    logger.info(f"Wrote XLIFF to {out_path}")

"""
Metadata Writer

Writes TQE metadata and match rates to XLIFF using standard formats.
"""
import logging
from typing import Dict, Optional
from lxml import etree

logger = logging.getLogger(__name__)


class MetadataWriter:
    """
    Writes quality metadata to XLIFF translation units.
    
    Features:
    - Standard XLIFF 1.2 and 2.0+ formats
    - Match rate attributes
    - Quality warnings
    - TQE scores
    """
    
    @staticmethod
    def write_match_rate_1_2(tu_node: etree._Element, match_rate: float, 
                             match_type: str = "tm", origin: Optional[str] = None):
        """
        Write match rate in XLIFF 1.2 format.
        
        Args:
            tu_node: Translation unit XML node
            match_rate: Match rate (0-100)
            match_type: Match type
            origin: Optional origin string
        """
        # Find or create alt-trans
        alt_trans = tu_node.find(".//{*}alt-trans")
        if alt_trans is None:
            alt_trans = etree.SubElement(tu_node, "alt-trans")
        
        # Set match-quality (0-1 range in XLIFF 1.2)
        alt_trans.set("match-quality", f"{match_rate / 100.0:.4f}")
        
        # Set origin
        if origin is None:
            origin_map = {
                'tm': 'tm',
                'mt': 'mt',
                'exact': 'tm',
                'fuzzy': 'tm',
                'llm': 'mt'
            }
            origin = origin_map.get(match_type, 'mt')
        alt_trans.set("origin", origin)
        
        # Set state-qualifier for quality indication
        if match_rate >= 95:
            alt_trans.set("state-qualifier", "exact-match")
        elif match_rate >= 75:
            alt_trans.set("state-qualifier", "fuzzy-match")
        else:
            alt_trans.set("state-qualifier", "low-match")
    
    @staticmethod
    def write_match_rate_2_0(tu_node: etree._Element, match_rate: float,
                             match_type: str = "tm", origin: Optional[str] = None):
        """
        Write match rate in XLIFF 2.0+ format.
        
        Args:
            tu_node: Translation unit XML node
            match_rate: Match rate (0-100)
            match_type: Match type
            origin: Optional origin string
        """
        # Get namespace
        nsmap = tu_node.nsmap
        mtc_ns = nsmap.get('mtc', 'urn:oasis:names:tc:xliff:matches:2.0')
        
        # Create match element
        match_elem = etree.Element(f"{{{mtc_ns}}}match")
        
        # Set similarity (0-1 range)
        match_elem.set("similarity", f"{match_rate / 100.0:.4f}")
        
        # Set matchQuality (0-100 range)
        match_elem.set("matchQuality", f"{match_rate:.1f}")
        
        # Set matchSuitability
        if match_rate >= 95:
            suitability = "exact"
        elif match_rate >= 75:
            suitability = "fuzzy"
        else:
            suitability = "low"
        match_elem.set("matchSuitability", suitability)
        
        # Set type and origin
        if origin is None:
            origin_map = {
                'tm': 'tm',
                'mt': 'mt',
                'exact': 'tm',
                'fuzzy': 'tm',
                'llm': 'mt'
            }
            origin = origin_map.get(match_type, 'mt')
        
        match_elem.set("type", origin)
        match_elem.set("origin", origin)
        
        # Add to translation unit
        tu_node.append(match_elem)
    
    @staticmethod
    def write_quality_warning(tu_node: etree._Element, warning_message: str,
                             category: str = "quality"):
        """
        Write quality warning as note element.
        
        Args:
            tu_node: Translation unit XML node
            warning_message: Warning message
            category: Note category
        """
        note = etree.SubElement(tu_node, "note")
        note.set("category", category)
        note.set("type", "warning")
        note.text = warning_message
    
    @staticmethod
    def write_tqe_scores(tu_node: etree._Element, scores: Dict[str, float],
                        decision: str, hallucination: bool = False):
        """
        Write TQE scores to translation unit.
        
        Args:
            tu_node: Translation unit XML node
            scores: Dictionary of scores (accuracy, fluency, tone, weighted)
            decision: Decision string
            hallucination: Whether hallucination was detected
        """
        from shared.tqe.xliff_utils import add_tqe_props_to_tu
        
        props = {
            "tqe:accuracy": str(scores.get('accuracy', 0.0)),
            "tqe:fluency": str(scores.get('fluency', 0.0)),
            "tqe:tone": str(scores.get('tone', 0.0)),
            "tqe:weighted_score": str(scores.get('weighted', 0.0)),
            "tqe:decision": decision,
            "tqe:uqm_hallucination": str(hallucination)
        }
        
        add_tqe_props_to_tu(tu_node, props)

"""
XLIFF Processor

Handles XLIFF file processing with metadata preservation.
"""
import logging
from typing import Dict, List, Optional
from pathlib import Path
from lxml import etree

from shared.tqe.xliff_utils import parse_xliff, write_xliff, safe_get_text

logger = logging.getLogger(__name__)


class XLIFFProcessor:
    """
    Processes XLIFF files with metadata preservation.
    
    Features:
    - Parse XLIFF 1.2 and 2.0+
    - Preserve existing metadata
    - Write translations and quality scores
    - Handle tags and formatting
    """
    
    def __init__(self, xliff_path: Path):
        """
        Initialize XLIFFProcessor.
        
        Args:
            xliff_path: Path to XLIFF file
        """
        self.xliff_path = Path(xliff_path)
        self.tree = None
        self.tu_list = None
        self._parse()
    
    def _parse(self):
        """Parse XLIFF file."""
        try:
            self.tree, self.tu_list = parse_xliff(str(self.xliff_path))
            logger.info(f"Parsed {len(self.tu_list)} translation units")
        except Exception as e:
            logger.error(f"Error parsing XLIFF {self.xliff_path}: {e}")
            raise
    
    def get_segments(self) -> List[Dict]:
        """
        Get all translation segments.
        
        Returns:
            List of segment dictionaries with id, src, tgt, xml_node
        """
        return self.tu_list
    
    def update_translation(self, tu_id: str, translation: str, 
                          metadata: Optional[Dict[str, str]] = None):
        """
        Update translation for a translation unit.
        
        Args:
            tu_id: Translation unit ID
            translation: New translation text
            metadata: Optional metadata to add
        """
        # Find translation unit
        tu = next((t for t in self.tu_list if t['id'] == tu_id), None)
        if not tu:
            logger.warning(f"Translation unit {tu_id} not found")
            return
        
        xml_node = tu['xml_node']
        
        # Update target
        target_node = tu.get('target_node')
        if target_node is None:
            target_node = etree.SubElement(xml_node, "target")
        target_node.text = translation
        
        # Add metadata if provided
        if metadata:
            from shared.tqe.xliff_utils import add_tqe_props_to_tu
            add_tqe_props_to_tu(xml_node, metadata)
    
    def write_match_rate(self, tu_id: str, match_rate: float, match_type: str = "tm"):
        """
        Write match rate to translation unit using standard XLIFF format.
        
        Args:
            tu_id: Translation unit ID
            match_rate: Match rate (0-100)
            match_type: Match type ('tm', 'mt', 'exact', 'fuzzy', etc.)
        """
        tu = next((t for t in self.tu_list if t['id'] == tu_id), None)
        if not tu:
            return
        
        xml_node = tu['xml_node']
        root = self.tree.getroot()
        
        # Determine XLIFF version
        xliff_version = root.get('version', '2.0')
        
        if xliff_version.startswith('1.'):
            # XLIFF 1.2 format
            self._write_match_rate_1_2(xml_node, match_rate, match_type)
        else:
            # XLIFF 2.0+ format
            self._write_match_rate_2_0(xml_node, match_rate, match_type)
    
    def _write_match_rate_1_2(self, tu_node: etree._Element, match_rate: float, match_type: str):
        """Write match rate in XLIFF 1.2 format."""
        # Find or create alt-trans
        alt_trans = tu_node.find(".//{*}alt-trans")
        if alt_trans is None:
            alt_trans = etree.SubElement(tu_node, "alt-trans")
        
        # Set match-quality attribute
        alt_trans.set("match-quality", f"{match_rate:.1f}")
        
        # Set origin
        origin_map = {
            'tm': 'tm',
            'mt': 'mt',
            'exact': 'tm',
            'fuzzy': 'tm'
        }
        origin = origin_map.get(match_type, 'mt')
        alt_trans.set("origin", origin)
    
    def _write_match_rate_2_0(self, tu_node: etree._Element, match_rate: float, match_type: str):
        """Write match rate in XLIFF 2.0+ format."""
        # Find or create mtc:match element
        # XLIFF 2.0 uses Translation Candidates module
        nsmap = tu_node.nsmap
        mtc_ns = nsmap.get('mtc', 'urn:oasis:names:tc:xliff:matches:2.0')
        
        # Create match element
        match_elem = etree.Element(f"{{{mtc_ns}}}match")
        match_elem.set("similarity", f"{match_rate / 100.0:.4f}")
        match_elem.set("matchQuality", f"{match_rate:.1f}")
        
        # Set match suitability
        if match_rate >= 95:
            suitability = "exact"
        elif match_rate >= 75:
            suitability = "fuzzy"
        else:
            suitability = "low"
        match_elem.set("matchSuitability", suitability)
        
        # Set type and origin
        origin_map = {
            'tm': 'tm',
            'mt': 'mt',
            'exact': 'tm',
            'fuzzy': 'tm'
        }
        origin = origin_map.get(match_type, 'mt')
        match_elem.set("type", origin)
        match_elem.set("origin", origin)
        
        # Add to translation unit
        tu_node.append(match_elem)
    
    def write_quality_warning(self, tu_id: str, warning_message: str):
        """
        Write quality warning to translation unit.
        
        Args:
            tu_id: Translation unit ID
            warning_message: Warning message
        """
        tu = next((t for t in self.tu_list if t['id'] == tu_id), None)
        if not tu:
            return
        
        xml_node = tu['xml_node']
        
        # Add note with quality warning
        note = etree.SubElement(xml_node, "note")
        note.set("category", "quality")
        note.set("type", "warning")
        note.text = warning_message
    
    def save(self, output_path: Path):
        """
        Save processed XLIFF to file.
        
        Args:
            output_path: Output file path
        """
        write_xliff(self.tree, str(output_path))
        logger.info(f"Saved XLIFF to {output_path}")

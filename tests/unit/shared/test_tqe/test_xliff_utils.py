"""
Unit tests for XLIFF utilities.
"""
import pytest
from lxml import etree
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.tqe.xliff_utils import (
    safe_get_text, parse_xliff, is_human_translation_from_xliff_tu,
    add_tqe_props_to_tu, write_xliff
)


class TestXLIFFUtils:
    """Tests for XLIFF utilities."""
    
    def test_safe_get_text_with_text(self):
        """Test safe_get_text with node containing text."""
        node = etree.Element("test")
        node.text = "  test text  "
        
        result = safe_get_text(node)
        
        assert result == "test text"
    
    def test_safe_get_text_none(self):
        """Test safe_get_text with None node."""
        result = safe_get_text(None)
        
        assert result == ""
    
    def test_safe_get_text_empty(self):
        """Test safe_get_text with empty node."""
        node = etree.Element("test")
        
        result = safe_get_text(node)
        
        assert result == ""
    
    def test_parse_xliff_simple(self, sample_xliff_path):
        """Test parsing a simple XLIFF file."""
        if not sample_xliff_path.exists():
            pytest.skip(f"Test file not found: {sample_xliff_path}")
        
        tree, tus = parse_xliff(str(sample_xliff_path))
        
        assert tree is not None
        assert len(tus) > 0
        assert all('id' in tu for tu in tus)
        assert all('src' in tu for tu in tus)
    
    def test_is_human_translation_machine_note(self):
        """Test detecting machine translation from note."""
        tu = etree.Element("unit")
        note = etree.SubElement(tu, "note")
        note.text = "Translated by Google Translate"
        
        result = is_human_translation_from_xliff_tu(tu)
        
        assert result is False
    
    def test_is_human_translation_human_tool(self):
        """Test detecting human translation from tool."""
        tu = etree.Element("unit")
        tu.set("creationtool", "Trados Studio")
        
        result = is_human_translation_from_xliff_tu(tu)
        
        assert result is True
    
    def test_add_tqe_props_to_tu(self):
        """Test adding TQE properties to translation unit."""
        tu = etree.Element("unit")
        props = {
            "tqe:accuracy": "85.5",
            "tqe:fluency": "90.0"
        }
        
        add_tqe_props_to_tu(tu, props)
        
        # Check prop-group was created
        pg = tu.find(".//prop-group")
        assert pg is not None
        
        # Check properties were added
        prop_types = [p.get("type") for p in pg.findall(".//prop")]
        assert "tqe:accuracy" in prop_types
        assert "tqe:fluency" in prop_types
    
    def test_write_xliff(self, temp_dir):
        """Test writing XLIFF file."""
        # Create simple XLIFF tree
        root = etree.Element("xliff", version="2.0")
        file_elem = etree.SubElement(root, "file")
        unit = etree.SubElement(file_elem, "unit", id="test1")
        source = etree.SubElement(unit, "source")
        source.text = "Hello"
        
        tree = etree.ElementTree(root)
        out_path = temp_dir / "test.xlf"
        
        write_xliff(tree, str(out_path))
        
        assert out_path.exists()
        # Verify it's valid XML
        parsed = etree.parse(str(out_path))
        assert parsed is not None

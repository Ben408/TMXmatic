"""
Unit tests for metadata writer.
"""
import pytest
from lxml import etree
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.io.metadata_writer import MetadataWriter


class TestMetadataWriter:
    """Tests for MetadataWriter class."""
    
    def test_write_match_rate_1_2(self):
        """Test writing match rate in XLIFF 1.2 format."""
        tu = etree.Element("trans-unit", id="test1")
        
        MetadataWriter.write_match_rate_1_2(tu, 85.5, "fuzzy")
        
        alt_trans = tu.find(".//alt-trans")
        assert alt_trans is not None
        assert alt_trans.get("match-quality") is not None
        assert alt_trans.get("origin") is not None
    
    def test_write_match_rate_2_0(self):
        """Test writing match rate in XLIFF 2.0 format."""
        root = etree.Element("xliff", version="2.0")
        root.set("{http://www.w3.org/XML/1998/namespace}ns", 
                "urn:oasis:names:tc:xliff:document:2.0")
        tu = etree.SubElement(root, "unit", id="test1")
        
        MetadataWriter.write_match_rate_2_0(tu, 85.5, "fuzzy")
        
        # Check match element was created
        matches = tu.findall(".//{urn:oasis:names:tc:xliff:matches:2.0}match")
        if not matches:
            # Try without namespace
            matches = tu.findall(".//match")
        assert len(matches) > 0
    
    def test_write_quality_warning(self):
        """Test writing quality warning."""
        tu = etree.Element("unit", id="test1")
        
        MetadataWriter.write_quality_warning(tu, "Low quality detected")
        
        notes = tu.findall(".//note")
        assert len(notes) > 0
        assert any(n.get("category") == "quality" for n in notes)
    
    def test_write_tqe_scores(self):
        """Test writing TQE scores."""
        tu = etree.Element("unit", id="test1")
        
        scores = {
            'accuracy': 85.0,
            'fluency': 90.0,
            'tone': 80.0,
            'weighted': 85.5
        }
        
        MetadataWriter.write_tqe_scores(tu, scores, "accept_auto", hallucination=False)
        
        # Check props were added
        prop_group = tu.find(".//prop-group")
        assert prop_group is not None
        props = prop_group.findall(".//prop")
        prop_types = [p.get("type") for p in props]
        assert "tqe:accuracy" in prop_types
        assert "tqe:decision" in prop_types

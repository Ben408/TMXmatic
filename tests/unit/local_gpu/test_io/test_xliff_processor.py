"""
Unit tests for XLIFF processor.
"""
import pytest
from lxml import etree
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.io.xliff_processor import XLIFFProcessor


class TestXLIFFProcessor:
    """Tests for XLIFFProcessor class."""
    
    def test_xliff_processor_initialization(self, sample_xliff_path):
        """Test XLIFFProcessor initialization."""
        if not sample_xliff_path.exists():
            pytest.skip(f"Test file not found: {sample_xliff_path}")
        
        processor = XLIFFProcessor(sample_xliff_path)
        
        assert processor.tree is not None
        assert processor.tu_list is not None
        assert len(processor.tu_list) > 0
    
    def test_get_segments(self, sample_xliff_path):
        """Test getting all segments."""
        if not sample_xliff_path.exists():
            pytest.skip(f"Test file not found: {sample_xliff_path}")
        
        processor = XLIFFProcessor(sample_xliff_path)
        segments = processor.get_segments()
        
        assert len(segments) > 0
        assert all('id' in seg for seg in segments)
        assert all('src' in seg for seg in segments)
    
    def test_update_translation(self, sample_xliff_path, temp_dir):
        """Test updating translation."""
        if not sample_xliff_path.exists():
            pytest.skip(f"Test file not found: {sample_xliff_path}")
        
        processor = XLIFFProcessor(sample_xliff_path)
        segments = processor.get_segments()
        
        if segments:
            tu_id = segments[0]['id']
            processor.update_translation(tu_id, "New translation")
            
            # Verify update
            updated_seg = next(s for s in segments if s['id'] == tu_id)
            target_node = updated_seg.get('target_node')
            if target_node is not None:
                assert target_node.text == "New translation"
    
    def test_write_match_rate_1_2(self, temp_dir):
        """Test writing match rate in XLIFF 1.2 format."""
        # Create simple XLIFF 1.2
        root = etree.Element("xliff", version="1.2")
        file_elem = etree.SubElement(root, "file")
        body = etree.SubElement(file_elem, "body")
        tu = etree.SubElement(body, "trans-unit", id="test1")
        source = etree.SubElement(tu, "source")
        source.text = "Hello"
        
        tree = etree.ElementTree(root)
        xliff_path = temp_dir / "test.xlf"
        tree.write(str(xliff_path), encoding="utf-8", xml_declaration=True)
        
        processor = XLIFFProcessor(xliff_path)
        processor.write_match_rate("test1", 85.5, "fuzzy")
        
        # Verify match rate was written
        tu_node = next(t['xml_node'] for t in processor.tu_list if t['id'] == 'test1')
        alt_trans = tu_node.find(".//alt-trans")
        assert alt_trans is not None
        assert alt_trans.get("match-quality") is not None
    
    def test_write_quality_warning(self, sample_xliff_path):
        """Test writing quality warning."""
        if not sample_xliff_path.exists():
            pytest.skip(f"Test file not found: {sample_xliff_path}")
        
        processor = XLIFFProcessor(sample_xliff_path)
        segments = processor.get_segments()
        
        if segments:
            tu_id = segments[0]['id']
            processor.write_quality_warning(tu_id, "Low quality score")
            
            # Verify warning was written
            tu = next(t for t in segments if t['id'] == tu_id)
            notes = tu['xml_node'].findall(".//note")
            assert any(n.get("category") == "quality" for n in notes)

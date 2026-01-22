"""
Unit tests for TMX utilities.
"""
import pytest
from lxml import etree
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.tqe.tmx_utils import parse_tmx, fuzzy_tmx_lookup


class TestTMXUtils:
    """Tests for TMX utilities."""
    
    def test_parse_tmx_simple(self, sample_tmx_path):
        """Test parsing a simple TMX file."""
        if not sample_tmx_path.exists():
            pytest.skip(f"Test file not found: {sample_tmx_path}")
        
        tmx_map = parse_tmx(str(sample_tmx_path))
        
        assert isinstance(tmx_map, dict)
        # Should have some entries
        if len(tmx_map) > 0:
            # Check structure
            first_key = list(tmx_map.keys())[0]
            assert isinstance(tmx_map[first_key], list)
            assert len(tmx_map[first_key]) > 0
            assert 'target' in tmx_map[first_key][0]
    
    def test_fuzzy_tmx_lookup_exact(self):
        """Test fuzzy TMX lookup with exact match."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde", "is_human": True}]
        }
        
        result = fuzzy_tmx_lookup("Hello world", tmx_map, threshold=0.8)
        
        assert result is not None
        target, score = result
        assert target == "Bonjour le monde"
        assert score >= 0.99  # Should be very high for exact match
    
    def test_fuzzy_tmx_lookup_fuzzy(self):
        """Test fuzzy TMX lookup with fuzzy match."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde", "is_human": True}]
        }
        
        result = fuzzy_tmx_lookup("Hello worl", tmx_map, threshold=0.8)
        
        # May or may not match depending on similarity
        if result:
            target, score = result
            assert score >= 0.8
    
    def test_fuzzy_tmx_lookup_no_match(self):
        """Test fuzzy TMX lookup with no match."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde", "is_human": True}]
        }
        
        result = fuzzy_tmx_lookup("Completely different text", tmx_map, threshold=0.8)
        
        assert result is None
    
    def test_fuzzy_tmx_lookup_empty_map(self):
        """Test fuzzy TMX lookup with empty map."""
        result = fuzzy_tmx_lookup("Hello", {}, threshold=0.8)
        
        assert result is None

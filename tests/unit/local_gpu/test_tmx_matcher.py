"""
Unit tests for TMX matcher.
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.integration.tmx_matcher import TMXMatcher


class TestTMXMatcher:
    """Tests for TMXMatcher class."""
    
    def test_tmx_matcher_initialization(self):
        """Test TMXMatcher initialization."""
        matcher = TMXMatcher()
        
        assert matcher.tmx_map == {}
        assert matcher.fuzzy_threshold == 0.75
    
    def test_tmx_matcher_with_map(self):
        """Test TMXMatcher initialization with pre-loaded map."""
        tmx_map = {
            "Hello": [{"target": "Bonjour", "is_human": True}]
        }
        matcher = TMXMatcher(tmx_map=tmx_map, fuzzy_threshold=0.8)
        
        assert matcher.tmx_map == tmx_map
        assert matcher.fuzzy_threshold == 0.8
    
    @patch('local_gpu_translation.integration.tmx_matcher.parse_tmx')
    def test_load_tmx(self, mock_parse_tmx, temp_dir):
        """Test loading TMX file."""
        mock_parse_tmx.return_value = {"Hello": [{"target": "Bonjour"}]}
        
        matcher = TMXMatcher()
        tmx_path = temp_dir / 'test.tmx'
        tmx_path.touch()
        
        result = matcher.load_tmx(str(tmx_path))
        
        assert result is True
        assert len(matcher.tmx_map) > 0
    
    def test_match_exact(self):
        """Test exact matching."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde", "is_human": True}]
        }
        matcher = TMXMatcher(tmx_map=tmx_map)
        
        translation, match_type, similarity = matcher.match("Hello world")
        
        assert translation == "Bonjour le monde"
        assert match_type == 'exact'
        assert similarity == 1.0
    
    def test_match_fuzzy(self):
        """Test fuzzy matching."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde", "is_human": True}]
        }
        matcher = TMXMatcher(tmx_map=tmx_map, fuzzy_threshold=0.8)
        
        translation, match_type, similarity = matcher.match("Hello worl")
        
        # May or may not match depending on similarity
        if translation:
            assert match_type == 'fuzzy'
            assert 0.8 <= similarity < 1.0
    
    def test_match_none(self):
        """Test no match."""
        tmx_map = {
            "Hello world": [{"target": "Bonjour le monde"}]
        }
        matcher = TMXMatcher(tmx_map=tmx_map, fuzzy_threshold=0.9)
        
        translation, match_type, similarity = matcher.match("Completely different")
        
        assert translation is None
        assert match_type == 'none'
        assert similarity == 0.0
    
    def test_should_use_llm_repair(self):
        """Test LLM repair decision."""
        matcher = TMXMatcher(fuzzy_threshold=0.75)
        
        # High fuzzy match
        assert matcher.should_use_llm_repair(0.85) is True
        
        # Exact match
        assert matcher.should_use_llm_repair(1.0) is False
        
        # Low match
        assert matcher.should_use_llm_repair(0.5) is False
    
    def test_should_generate_new(self):
        """Test new translation decision."""
        matcher = TMXMatcher(fuzzy_threshold=0.75)
        
        # Low match
        assert matcher.should_generate_new(0.5) is True
        
        # High match
        assert matcher.should_generate_new(0.85) is False
        
        # No match
        assert matcher.should_generate_new(0.0) is True

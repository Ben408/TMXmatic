"""
Unit tests for term extractor.
"""
import pytest
from pathlib import Path
import sys
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.llm_translation.term_extractor import TermExtractor


class TestTermExtractor:
    """Tests for TermExtractor class."""
    
    def test_term_extractor_initialization(self):
        """Test TermExtractor initialization."""
        extractor = TermExtractor()
        
        assert extractor.term_db == {}
    
    def test_term_extractor_with_db(self):
        """Test TermExtractor initialization with pre-loaded DB."""
        db = {('en', 'fr'): [{'src': 'hello', 'tgt': 'bonjour', 'approved': True}]}
        extractor = TermExtractor(term_db=db)
        
        assert extractor.term_db == db
    
    @patch('local_gpu_translation.llm_translation.term_extractor.load_terms_tbx')
    def test_load_termbase_tbx(self, mock_load_tbx, temp_dir):
        """Test loading TBX termbase."""
        mock_load_tbx.return_value = {('en', 'fr'): [{'src': 'test', 'tgt': 'test_fr'}]}
        
        extractor = TermExtractor()
        tbx_path = temp_dir / 'test.tbx'
        tbx_path.touch()
        
        result = extractor.load_termbase(tbx_path, 'en', 'fr')
        
        assert result is True
        assert len(extractor.term_db) > 0
    
    @patch('local_gpu_translation.llm_translation.term_extractor.load_terms_csv')
    def test_load_termbase_csv(self, mock_load_csv, temp_dir):
        """Test loading CSV termbase."""
        mock_load_csv.return_value = {('en', 'fr'): [{'src': 'test', 'tgt': 'test_fr'}]}
        
        extractor = TermExtractor()
        csv_path = temp_dir / 'test.csv'
        csv_path.touch()
        
        result = extractor.load_termbase(csv_path, 'en', 'fr')
        
        assert result is True
    
    def test_extract_terms_exact_match(self):
        """Test extracting terms with exact match."""
        db = {
            ('en', 'fr'): [
                {'src': 'hello', 'tgt': 'bonjour', 'approved': True},
                {'src': 'world', 'tgt': 'monde', 'approved': True}
            ]
        }
        extractor = TermExtractor(term_db=db)
        
        terms = extractor.extract_terms_for_segment("Hello world", 'en', 'fr')
        
        assert len(terms) > 0
        assert any(t['src'].lower() == 'hello' for t in terms)
    
    def test_extract_terms_max_limit(self):
        """Test that term extraction respects max_terms limit."""
        db = {
            ('en', 'fr'): [
                {'src': f'term{i}', 'tgt': f'terme{i}', 'approved': True}
                for i in range(20)
            ]
        }
        extractor = TermExtractor(term_db=db)
        
        terms = extractor.extract_terms_for_segment(
            " ".join([f'term{i}' for i in range(20)]),
            'en', 'fr', max_terms=5
        )
        
        assert len(terms) <= 5
    
    def test_format_terms_for_prompt(self):
        """Test formatting terms for prompt."""
        extractor = TermExtractor()
        terms = [
            {'src': 'hello', 'tgt': 'bonjour'},
            {'src': 'world', 'tgt': 'monde'}
        ]
        
        formatted = extractor.format_terms_for_prompt(terms)
        
        assert 'hello' in formatted
        assert 'bonjour' in formatted
        assert 'world' in formatted
        assert 'monde' in formatted
    
    def test_format_terms_empty(self):
        """Test formatting empty terms list."""
        extractor = TermExtractor()
        
        formatted = extractor.format_terms_for_prompt([])
        
        assert formatted == "None"

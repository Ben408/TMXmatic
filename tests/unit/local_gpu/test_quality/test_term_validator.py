"""
Unit tests for term validator.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.quality.term_validator import TermValidator


class TestTermValidator:
    """Tests for TermValidator class."""
    
    def test_term_validator_initialization(self):
        """Test TermValidator initialization."""
        validator = TermValidator()
        
        assert validator.term_db == {}
        assert validator.enforcement_policy == "soft"
    
    def test_term_validator_with_db(self):
        """Test TermValidator initialization with term database."""
        db = {
            ('en', 'fr'): [
                {'src': 'hello', 'tgt': 'bonjour', 'approved': True},
                {'src': 'world', 'tgt': 'monde', 'approved': True}
            ]
        }
        validator = TermValidator(term_db=db, enforcement_policy='strict')
        
        assert validator.term_db == db
        assert validator.enforcement_policy == 'strict'
    
    def test_validate_candidate_all_terms_used(self):
        """Test validation when all terms are used."""
        db = {
            ('en', 'fr'): [
                {'src': 'hello', 'tgt': 'bonjour', 'approved': True},
                {'src': 'world', 'tgt': 'monde', 'approved': True}
            ]
        }
        validator = TermValidator(term_db=db)
        
        result = validator.validate_candidate(
            "bonjour monde", "hello world", "en", "fr"
        )
        
        assert result['term_match_score'] == 100.0
        assert len(result['used_terms']) == 2
        assert len(result['missing_terms']) == 0
    
    def test_validate_candidate_missing_terms(self):
        """Test validation when terms are missing."""
        db = {
            ('en', 'fr'): [
                {'src': 'hello', 'tgt': 'bonjour', 'approved': True},
                {'src': 'world', 'tgt': 'monde', 'approved': True}
            ]
        }
        validator = TermValidator(term_db=db)
        
        result = validator.validate_candidate(
            "bonjour", "hello world", "en", "fr"
        )
        
        assert result['term_match_score'] < 100.0
        assert len(result['missing_terms']) > 0
    
    def test_validate_candidate_no_terms(self):
        """Test validation when no terms in database."""
        validator = TermValidator()
        
        result = validator.validate_candidate(
            "translation", "source", "en", "fr"
        )
        
        assert result['term_match_score'] == 100.0
        assert len(result['missing_terms']) == 0
    
    def test_calculate_term_penalty_soft(self):
        """Test term penalty calculation with soft policy."""
        validator = TermValidator(enforcement_policy='soft')
        validation_result = {
            'missing_terms': [{'src': 'hello'}],
            'violations': []
        }
        
        adjusted = validator.calculate_term_penalty(validation_result, 100.0, 15.0)
        
        assert adjusted == 85.0  # 100 - 15
    
    def test_calculate_term_penalty_strict(self):
        """Test term penalty calculation with strict policy."""
        validator = TermValidator(enforcement_policy='strict')
        validation_result = {
            'missing_terms': [{'src': 'hello'}],
            'violations': ['Missing approved term: hello']
        }
        
        adjusted = validator.calculate_term_penalty(validation_result, 100.0, 15.0)
        
        assert adjusted == 0.0  # Strict policy fails on violations
    
    def test_calculate_term_penalty_no_missing(self):
        """Test term penalty calculation with no missing terms."""
        validator = TermValidator()
        validation_result = {
            'missing_terms': [],
            'violations': []
        }
        
        adjusted = validator.calculate_term_penalty(validation_result, 100.0, 15.0)
        
        assert adjusted == 100.0  # No penalty

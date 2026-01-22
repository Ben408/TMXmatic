"""
Term Validator

Validates term usage in translation candidates.
"""
import logging
from typing import List, Dict, Optional, Tuple
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)


class TermValidator:
    """
    Validates term usage in translation candidates.
    
    Features:
    - Check for approved term usage
    - Detect missing required terms
    - Calculate term-match scores
    - Support strict/soft enforcement policies
    """
    
    def __init__(self, term_db: Optional[Dict] = None, 
                 enforcement_policy: str = "soft"):
        """
        Initialize TermValidator.
        
        Args:
            term_db: Term database dictionary
            enforcement_policy: 'strict' or 'soft'
        """
        self.term_db = term_db or {}
        self.enforcement_policy = enforcement_policy
    
    def validate_candidate(self, candidate: str, source_text: str,
                           src_lang: str, tgt_lang: str) -> Dict:
        """
        Validate term usage in a translation candidate.
        
        Args:
            candidate: Translation candidate
            source_text: Source text
            src_lang: Source language code
            tgt_lang: Target language code
        
        Returns:
            Dictionary with validation results:
            {
                'term_match_score': float (0-100),
                'missing_terms': List[str],
                'used_terms': List[str],
                'violations': List[str]
            }
        """
        key = (src_lang, tgt_lang)
        if key not in self.term_db:
            return {
                'term_match_score': 100.0,  # No terms to validate
                'missing_terms': [],
                'used_terms': [],
                'violations': []
            }
        
        terms = self.term_db[key]
        candidate_lower = candidate.lower()
        source_lower = source_text.lower()
        
        used_terms = []
        missing_terms = []
        violations = []
        
        # Check each term
        for term_entry in terms:
            src_term = term_entry.get('src', '').lower()
            tgt_term = term_entry.get('tgt', '').lower()
            approved = term_entry.get('approved', True)
            
            # Check if source term appears in source text
            if src_term in source_lower:
                # Term should appear in candidate
                if tgt_term in candidate_lower:
                    used_terms.append(term_entry)
                else:
                    missing_terms.append(term_entry)
                    if approved and self.enforcement_policy == 'strict':
                        violations.append(f"Missing approved term: {term_entry.get('src')}")
        
        # Calculate term match score
        total_terms = len([t for t in terms if t.get('src', '').lower() in source_lower])
        if total_terms == 0:
            term_match_score = 100.0
        else:
            term_match_score = (len(used_terms) / total_terms) * 100.0
        
        return {
            'term_match_score': term_match_score,
            'missing_terms': missing_terms,
            'used_terms': used_terms,
            'violations': violations
        }
    
    def calculate_term_penalty(self, validation_result: Dict, 
                               base_score: float, penalty_per_missing: float = 15.0) -> float:
        """
        Calculate penalty for missing terms.
        
        Args:
            validation_result: Result from validate_candidate
            base_score: Base quality score
            penalty_per_missing: Penalty per missing term
        
        Returns:
            Adjusted score after term penalty
        """
        missing_count = len(validation_result.get('missing_terms', []))
        penalty = missing_count * penalty_per_missing
        
        if self.enforcement_policy == 'strict':
            # Strict: Fail if any missing approved terms
            if validation_result.get('violations'):
                return 0.0
        
        return max(0.0, base_score - penalty)

"""
Scoring Aggregator

Aggregates multiple quality scores into final decision.
"""
import logging
from typing import Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class ScoringAggregator:
    """
    Aggregates quality scores and makes decisions.
    
    Features:
    - Weighted score combination
    - Profile-based thresholds
    - Decision buckets
    - Term validation integration
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None,
                 thresholds: Optional[Dict[str, float]] = None):
        """
        Initialize ScoringAggregator.
        
        Args:
            weights: Dictionary of metric weights
            thresholds: Dictionary of decision thresholds
        """
        self.weights = weights or {
            'accuracy': 0.6,
            'fluency': 0.25,
            'tone': 0.15,
            'term_match': 0.1
        }
        self.thresholds = thresholds or {
            'accept_auto': 85.0,
            'accept_with_review': 70.0,
            'needs_human_revision': 70.0
        }
    
    def aggregate(self, accuracy: float, fluency: float, tone: float,
                  term_match: float = 100.0, hallucination: bool = False,
                  term_violations: bool = False) -> Tuple[float, str]:
        """
        Aggregate scores into weighted score and decision.
        
        Args:
            accuracy: Accuracy score (0-100)
            fluency: Fluency score (0-100)
            tone: Tone score (0-100)
            term_match: Term match score (0-100)
            hallucination: Whether hallucination detected
            term_violations: Whether term violations exist
        
        Returns:
            Tuple of (weighted_score, decision)
        """
        # Apply weights
        weighted = (
            self.weights['accuracy'] * accuracy +
            self.weights['fluency'] * fluency +
            self.weights['tone'] * tone +
            self.weights['term_match'] * term_match
        )
        
        # Apply penalties
        if hallucination:
            weighted = weighted * 0.25  # Severe penalty for hallucination
        
        if term_violations:
            # Additional penalty for term violations
            weighted = weighted * 0.85
        
        # Make decision
        if hallucination or term_violations:
            decision = "needs_human_revision"
        elif weighted >= self.thresholds['accept_auto']:
            decision = "accept_auto"
        elif weighted >= self.thresholds['accept_with_review']:
            decision = "accept_with_review"
        else:
            decision = "needs_human_revision"
        
        return weighted, decision
    
    def calculate_match_rate_equivalent(self, weighted_score: float, 
                                       match_type: str) -> float:
        """
        Calculate TMS-compatible match rate equivalent.
        
        Args:
            weighted_score: Weighted quality score (0-100)
            match_type: Match type ('exact', 'fuzzy', 'new', etc.)
        
        Returns:
            Equivalent match rate (0-100) for TMS compatibility
        """
        # Map quality score to match rate
        # High quality scores map to high match rates
        if match_type == 'exact':
            return 100.0
        elif match_type == 'fuzzy_repair':
            # Fuzzy repairs: 75-99% range
            return min(99.0, max(75.0, weighted_score))
        else:
            # New translations: 0-85% range
            return min(85.0, max(0.0, weighted_score * 0.85))

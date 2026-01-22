"""
Unit tests for scoring aggregator.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.quality.scoring_aggregator import ScoringAggregator


class TestScoringAggregator:
    """Tests for ScoringAggregator class."""
    
    def test_scoring_aggregator_initialization(self):
        """Test ScoringAggregator initialization."""
        aggregator = ScoringAggregator()
        
        assert aggregator.weights['accuracy'] == 0.6
        assert aggregator.weights['fluency'] == 0.25
        assert aggregator.thresholds['accept_auto'] == 85.0
    
    def test_scoring_aggregator_custom_weights(self):
        """Test ScoringAggregator with custom weights."""
        weights = {'accuracy': 0.5, 'fluency': 0.3, 'tone': 0.2, 'term_match': 0.1}
        aggregator = ScoringAggregator(weights=weights)
        
        assert aggregator.weights == weights
    
    def test_aggregate_high_scores(self):
        """Test aggregation with high scores."""
        aggregator = ScoringAggregator()
        
        weighted, decision = aggregator.aggregate(
            accuracy=90.0, fluency=85.0, tone=80.0, term_match=100.0
        )
        
        assert weighted >= 85.0
        assert decision == "accept_auto"
    
    def test_aggregate_low_scores(self):
        """Test aggregation with low scores."""
        aggregator = ScoringAggregator()
        
        weighted, decision = aggregator.aggregate(
            accuracy=50.0, fluency=45.0, tone=40.0, term_match=100.0
        )
        
        assert weighted < 70.0
        assert decision == "needs_human_revision"
    
    def test_aggregate_with_hallucination(self):
        """Test aggregation with hallucination detected."""
        aggregator = ScoringAggregator()
        
        weighted, decision = aggregator.aggregate(
            accuracy=90.0, fluency=85.0, tone=80.0,
            hallucination=True
        )
        
        assert decision == "needs_human_revision"
        assert weighted < 90.0  # Should be penalized
    
    def test_aggregate_with_term_violations(self):
        """Test aggregation with term violations."""
        aggregator = ScoringAggregator()
        
        weighted, decision = aggregator.aggregate(
            accuracy=90.0, fluency=85.0, tone=80.0,
            term_violations=True
        )
        
        assert decision == "needs_human_revision"
        assert weighted < 90.0  # Should be penalized
    
    def test_calculate_match_rate_exact(self):
        """Test match rate calculation for exact match."""
        aggregator = ScoringAggregator()
        
        match_rate = aggregator.calculate_match_rate_equivalent(95.0, 'exact')
        
        assert match_rate == 100.0
    
    def test_calculate_match_rate_fuzzy(self):
        """Test match rate calculation for fuzzy match."""
        aggregator = ScoringAggregator()
        
        match_rate = aggregator.calculate_match_rate_equivalent(85.0, 'fuzzy_repair')
        
        assert 75.0 <= match_rate <= 99.0
    
    def test_calculate_match_rate_new(self):
        """Test match rate calculation for new translation."""
        aggregator = ScoringAggregator()
        
        match_rate = aggregator.calculate_match_rate_equivalent(80.0, 'new')
        
        assert 0.0 <= match_rate <= 85.0

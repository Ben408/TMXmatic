"""
Unit tests for TQE scoring functions.
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.tqe.scoring import (
    compute_accuracy_with_reference_bertscore,
    compute_accuracy_without_reference_sbert,
    compute_fluency_perplexity,
    compute_tone_score,
    aggregate_scores,
    normalize_comet_score
)


class TestScoringFunctions:
    """Tests for scoring functions."""
    
    def test_normalize_comet_score(self):
        """Test COMET score normalization."""
        # Test normal range
        score = normalize_comet_score(0.5, raw_min=-1.0, raw_max=1.0)
        assert 0 <= score <= 100
        
        # Test minimum
        score = normalize_comet_score(-1.0, raw_min=-1.0, raw_max=1.0)
        assert score == 0.0
        
        # Test maximum
        score = normalize_comet_score(1.0, raw_min=-1.0, raw_max=1.0)
        assert score == 100.0
    
    def test_aggregate_scores_high(self):
        """Test score aggregation with high scores."""
        weighted, decision = aggregate_scores(90.0, 85.0, 80.0, uq_halluc=False)
        
        assert weighted > 0
        assert decision in ["accept_auto", "accept_with_review", "needs_human_revision"]
        assert weighted >= 85.0  # Should be high
    
    def test_aggregate_scores_low(self):
        """Test score aggregation with low scores."""
        weighted, decision = aggregate_scores(50.0, 45.0, 40.0, uq_halluc=False)
        
        assert weighted > 0
        assert decision == "needs_human_revision"
    
    def test_aggregate_scores_hallucination(self):
        """Test score aggregation with hallucination."""
        weighted, decision = aggregate_scores(90.0, 85.0, 80.0, uq_halluc=True)
        
        assert decision == "needs_human_revision"
    
    def test_aggregate_scores_custom_weights(self):
        """Test score aggregation with custom weights."""
        weighted, decision = aggregate_scores(
            80.0, 70.0, 60.0,
            weights=(0.5, 0.3, 0.2)
        )
        
        assert weighted > 0
        # Weighted should reflect custom weights
        expected = 0.5 * 80.0 + 0.3 * 70.0 + 0.2 * 60.0
        assert abs(weighted - expected) < 0.1
    
    @patch('shared.tqe.scoring.BERTSCORE_AVAILABLE', False)
    @patch('shared.tqe.scoring.SBERT_AVAILABLE', False)
    def test_compute_accuracy_no_libs(self):
        """Test accuracy computation when no libraries available."""
        score = compute_accuracy_with_reference_bertscore("test", "test", "en")
        
        assert score == 50.0  # Default fallback
    
    @patch('shared.tqe.scoring.SBERT_AVAILABLE', False)
    def test_compute_accuracy_no_ref_no_libs(self):
        """Test accuracy computation without reference when no libraries available."""
        score = compute_accuracy_without_reference_sbert("source", "candidate")
        
        assert score == 50.0  # Default fallback

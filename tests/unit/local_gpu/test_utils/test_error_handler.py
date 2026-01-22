"""
Unit tests for error handler.
"""
import pytest
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.utils.error_handler import (
    ErrorHandler, TranslationError, ModelLoadError, SegmentProcessingError
)


class TestErrorHandler:
    """Tests for ErrorHandler class."""
    
    def test_error_handler_initialization(self):
        """Test ErrorHandler initialization."""
        handler = ErrorHandler()
        
        assert handler.save_partial_on_error is True
        assert len(handler.errors) == 0
    
    def test_handle_segment_error(self):
        """Test handling segment error."""
        handler = ErrorHandler()
        error = ValueError("Test error")
        
        result = handler.handle_segment_error("tu1", error)
        
        assert result['segment_id'] == "tu1"
        assert result['error_type'] == "ValueError"
        assert len(handler.errors) == 1
    
    def test_handle_batch_error(self):
        """Test handling batch error."""
        handler = ErrorHandler()
        error = RuntimeError("Batch error")
        batch_info = {'batch_num': 1, 'size': 50}
        
        result = handler.handle_batch_error(batch_info, error)
        
        assert result['batch'] == batch_info
        assert result['error_type'] == "RuntimeError"
        assert len(handler.errors) == 1
    
    def test_should_save_partial_high_error_rate(self):
        """Test partial save decision with high error rate."""
        handler = ErrorHandler(save_partial_on_error=True)
        
        result = handler.should_save_partial(0.6, threshold=0.5)
        
        assert result is True
    
    def test_should_save_partial_low_error_rate(self):
        """Test partial save decision with low error rate."""
        handler = ErrorHandler(save_partial_on_error=True)
        
        result = handler.should_save_partial(0.3, threshold=0.5)
        
        assert result is False
    
    def test_get_error_summary(self):
        """Test getting error summary."""
        handler = ErrorHandler()
        handler.handle_segment_error("tu1", ValueError("Error 1"))
        handler.handle_segment_error("tu2", ConnectionError("Error 2"))
        
        summary = handler.get_error_summary()
        
        assert summary['total_errors'] == 2
        assert 'retryable_errors' in summary
        assert 'fatal_errors' in summary
    
    def test_clear(self):
        """Test clearing errors."""
        handler = ErrorHandler()
        handler.handle_segment_error("tu1", ValueError("Error"))
        
        assert len(handler.errors) == 1
        
        handler.clear()
        
        assert len(handler.errors) == 0

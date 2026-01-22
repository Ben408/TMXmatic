"""
Error Handler

Enhanced error handling for translation workflows.
"""
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from shared.utils.error_recovery import retry_on_error

logger = logging.getLogger(__name__)


class TranslationError(Exception):
    """Base exception for translation errors."""
    pass


class ModelLoadError(TranslationError):
    """Error loading model."""
    pass


class GPUError(TranslationError):
    """GPU-related error."""
    pass


class SegmentProcessingError(TranslationError):
    """Error processing a single segment."""
    def __init__(self, segment_id: str, message: str, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.segment_id = segment_id
        self.original_error = original_error


class ErrorHandler:
    """
    Enhanced error handler for translation workflows.
    
    Features:
    - Error classification
    - Retry logic
    - Partial result saving
    - Error reporting
    """
    
    def __init__(self, save_partial_on_error: bool = True):
        """
        Initialize ErrorHandler.
        
        Args:
            save_partial_on_error: Whether to save partial results on error
        """
        self.save_partial_on_error = save_partial_on_error
        self.errors = []
        self.warnings = []
    
    def handle_segment_error(self, segment_id: str, error: Exception,
                            context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Handle error during segment processing.
        
        Args:
            segment_id: Translation unit ID
            error: Exception that occurred
            context: Optional context information
        
        Returns:
            Dictionary with error information
        """
        # Determine if error is retryable
        retryable = isinstance(error, (ConnectionError, TimeoutError, OSError))
        
        error_info = {
            'segment_id': segment_id,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'retryable': retryable,
            'context': context or {}
        }
        
        self.errors.append(error_info)
        
        # Log based on severity
        if retryable:
            logger.warning(f"Retryable error in segment {segment_id}: {error}")
        else:
            logger.error(f"Error in segment {segment_id}: {error}")
        
        return error_info
    
    def handle_batch_error(self, batch_info: Dict[str, Any], 
                          error: Exception) -> Dict[str, Any]:
        """
        Handle error during batch processing.
        
        Args:
            batch_info: Batch information
            error: Exception that occurred
        
        Returns:
            Dictionary with error information
        """
        retryable = isinstance(error, (ConnectionError, TimeoutError, OSError))
        
        error_info = {
            'batch': batch_info,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'retryable': retryable
        }
        
        self.errors.append(error_info)
        logger.error(f"Error in batch processing: {error}")
        
        return error_info
    
    def should_save_partial(self, error_rate: float, threshold: float = 0.5) -> bool:
        """
        Determine if partial results should be saved.
        
        Args:
            error_rate: Current error rate (0-1)
            threshold: Threshold for saving partial results
        
        Returns:
            True if partial results should be saved
        """
        return self.save_partial_on_error and error_rate >= threshold
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of all errors.
        
        Returns:
            Dictionary with error summary
        """
        retryable_count = sum(1 for e in self.errors if e.get('retryable', False))
        fatal_count = len(self.errors) - retryable_count
        
        return {
            'total_errors': len(self.errors),
            'retryable_errors': retryable_count,
            'fatal_errors': fatal_count,
            'warnings': len(self.warnings),
            'errors': self.errors[:10]  # First 10 errors
        }
    
    def clear(self):
        """Clear all errors and warnings."""
        self.errors.clear()
        self.warnings.clear()

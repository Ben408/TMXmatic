"""
Error Recovery Utilities

Provides common error recovery patterns and retry logic.
"""
import logging
import time
from typing import Callable, Optional, Type, Tuple, Any
from functools import wraps

logger = logging.getLogger(__name__)


class ErrorClassifier:
    """Classifies errors for recovery strategies."""
    
    TRANSIENT_ERRORS = (
        ConnectionError,
        TimeoutError,
        OSError,  # Includes network errors
    )
    
    RESOURCE_ERRORS = (
        MemoryError,
        RuntimeError,  # May include GPU OOM
    )
    
    PERMANENT_ERRORS = (
        ValueError,
        TypeError,
        AttributeError,
        KeyError,
    )
    
    @classmethod
    def is_transient(cls, error: Exception) -> bool:
        """Check if error is transient (retryable)."""
        return isinstance(error, cls.TRANSIENT_ERRORS)
    
    @classmethod
    def is_resource_error(cls, error: Exception) -> bool:
        """Check if error is a resource error (may be retryable with backoff)."""
        if isinstance(error, cls.RESOURCE_ERRORS):
            # Check for GPU OOM
            error_str = str(error).lower()
            if 'out of memory' in error_str or 'cuda' in error_str:
                return True
        return False
    
    @classmethod
    def is_permanent(cls, error: Exception) -> bool:
        """Check if error is permanent (not retryable)."""
        return isinstance(error, cls.PERMANENT_ERRORS)
    
    @classmethod
    def classify(cls, error: Exception) -> str:
        """
        Classify an error.
        
        Returns:
            'transient', 'resource', or 'permanent'
        """
        if cls.is_transient(error):
            return 'transient'
        if cls.is_resource_error(error):
            return 'resource'
        if cls.is_permanent(error):
            return 'permanent'
        return 'unknown'


def retry_on_error(max_attempts: int = 3, delay: float = 1.0, 
                   backoff: float = 2.0, exceptions: Tuple[Type[Exception], ...] = (Exception,),
                   classifier: Optional[ErrorClassifier] = None):
    """
    Decorator for retrying functions on errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Backoff multiplier for delay
        exceptions: Tuple of exception types to catch
        classifier: Optional error classifier for smart retry logic
    
    Returns:
        Decorated function
    """
    if classifier is None:
        classifier = ErrorClassifier()
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    # Classify error
                    error_type = classifier.classify(e)
                    
                    # Don't retry permanent errors
                    if error_type == 'permanent':
                        logger.error(f"Permanent error in {func.__name__}: {e}")
                        raise
                    
                    # Don't retry if max attempts reached
                    if attempt >= max_attempts:
                        logger.error(f"Max attempts reached for {func.__name__}: {e}")
                        raise
                    
                    # Log retry
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    
                    # Wait before retry
                    time.sleep(current_delay)
                    
                    # Increase delay for next retry (exponential backoff)
                    current_delay *= backoff
            
            # Should not reach here, but just in case
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def retry_with_backoff(max_attempts: int = 5, initial_delay: float = 1.0,
                       max_delay: float = 60.0, backoff: float = 2.0):
    """
    Decorator for retrying with exponential backoff.
    
    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay (seconds)
        max_delay: Maximum delay (seconds)
        backoff: Backoff multiplier
    
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt >= max_attempts:
                        logger.error(f"Max attempts reached for {func.__name__}: {e}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.2f}s..."
                    )
                    
                    time.sleep(min(delay, max_delay))
                    delay = min(delay * backoff, max_delay)
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def handle_partial_results(func: Callable, result_accumulator: Callable = None):
    """
    Decorator for handling partial results on failure.
    
    Args:
        func: Function to wrap
        result_accumulator: Function to accumulate partial results
    
    Returns:
        Decorated function
    """
    @wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}")
            
            # Try to get partial results if accumulator provided
            if result_accumulator:
                try:
                    partial = result_accumulator()
                    if partial:
                        logger.info(f"Returning partial results from {func.__name__}")
                        return partial
                except Exception as acc_error:
                    logger.warning(f"Error getting partial results: {acc_error}")
            
            raise
    
    return wrapper

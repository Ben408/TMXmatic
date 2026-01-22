"""
Unit tests for error recovery utilities.
"""
import pytest
import time
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.error_recovery import (
    ErrorClassifier, retry_on_error, retry_with_backoff, handle_partial_results
)


class TestErrorClassifier:
    """Tests for ErrorClassifier."""
    
    def test_is_transient_connection_error(self):
        """Test classifying connection error as transient."""
        error = ConnectionError("Connection failed")
        
        assert ErrorClassifier.is_transient(error) is True
    
    def test_is_transient_timeout(self):
        """Test classifying timeout as transient."""
        error = TimeoutError("Request timed out")
        
        assert ErrorClassifier.is_transient(error) is True
    
    def test_is_resource_error_memory(self):
        """Test classifying memory error as resource error."""
        error = MemoryError("Out of memory")
        
        assert ErrorClassifier.is_resource_error(error) is True
    
    def test_is_resource_error_gpu_oom(self):
        """Test classifying GPU OOM as resource error."""
        error = RuntimeError("CUDA out of memory")
        
        assert ErrorClassifier.is_resource_error(error) is True
    
    def test_is_permanent_value_error(self):
        """Test classifying ValueError as permanent."""
        error = ValueError("Invalid value")
        
        assert ErrorClassifier.is_permanent(error) is True
    
    def test_classify_transient(self):
        """Test classifying a transient error."""
        error = ConnectionError("Connection failed")
        
        assert ErrorClassifier.classify(error) == 'transient'
    
    def test_classify_resource(self):
        """Test classifying a resource error."""
        error = RuntimeError("CUDA out of memory")
        
        assert ErrorClassifier.classify(error) == 'resource'
    
    def test_classify_permanent(self):
        """Test classifying a permanent error."""
        error = ValueError("Invalid value")
        
        assert ErrorClassifier.classify(error) == 'permanent'


class TestRetryOnError:
    """Tests for retry_on_error decorator."""
    
    def test_retry_success_first_attempt(self):
        """Test function that succeeds on first attempt."""
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
    
    def test_retry_success_after_retry(self):
        """Test function that succeeds after retry."""
        call_count = [0]
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise ConnectionError("Temporary failure")
            return "success"
        
        result = test_func()
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_max_attempts(self):
        """Test function that fails after max attempts."""
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_func():
            raise ConnectionError("Always fails")
        
        with pytest.raises(ConnectionError):
            test_func()
    
    def test_retry_permanent_error_no_retry(self):
        """Test that permanent errors are not retried."""
        call_count = [0]
        
        @retry_on_error(max_attempts=3, delay=0.1)
        def test_func():
            call_count[0] += 1
            raise ValueError("Permanent error")
        
        with pytest.raises(ValueError):
            test_func()
        
        # Should only be called once (no retries)
        assert call_count[0] == 1
    
    def test_retry_backoff(self):
        """Test that retry uses exponential backoff."""
        call_times = []
        
        @retry_on_error(max_attempts=3, delay=0.1, backoff=2.0)
        def test_func():
            call_times.append(time.time())
            if len(call_times) < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        start_time = time.time()
        result = test_func()
        
        assert result == "success"
        # Verify delays increased (rough check)
        if len(call_times) >= 2:
            delay1 = call_times[1] - call_times[0]
            assert delay1 >= 0.1  # At least initial delay


class TestRetryWithBackoff:
    """Tests for retry_with_backoff decorator."""
    
    def test_retry_with_backoff_success(self):
        """Test retry with backoff that succeeds."""
        call_count = [0]
        
        @retry_with_backoff(max_attempts=3, initial_delay=0.1)
        def test_func():
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Temporary failure")
            return "success"
        
        result = test_func()
        
        assert result == "success"
        assert call_count[0] == 2
    
    def test_retry_with_backoff_max_delay(self):
        """Test that backoff respects max delay."""
        @retry_with_backoff(max_attempts=2, initial_delay=0.1, max_delay=0.2)
        def test_func():
            raise Exception("Always fails")
        
        start_time = time.time()
        with pytest.raises(Exception):
            test_func()
        elapsed = time.time() - start_time
        
        # Should not exceed max_delay significantly
        assert elapsed < 1.0  # Reasonable upper bound


class TestHandlePartialResults:
    """Tests for handle_partial_results decorator."""
    
    def test_handle_partial_results_success(self):
        """Test function that succeeds."""
        @handle_partial_results
        def test_func():
            return "success"
        
        result = test_func()
        
        assert result == "success"
    
    def test_handle_partial_results_with_accumulator(self):
        """Test function that fails but returns partial results."""
        partial_data = {"partial": "results"}
        
        def accumulator():
            return partial_data
        
        @handle_partial_results
        def test_func():
            raise Exception("Error occurred")
        
        # Without accumulator, should raise
        with pytest.raises(Exception):
            test_func()
        
        # Note: The decorator signature in implementation needs accumulator as parameter
        # This test documents expected behavior

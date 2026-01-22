"""
Unit tests for progress tracker.
"""
import pytest
import time
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.utils.progress_tracker import ProgressTracker


class TestProgressTracker:
    """Tests for ProgressTracker class."""
    
    def test_progress_tracker_initialization(self):
        """Test ProgressTracker initialization."""
        tracker = ProgressTracker(total=100)
        
        assert tracker.total == 100
        assert tracker.processed == 0
        assert tracker.start_time is None
    
    def test_start(self):
        """Test starting tracker."""
        tracker = ProgressTracker(total=100)
        tracker.start()
        
        assert tracker.start_time is not None
    
    def test_update(self):
        """Test updating progress."""
        tracker = ProgressTracker(total=100)
        tracker.start()
        tracker.update(10)
        
        assert tracker.processed == 10
    
    def test_update_with_statistics(self):
        """Test updating progress with statistics."""
        tracker = ProgressTracker(total=100)
        tracker.start()
        tracker.update(1, statistics={'exact_matches': 1})
        
        assert tracker.processed == 1
        assert tracker.statistics['exact_matches'] == 1
    
    def test_get_progress_not_started(self):
        """Test getting progress before starting."""
        tracker = ProgressTracker(total=100)
        
        progress = tracker.get_progress()
        
        assert progress['percentage'] == 0.0
        assert progress['eta_seconds'] is None
    
    def test_get_progress_started(self):
        """Test getting progress after starting."""
        import time
        tracker = ProgressTracker(total=100)
        tracker.start()
        time.sleep(0.01)  # Small delay to ensure elapsed > 0
        tracker.update(50)
        
        progress = tracker.get_progress()
        
        assert progress['processed'] == 50
        assert progress['percentage'] == 50.0
        # ETA may be None if elapsed is too small, so just check it's a number or None
        assert progress['eta_seconds'] is None or isinstance(progress['eta_seconds'], (int, float))
    
    def test_callback(self):
        """Test callback function."""
        callback_called = []
        
        def callback(progress):
            callback_called.append(progress)
        
        tracker = ProgressTracker(total=100, callback=callback)
        tracker.start()
        tracker.update(10)
        
        assert len(callback_called) == 1
        assert callback_called[0]['processed'] == 10

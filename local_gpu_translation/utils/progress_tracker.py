"""
Progress Tracker

Tracks progress of long-running translation jobs.
"""
import logging
import time
from typing import Dict, Optional, Callable
from datetime import datetime

logger = logging.getLogger(__name__)


class ProgressTracker:
    """
    Tracks progress of translation jobs.
    
    Features:
    - Real-time progress updates
    - ETA calculation
    - Callback support
    - Statistics tracking
    """
    
    def __init__(self, total: int, callback: Optional[Callable] = None):
        """
        Initialize ProgressTracker.
        
        Args:
            total: Total number of items to process
            callback: Optional callback function for progress updates
        """
        self.total = total
        self.processed = 0
        self.errors = 0
        self.start_time = None
        self.callback = callback
        self.statistics = {
            'exact_matches': 0,
            'fuzzy_repairs': 0,
            'new_translations': 0,
            'errors': 0
        }
    
    def start(self):
        """Start tracking."""
        self.start_time = time.time()
        logger.info(f"Starting progress tracking for {self.total} items")
    
    def update(self, count: int = 1, statistics: Optional[Dict] = None):
        """
        Update progress.
        
        Args:
            count: Number of items processed
            statistics: Optional statistics update
        """
        self.processed += count
        
        if statistics:
            for key, value in statistics.items():
                if key in self.statistics:
                    self.statistics[key] += value
        
        if self.callback:
            self.callback(self.get_progress())
    
    def get_progress(self) -> Dict[str, any]:
        """
        Get current progress information.
        
        Returns:
            Dictionary with progress information
        """
        if self.start_time is None:
            return {
                'total': self.total,
                'processed': self.processed,
                'percentage': 0.0,
                'eta_seconds': None,
                'statistics': self.statistics.copy()
            }
        
        elapsed = time.time() - self.start_time
        percentage = (self.processed / self.total * 100) if self.total > 0 else 0.0
        
        # Calculate ETA
        eta_seconds = None
        if self.processed > 0 and elapsed > 0:
            rate = self.processed / elapsed
            remaining = self.total - self.processed
            eta_seconds = remaining / rate if rate > 0 else None
        
        return {
            'total': self.total,
            'processed': self.processed,
            'percentage': round(percentage, 2),
            'elapsed_seconds': round(elapsed, 2),
            'eta_seconds': round(eta_seconds, 2) if eta_seconds else None,
            'rate_per_second': round(self.processed / elapsed, 2) if elapsed > 0.001 else 0.0,
            'statistics': self.statistics.copy()
        }
    
    def log_progress(self):
        """Log current progress."""
        progress = self.get_progress()
        logger.info(
            f"Progress: {progress['processed']}/{progress['total']} "
            f"({progress['percentage']:.1f}%)"
        )
        if progress['eta_seconds']:
            logger.info(f"ETA: {progress['eta_seconds']:.0f} seconds")

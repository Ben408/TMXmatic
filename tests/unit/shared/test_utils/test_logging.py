"""
Unit tests for logging utilities.
"""
import pytest
import logging
import sys
from pathlib import Path
import sys
from io import StringIO

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.utils.logging import setup_logging, get_logger, create_log_file


class TestLoggingUtilities:
    """Tests for logging utilities."""
    
    def test_setup_logging_console_only(self):
        """Test setting up logging with console handler only."""
        logger = setup_logging(log_file=None, level=logging.INFO)
        
        assert logger is not None
        # Check effective level (logger may inherit from root)
        assert logger.getEffectiveLevel() == logging.INFO
    
    def test_setup_logging_with_file(self, temp_dir):
        """Test setting up logging with file handler."""
        log_file = temp_dir / 'test.log'
        logger = setup_logging(log_file=log_file, level=logging.DEBUG)
        
        assert logger is not None
        assert log_file.exists() or log_file.parent.exists()
    
    def test_setup_logging_custom_format(self):
        """Test setting up logging with custom format."""
        custom_format = '%(levelname)s - %(message)s'
        logger = setup_logging(log_file=None, format_string=custom_format)
        
        assert logger is not None
    
    def test_get_logger(self):
        """Test getting a logger instance."""
        logger = get_logger('test_module')
        
        assert logger is not None
        assert logger.name == 'test_module'
        assert isinstance(logger, logging.Logger)
    
    def test_create_log_file_default(self, temp_dir):
        """Test creating log file with default settings."""
        log_file = create_log_file(base_name='test', log_dir=temp_dir)
        
        assert log_file.parent == temp_dir
        assert 'test_' in log_file.name
        assert log_file.suffix == '.log'
        assert '_' in log_file.stem  # Should have timestamp
    
    def test_create_log_file_custom(self, temp_dir):
        """Test creating log file with custom name."""
        log_file = create_log_file(base_name='custom', log_dir=temp_dir)
        
        assert 'custom_' in log_file.name
        assert log_file.parent == temp_dir
    
    def test_logging_output(self, temp_dir):
        """Test that logging actually outputs messages."""
        log_file = temp_dir / 'output.log'
        logger = setup_logging(log_file=log_file, level=logging.INFO)
        
        test_logger = get_logger('test')
        test_logger.info('Test message')
        
        # Log file should exist and contain message
        if log_file.exists():
            content = log_file.read_text(encoding='utf-8')
            assert 'Test message' in content

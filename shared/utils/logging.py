"""
Shared Logging Utilities

Provides consistent logging configuration aligned with TMXmatic.
"""
import logging
import sys
from pathlib import Path
from typing import Optional
from datetime import datetime


def setup_logging(log_file: Optional[Path] = None, level: int = logging.INFO,
                  format_string: Optional[str] = None) -> logging.Logger:
    """
    Set up logging configuration aligned with TMXmatic.
    
    Args:
        log_file: Path to log file. If None, logs to console only.
        level: Logging level (default: INFO)
        format_string: Custom format string. If None, uses default.
    
    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = '%(asctime)s - %(levelname)s - [%(name)s] - %(message)s'
    
    date_format = '%Y-%m-%d %H:%M:%S'
    
    handlers = []
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_formatter = logging.Formatter(format_string, datefmt=date_format)
    console_handler.setFormatter(console_formatter)
    handlers.append(console_handler)
    
    # File handler (if specified)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(level)
        file_formatter = logging.Formatter(format_string, datefmt=date_format)
        file_handler.setFormatter(file_formatter)
        handlers.append(file_handler)
    
    # Configure root logger
    logging.basicConfig(
        level=level,
        format=format_string,
        datefmt=date_format,
        handlers=handlers,
        force=True  # Override any existing configuration
    )
    
    logger = logging.getLogger(__name__)
    logger.info("Logging configured")
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def create_log_file(base_name: str = "tmxmatic", log_dir: Optional[Path] = None) -> Path:
    """
    Create a timestamped log file path.
    
    Args:
        base_name: Base name for log file
        log_dir: Directory for log file. If None, uses current directory.
    
    Returns:
        Path to log file
    """
    if log_dir is None:
        log_dir = Path.cwd()
    else:
        log_dir = Path(log_dir)
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = log_dir / f"{base_name}_{timestamp}.log"
    
    return log_file

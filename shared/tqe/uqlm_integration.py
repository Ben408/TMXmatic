"""
UQLM Integration

Integration with UQLM (Uncertainty Quantification for Language Models) for hallucination detection.
"""
import logging
from typing import Dict, Optional, Any
import subprocess
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# UQLM will be pulled from GitHub repo: cvs-health/uqlm
# We don't bundle it, fetch on-demand if needed


def check_uqlm_available() -> bool:
    """
    Check if UQLM is available in the environment.
    
    Returns:
        True if UQLM is available, False otherwise
    """
    try:
        import uqlm
        return True
    except ImportError:
        return False


def install_uqlm() -> bool:
    """
    Install UQLM from GitHub repository.
    
    Returns:
        True if installation successful, False otherwise
    """
    try:
        logger.info("Installing UQLM from GitHub...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "git+https://github.com/cvs-health/uqlm.git"],
            capture_output=True,
            text=True,
            check=True
        )
        logger.info("UQLM installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to install UQLM: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Error installing UQLM: {e}")
        return False


def detect_hallucination(text: str, source: Optional[str] = None, 
                        model: Optional[Any] = None) -> Dict[str, Any]:
    """
    Detect hallucination in text using UQLM.
    
    Args:
        text: Text to check for hallucination
        source: Optional source text for reference
        model: Optional pre-loaded UQLM model
    
    Returns:
        Dictionary with hallucination detection results:
        {
            'hallucination': bool,
            'is_hallucination': bool,
            'confidence': float,
            'details': dict
        }
    """
    if not check_uqlm_available():
        logger.warning("UQLM not available, attempting installation...")
        if not install_uqlm():
            logger.warning("UQLM installation failed, returning default result")
            return {
                'hallucination': False,
                'is_hallucination': False,
                'confidence': 0.0,
                'details': {'error': 'UQLM not available'}
            }
    
    try:
        import uqlm
        
        # Use UQLM API to detect hallucination
        # Note: Actual API may vary - this is a placeholder structure
        # Adjust based on actual UQLM API when integrated
        result = uqlm.detect(text, source=source, model=model)
        
        return {
            'hallucination': result.get('hallucination', False),
            'is_hallucination': result.get('hallucination', False),
            'confidence': result.get('confidence', 0.0),
            'details': result
        }
    except Exception as e:
        logger.error(f"Error detecting hallucination: {e}")
        return {
            'hallucination': False,
            'is_hallucination': False,
            'confidence': 0.0,
            'details': {'error': str(e)}
        }

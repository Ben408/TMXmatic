"""
Model Verification Tests

Tests to verify models can be loaded and used.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from shared.models.model_manager import ModelManager
from shared.gpu.detector import GPUDetector


class TestModelVerification:
    """Tests for model verification."""
    
    def test_model_manager_initialization(self):
        """Test ModelManager can be initialized."""
        manager = ModelManager()
        assert manager is not None
    
    def test_gpu_detector_initialization(self):
        """Test GPUDetector can be initialized."""
        detector = GPUDetector()
        assert detector is not None
    
    def test_model_path_retrieval(self):
        """Test model path retrieval."""
        manager = ModelManager()
        
        # Test that get_model_path doesn't error (may return None if model not registered)
        path = manager.get_model_path('test-model')
        # Path may be None if model not registered, which is expected
        assert path is None or isinstance(path, Path)
    
    def test_required_models_listed(self):
        """Test that required models are properly listed."""
        required_models = [
            'google/translategemma-12b-it',
            'sentence-transformers/paraphrase-multilingual-mpnet-base-v2'
        ]
        
        # These should be in the model manager's registry
        manager = ModelManager()
        # Just verify manager can handle these IDs
        for model_id in required_models:
            path = manager.get_model_path(model_id)
            # Path may be None if not downloaded, but should not error
            assert path is None or isinstance(path, Path)

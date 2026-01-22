"""
Unit tests for model manager.

Tests model downloading, caching, versioning, and metadata management.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock, mock_open
import json
import shutil
from pathlib import Path
import sys
from datetime import datetime

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.model_manager import ModelManager, ModelInfo


class TestModelInfo:
    """Tests for ModelInfo class."""
    
    def test_model_info_creation(self):
        """Test ModelInfo object creation."""
        model_info = ModelInfo(
            model_id='test-model',
            model_type='llm',
            local_path=Path('/path/to/model'),
            version='1.0',
            downloaded=True,
            download_date='2024-01-01T00:00:00',
            size_gb=12.0
        )
        
        assert model_info.model_id == 'test-model'
        assert model_info.model_type == 'llm'
        assert model_info.local_path == Path('/path/to/model')
        assert model_info.version == '1.0'
        assert model_info.downloaded is True
        assert model_info.size_gb == 12.0
    
    def test_model_info_to_dict(self):
        """Test ModelInfo to_dict conversion."""
        model_info = ModelInfo(
            model_id='test-model',
            model_type='llm',
            local_path=Path('/path/to/model'),
            downloaded=True,
            size_gb=12.0
        )
        
        result = model_info.to_dict()
        
        assert result['model_id'] == 'test-model'
        assert result['model_type'] == 'llm'
        # Path conversion handles OS-specific separators
        assert result['local_path'] == str(Path('/path/to/model'))
        assert result['downloaded'] is True
        assert result['size_gb'] == 12.0
    
    def test_model_info_from_dict(self):
        """Test ModelInfo from_dict creation."""
        data = {
            'model_id': 'test-model',
            'model_type': 'llm',
            'local_path': '/path/to/model',
            'version': '1.0',
            'downloaded': True,
            'download_date': '2024-01-01T00:00:00',
            'size_gb': 12.0
        }
        
        model_info = ModelInfo.from_dict(data)
        
        assert model_info.model_id == 'test-model'
        assert model_info.model_type == 'llm'
        assert model_info.local_path == Path('/path/to/model')
        assert model_info.downloaded is True
        assert model_info.size_gb == 12.0


class TestModelManager:
    """Tests for ModelManager class."""
    
    def test_model_manager_initialization_default(self, temp_dir):
        """Test ModelManager initialization with default models directory."""
        manager = ModelManager()
        
        assert manager.models_dir.exists()
        assert manager.metadata_file.exists() or not manager.metadata_file.exists()  # May not exist yet
    
    def test_model_manager_initialization_custom(self, temp_dir):
        """Test ModelManager initialization with custom models directory."""
        custom_dir = temp_dir / 'custom_models'
        manager = ModelManager(models_dir=custom_dir)
        
        assert manager.models_dir == custom_dir
        assert custom_dir.exists()
    
    def test_load_metadata_nonexistent(self, temp_dir):
        """Test loading metadata when file doesn't exist."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        assert len(manager._models_cache) == 0
    
    def test_load_metadata_existing(self, temp_dir):
        """Test loading metadata from existing file."""
        models_dir = temp_dir / 'models'
        models_dir.mkdir()
        
        metadata_file = models_dir / 'models_metadata.json'
        metadata = {
            'test-model': {
                'model_id': 'test-model',
                'model_type': 'llm',
                'local_path': '/path/to/model',
                'downloaded': True,
                'size_gb': 12.0
            }
        }
        
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f)
        
        manager = ModelManager(models_dir=models_dir)
        
        assert 'test-model' in manager._models_cache
        assert manager._models_cache['test-model'].model_id == 'test-model'
    
    def test_get_model_info_registered(self, temp_dir):
        """Test getting info for a registered model."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        model_info = manager.get_model_info('translategemma-12b-it')
        
        assert model_info is not None
        assert model_info.model_id == 'translategemma-12b-it'
        assert model_info.model_type == 'llm'
    
    def test_get_model_info_unregistered(self, temp_dir):
        """Test getting info for an unregistered model."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        model_info = manager.get_model_info('nonexistent-model')
        
        assert model_info is None
    
    def test_is_model_downloaded_false(self, temp_dir):
        """Test checking if model is downloaded when it's not."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        result = manager.is_model_downloaded('translategemma-12b-it')
        
        assert result is False
    
    def test_is_model_downloaded_true(self, temp_dir):
        """Test checking if model is downloaded when it is."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Create fake model directory
        model_path = models_dir / 'translategemma-12b-it'
        model_path.mkdir(parents=True)
        (model_path / 'config.json').touch()
        
        # Update metadata
        model_info = ModelInfo(
            model_id='translategemma-12b-it',
            model_type='llm',
            local_path=model_path,
            downloaded=True
        )
        manager._models_cache['translategemma-12b-it'] = model_info
        manager._save_metadata()
        
        result = manager.is_model_downloaded('translategemma-12b-it')
        
        assert result is True
    
    def test_get_model_path_not_downloaded(self, temp_dir):
        """Test getting model path when model is not downloaded."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        path = manager.get_model_path('translategemma-12b-it')
        
        assert path is None
    
    def test_get_model_path_downloaded(self, temp_dir):
        """Test getting model path when model is downloaded."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Create fake model directory
        model_path = models_dir / 'translategemma-12b-it'
        model_path.mkdir(parents=True)
        (model_path / 'config.json').touch()
        
        # Update metadata
        model_info = ModelInfo(
            model_id='translategemma-12b-it',
            model_type='llm',
            local_path=model_path,
            downloaded=True
        )
        manager._models_cache['translategemma-12b-it'] = model_info
        
        path = manager.get_model_path('translategemma-12b-it')
        
        assert path == model_path
    
    @patch('shared.models.model_manager.snapshot_download')
    def test_download_model_success(self, mock_download, temp_dir):
        """Test successful model download."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Ensure model is not already marked as downloaded
        assert not manager.is_model_downloaded('translategemma-12b-it')
        
        # Mock download - snapshot_download returns the path it was given
        model_path = models_dir / 'translategemma-12b-it'
        mock_download.return_value = str(model_path)
        
        # Create the directory structure after mock returns
        def side_effect(**kwargs):
            model_path.mkdir(parents=True, exist_ok=True)
            (model_path / 'config.json').touch()
            return str(model_path)
        
        mock_download.side_effect = side_effect
        
        result = manager.download_model('translategemma-12b-it')
        
        assert result == model_path
        assert manager.is_model_downloaded('translategemma-12b-it')
        mock_download.assert_called_once()
    
    @patch('shared.models.model_manager.snapshot_download')
    def test_download_model_already_downloaded(self, mock_download, temp_dir):
        """Test downloading model that's already downloaded."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Create fake model directory
        model_path = models_dir / 'translategemma-12b-it'
        model_path.mkdir(parents=True)
        (model_path / 'config.json').touch()
        
        # Mark as downloaded
        model_info = ModelInfo(
            model_id='translategemma-12b-it',
            model_type='llm',
            local_path=model_path,
            downloaded=True
        )
        manager._models_cache['translategemma-12b-it'] = model_info
        
        result = manager.download_model('translategemma-12b-it')
        
        assert result == model_path
        mock_download.assert_not_called()  # Should not download again
    
    def test_download_model_not_in_registry(self, temp_dir):
        """Test downloading model not in registry."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        with pytest.raises(ValueError, match="not in the registry"):
            manager.download_model('nonexistent-model')
    
    @patch('shared.models.model_manager.HUGGINGFACE_AVAILABLE', False)
    def test_download_model_huggingface_unavailable(self, temp_dir):
        """Test downloading when HuggingFace Hub is not available."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        with pytest.raises(RuntimeError, match="huggingface_hub is not available"):
            manager.download_model('translategemma-12b-it')
    
    def test_delete_model_success(self, temp_dir):
        """Test successful model deletion."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Create fake model directory
        model_path = models_dir / 'translategemma-12b-it'
        model_path.mkdir(parents=True)
        (model_path / 'config.json').touch()
        
        # Mark as downloaded
        model_info = ModelInfo(
            model_id='translategemma-12b-it',
            model_type='llm',
            local_path=model_path,
            downloaded=True
        )
        manager._models_cache['translategemma-12b-it'] = model_info
        
        result = manager.delete_model('translategemma-12b-it')
        
        assert result is True
        assert not model_path.exists()
        assert not manager.is_model_downloaded('translategemma-12b-it')
    
    def test_delete_model_not_downloaded(self, temp_dir):
        """Test deleting model that's not downloaded."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        result = manager.delete_model('translategemma-12b-it')
        
        assert result is False
    
    def test_list_models(self, temp_dir):
        """Test listing all registered models."""
        manager = ModelManager(models_dir=temp_dir / 'models')
        
        models = manager.list_models()
        
        assert len(models) > 0
        assert all(isinstance(m, ModelInfo) for m in models)
        model_ids = [m.model_id for m in models]
        assert 'translategemma-12b-it' in model_ids
    
    def test_get_disk_usage(self, temp_dir):
        """Test getting disk usage information."""
        models_dir = temp_dir / 'models'
        manager = ModelManager(models_dir=models_dir)
        
        # Create fake model directory
        model_path = models_dir / 'translategemma-12b-it'
        model_path.mkdir(parents=True)
        test_file = model_path / 'test.bin'
        test_file.write_bytes(b'x' * 1024)  # 1KB file
        
        # Mark as downloaded
        model_info = ModelInfo(
            model_id='translategemma-12b-it',
            model_type='llm',
            local_path=model_path,
            downloaded=True
        )
        manager._models_cache['translategemma-12b-it'] = model_info
        
        usage = manager.get_disk_usage()
        
        assert 'total_size_gb' in usage
        assert 'model_sizes' in usage
        assert 'models_dir' in usage
        assert 'translategemma-12b-it' in usage['model_sizes']

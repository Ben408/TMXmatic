"""
Model Management

Handles downloading, caching, versioning, and loading of models.
"""
import logging
import os
import shutil
from pathlib import Path
from typing import Optional, Dict, Any, List
import json
from datetime import datetime

try:
    from huggingface_hub import snapshot_download, hf_hub_download
    HUGGINGFACE_AVAILABLE = True
except ImportError:
    HUGGINGFACE_AVAILABLE = False
    logging.warning("huggingface_hub not available. Model downloads will not work.")

logger = logging.getLogger(__name__)


class ModelInfo:
    """Information about a model."""
    
    def __init__(self, model_id: str, model_type: str, local_path: Optional[Path] = None,
                 version: Optional[str] = None, downloaded: bool = False,
                 download_date: Optional[str] = None, size_gb: Optional[float] = None):
        self.model_id = model_id
        self.model_type = model_type  # 'llm', 'comet', 'sbert', etc.
        self.local_path = local_path
        self.version = version
        self.downloaded = downloaded
        self.download_date = download_date
        self.size_gb = size_gb
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'model_id': self.model_id,
            'model_type': self.model_type,
            'local_path': str(self.local_path) if self.local_path else None,
            'version': self.version,
            'downloaded': self.downloaded,
            'download_date': self.download_date,
            'size_gb': self.size_gb
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ModelInfo':
        """Create ModelInfo from dictionary."""
        return cls(
            model_id=data['model_id'],
            model_type=data['model_type'],
            local_path=Path(data['local_path']) if data.get('local_path') else None,
            version=data.get('version'),
            downloaded=data.get('downloaded', False),
            download_date=data.get('download_date'),
            size_gb=data.get('size_gb')
        )


class ModelManager:
    """Manages model downloads, caching, and versioning."""
    
    # Model registry - maps model IDs to their configurations
    MODEL_REGISTRY = {
        'translategemma-12b-it': {
            'type': 'llm',
            'repo_id': 'google/translategemma-12b-it',
            'files': ['model.safetensors', 'tokenizer.json', 'config.json'],
            'estimated_size_gb': 24.0
        },
        'comet-22': {
            'type': 'comet',
            'repo_id': 'Unbabel/wmt22-comet-da',
            'files': ['pytorch_model.bin', 'config.json'],
            'estimated_size_gb': 0.5
        },
        'comet-qe-22': {
            'type': 'comet',
            'repo_id': 'Unbabel/wmt22-cometkiwi-da',
            'files': ['pytorch_model.bin', 'config.json'],
            'estimated_size_gb': 0.5
        },
        'sbert-multilingual': {
            'type': 'sbert',
            'repo_id': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
            'files': ['pytorch_model.bin', 'config.json'],
            'estimated_size_gb': 0.4
        }
    }
    
    def __init__(self, models_dir: Optional[Path] = None):
        """
        Initialize ModelManager.
        
        Args:
            models_dir: Directory to store models. If None, uses default.
        """
        if models_dir is None:
            # Default to project root / models
            project_root = Path(__file__).parent.parent.parent.parent
            models_dir = project_root / 'models'
        
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.models_dir / 'models_metadata.json'
        self._models_cache: Dict[str, ModelInfo] = {}
        self._load_metadata()
    
    def _load_metadata(self):
        """Load model metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._models_cache = {
                        model_id: ModelInfo.from_dict(model_data)
                        for model_id, model_data in data.items()
                    }
                logger.info(f"Loaded metadata for {len(self._models_cache)} models")
            except Exception as e:
                logger.error(f"Error loading model metadata: {e}")
                self._models_cache = {}
        else:
            self._models_cache = {}
    
    def _save_metadata(self):
        """Save model metadata to disk."""
        try:
            data = {
                model_id: model_info.to_dict()
                for model_id, model_info in self._models_cache.items()
            }
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug("Saved model metadata")
        except Exception as e:
            logger.error(f"Error saving model metadata: {e}")
    
    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get information about a model.
        
        Args:
            model_id: The model identifier
        
        Returns:
            ModelInfo if found, None otherwise
        """
        # Check cache first
        if model_id in self._models_cache:
            model_info = self._models_cache[model_id]
            # Verify local path still exists
            if model_info.downloaded and model_info.local_path:
                if not model_info.local_path.exists():
                    logger.warning(f"Model {model_id} marked as downloaded but path doesn't exist")
                    model_info.downloaded = False
                    self._save_metadata()
            return model_info
        
        # Check if model is in registry
        if model_id in self.MODEL_REGISTRY:
            config = self.MODEL_REGISTRY[model_id]
            model_path = self.models_dir / model_id
            
            model_info = ModelInfo(
                model_id=model_id,
                model_type=config['type'],
                local_path=model_path if model_path.exists() else None,
                downloaded=model_path.exists(),
                size_gb=config.get('estimated_size_gb')
            )
            
            self._models_cache[model_id] = model_info
            self._save_metadata()
            return model_info
        
        return None
    
    def is_model_downloaded(self, model_id: str) -> bool:
        """
        Check if a model is downloaded.
        
        Args:
            model_id: The model identifier
        
        Returns:
            True if model is downloaded, False otherwise
        """
        model_info = self.get_model_info(model_id)
        if model_info is None:
            return False
        
        if not model_info.downloaded:
            return False
        
        # Verify path exists
        if model_info.local_path and model_info.local_path.exists():
            return True
        
        # Path doesn't exist, mark as not downloaded
        model_info.downloaded = False
        self._save_metadata()
        return False
    
    def get_model_path(self, model_id: str) -> Optional[Path]:
        """
        Get the local path to a model.
        
        Args:
            model_id: The model identifier
        
        Returns:
            Path to model if downloaded, None otherwise
        """
        model_info = self.get_model_info(model_id)
        if model_info is None:
            return None
        
        if not model_info.downloaded:
            return None
        
        if model_info.local_path and model_info.local_path.exists():
            return model_info.local_path
        
        return None
    
    def download_model(self, model_id: str, progress_callback=None) -> Path:
        """
        Download a model from HuggingFace Hub.
        
        Args:
            model_id: The model identifier
            progress_callback: Optional callback function for progress updates
        
        Returns:
            Path to downloaded model
        
        Raises:
            ValueError: If model_id is not in registry
            RuntimeError: If download fails
        """
        if not HUGGINGFACE_AVAILABLE:
            raise RuntimeError("huggingface_hub is not available. Cannot download models.")
        
        if model_id not in self.MODEL_REGISTRY:
            raise ValueError(f"Model {model_id} is not in the registry")
        
        # Check if already downloaded
        if self.is_model_downloaded(model_id):
            logger.info(f"Model {model_id} is already downloaded")
            return self.get_model_path(model_id)
        
        config = self.MODEL_REGISTRY[model_id]
        repo_id = config['repo_id']
        model_path = self.models_dir / model_id
        
        logger.info(f"Downloading model {model_id} from {repo_id}...")
        
        try:
            # Download model
            downloaded_path = snapshot_download(
                repo_id=repo_id,
                local_dir=str(model_path),
                local_dir_use_symlinks=False
            )
            
            model_path = Path(downloaded_path)
            
            # Calculate size
            size_gb = self._calculate_directory_size(model_path) / (1024 ** 3)
            
            # Update metadata
            model_info = ModelInfo(
                model_id=model_id,
                model_type=config['type'],
                local_path=model_path,
                version=None,  # Could extract from config.json if needed
                downloaded=True,
                download_date=datetime.now().isoformat(),
                size_gb=size_gb
            )
            
            self._models_cache[model_id] = model_info
            self._save_metadata()
            
            logger.info(f"Successfully downloaded model {model_id} ({size_gb:.2f}GB)")
            
            return model_path
            
        except Exception as e:
            logger.error(f"Error downloading model {model_id}: {e}")
            # Clean up partial download
            if model_path.exists():
                shutil.rmtree(model_path, ignore_errors=True)
            raise RuntimeError(f"Failed to download model {model_id}: {e}")
    
    def _calculate_directory_size(self, path: Path) -> int:
        """Calculate total size of directory in bytes."""
        total = 0
        try:
            for entry in path.rglob('*'):
                if entry.is_file():
                    total += entry.stat().st_size
        except Exception as e:
            logger.warning(f"Error calculating directory size: {e}")
        return total
    
    def delete_model(self, model_id: str) -> bool:
        """
        Delete a downloaded model.
        
        Args:
            model_id: The model identifier
        
        Returns:
            True if deleted successfully, False otherwise
        """
        model_info = self.get_model_info(model_id)
        if model_info is None or not model_info.downloaded:
            logger.warning(f"Model {model_id} is not downloaded")
            return False
        
        if model_info.local_path and model_info.local_path.exists():
            try:
                shutil.rmtree(model_info.local_path)
                logger.info(f"Deleted model {model_id}")
            except Exception as e:
                logger.error(f"Error deleting model {model_id}: {e}")
                return False
        
        # Update metadata
        model_info.downloaded = False
        model_info.local_path = None
        model_info.download_date = None
        self._save_metadata()
        
        return True
    
    def list_models(self) -> List[ModelInfo]:
        """
        List all registered models with their status.
        
        Returns:
            List of ModelInfo objects
        """
        models = []
        for model_id in self.MODEL_REGISTRY.keys():
            model_info = self.get_model_info(model_id)
            if model_info:
                models.append(model_info)
        return models
    
    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Get disk usage information for models directory.
        
        Returns:
            Dictionary with disk usage information
        """
        total_size = 0
        model_sizes = {}
        
        for model_id, model_info in self._models_cache.items():
            if model_info.downloaded and model_info.local_path:
                if model_info.local_path.exists():
                    size = self._calculate_directory_size(model_info.local_path)
                    size_gb = size / (1024 ** 3)
                    total_size += size
                    model_sizes[model_id] = size_gb
        
        return {
            'total_size_gb': total_size / (1024 ** 3),
            'model_sizes': model_sizes,
            'models_dir': str(self.models_dir)
        }

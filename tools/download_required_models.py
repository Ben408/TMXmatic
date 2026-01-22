"""
Download Required Models Script

Downloads all required models for the LLM Quality Module.
"""
import sys
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.models.model_manager import ModelManager
from shared.gpu.detector import GPUDetector
from huggingface_hub import snapshot_download
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Required models (using MODEL_REGISTRY IDs)
REQUIRED_MODELS = [
    {
        'id': 'translategemma-12b-it',  # Model registry ID
        'hf_repo': 'google/translategemma-12b-it',  # HuggingFace repo
        'name': 'TranslateGemma 12B IT',
        'required': True,
        'size_gb': 24.0,
        'description': 'Main translation model'
    },
    {
        'id': 'sbert-multilingual',  # Model registry ID (note: different from HF repo)
        'hf_repo': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',  # Actual HF repo we want
        'name': 'SBERT Multilingual',
        'required': True,
        'size_gb': 0.4,
        'description': 'Sentence embeddings for similarity'
    }
]

# Optional models
OPTIONAL_MODELS = [
    {
        'id': 'comet-22',  # Model registry ID
        'hf_repo': 'Unbabel/wmt22-comet-da',  # HuggingFace repo
        'name': 'COMET Reference',
        'required': False,
        'size_gb': 0.5,
        'description': 'COMET reference-based quality estimation'
    },
    {
        'id': 'comet-qe-22',  # Model registry ID
        'hf_repo': 'Unbabel/wmt22-cometkiwi-da',  # HuggingFace repo
        'name': 'COMET-QE',
        'required': False,
        'size_gb': 0.5,
        'description': 'COMET quality estimation without reference'
    }
]


def download_model(model_id: str, model_manager: ModelManager, hf_repo: str = None) -> bool:
    """
    Download a model using the model manager.
    
    Args:
        model_id: Model registry ID
        model_manager: ModelManager instance
        hf_repo: Optional HuggingFace repo ID (if different from registry)
    
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Downloading {model_id}...")
        if hf_repo:
            logger.info(f"HuggingFace repo: {hf_repo}")
        logger.info("This may take a while, especially for large models...")
        
        # Check if already downloaded
        existing_path = model_manager.get_model_path(model_id)
        if existing_path and existing_path.exists():
            logger.info(f"Model {model_id} already exists at {existing_path}")
            return True
        
        # Check if model is in registry
        if model_id not in model_manager.MODEL_REGISTRY:
            logger.error(f"Model {model_id} not in MODEL_REGISTRY")
            logger.info("Available models in registry:")
            for reg_id in model_manager.MODEL_REGISTRY.keys():
                logger.info(f"  - {reg_id}")
            return False
        
        # Download using model manager
        model_path = model_manager.download_model(model_id)
        
        if model_path and model_path.exists():
            logger.info(f"Successfully downloaded {model_id} to {model_path}")
            return True
        else:
            logger.error(f"Download completed but path not found: {model_path}")
            return False
            
    except Exception as e:
        logger.error(f"Error downloading {model_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def check_disk_space(required_gb: float) -> bool:
    """
    Check if sufficient disk space is available.
    
    Args:
        required_gb: Required space in GB
    
    Returns:
        True if sufficient space available
    """
    import shutil
    
    # Check available space in Models directory
    models_dir = Path(project_root) / "Models"
    models_dir.mkdir(exist_ok=True)
    
    stat = shutil.disk_usage(models_dir)
    available_gb = stat.free / (1024 ** 3)
    
    logger.info(f"Available disk space: {available_gb:.1f}GB")
    logger.info(f"Required space: {required_gb:.1f}GB")
    
    if available_gb < required_gb:
        logger.warning(f"Insufficient disk space. Need {required_gb:.1f}GB, have {available_gb:.1f}GB")
        return False
    
    return True


def main():
    """Main function to download all required models."""
    print("=" * 80)
    print("MODEL DOWNLOAD SCRIPT")
    print("=" * 80)
    print()
    
    # Check GPU
    gpu_detector = GPUDetector()
    if not gpu_detector.is_cuda_available():
        print("WARNING: CUDA not available. Models will work on CPU but may be slow.")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    else:
        gpus = gpu_detector.get_gpu_info()
        print(f"GPU detected: {len(gpus)} GPU(s)")
        for gpu in gpus:
            print(f"  - {gpu.name}: {gpu.available_memory_gb:.1f}GB available")
    print()
    
    # Check disk space
    total_required = sum(m['size_gb'] for m in REQUIRED_MODELS)
    if not check_disk_space(total_required):
        print("ERROR: Insufficient disk space")
        return
    print()
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Download required models
    print("=" * 80)
    print("REQUIRED MODELS")
    print("=" * 80)
    print()
    
    required_success = True
    for model in REQUIRED_MODELS:
        print(f"Model: {model['name']} ({model['id']})")
        print(f"Size: {model['size_gb']}GB")
        print(f"Description: {model['description']}")
        print()
        
        if not download_model(model['id'], model_manager, model.get('hf_repo')):
            print(f"FAILED to download {model['id']}")
            required_success = False
        else:
            print(f"SUCCESS: {model['id']} downloaded")
        print()
    
    # Download optional models
    print("=" * 80)
    print("OPTIONAL MODELS")
    print("=" * 80)
    print()
    
    response = input("Download optional models? (y/n): ")
    if response.lower() == 'y':
        for model in OPTIONAL_MODELS:
            print(f"Model: {model['name']} ({model['id']})")
            print(f"Size: {model['size_gb']}GB")
            print(f"Description: {model['description']}")
            print()
            
            if not download_model(model['id'], model_manager, model.get('hf_repo')):
                print(f"FAILED to download {model['id']}")
            else:
                print(f"SUCCESS: {model['id']} downloaded")
            print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if required_success:
        print("SUCCESS: All required models downloaded")
    else:
        print("WARNING: Some required models failed to download")
        print("You may need to download them manually or check your internet connection")
    
    print()
    print("Verify models with: python tools/verify_models.py")


if __name__ == "__main__":
    main()

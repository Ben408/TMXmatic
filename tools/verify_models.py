"""
Model Verification Script

Verifies that all required models are downloaded and available.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from shared.models.model_manager import ModelManager
from shared.gpu.detector import GPUDetector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Required models
REQUIRED_MODELS = {
    'translation': {
        'id': 'google/translategemma-12b-it',
        'name': 'TranslateGemma 12B IT',
        'required': True,
        'size_gb': 24.0,
        'description': 'Main translation model'
    },
    'sbert': {
        'id': 'sentence-transformers/paraphrase-multilingual-mpnet-base-v2',
        'name': 'SBERT Multilingual',
        'required': True,
        'size_gb': 0.4,
        'description': 'Sentence embeddings for similarity'
    },
    'comet_ref': {
        'id': 'Unbabel/wmt22-comet-da',
        'name': 'COMET Reference',
        'required': False,
        'size_gb': 0.5,
        'description': 'COMET reference-based quality estimation'
    },
    'comet_qe': {
        'id': 'Unbabel/wmt22-cometkiwi-da',
        'name': 'COMET-QE',
        'required': False,
        'size_gb': 0.5,
        'description': 'COMET quality estimation without reference'
    }
}


def verify_models():
    """Verify all required models are available."""
    model_manager = ModelManager()
    gpu_detector = GPUDetector()
    
    print("=" * 80)
    print("MODEL VERIFICATION REPORT")
    print("=" * 80)
    print()
    
    # Check GPU
    print("GPU Status:")
    if gpu_detector.is_cuda_available():
        gpus = gpu_detector.get_gpu_info()
        print(f"  ✅ CUDA Available")
        print(f"  ✅ GPUs Detected: {len(gpus)}")
        for gpu in gpus:
            print(f"     - {gpu.name}: {gpu.available_memory_gb:.1f}GB available")
    else:
        print(f"  WARNING: CUDA Not Available (will use CPU)")
    print()
    
    # Check models
    print("Model Status:")
    all_available = True
    required_available = True
    
    for model_key, model_info in REQUIRED_MODELS.items():
        model_id = model_info['id']
        model_path = model_manager.get_model_path(model_id)
        
        if model_path and model_path.exists():
            status = "[OK]"
            available = True
        else:
            if model_info['required']:
                status = "[MISSING]"
                available = False
                required_available = False
            else:
                status = "[OPTIONAL]"
                available = False
            all_available = False
        
        print(f"  {status} {model_info['name']} ({model_id})")
        print(f"     Required: {'Yes' if model_info['required'] else 'No (Optional)'}")
        print(f"     Size: {model_info['size_gb']}GB")
        print(f"     Status: {'Downloaded' if available else 'Not Downloaded'}")
        if model_path:
            print(f"     Path: {model_path}")
        print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    if required_available:
        print("[PASS] All REQUIRED models are available")
    else:
        print("[FAIL] Some REQUIRED models are missing")
        print("\nTo download missing models, use:")
        print("  python -m shared.models.model_manager download <model_id>")
    
    if all_available:
        print("[PASS] All models (including optional) are available")
    else:
        print("[WARN] Some optional models are missing (functionality may be limited)")
    
    print()
    
    return required_available


if __name__ == "__main__":
    success = verify_models()
    sys.exit(0 if success else 1)

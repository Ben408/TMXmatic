"""
Model Loading Integration Tests

Tests actual model loading and basic inference.
Requires models to be downloaded.
"""
import pytest
import sys
from pathlib import Path
import torch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from local_gpu_translation.llm_translation.candidate_generator import CandidateGenerator
from shared.tqe.tqe import TQEEngine


@pytest.mark.integration
@pytest.mark.requires_models
class TestModelLoading:
    """Tests for actual model loading."""
    
    @pytest.fixture
    def model_manager(self):
        """Get model manager."""
        return ModelManager()
    
    @pytest.fixture
    def memory_manager(self):
        """Get memory manager."""
        return MemoryManager()
    
    def test_sbert_model_loading(self, model_manager):
        """Test loading SBERT model."""
        from sentence_transformers import SentenceTransformer
        
        model_id = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        model_path = model_manager.get_model_path(model_id)
        
        if not model_path or not model_path.exists():
            pytest.skip(f"SBERT model not downloaded: {model_id}")
        
        # Load model
        model = SentenceTransformer(str(model_path))
        
        # Test inference
        embeddings = model.encode(["Hello world", "Bonjour le monde"])
        
        assert embeddings is not None
        assert len(embeddings) == 2
        assert embeddings[0].shape[0] > 0
    
    def test_translategemma_model_loading(self, model_manager, memory_manager):
        """Test loading translategemma model."""
        model_id = "google/translategemma-12b-it"
        model_path = model_manager.get_model_path(model_id)
        
        if not model_path or not model_path.exists():
            pytest.skip(f"translategemma model not downloaded: {model_id}")
        
        # Check GPU
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # Initialize candidate generator
        generator = CandidateGenerator(
            model_manager, memory_manager,
            device=device,
            model_id=model_id,
            num_candidates=2  # Small for testing
        )
        
        # Load model
        generator._load_model()
        
        assert generator.model is not None
        assert generator.tokenizer is not None
        assert generator._model_loaded is True
    
    def test_translategemma_generation(self, model_manager, memory_manager):
        """Test actual translation generation."""
        model_id = "google/translategemma-12b-it"
        model_path = model_manager.get_model_path(model_id)
        
        if not model_path or not model_path.exists():
            pytest.skip(f"translategemma model not downloaded: {model_id}")
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        generator = CandidateGenerator(
            model_manager, memory_manager,
            device=device,
            model_id=model_id,
            num_candidates=2
        )
        
        # Load model
        generator._load_model()
        
        # Generate candidates
        prompt = "Translate to French: Hello world"
        candidates = generator.generate_candidates(prompt, max_length=50)
        
        assert len(candidates) > 0
        assert all(isinstance(c, str) for c in candidates)
        assert all(len(c) > 0 for c in candidates)
    
    def test_tqe_engine_model_loading(self):
        """Test TQE engine with models."""
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
        model_manager = ModelManager()
        sbert_path = model_manager.get_model_path(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        
        if not sbert_path or not sbert_path.exists():
            pytest.skip("SBERT model not downloaded")
        
        # Initialize TQE engine with SBERT
        tqe_engine = TQEEngine(
            device=device,
            sbert_name="sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        
        assert tqe_engine.sbert_model is not None
        
        # Test scoring
        source = "Hello world"
        candidate = "Bonjour le monde"
        reference = "Bonjour le monde"  # Same as candidate for testing
        
        result = tqe_engine.score_candidate(
            candidate=candidate,
            source=source,
            reference=reference,
            uqlm_check=False
        )
        
        assert 'accuracy' in result
        assert 'fluency' in result
        assert 'tone' in result
        assert 'weighted' in result
        assert 'decision' in result

"""
Full Integration Test with Real Files

Tests complete translation workflow with actual XLIFF, TMX, and TBX files.
Requires models to be downloaded.
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.integration.workflow_manager import WorkflowManager
from local_gpu_translation.llm_translation.translator import Translator
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from shared.tqe.tqe import TQEEngine
from shared.gpu.detector import GPUDetector


# Test file paths (user-provided)
TEST_XLIFF = Path(r"C:\Users\bjcor\Desktop\Sage Local\SW XLIFF\error message.xlf")
TEST_TBX = Path(r"C:\Users\bjcor\Desktop\Sage Local\SDMO Glossary\SDMO_multilingual_merged.tbx")
TEST_TMX_DIR = Path(r"C:\Users\bjcor\Desktop\TMXmatic\Test_files")


@pytest.mark.integration
@pytest.mark.requires_models
class TestFullWorkflowRealFiles:
    """Full integration tests with real files and models."""
    
    @pytest.fixture
    def check_models(self):
        """Check if models are available."""
        model_manager = ModelManager()
        
        # Check required models
        translategemma_path = model_manager.get_model_path("google/translategemma-12b-it")
        sbert_path = model_manager.get_model_path(
            "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
        )
        
        if not translategemma_path or not translategemma_path.exists():
            pytest.skip("translategemma-12b-it model not downloaded")
        
        if not sbert_path or not sbert_path.exists():
            pytest.skip("SBERT model not downloaded")
    
    @pytest.fixture
    def check_test_files(self):
        """Check if test files are available."""
        if not TEST_XLIFF.exists():
            pytest.skip(f"Test XLIFF not found: {TEST_XLIFF}")
        
        if not TEST_TBX.exists():
            pytest.skip(f"Test TBX not found: {TEST_TBX}")
    
    @pytest.fixture
    def setup_workflow(self, check_models, check_test_files):
        """Set up workflow with real models."""
        model_manager = ModelManager()
        memory_manager = MemoryManager()
        gpu_detector = GPUDetector()
        
        # Check GPU
        device = "cuda" if gpu_detector.is_cuda_available() else "cpu"
        
        # Initialize translator
        translator = Translator(
            model_manager, memory_manager,
            device=device,
            num_candidates=3  # Reduced for testing
        )
        
        # Initialize TQE engine
        tqe_engine = TQEEngine(device=device)
        
        # Create workflow manager
        workflow_manager = WorkflowManager(translator, tqe_engine)
        
        return workflow_manager, device
    
    def test_full_workflow_xliff_only(self, setup_workflow, temp_dir):
        """Test full workflow with XLIFF only."""
        workflow_manager, device = setup_workflow
        
        output_path = temp_dir / "output_xliff_only.xlf"
        
        stats = workflow_manager.process_xliff(
            TEST_XLIFF, output_path,
            src_lang="en", tgt_lang="fr",
            batch_size=10,  # Small batch for testing
            save_interval=5
        )
        
        assert stats['processed'] > 0
        assert output_path.exists()
        assert stats['errors'] < stats['total']  # Some success
    
    def test_full_workflow_with_tmx(self, setup_workflow, temp_dir):
        """Test full workflow with XLIFF and TMX."""
        workflow_manager, device = setup_workflow
        
        # Find TMX file in test directory
        tmx_files = list(TEST_TMX_DIR.glob("*.tmx")) if TEST_TMX_DIR.exists() else []
        if not tmx_files:
            pytest.skip("No TMX files found in test directory")
        
        tmx_path = tmx_files[0]
        
        # Setup workflow with TMX
        workflow_manager.setup_workflow(
            TEST_XLIFF, tmx_path, None,
            src_lang="en", tgt_lang="fr"
        )
        
        output_path = temp_dir / "output_with_tmx.xlf"
        
        stats = workflow_manager.process_xliff(
            TEST_XLIFF, output_path,
            src_lang="en", tgt_lang="fr",
            batch_size=10
        )
        
        assert stats['processed'] > 0
        assert stats.get('exact_matches', 0) >= 0  # May have exact matches
        assert output_path.exists()
    
    def test_full_workflow_with_tbx(self, setup_workflow, temp_dir):
        """Test full workflow with XLIFF and TBX."""
        workflow_manager, device = setup_workflow
        
        # Setup workflow with TBX
        workflow_manager.setup_workflow(
            TEST_XLIFF, None, TEST_TBX,
            src_lang="en", tgt_lang="fr"
        )
        
        output_path = temp_dir / "output_with_tbx.xlf"
        
        stats = workflow_manager.process_xliff(
            TEST_XLIFF, output_path,
            src_lang="en", tgt_lang="fr",
            batch_size=10
        )
        
        assert stats['processed'] > 0
        assert output_path.exists()
    
    def test_full_workflow_all_assets(self, setup_workflow, temp_dir):
        """Test full workflow with XLIFF, TMX, and TBX."""
        workflow_manager, device = setup_workflow
        
        # Find TMX file
        tmx_files = list(TEST_TMX_DIR.glob("*.tmx")) if TEST_TMX_DIR.exists() else []
        tmx_path = tmx_files[0] if tmx_files else None
        
        # Setup workflow with all assets
        workflow_manager.setup_workflow(
            TEST_XLIFF, tmx_path, TEST_TBX,
            src_lang="en", tgt_lang="fr"
        )
        
        output_path = temp_dir / "output_all_assets.xlf"
        
        stats = workflow_manager.process_xliff(
            TEST_XLIFF, output_path,
            src_lang="en", tgt_lang="fr",
            batch_size=10
        )
        
        assert stats['processed'] > 0
        assert output_path.exists()
        
        # Verify output has translations
        from shared.tqe.xliff_utils import parse_xliff
        tree, tus = parse_xliff(str(output_path))
        assert len(tus) > 0
        
        # Check that some TUs have translations
        tus_with_targets = [tu for tu in tus if tu.get('tgt')]
        assert len(tus_with_targets) > 0

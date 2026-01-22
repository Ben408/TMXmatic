"""
Integration tests for translation workflow.

Tests end-to-end translation workflow with XLIFF, TMX, and TBX.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path
import tempfile

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.integration.workflow_manager import WorkflowManager
from local_gpu_translation.llm_translation.translator import Translator
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager
from shared.tqe.tqe import TQEEngine


class TestTranslationWorkflow:
    """Tests for translation workflow integration."""
    
    @pytest.fixture
    def mock_translator(self):
        """Create mock translator."""
        model_manager = Mock(spec=ModelManager)
        memory_manager = Mock(spec=MemoryManager)
        translator = Mock(spec=Translator)
        translator.load_termbase.return_value = True
        translator.translate_segment.return_value = ["Translation 1", "Translation 2"]
        return translator
    
    @pytest.fixture
    def mock_tqe_engine(self):
        """Create mock TQE engine."""
        engine = Mock(spec=TQEEngine)
        return engine
    
    def test_workflow_manager_initialization(self, mock_translator, mock_tqe_engine):
        """Test WorkflowManager initialization."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        assert manager.translator == mock_translator
        assert manager.tqe_engine == mock_tqe_engine
    
    def test_detect_assets_all(self, mock_translator, mock_tqe_engine, temp_dir):
        """Test asset detection with all assets."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        xliff = temp_dir / "test.xlf"
        tmx = temp_dir / "test.tmx"
        tbx = temp_dir / "test.tbx"
        xliff.touch()
        tmx.touch()
        tbx.touch()
        
        assets = manager.detect_assets(xliff, tmx, tbx)
        
        assert assets['xliff'] is True
        assert assets['tmx'] is True
        assert assets['tbx'] is True
    
    def test_detect_assets_xliff_only(self, mock_translator, mock_tqe_engine, temp_dir):
        """Test asset detection with XLIFF only."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        xliff = temp_dir / "test.xlf"
        xliff.touch()
        
        assets = manager.detect_assets(xliff, None, None)
        
        assert assets['xliff'] is True
        assert assets['tmx'] is False
        assert assets['tbx'] is False
    
    def test_setup_workflow_with_tmx(self, mock_translator, mock_tqe_engine, temp_dir, sample_tmx_path):
        """Test workflow setup with TMX."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        xliff = temp_dir / "test.xlf"
        xliff.touch()
        
        if sample_tmx_path.exists():
            result = manager.setup_workflow(xliff, sample_tmx_path, None, "en", "fr")
            assert result is True
            assert manager.tmx_matcher is not None
    
    def test_process_segment_exact_match(self, mock_translator, mock_tqe_engine):
        """Test processing segment with exact TMX match."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        # Create TMX matcher with exact match
        from local_gpu_translation.integration.tmx_matcher import TMXMatcher
        tmx_map = {"Hello": [{"target": "Bonjour", "is_human": True}]}
        manager.tmx_matcher = TMXMatcher(tmx_map=tmx_map)
        
        translation, match_type, candidates = manager.process_segment(
            "Hello", None, "en", "fr"
        )
        
        assert translation == "Bonjour"
        assert match_type == 'exact'
        assert len(candidates) == 1
    
    def test_process_segment_fuzzy_repair(self, mock_translator, mock_tqe_engine):
        """Test processing segment with fuzzy match requiring repair."""
        manager = WorkflowManager(mock_translator, mock_tqe_engine)
        
        # Create TMX matcher with fuzzy match
        from local_gpu_translation.integration.tmx_matcher import TMXMatcher
        tmx_map = {"Hello world": [{"target": "Bonjour le monde", "is_human": True}]}
        manager.tmx_matcher = TMXMatcher(tmx_map=tmx_map, fuzzy_threshold=0.75)
        
        # Mock translator to return repair candidates
        mock_translator.translate_segment.return_value = ["Bonjour le monde amélioré"]
        
        translation, match_type, candidates = manager.process_segment(
            "Hello worl", None, "en", "fr"
        )
        
        # Should use LLM repair for fuzzy match
        assert match_type in ['fuzzy_repair', 'new']
        assert translation is not None

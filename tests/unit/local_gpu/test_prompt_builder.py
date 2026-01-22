"""
Unit tests for prompt builder.
"""
import pytest
from unittest.mock import Mock, patch
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from local_gpu_translation.llm_translation.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """Tests for PromptBuilder class."""
    
    def test_prompt_builder_initialization(self):
        """Test PromptBuilder initialization."""
        builder = PromptBuilder()
        
        assert builder.prompt_manager is not None
    
    @patch('local_gpu_translation.llm_translation.prompt_builder.PromptManager')
    def test_build_translation_prompt_new_with_terms(self, mock_pm_class, temp_dir):
        """Test building new translation prompt with terms."""
        mock_pm = Mock()
        # Mock should return formatted prompt (PromptManager handles formatting)
        mock_pm.get_prompt.return_value = "Test prompt: Hello world hello → bonjour"
        mock_pm_class.return_value = mock_pm
        
        builder = PromptBuilder(mock_pm)
        terms = [{'src': 'hello', 'tgt': 'bonjour'}]
        
        prompt = builder.build_translation_prompt(
            source_text="Hello world",
            target_language="fr",
            terms=terms
        )
        
        assert prompt is not None
        assert 'Hello world' in prompt
        mock_pm.get_prompt.assert_called_once()
        call_args = mock_pm.get_prompt.call_args
        assert call_args[0][0] == 'new_translation_with_terms'
    
    @patch('local_gpu_translation.llm_translation.prompt_builder.PromptManager')
    def test_build_translation_prompt_fuzzy_repair(self, mock_pm_class):
        """Test building fuzzy repair prompt."""
        mock_pm = Mock()
        mock_pm.get_prompt.return_value = "Repair: {source_text} {fuzzy_translation}"
        mock_pm_class.return_value = mock_pm
        
        builder = PromptBuilder(mock_pm)
        
        prompt = builder.build_translation_prompt(
            source_text="Hello",
            target_language="fr",
            fuzzy_translation="Bonjour",
            similarity=0.85
        )
        
        assert prompt is not None
        call_args = mock_pm.get_prompt.call_args
        assert call_args[0][0] == 'fuzzy_repair_without_terms'
        assert 'similarity' in call_args[1]
    
    @patch('local_gpu_translation.llm_translation.prompt_builder.PromptManager')
    def test_build_translation_prompt_fallback(self, mock_pm_class):
        """Test prompt building with fallback when template not found."""
        mock_pm = Mock()
        mock_pm.get_prompt.return_value = None
        mock_pm_class.return_value = mock_pm
        
        builder = PromptBuilder(mock_pm)
        
        prompt = builder.build_translation_prompt(
            source_text="Hello",
            target_language="fr"
        )
        
        assert prompt is not None
        assert 'Hello' in prompt
        assert 'fr' in prompt

"""
Unit tests for prompt manager.

Tests prompt template loading, variable substitution, and template management.
"""
import pytest
import configparser
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from shared.config.prompt_manager import PromptManager


class TestPromptManager:
    """Tests for PromptManager class."""
    
    def test_prompt_manager_initialization(self, temp_dir):
        """Test PromptManager initialization."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        assert manager.prompts_dir == prompts_dir
        assert manager.templates_file.exists()  # Default templates should be created
    
    def test_default_templates_created(self, temp_dir):
        """Test that default templates are created."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        assert manager.templates_file.exists()
        
        # Verify default sections exist
        templates = manager._load_templates()
        assert 'fuzzy_repair_with_terms' in templates
        assert 'fuzzy_repair_without_terms' in templates
        assert 'new_translation_with_terms' in templates
        assert 'new_translation_without_terms' in templates
    
    def test_get_prompt_with_terms(self, temp_dir):
        """Test getting a prompt with term substitution."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        prompt = manager.get_prompt(
            'fuzzy_repair_with_terms',
            source_text='Hello',
            fuzzy_translation='Bonjour',
            similarity=85,
            term_list='term1, term2'
        )
        
        assert prompt is not None
        assert 'Hello' in prompt
        assert 'Bonjour' in prompt
        assert '85' in prompt
        assert 'term1' in prompt or 'term2' in prompt
    
    def test_get_prompt_without_terms(self, temp_dir):
        """Test getting a prompt without terms."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        prompt = manager.get_prompt(
            'fuzzy_repair_without_terms',
            source_text='Hello',
            fuzzy_translation='Bonjour',
            similarity=85
        )
        
        assert prompt is not None
        assert 'Hello' in prompt
        assert 'Bonjour' in prompt
    
    def test_get_prompt_not_found(self, temp_dir):
        """Test getting a non-existent prompt type."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        prompt = manager.get_prompt('nonexistent_prompt')
        
        assert prompt is None
    
    def test_get_prompt_missing_variables(self, temp_dir):
        """Test getting a prompt with missing variables."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        # Get prompt without all required variables
        prompt = manager.get_prompt('fuzzy_repair_with_terms', source_text='Hello')
        
        # Should still return a prompt (with missing variables replaced)
        assert prompt is not None
    
    def test_update_prompt(self, temp_dir):
        """Test updating a prompt template."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        new_prompt = "Custom prompt: {source_text}"
        result = manager.update_prompt('fuzzy_repair_with_terms', new_prompt)
        
        assert result is True
        
        # Verify update
        prompt = manager.get_prompt('fuzzy_repair_with_terms', source_text='Test')
        assert 'Custom prompt' in prompt
        assert 'Test' in prompt
    
    def test_update_prompt_new_section(self, temp_dir):
        """Test updating a prompt that creates a new section."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        new_prompt = "New prompt type: {source_text}"
        result = manager.update_prompt('custom_prompt', new_prompt)
        
        assert result is True
        
        # Verify new section exists
        prompt = manager.get_prompt('custom_prompt', source_text='Test')
        assert prompt is not None
        assert 'New prompt type' in prompt
    
    def test_list_prompt_types(self, temp_dir):
        """Test listing available prompt types."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        prompt_types = manager.list_prompt_types()
        
        assert len(prompt_types) > 0
        assert 'fuzzy_repair_with_terms' in prompt_types
        assert 'new_translation_with_terms' in prompt_types
    
    def test_validate_template_valid(self, temp_dir):
        """Test validating a valid prompt template."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        valid_prompt = "This is a valid prompt template with {variable} substitution."
        is_valid, error = manager.validate_template(valid_prompt)
        
        assert is_valid is True
        assert error is None
    
    def test_validate_template_empty(self, temp_dir):
        """Test validating an empty prompt template."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        is_valid, error = manager.validate_template('')
        
        assert is_valid is False
        assert error is not None
        assert 'empty' in error.lower()
    
    def test_validate_template_too_short(self, temp_dir):
        """Test validating a prompt template that's too short."""
        prompts_dir = temp_dir / 'prompts'
        manager = PromptManager(prompts_dir=prompts_dir)
        
        is_valid, error = manager.validate_template('short')
        
        assert is_valid is False
        assert error is not None
        assert 'short' in error.lower()

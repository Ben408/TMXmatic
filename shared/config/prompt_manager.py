"""
Prompt Template Management

Handles externalized prompt templates in INI format.
"""
import logging
import configparser
from pathlib import Path
from typing import Optional, Dict, List
import os

logger = logging.getLogger(__name__)


class PromptManager:
    """
    Manages prompt templates stored in INI format.
    
    Features:
    - Load prompt templates from INI files
    - Template variable substitution
    - Support for multiple prompt types (with/without terms)
    - User-editable templates
    """
    
    # Prompt template sections
    PROMPT_SECTIONS = [
        'fuzzy_repair_with_terms',
        'fuzzy_repair_without_terms',
        'new_translation_with_terms',
        'new_translation_without_terms'
    ]
    
    def __init__(self, prompts_dir: Optional[Path] = None):
        """
        Initialize PromptManager.
        
        Args:
            prompts_dir: Directory containing prompt templates. If None, uses default.
        """
        if prompts_dir is None:
            # Default to project root / config / prompts
            project_root = Path(__file__).parent.parent.parent.parent
            prompts_dir = project_root / 'config' / 'prompts'
        
        self.prompts_dir = Path(prompts_dir)
        self.prompts_dir.mkdir(parents=True, exist_ok=True)
        
        self.templates_file = self.prompts_dir / 'prompt_templates.ini'
        self._templates: Optional[configparser.ConfigParser] = None
        
        # Initialize default templates if file doesn't exist
        if not self.templates_file.exists():
            self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default prompt templates."""
        # Disable interpolation to allow {variable} syntax
        config = configparser.ConfigParser(interpolation=None)
        
        # Fuzzy repair with terms
        config['fuzzy_repair_with_terms'] = {
            'prompt': '''You are a professional translator. The following is a fuzzy match translation (approximately {similarity}% similarity) for the source text. Please repair and improve this translation to better match the source while maintaining the meaning and correct terminology.

IMPORTANT: Preserve all XML tags in the correct order and position. Do not modify, remove, or add tags.

Source: {source_text}
Fuzzy Translation: {fuzzy_translation}
Approved Terms (use these when applicable): {term_list}

Please provide an improved translation that:
1. Better matches the source text
2. Uses approved terminology when applicable
3. Maintains correct grammar and fluency
4. Preserves all XML tags exactly as they appear
5. Maintains the same tone and style

Improved Translation:'''
        }
        
        # Fuzzy repair without terms
        config['fuzzy_repair_without_terms'] = {
            'prompt': '''You are a professional translator. The following is a fuzzy match translation (approximately {similarity}% similarity) for the source text. Please repair and improve this translation to better match the source while maintaining the meaning.

IMPORTANT: Preserve all XML tags in the correct order and position. Do not modify, remove, or add tags.

Source: {source_text}
Fuzzy Translation: {fuzzy_translation}

Please provide an improved translation that:
1. Better matches the source text
2. Maintains correct grammar and fluency
3. Preserves all XML tags exactly as they appear
4. Maintains the same tone and style

Improved Translation:'''
        }
        
        # New translation with terms
        config['new_translation_with_terms'] = {
            'prompt': '''You are a professional translator. Please translate the following source text to the target language.

IMPORTANT: Preserve all XML tags in the correct order and position. Do not modify, remove, or add tags.

Source: {source_text}
Target Language: {target_language}
Approved Terms (use these when applicable): {term_list}

Please provide a translation that:
1. Accurately conveys the meaning of the source
2. Uses approved terminology when applicable
3. Maintains correct grammar and fluency
4. Preserves all XML tags exactly as they appear
5. Maintains appropriate tone and style

Translation:'''
        }
        
        # New translation without terms
        config['new_translation_without_terms'] = {
            'prompt': '''You are a professional translator. Please translate the following source text to the target language.

IMPORTANT: Preserve all XML tags in the correct order and position. Do not modify, remove, or add tags.

Source: {source_text}
Target Language: {target_language}

Please provide a translation that:
1. Accurately conveys the meaning of the source
2. Maintains correct grammar and fluency
3. Preserves all XML tags exactly as they appear
4. Maintains appropriate tone and style

Translation:'''
        }
        
        # Save default templates
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                config.write(f)
            logger.info("Created default prompt templates")
        except Exception as e:
            logger.error(f"Error creating default templates: {e}")
    
    def _load_templates(self) -> configparser.ConfigParser:
        """Load prompt templates from file."""
        if self._templates is not None:
            return self._templates
        
        # Disable interpolation to allow {variable} syntax
        config = configparser.ConfigParser(interpolation=None)
        
        if self.templates_file.exists():
            try:
                config.read(self.templates_file, encoding='utf-8')
                self._templates = config
                logger.debug("Loaded prompt templates")
            except Exception as e:
                logger.error(f"Error loading prompt templates: {e}")
                self._templates = configparser.ConfigParser()
        else:
            self._templates = configparser.ConfigParser()
        
        return self._templates
    
    def get_prompt(self, prompt_type: str, **kwargs) -> Optional[str]:
        """
        Get a prompt template with variable substitution.
        
        Args:
            prompt_type: Type of prompt (e.g., 'fuzzy_repair_with_terms')
            **kwargs: Variables to substitute in the template
        
        Returns:
            Formatted prompt string, or None if template not found
        """
        templates = self._load_templates()
        
        if prompt_type not in templates:
            logger.warning(f"Prompt type '{prompt_type}' not found")
            return None
        
        try:
            prompt_template = templates[prompt_type].get('prompt', '')
            
            # Format template with provided variables
            # Handle missing variables gracefully
            try:
                formatted = prompt_template.format(**kwargs)
            except KeyError as e:
                logger.warning(f"Missing variable in prompt template: {e}")
                # Replace missing variables with placeholder
                formatted = prompt_template
                for key in kwargs:
                    formatted = formatted.replace(f'{{{key}}}', str(kwargs[key]))
                # Replace any remaining {variable} with empty string
                import re
                formatted = re.sub(r'\{[^}]+\}', '', formatted)
            
            return formatted
            
        except Exception as e:
            logger.error(f"Error getting prompt '{prompt_type}': {e}")
            return None
    
    def update_prompt(self, prompt_type: str, prompt_text: str) -> bool:
        """
        Update a prompt template.
        
        Args:
            prompt_type: Type of prompt to update
            prompt_text: New prompt text
        
        Returns:
            True if updated successfully, False otherwise
        """
        templates = self._load_templates()
        
        if prompt_type not in templates:
            # Create new section
            templates.add_section(prompt_type)
        
        templates[prompt_type]['prompt'] = prompt_text
        
        try:
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                templates.write(f)
            
            # Reload templates
            self._templates = None
            self._load_templates()
            
            logger.info(f"Updated prompt template: {prompt_type}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating prompt template '{prompt_type}': {e}")
            return False
    
    def list_prompt_types(self) -> List[str]:
        """
        List available prompt types.
        
        Returns:
            List of prompt type names
        """
        templates = self._load_templates()
        return list(templates.sections())
    
    def validate_template(self, prompt_text: str) -> tuple[bool, Optional[str]]:
        """
        Validate a prompt template.
        
        Args:
            prompt_text: Prompt text to validate
        
        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        if not prompt_text or not prompt_text.strip():
            return False, "Prompt template is empty"
        
        # Check for basic structure
        if len(prompt_text) < 10:
            return False, "Prompt template is too short"
        
        # Check for common required variables (optional check)
        # This is a basic validation - could be enhanced
        
        return True, None

"""
Prompt Builder

Builds prompts from externalized templates with term injection.
"""
import logging
from typing import Optional, List, Dict

from shared.config.prompt_manager import PromptManager

logger = logging.getLogger(__name__)


class PromptBuilder:
    """
    Builds prompts from externalized templates.
    
    Features:
    - Load prompts from prompt manager
    - Inject terms into prompts
    - Handle tag preservation instructions
    - Support multiple prompt types
    """
    
    def __init__(self, prompt_manager: Optional[PromptManager] = None):
        """
        Initialize PromptBuilder.
        
        Args:
            prompt_manager: Optional PromptManager instance
        """
        self.prompt_manager = prompt_manager or PromptManager()
    
    def build_translation_prompt(self, source_text: str, target_language: str,
                                 terms: Optional[List[Dict]] = None,
                                 fuzzy_translation: Optional[str] = None,
                                 similarity: Optional[float] = None) -> str:
        """
        Build a translation prompt.
        
        Args:
            source_text: Source text to translate
            target_language: Target language code
            terms: Optional list of terms to inject
            fuzzy_translation: Optional fuzzy match translation (for repair)
            similarity: Optional similarity score for fuzzy match
        
        Returns:
            Formatted prompt string
        """
        # Determine prompt type
        if fuzzy_translation:
            # Fuzzy repair prompt
            if terms:
                prompt_type = 'fuzzy_repair_with_terms'
            else:
                prompt_type = 'fuzzy_repair_without_terms'
        else:
            # New translation prompt
            if terms:
                prompt_type = 'new_translation_with_terms'
            else:
                prompt_type = 'new_translation_without_terms'
        
        # Format terms
        term_list = "None"
        if terms:
            term_list = ", ".join([f"{t['src']} → {t['tgt']}" for t in terms])
        
        # Build prompt variables
        kwargs = {
            'source_text': source_text,
            'target_language': target_language,
            'term_list': term_list
        }
        
        if fuzzy_translation:
            kwargs['fuzzy_translation'] = fuzzy_translation
            if similarity:
                kwargs['similarity'] = int(similarity * 100)
        
        # Get prompt from template
        prompt = self.prompt_manager.get_prompt(prompt_type, **kwargs)
        
        if prompt is None:
            logger.warning(f"Could not get prompt type '{prompt_type}', using fallback")
            # Fallback prompt
            if fuzzy_translation:
                prompt = f"Repair and improve this translation:\nSource: {source_text}\nFuzzy: {fuzzy_translation}\nImproved:"
            else:
                prompt = f"Translate to {target_language}:\n{source_text}\nTranslation:"
        
        return prompt

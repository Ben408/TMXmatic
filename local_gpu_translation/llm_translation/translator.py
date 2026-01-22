"""
Translator

Main translation orchestrator that coordinates candidate generation, term injection, and prompt building.
"""
import logging
from typing import List, Dict, Optional, Tuple

from local_gpu_translation.llm_translation.candidate_generator import CandidateGenerator
from local_gpu_translation.llm_translation.term_extractor import TermExtractor
from local_gpu_translation.llm_translation.prompt_builder import PromptBuilder
from shared.models.model_manager import ModelManager
from shared.models.memory_manager import MemoryManager

logger = logging.getLogger(__name__)


class Translator:
    """
    Main translation orchestrator.
    
    Coordinates:
    - Term extraction from termbases
    - Prompt building with term injection
    - Candidate generation via LLM
    - Model lifecycle management
    """
    
    def __init__(self, model_manager: ModelManager, memory_manager: MemoryManager,
                 prompt_manager=None, device: str = "cuda", num_candidates: int = 5):
        """
        Initialize Translator.
        
        Args:
            model_manager: ModelManager instance
            memory_manager: MemoryManager instance
            prompt_manager: Optional PromptManager instance
            device: Device to use
            num_candidates: Number of candidates to generate
        """
        self.model_manager = model_manager
        self.memory_manager = memory_manager
        
        self.candidate_generator = CandidateGenerator(
            model_manager, memory_manager, device=device, num_candidates=num_candidates
        )
        self.term_extractor = TermExtractor()
        self.prompt_builder = PromptBuilder(prompt_manager)
    
    def load_termbase(self, termbase_path, src_lang: str, tgt_lang: str) -> bool:
        """
        Load termbase for term injection.
        
        Args:
            termbase_path: Path to TBX or CSV termbase
            src_lang: Source language code
            tgt_lang: Target language code
        
        Returns:
            True if loaded successfully
        """
        return self.term_extractor.load_termbase(termbase_path, src_lang, tgt_lang)
    
    def translate_segment(self, source_text: str, target_language: str,
                          source_language: str = "en",
                          fuzzy_translation: Optional[str] = None,
                          similarity: Optional[float] = None) -> List[str]:
        """
        Translate a source segment.
        
        Args:
            source_text: Source text to translate
            target_language: Target language code
            source_language: Source language code
            fuzzy_translation: Optional fuzzy match to repair
            similarity: Optional similarity score
        
        Returns:
            List of translation candidates
        """
        # Extract terms if termbase loaded
        terms = []
        if self.term_extractor.term_db:
            terms = self.term_extractor.extract_terms_for_segment(
                source_text, source_language, target_language
            )
        
        # Build prompt
        prompt = self.prompt_builder.build_translation_prompt(
            source_text=source_text,
            target_language=target_language,
            terms=terms if terms else None,
            fuzzy_translation=fuzzy_translation,
            similarity=similarity
        )
        
        # Generate candidates
        try:
            candidates = self.candidate_generator.generate_candidates(prompt)
            logger.debug(f"Generated {len(candidates)} candidates for segment")
            return candidates
        except Exception as e:
            logger.error(f"Error generating translation candidates: {e}")
            # Return empty list on error (caller handles)
            return []

"""
TMX Matcher

Handles exact and fuzzy matching against TMX translation memory.
"""
import logging
from typing import Optional, Tuple, Dict, List
from rapidfuzz import fuzz

from shared.tqe.tmx_utils import parse_tmx, fuzzy_tmx_lookup

logger = logging.getLogger(__name__)


class TMXMatcher:
    """
    Matches source segments against TMX translation memory.
    
    Features:
    - Exact matching (100% similarity)
    - Fuzzy matching with configurable threshold
    - Returns match type and translation
    """
    
    def __init__(self, tmx_map: Optional[Dict[str, List[Dict]]] = None,
                 fuzzy_threshold: float = 0.75):
        """
        Initialize TMXMatcher.
        
        Args:
            tmx_map: Pre-loaded TMX translation memory map
            fuzzy_threshold: Threshold for fuzzy matching (0-1)
        """
        self.tmx_map = tmx_map or {}
        self.fuzzy_threshold = fuzzy_threshold
    
    def load_tmx(self, tmx_path: str) -> bool:
        """
        Load TMX file.
        
        Args:
            tmx_path: Path to TMX file
        
        Returns:
            True if loaded successfully
        """
        try:
            self.tmx_map = parse_tmx(tmx_path)
            logger.info(f"Loaded TMX with {len(self.tmx_map)} source entries")
            return True
        except Exception as e:
            logger.error(f"Error loading TMX {tmx_path}: {e}")
            return False
    
    def match(self, source_text: str) -> Tuple[Optional[str], str, float]:
        """
        Match source text against TMX.
        
        Args:
            source_text: Source text to match
        
        Returns:
            Tuple of (translation, match_type, similarity_score)
            match_type: 'exact', 'fuzzy', or 'none'
        """
        if not self.tmx_map:
            return None, 'none', 0.0
        
        # Check for exact match
        if source_text in self.tmx_map:
            entries = self.tmx_map[source_text]
            # Prefer human-marked translations
            for entry in entries:
                if entry.get("is_human", True):
                    return entry.get("target"), 'exact', 1.0
            # Fallback to first entry
            if entries:
                return entries[0].get("target"), 'exact', 1.0
        
        # Try fuzzy match
        match_result = fuzzy_tmx_lookup(source_text, self.tmx_map, 
                                       threshold=self.fuzzy_threshold)
        if match_result:
            translation, similarity = match_result
            match_type = 'fuzzy'
            return translation, match_type, similarity
        
        return None, 'none', 0.0
    
    def should_use_llm_repair(self, similarity: float) -> bool:
        """
        Determine if LLM repair should be used for fuzzy match.
        
        Args:
            similarity: Similarity score (0-1)
        
        Returns:
            True if LLM repair should be used
        """
        # Use LLM repair for high fuzzy matches (≥threshold)
        return similarity >= self.fuzzy_threshold and similarity < 1.0
    
    def should_generate_new(self, similarity: float) -> bool:
        """
        Determine if new translation should be generated.
        
        Args:
            similarity: Similarity score (0-1)
        
        Returns:
            True if new translation should be generated
        """
        # Generate new for low/no matches
        return similarity < self.fuzzy_threshold

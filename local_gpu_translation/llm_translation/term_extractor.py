"""
Term Extractor

Extracts relevant terms from TBX/CSV termbases and matches them to source segments.
"""
import logging
from typing import List, Dict, Optional, Tuple
from pathlib import Path

from shared.tqe.terminology import (
    load_terms_csv, load_terms_tbx, lookup_exact_term, fuzzy_lookup_term
)

logger = logging.getLogger(__name__)


class TermExtractor:
    """
    Extracts and manages terms for translation prompts.
    
    Features:
    - Load terms from TBX or CSV
    - Match terms to source segments
    - Select top-K most relevant terms
    - Format terms for prompt injection
    """
    
    def __init__(self, term_db=None):
        """
        Initialize TermExtractor.
        
        Args:
            term_db: Optional pre-loaded term database
        """
        self.term_db = term_db or {}
    
    def load_termbase(self, termbase_path: Path, src_lang: str, tgt_lang: str) -> bool:
        """
        Load termbase from file.
        
        Args:
            termbase_path: Path to TBX or CSV file
            src_lang: Source language code
            tgt_lang: Target language code
        
        Returns:
            True if loaded successfully, False otherwise
        """
        try:
            if termbase_path.suffix.lower() == '.tbx':
                db = load_terms_tbx(str(termbase_path))
            elif termbase_path.suffix.lower() == '.csv':
                db = load_terms_csv(str(termbase_path))
            else:
                logger.error(f"Unsupported termbase format: {termbase_path.suffix}")
                return False
            
            # Filter for relevant language pair
            key = (src_lang, tgt_lang)
            if key in db:
                self.term_db = db
                logger.info(f"Loaded {len(db[key])} terms from {termbase_path}")
                return True
            else:
                logger.warning(f"No terms found for language pair {src_lang}-{tgt_lang}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading termbase {termbase_path}: {e}")
            return False
    
    def extract_terms_for_segment(self, source_text: str, src_lang: str, tgt_lang: str,
                                  max_terms: int = 8, fuzzy_threshold: float = 0.8) -> List[Dict]:
        """
        Extract relevant terms for a source segment.
        
        Args:
            source_text: Source segment text
            src_lang: Source language code
            tgt_lang: Target language code
            max_terms: Maximum number of terms to return
            fuzzy_threshold: Threshold for fuzzy term matching
        
        Returns:
            List of term dictionaries with 'src', 'tgt', 'match_type'
        """
        if not self.term_db:
            return []
        
        key = (src_lang, tgt_lang)
        if key not in self.term_db:
            return []
        
        terms = []
        source_lower = source_text.lower()
        
        # Try exact matches first
        words = source_text.split()
        for word in words:
            word_clean = word.strip('.,!?;:()[]{}"\'')
            if not word_clean:
                continue
            
            exact = lookup_exact_term(word_clean, src_lang, tgt_lang, self.term_db)
            if exact and exact not in terms:
                terms.append({
                    'src': exact['src'],
                    'tgt': exact['tgt'],
                    'match_type': 'exact'
                })
        
        # Try fuzzy matches for remaining slots
        if len(terms) < max_terms:
            for entry in self.term_db[key]:
                if len(terms) >= max_terms:
                    break
                
                # Check if already added
                if any(t['src'] == entry['src'] for t in terms):
                    continue
                
                # Try fuzzy match
                fuzzy = fuzzy_lookup_term(entry['src'], src_lang, tgt_lang, 
                                         self.term_db, threshold=fuzzy_threshold)
                if fuzzy:
                    entry_match, score = fuzzy
                    # Check if term appears in source
                    if entry_match['src'].lower() in source_lower:
                        terms.append({
                            'src': entry_match['src'],
                            'tgt': entry_match['tgt'],
                            'match_type': 'fuzzy',
                            'score': score
                        })
        
        # Sort by match quality and return top-K
        # Exact matches first, then by score
        terms_sorted = sorted(terms, key=lambda x: (
            0 if x['match_type'] == 'exact' else 1,
            -x.get('score', 0)
        ))
        
        return terms_sorted[:max_terms]
    
    def format_terms_for_prompt(self, terms: List[Dict]) -> str:
        """
        Format terms for injection into prompt template.
        
        Args:
            terms: List of term dictionaries
        
        Returns:
            Formatted string for prompt
        """
        if not terms:
            return "None"
        
        formatted = []
        for term in terms:
            formatted.append(f"{term['src']} → {term['tgt']}")
        
        return ", ".join(formatted)

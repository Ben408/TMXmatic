"""
Workflow Manager

Orchestrates translation workflow based on available assets.
"""
import logging
from typing import Dict, List, Optional, Tuple
from pathlib import Path

from local_gpu_translation.llm_translation.translator import Translator
from local_gpu_translation.integration.tmx_matcher import TMXMatcher
from shared.tqe.xliff_utils import parse_xliff
from shared.tqe.tqe import TQEEngine

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Manages translation workflows based on available assets.
    
    Workflows:
    - XLIFF only → Translate missing segments
    - XLIFF + TMX → Match TMX first, then translate remaining
    - XLIFF + TMX + TBX → Full workflow with term injection
    """
    
    def __init__(self, translator: Translator, tqe_engine: Optional[TQEEngine] = None):
        """
        Initialize WorkflowManager.
        
        Args:
            translator: Translator instance
            tqe_engine: Optional TQE engine for scoring
        """
        self.translator = translator
        self.tqe_engine = tqe_engine
        self.tmx_matcher = None
    
    def detect_assets(self, xliff_path: Path, tmx_path: Optional[Path] = None,
                     tbx_path: Optional[Path] = None) -> Dict[str, bool]:
        """
        Detect available assets.
        
        Args:
            xliff_path: Path to XLIFF file
            tmx_path: Optional path to TMX file
            tbx_path: Optional path to TBX file
        
        Returns:
            Dictionary indicating which assets are available
        """
        assets = {
            'xliff': xliff_path.exists() if xliff_path else False,
            'tmx': tmx_path.exists() if tmx_path else False,
            'tbx': tbx_path.exists() if tbx_path else False
        }
        logger.info(f"Detected assets: {assets}")
        return assets
    
    def setup_workflow(self, xliff_path: Path, tmx_path: Optional[Path] = None,
                      tbx_path: Optional[Path] = None, src_lang: str = "en",
                      tgt_lang: str = "fr") -> bool:
        """
        Set up workflow based on available assets.
        
        Args:
            xliff_path: Path to XLIFF file
            tmx_path: Optional path to TMX file
            tbx_path: Optional path to TBX file
            src_lang: Source language code
            tgt_lang: Target language code
        
        Returns:
            True if setup successful
        """
        assets = self.detect_assets(xliff_path, tmx_path, tbx_path)
        
        # Load TMX if available
        if assets['tmx'] and tmx_path:
            self.tmx_matcher = TMXMatcher()
            if not self.tmx_matcher.load_tmx(str(tmx_path)):
                logger.warning("Failed to load TMX, continuing without TMX matching")
                self.tmx_matcher = None
        
        # Load TBX if available
        if assets['tbx'] and tbx_path:
            if not self.translator.load_termbase(tbx_path, src_lang, tgt_lang):
                logger.warning("Failed to load TBX, continuing without term injection")
        
        return True
    
    def process_segment(self, source_text: str, existing_target: Optional[str],
                       src_lang: str, tgt_lang: str) -> Tuple[Optional[str], str, List[str]]:
        """
        Process a single segment through the workflow.
        
        Args:
            source_text: Source text
            existing_target: Optional existing target translation
            src_lang: Source language code
            tgt_lang: Target language code
        
        Returns:
            Tuple of (best_translation, match_type, all_candidates)
            match_type: 'exact', 'fuzzy_repair', 'new', or 'existing'
        """
        # Check TMX match if available
        if self.tmx_matcher:
            translation, match_type, similarity = self.tmx_matcher.match(source_text)
            
            if match_type == 'exact':
                # Use TMX translation directly, skip LLM
                logger.debug(f"Exact TMX match for segment")
                return translation, 'exact', [translation]
            
            elif match_type == 'fuzzy' and self.tmx_matcher.should_use_llm_repair(similarity):
                # LLM repair for high fuzzy match
                logger.debug(f"Fuzzy match ({similarity:.2%}), using LLM repair")
                candidates = self.translator.translate_segment(
                    source_text=source_text,
                    target_language=tgt_lang,
                    source_language=src_lang,
                    fuzzy_translation=translation,
                    similarity=similarity
                )
                return candidates[0] if candidates else translation, 'fuzzy_repair', candidates
        
        # Generate new translation
        logger.debug("No TMX match, generating new translation")
        candidates = self.translator.translate_segment(
            source_text=source_text,
            target_language=tgt_lang,
            source_language=src_lang
        )
        
        if candidates:
            return candidates[0], 'new', candidates
        elif existing_target:
            return existing_target, 'existing', [existing_target]
        else:
            return None, 'none', []
    
    def process_xliff(self, xliff_path: Path, output_path: Path,
                     src_lang: str, tgt_lang: str,
                     batch_size: int = 100, save_interval: int = 50) -> Dict:
        """
        Process entire XLIFF file through workflow.
        
        Args:
            xliff_path: Input XLIFF path
            output_path: Output XLIFF path
            src_lang: Source language code
            tgt_lang: Target language code
            batch_size: Number of segments to process in batch
            save_interval: Save partial results every N segments
        
        Returns:
            Dictionary with processing statistics
        """
        tree, tu_list = parse_xliff(str(xliff_path))
        
        stats = {
            'total': len(tu_list),
            'processed': 0,
            'exact_matches': 0,
            'fuzzy_repairs': 0,
            'new_translations': 0,
            'errors': 0
        }
        
        candidates_map = {}
        
        # Process in batches
        for i, tu in enumerate(tu_list):
            try:
                source_text = tu['src']
                existing_target = tu['tgt']
                tu_id = tu['id']
                
                # Process segment
                best_translation, match_type, candidates = self.process_segment(
                    source_text, existing_target, src_lang, tgt_lang
                )
                
                if best_translation:
                    candidates_map[tu_id] = candidates
                    
                    # Calculate match rate for metadata
                    match_rate = 100.0 if match_type == 'exact' else (
                        85.0 if match_type == 'fuzzy_repair' else 0.0
                    )
                    
                    # Update XLIFF with translation and match rate
                    from local_gpu_translation.io.xliff_processor import XLIFFProcessor
                    processor = XLIFFProcessor(xliff_path)
                    processor.update_translation(tu_id, best_translation)
                    processor.write_match_rate(tu_id, match_rate, match_type)
                    
                    # Update statistics
                    if match_type == 'exact':
                        stats['exact_matches'] += 1
                    elif match_type == 'fuzzy_repair':
                        stats['fuzzy_repairs'] += 1
                    elif match_type == 'new':
                        stats['new_translations'] += 1
                    
                    stats['processed'] += 1
                else:
                    stats['errors'] += 1
                    logger.warning(f"No translation generated for TU {tu_id}")
                
                # Save partial results periodically
                if (i + 1) % save_interval == 0:
                    logger.info(f"Processed {i + 1}/{len(tu_list)} segments, saving partial results...")
                    # TODO: Save partial XLIFF with current translations
                
            except Exception as e:
                logger.error(f"Error processing segment {tu.get('id', 'unknown')}: {e}")
                stats['errors'] += 1
        
        # Score candidates if TQE engine available
        if self.tqe_engine and candidates_map:
            logger.info("Scoring translation candidates with TQE...")
            try:
                self.tqe_engine.score_xliff(
                    xliff_path=str(xliff_path),
                    candidates=candidates_map,
                    out_path=str(output_path)
                )
            except Exception as e:
                logger.error(f"Error scoring with TQE: {e}")
                # Fall back to writing without scoring
                from shared.tqe.xliff_utils import write_xliff
                write_xliff(tree, str(output_path))
        else:
            # Write without scoring
            from shared.tqe.xliff_utils import write_xliff
            write_xliff(tree, str(output_path))
        
        logger.info(f"Processing complete: {stats}")
        return stats

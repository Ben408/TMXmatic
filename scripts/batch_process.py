import os
import logging
from datetime import datetime
from .remove_old import remove_old_tus
from .remove_empty import empty_targets
from .remove_duplicates import find_true_duplicates
from .extract_ntds import extract_non_true_duplicates
from .remove_sentence import find_sentence_level_segments
from .tmx_utils import copy_xliff_roundtrip_sidecar, from_tmx
import pickle
from multiprocessing import Pool
import shutil
from pathlib import Path
from typing import List, Tuple, Optional, Sequence
import PythonTmx
import re
import lxml.etree as etree

class BatchProgress:
    def __init__(self):
        self.current_step = 0
        self.total_steps = 0
        self.current_operation = ""
        self.status = "pending"
        self.errors = []

    def update(self, step, operation):
        self.current_step = step
        self.current_operation = operation

class ProcessingReport:
    def __init__(self):
        self.start_time = datetime.now()
        self.steps_completed = []
        self.statistics = {
            'tus_processed': 0,
            'tus_removed': 0,
            'duplicates_found': 0,
            'empty_targets': 0
        }
        
    def generate_html(self):
        """Generate HTML report of processing results"""

class BatchConfig:
    def __init__(self):
        self.max_file_size_mb = 500
        self.backup_enabled = True
        self.checkpoint_interval = 1000  # TUs
        self.parallel_processing = False

class TMXLogger:
    def __init__(self, log_file):
        self.log_file = log_file
        self.debug_mode = False
        
    def log_operation(self, operation, details):
        """Log operation with detailed debugging if enabled"""

logger = logging.getLogger(__name__)
_FULL_MRK_WRAPPER_RE = re.compile(r'^\s*<mrk\b[^>]*>(.*?)</mrk>\s*$', re.IGNORECASE | re.DOTALL)


def _unwrap_full_mrk_wrapper(text: str) -> str:
    """
    If a segment is fully wrapped by a single <mrk ...>...</mrk>, unwrap it and keep inner text.
    Otherwise, return text unchanged.
    """
    match = _FULL_MRK_WRAPPER_RE.match(text or "")
    if not match:
        return text
    return match.group(1)

def batch_process_1_5(file_path: str) -> Tuple[str, List[str]]:
    """
    Process TMX file through steps 1-5:
    1. Remove empty targets
    2. Remove true duplicates
    3. Extract non-true duplicates
    4. Remove sentence-level segments
    5. Clean output
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to final TMX, List of intermediate file paths)
    """
    logger.info(f"Starting batch process 1-5 for: {file_path}")
    intermediate_files = []
    current_file = file_path

    try:
        # Step 1: Remove empty targets
        logger.info("Step 1: Removing empty targets")
        clean_file, empty_file = empty_targets(current_file)
        intermediate_files.append(empty_file)
        current_file = clean_file

        # Step 2: Remove true duplicates
        logger.info("Step 2: Removing true duplicates")
        clean_file, dups_file = find_true_duplicates(current_file)
        intermediate_files.append(dups_file)
        current_file = clean_file

        # Step 3: Extract non-true duplicates
        logger.info("Step 3: Extracting non-true duplicates")
        clean_file, ntd_file = extract_non_true_duplicates(current_file)
        intermediate_files.append(ntd_file)
        current_file = clean_file

        # Step 4: Remove sentence-level segments
        logger.info("Step 4: Removing sentence-level segments")
        final_file, sentence_file = find_sentence_level_segments(current_file)
        intermediate_files.append(sentence_file)

        logger.info("Batch process 1-5 completed successfully")
        return final_file, intermediate_files

    except Exception as e:
        logger.error(f"Error in batch process 1-5: {e}")
        raise


def _strip_tmx_namespace_tags(root: etree._Element) -> None:
    """from_element matches tags like 'tmx'; strip namespace prefixes from lxml tree."""
    for elem in root.iter():
        if isinstance(elem.tag, str) and elem.tag.startswith("{"):
            elem.tag = elem.tag.split("}", 1)[1]


def _load_tmx_object(file_path: str) -> PythonTmx.Tmx:
    """Parse TMX file into a PythonTmx.Tmx (Tmx is a dataclass; it is not callable with a path)."""
    path = str(file_path)
    tm = None
    try:
        tm = etree.parse(path)
    except Exception:
        pass
    if tm is None:
        try:
            tm = etree.parse(path, etree.XMLParser(recover=True))
        except Exception:
            tm = None
    if tm is None:
        for encoding in ("utf-8", "cp1252", "latin-1"):
            try:
                parser = etree.XMLParser(encoding=encoding, recover=True)
                tm = etree.parse(path, parser)
                if tm is not None and tm.getroot() is not None:
                    break
            except Exception:
                continue
    if tm is None or tm.getroot() is None:
        raise ValueError(f"Could not parse TMX file: {path}")
    root = tm.getroot()
    _strip_tmx_namespace_tags(root)
    parsed = PythonTmx.from_element(root, keep_extra=True)
    if not isinstance(parsed, PythonTmx.Tmx):
        raise ValueError("TMX root element did not parse to a Tmx object")
    return parsed


def _write_mt_training_outputs(
    source_tmx_path: str,
    clean_tmx: PythonTmx.Tmx,
    tag_removed: List[PythonTmx.Tu],
    invalid: List[PythonTmx.Tu],
) -> Tuple[str, str]:
    """Write MT-ready TMX and a TMX of segments removed by clean_for_mt."""
    input_path = Path(source_tmx_path)
    out_dir = input_path.parent
    mt_path = out_dir / f"mt_{input_path.name}"
    removed_path = out_dir / f"removed_mt_{input_path.name}"

    clean_root = PythonTmx.to_element(clean_tmx, True)
    etree.ElementTree(clean_root).write(str(mt_path), encoding="utf-8", xml_declaration=True)

    removed_tmx = PythonTmx.Tmx(header=clean_tmx.header, tus=[*tag_removed, *invalid])
    removed_root = PythonTmx.to_element(removed_tmx, True)
    etree.ElementTree(removed_root).write(str(removed_path), encoding="utf-8", xml_declaration=True)

    copy_xliff_roundtrip_sidecar(str(source_tmx_path), str(mt_path), str(removed_path))
    return str(mt_path), str(removed_path)


def batch_process_1_5_9(
    file_path: str,
    cutoff_date: Optional[datetime] = None,
    selected_steps: Optional[Sequence[str]] = None,
) -> Tuple[str, List[str]]:
    """
    Process TMX file through steps 1-5 plus step 9, then MT training pass:
    1-5. All steps from batch_process_1_5
    9. Remove old TUs (optional, if cutoff_date)
    MT. clean_for_mt — tag stripping and MT-oriented filters; writes mt_*.tmx

    Args:
        file_path: Path to TMX file
        cutoff_date: Optional date for removing old TUs

    Returns:
        tuple: (Path to final MT-ready TMX, List of intermediate file paths)
    """
    logger.info(f"Starting batch process 1-5-9 for: {file_path}")

    try:
        step_order = ["remove_empty", "find_duplicates", "non_true_duplicates", "remove_sentence", "remove_old"]
        enabled_steps = list(selected_steps) if selected_steps is not None else step_order[:-1]
        current_file = file_path
        intermediate_files: List[str] = []

        if "remove_empty" in enabled_steps:
            logger.info("Step 1: Removing empty targets")
            clean_file, empty_file = empty_targets(current_file)
            intermediate_files.append(empty_file)
            current_file = clean_file

        if "find_duplicates" in enabled_steps:
            logger.info("Step 2: Removing true duplicates")
            clean_file, dups_file = find_true_duplicates(current_file)
            intermediate_files.append(dups_file)
            current_file = clean_file

        if "non_true_duplicates" in enabled_steps:
            logger.info("Step 3: Extracting non-true duplicates")
            clean_file, ntd_file = extract_non_true_duplicates(current_file)
            intermediate_files.append(ntd_file)
            current_file = clean_file

        if "remove_sentence" in enabled_steps:
            logger.info("Step 4: Removing sentence-level segments")
            clean_file, sentence_file = find_sentence_level_segments(current_file)
            intermediate_files.append(sentence_file)
            current_file = clean_file

        # Step 9: Remove old TUs if cutoff date provided
        if "remove_old" in enabled_steps and cutoff_date:
            logger.info(f"Step 9: Removing TUs older than {cutoff_date}")
            clean_file, old_file = remove_old_tus(current_file, cutoff_date)
            intermediate_files.append(old_file)
            current_file = clean_file
        elif "remove_old" in enabled_steps and not cutoff_date:
            logger.info("Step 9 selected, but no cutoff date supplied. Skipping remove_old_tus.")

        final_file = current_file

        logger.info("Step MT: clean_for_mt (final pass for MT training)")
        clean_tmx, tag_removed, invalid = clean_for_mt(final_file)
        mt_path, removed_mt_path = _write_mt_training_outputs(
            final_file, clean_tmx, tag_removed, invalid
        )
        intermediate_files.append(removed_mt_path)

        logger.info("Batch process 1-5-9 (including MT pass) completed successfully")
        return mt_path, intermediate_files

    except Exception as e:
        logger.error(f"Error in batch process 1-5-9: {e}")
        raise

def check_file_size(file_path, max_size_mb=500):
    """Verify file size is manageable"""
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > max_size_mb:
        raise ValueError(f"File too large ({size_mb:.1f}MB). Maximum size is {max_size_mb}MB")

def save_checkpoint(state, filepath):
    """Save processing state for potential recovery"""
    with open(filepath, 'wb') as f:
        pickle.dump(state, f)

def resume_from_checkpoint(filepath):
    """Resume processing from last successful step"""
    pass  # Add implementation later

def parallel_batch_process(source_file, num_workers=4):
    """Process large files in parallel where possible"""
    with Pool(num_workers) as pool:
        # Split processing for compatible operations
        pass  # Add implementation later

def create_backup(file_path):
    """Create a backup of the file"""
    backup_path = file_path + '.bak'
    with open(file_path, 'rb') as source:
        with open(backup_path, 'wb') as target:
            target.write(source.read())
    return backup_path

def validate_tmx_output(file_path):
    """Verify output TMX integrity"""
    try:
        tm = from_tmx(file_path)
        # Run various quality checks
        return True
    except Exception as e:
        return False

def clean_for_mt(tmx_file: str) -> Tuple[PythonTmx.Tmx, List[PythonTmx.Tu], List[PythonTmx.Tu]]:
    """
    Clean TMX for MT training by removing tags and applying additional filters.
    
    Args:
        tmx_file: Path to TMX file
    
    Returns:
        tuple: (Cleaned TMX, List of tag-removed TUs, List of short/invalid TUs)
    """
    logger.info(f"Starting MT cleaning for: {tmx_file}")

    # Compile regex patterns
    tag_pattern = re.compile(r'<[^>]+>')
    whitespace_pattern = re.compile(r'\s+')
    placeholder_pattern = re.compile(r'(%[sdfi]|\{\d+\}|\[\[\w+\]\])')  # Common software placeholders
    bullet_pattern = re.compile(r'^[•▪⚫⚪◦◆◇■□●○]+$')  # Common bullet points
    number_only_pattern = re.compile(r'^\d+$')
    
    try:
        tmx = _load_tmx_object(tmx_file)
        clean_tmx = PythonTmx.Tmx(header=tmx.header, tus=[])
        source_lang = (tmx.header.srclang or "en").lower()

        tag_removed_tus = []  # TUs removed due to tag content
        invalid_tus = []      # TUs removed due to length/content

        for tu in tmx.tus:
            source_text = ""
            target_text = ""
            original_source = ""
            original_target = ""
            
            # Process each TUV
            for tuv in tu.tuvs:
                # Get original text for comparison
                original_text = ' '.join(str(seg) for seg in tuv.content)
                original_text = _unwrap_full_mrk_wrapper(original_text)
                
                # Clean the text
                text = original_text
                text = tag_pattern.sub(' ', text)  # Remove XML tags
                text = whitespace_pattern.sub(' ', text).strip()  # Normalize whitespace
                
                # Store based on language (source = TMX header srclang)
                if tuv.lang.lower() == source_lang:
                    source_text = text
                    original_source = original_text
                else:
                    target_text = text
                    original_target = original_text
            
            # Skip if either source or target is empty after cleaning
            if not source_text or not target_text:
                tag_removed_tus.append(tu)
                continue
            
            # Check for minimum content (modified for UI strings)
            source_words = [w for w in source_text.split() if w.strip()]
            target_words = [w for w in target_text.split() if w.strip()]
            
            # Special handling for UI commands and short phrases
            is_ui_command = any(cmd in source_text.lower() for cmd in 
                              ['click', 'select', 'choose', 'enter', 'type', 'press'])
            
            # Skip length check for UI commands
            if not is_ui_command:
                if len(source_words) < 3 or len(target_words) < 3:
                    invalid_tus.append(tu)
                    continue
            else:
                # For UI commands, ensure there's at least meaningful content
                if len(source_words) < 1 or len(target_words) < 1:
                    invalid_tus.append(tu)
                    continue
            
            # Check for bullet-only or number-only content
            if (bullet_pattern.match(source_text) or bullet_pattern.match(target_text) or
                number_only_pattern.match(source_text) or number_only_pattern.match(target_text)):
                invalid_tus.append(tu)
                continue
            
            # Preserve placeholders
            source_placeholders = placeholder_pattern.findall(original_source)
            target_placeholders = placeholder_pattern.findall(original_target)
            
            # If source has placeholders but they're missing in target (or vice versa)
            if len(source_placeholders) != len(target_placeholders):
                invalid_tus.append(tu)
                continue
            
            # Check length ratio (to catch potentially misaligned segments)
            source_length = len(source_words)
            target_length = len(target_words)
            if max(source_length, target_length) / min(source_length, target_length) > 3:
                invalid_tus.append(tu)
                continue
            
            # Create new TU with cleaned content
            clean_tu = PythonTmx.Tu()
            tgt_lang = tmx.header.srclang or "en"
            for tuv in tu.tuvs:
                if tuv.lang.lower() != source_lang:
                    tgt_lang = tuv.lang
                    break

            src_tuv = PythonTmx.Tuv(lang=tmx.header.srclang or "en")
            src_tuv.content = source_text
            clean_tu.tuvs.append(src_tuv)

            tgt_tuv = PythonTmx.Tuv(lang=tgt_lang)
            tgt_tuv.content = target_text
            clean_tu.tuvs.append(tgt_tuv)
            
            clean_tmx.tus.append(clean_tu)
        
        logger.info(f"MT cleaning complete: {len(clean_tmx.tus)} TUs kept, "
                   f"{len(tag_removed_tus)} removed due to tags, "
                   f"{len(invalid_tus)} removed due to content/length")
        
        return clean_tmx, tag_removed_tus, invalid_tus
        
    except Exception as e:
        logger.error(f"Error in MT cleaning: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    include_date = input("Include date filtering? (y/n): ").lower() == 'y'
    
    try:
        if include_date:
            date_str = input("Enter cutoff date (YYYY-MM-DD): ")
            cutoff_date = datetime.strptime(date_str, "%Y-%m-%d")
            final_file, intermediates = batch_process_1_5_9(file_path, cutoff_date)
        else:
            final_file, intermediates = batch_process_1_5(file_path)
        
        print(f"Final file created: {final_file}")
        print("Intermediate files:")
        for f in intermediates:
            print(f"- {f}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
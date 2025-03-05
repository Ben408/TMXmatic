import sys
import os

# Add the parent directory of PythonTmx to the path
tmx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmx', 'Lib', 'site-packages')
if tmx_path not in sys.path:
    sys.path.insert(0, tmx_path)

import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Set
import math

logger = logging.getLogger(__name__)

def split_by_language(file_path: str) -> List[str]:
    """
    Split TMX file into separate files by target language.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        List[str]: Paths to created TMX files
    """
    logger.info(f"Splitting by language: {file_path}")
    
    try:
        input_path = Path(file_path)
        tmx = PythonTmx.Tmx(str(input_path))
        source_lang = tmx.header.srclang
        
        # Track languages and their TUs
        language_tus: Dict[str, PythonTmx.Tmx] = {}
        created_files: List[str] = []
        
        # Process TUs
        for tu in tmx.tus:
            target_langs: Set[str] = set()
            
            # Find target languages in TU
            for tuv in tu.tuvs:
                if tuv.lang != source_lang:
                    target_langs.add(tuv.lang)
            
            # Create TMX for each target language
            for lang in target_langs:
                if lang not in language_tus:
                    new_tmx = PythonTmx.Tmx()
                    new_tmx.header.srclang = source_lang
                    new_tmx.header.segtype = tmx.header.segtype
                    new_tmx.header.adminlang = tmx.header.adminlang
                    new_tmx.header.creationtool = "TMX Splitter"
                    new_tmx.header.creationtoolversion = "1.0"
                    new_tmx.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")
                    language_tus[lang] = new_tmx
                
                language_tus[lang].tus.append(tu)
        
        # Save language-specific TMX files
        for lang, lang_tmx in language_tus.items():
            output_path = input_path.parent / f"{input_path.stem}_{lang}.tmx"
            lang_tmx.save(str(output_path))
            created_files.append(str(output_path))
            logger.info(f"Created {lang} TMX with {len(lang_tmx.tus)} TUs")
        
        return created_files

    except Exception as e:
        logger.error(f"Error splitting TMX by language: {e}")
        raise

def split_by_size(file_path: str, max_tus: int = 50000) -> List[str]:
    """
    Split TMX file into smaller files with specified maximum TUs.
    
    Args:
        file_path: Path to TMX file
        max_tus: Maximum TUs per file
    
    Returns:
        List[str]: Paths to created TMX files
    """
    logger.info(f"Splitting by size: {file_path} (max {max_tus} TUs)")
    
    try:
        input_path = Path(file_path)
        tmx = PythonTmx.Tmx(str(input_path))
        created_files: List[str] = []
        
        # Calculate number of parts needed
        total_tus = len(tmx.tus)
        num_parts = math.ceil(total_tus / max_tus)
        
        for part in range(num_parts):
            # Create new TMX for this part
            part_tmx = PythonTmx.Tmx()
            part_tmx.header.srclang = tmx.header.srclang
            part_tmx.header.segtype = tmx.header.segtype
            part_tmx.header.adminlang = tmx.header.adminlang
            part_tmx.header.creationtool = "TMX Splitter"
            part_tmx.header.creationtoolversion = "1.0"
            part_tmx.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")
            
            # Add TUs for this part
            start_idx = part * max_tus
            end_idx = min((part + 1) * max_tus, total_tus)
            part_tmx.tus.extend(tmx.tus[start_idx:end_idx])
            
            # Save part file
            output_path = input_path.parent / f"{input_path.stem}_part{part + 1}.tmx"
            part_tmx.save(str(output_path))
            created_files.append(str(output_path))
            logger.info(f"Created part {part + 1} with {len(part_tmx.tus)} TUs")
        
        return created_files

    except Exception as e:
        logger.error(f"Error splitting TMX by size: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    split_type = input("Split by (l)anguage or (s)ize? ").lower()
    
    try:
        if split_type == 'l':
            files = split_by_language(file_path)
            print("Created language-specific files:")
        else:
            max_tus = int(input("Enter maximum TUs per file: "))
            files = split_by_size(file_path, max_tus)
            print("Created size-specific files:")
        
        for f in files:
            print(f"- {f}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
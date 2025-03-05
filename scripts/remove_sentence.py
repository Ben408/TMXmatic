import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

def find_sentence_level_segments(file_path: str) -> tuple[str, str]:
    """
    Extract sentence-level segments from TMX file.
    Identifies segments that appear to be complete sentences.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to clean TMX, Path to sentence TMX)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        sentence_path = output_dir / f"sentence_{input_path.name}"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Create TMX files for clean and sentence TUs
        clean_tmx = PythonTmx.Tmx()
        sentence_tmx = PythonTmx.Tmx()
        
        # Copy header properties
        for tmx_file in [clean_tmx, sentence_tmx]:
            tmx_file.header.srclang = tmx.header.srclang
            tmx_file.header.segtype = tmx.header.segtype
            tmx_file.header.adminlang = tmx.header.adminlang
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"
            tmx_file.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        # Sentence pattern matching
        # Matches strings that:
        # 1. Start with capital letter
        # 2. End with ., !, or ?
        # 3. Have 5 or more words
        sentence_pattern = re.compile(r'^[A-Z].*[.!?]$')
        
        clean_count = sentence_count = 0
        source_lang = tmx.header.srclang

        for tu in tmx.tus:
            is_sentence = False
            source_text = None
            
            # Get source text
            for tuv in tu.tuvs:
                if tuv.lang == source_lang:
                    source_text = tuv.seg.strip() if tuv.seg else ""
                    break
            
            if source_text:
                # Check if it matches sentence pattern
                if sentence_pattern.match(source_text):
                    # Count words (rough approximation)
                    word_count = len(source_text.split())
                    if word_count >= 5:
                        is_sentence = True

            if is_sentence:
                sentence_tmx.tus.append(tu)
                sentence_count += 1
            else:
                clean_tmx.tus.append(tu)
                clean_count += 1

        # Save TMX files
        clean_tmx.save(str(clean_path))
        sentence_tmx.save(str(sentence_path))
        
        logger.info(f"Processed {clean_count + sentence_count} TUs: {clean_count} kept, {sentence_count} identified as sentences")
        return str(clean_path), str(sentence_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        clean_file, sentence_file = find_sentence_level_segments(file_path)
        print(f"Created clean file: {clean_file}")
        print(f"Created sentence file: {sentence_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
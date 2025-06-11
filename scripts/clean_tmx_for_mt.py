import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import re
import lxml.etree as etree

logger = logging.getLogger(__name__)

def clean_tmx_for_mt(file_path: str) -> str:
    """
    Clean TMX file for machine translation by:
    1. Removing tags and placeholders
    2. Removing segments with special characters
    3. Removing segments with unbalanced parentheses/brackets
    4. Removing segments with unusual patterns
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        str: Path to cleaned TMX file
    """
    logger.info(f"Starting MT cleaning for: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"mt_clean_{input_path.name}"
      
        
        # Load TMX file
        tm : etree._ElementTree = etree.parse(input_path, etree.XMLParser(encoding="utf-8"))
        tmx_root: etree._Element = tm.getroot()
        tmx: PythonTmx.TmxElement = PythonTmx.from_element(tmx_root)
        

        # Create clean TMX
        clean_tmx = PythonTmx.Tmx(header = tmx.header)
        clean_tmx.header.creationtool = "TMX MT Cleaner"
        clean_tmx.header.creationtoolversion = "1.0"

        # Compile regex patterns
        tag_pattern = re.compile(r'(<[^>]+>|(Ept|Bpt|It|Hi|Ut|Ph)\(.*?\))')
        placeholder_pattern = re.compile(r'\{[0-9]+\}|\[\[.*?\]\]|\{\{.*?\}\}')
        special_chars_pattern = re.compile(r'[^a-zA-Z0-9\s\.,;:!?\'\"\-\(\)\[\]{}]')
        
        total_tus = kept_tus = 0

        # Process TUs
        for tu in tmx.tus:
            total_tus += 1
            keep_tu = True
            source_text = target_text = ""
            
            # Check each TUV
            for tuv in tu.tuvs:
                if not tuv.content:
                    keep_tu = False
                    break
                concat_text = ""
                for part in tuv.content:
                    if type(part) == str:
                        concat_text = concat_text + part

                text = concat_text.strip()
                # Store source/target for comparison
                if tuv.lang == tmx.header.srclang:
                    source_text = text
                else:
                    target_text = text

                # Remove tags and placeholders
                text = tag_pattern.sub(' ', text)
                text = placeholder_pattern.sub(' ', text)
                
                # Check for special characters
                if special_chars_pattern.search(text):
                    keep_tu = False
                    break
                
                # Check for balanced parentheses and brackets
                if not check_balanced_pairs(text):
                    keep_tu = False
                    break
                
                # Check for minimum content
                words = [w for w in text.split() if len(w) > 1]
                if len(words) < 2:
                    keep_tu = False
                    break

            # Additional checks if both source and target exist
            if keep_tu and source_text and target_text:
                # Check length ratio
                source_words = len(source_text.split())
                target_words = len(target_text.split())
                if max(source_words, target_words) / min(source_words, target_words) > 3:
                    keep_tu = False
                
                # Check for identical source and target
                if source_text == target_text:
                    keep_tu = False

            if keep_tu:
                clean_tmx.tus.append(tu)
                kept_tus += 1


        # Save cleaned TMX
        new_tmx_root: etree._Element = PythonTmx.to_element(clean_tmx, True)
        etree.ElementTree(new_tmx_root).write(output_path, encoding="utf-8", xml_declaration=True)


        
        logger.info(f"Cleaned {total_tus} TUs: kept {kept_tus}, removed {total_tus - kept_tus}")
        return str(output_path)

    except Exception as e:
        logger.error(f"Error cleaning TMX for MT: {e}")
        raise

def check_balanced_pairs(text: str) -> bool:
    """Check if parentheses and brackets are balanced in text."""
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}
    
    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop() != pairs[char]:
                return False
    
    return len(stack) == 0

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        output_file = clean_tmx_for_mt(file_path)
        print(f"Cleaned TMX created: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
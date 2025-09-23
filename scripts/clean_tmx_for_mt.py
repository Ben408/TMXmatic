import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import re
import lxml.etree as etree
from .tmx_utils import create_compatible_header

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
        output_path = input_path.parent / f"{input_path.name}"
      
        # Load TMX file using lxml XML parsing (more reliable)
        # Try multiple parsing approaches
        tm = None
        
        # First try: let lxml auto-detect encoding (works best with BOM files)
        try:
            tm = etree.parse(str(input_path))
            if tm is not None and tm.getroot() is not None:
                logger.info("Successfully parsed with auto-detected encoding")
        except Exception as parse_error:
            logger.debug(f"Failed with auto-detection: {parse_error}")
        
        # Second try: use recover mode if auto-detection failed
        if tm is None:
            try:
                parser = etree.XMLParser(recover=True)
                tm = etree.parse(str(input_path), parser)
                if tm is not None and tm.getroot() is not None:
                    logger.info("Successfully parsed with recovery mode")
            except Exception as parse_error:
                logger.debug(f"Failed with recovery mode: {parse_error}")
        
        # Third try: explicit encodings as last resort
        if tm is None:
            for encoding in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    parser = etree.XMLParser(encoding=encoding, recover=True)
                    tm = etree.parse(str(input_path), parser)
                    if tm is not None and tm.getroot() is not None:
                        logger.info(f"Successfully parsed with encoding: {encoding}")
                        break
                except Exception as parse_error:
                    logger.debug(f"Failed to parse with {encoding}: {parse_error}")
                    continue
        
        if tm is None or tm.getroot() is None:
            raise ValueError("Could not parse TMX file with any supported encoding")
        
        tmx_root = tm.getroot()
        
        # Extract header attributes from XML
        header_elem = tmx_root.find('header')
        if header_elem is None:
            raise ValueError("No header element found in TMX file")
        
        # Create a minimal header object for compatibility with required parameters
        header_attrs = {}
        for attr_name in ['creationtool', 'creationtoolversion', 'adminlang', 'srclang', 'segtype', 'datatype']:
            if attr_name in header_elem.attrib:
                header_attrs[attr_name] = header_elem.attrib[attr_name]
        
        # Convert string segtype to enum if needed
        segtype_str = header_attrs.get('segtype', 'sentence')
        if segtype_str == 'sentence':
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE
        elif segtype_str == 'paragraph':
            segtype_enum = PythonTmx.SEGTYPE.PARAGRAPH
        elif segtype_str == 'phrase':
            segtype_enum = PythonTmx.SEGTYPE.PHRASE
        elif segtype_str == 'block':
            segtype_enum = PythonTmx.SEGTYPE.BLOCK
        else:
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE  # Default fallback
        
        minimal_header = PythonTmx.Header(
            creationtool=header_attrs.get('creationtool', 'Unknown Tool'),
            creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
            adminlang=header_attrs.get('adminlang', 'en'),
            srclang=header_attrs.get('srclang', 'en'),
            segtype=segtype_enum,
            datatype=header_attrs.get('datatype', 'xml'),
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )
        
        clean_header = create_compatible_header(minimal_header, "TMX MT Cleaner", "1.0")
        
        # Parse TUs manually from XML
        tus = []
        body_elem = tmx_root.find('body')
        if body_elem is not None:
            for tu_elem in body_elem.findall('tu'):
                tu = PythonTmx.Tu()
                for tuv_elem in tu_elem.findall('tuv'):
                    lang = tuv_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                    seg_elem = tuv_elem.find('seg')
                    if seg_elem is not None and seg_elem.text:
                        tuv = PythonTmx.Tuv(lang=lang)
                        tuv.content = seg_elem.text
                        tu.tuvs.append(tuv)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=clean_header, tus=tus)

        # Create clean TMX using correct constructor
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])

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
        # Save TMX file using the correct method
        try:
            # Use the to_tmx method which should exist
            clean_tmx.to_tmx(str(output_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            clean_root = PythonTmx.to_element(clean_tmx, True)
            etree.ElementTree(clean_root).write(str(output_path), encoding="utf-8", xml_declaration=True)
        logger.info(f"Cleaned {total_tus} TUs: kept {kept_tus}, removed {total_tus - kept_tus}")
        return str(output_path), str(input_path)

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
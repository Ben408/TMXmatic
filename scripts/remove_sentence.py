import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import re
import lxml.etree as etree
from .tmx_utils import create_compatible_header

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
        
        clean_header = create_compatible_header(minimal_header, "TMX Cleaner", "1.0")
        sentence_header = create_compatible_header(minimal_header, "TMX Cleaner", "1.0")
        
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

        # Create TMX files for clean and sentence TUs using correct constructor
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])
        sentence_tmx = PythonTmx.Tmx(header=sentence_header, tus=[])

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
                    source_text = tuv.content.strip() if tuv.content else ""
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

        # Save TMX files using the correct method
        try:
            # Use the to_tmx method which should exist
            clean_tmx.to_tmx(str(clean_path))
            sentence_tmx.to_tmx(str(sentence_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            clean_root = PythonTmx.to_element(clean_tmx, True)
            sentence_root = PythonTmx.to_element(sentence_tmx, True)
            etree.ElementTree(clean_root).write(str(clean_path), encoding="utf-8", xml_declaration=True)
            etree.ElementTree(sentence_root).write(str(sentence_path), encoding="utf-8", xml_declaration=True)
        
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
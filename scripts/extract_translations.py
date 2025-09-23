import PythonTmx
from datetime import datetime
from pathlib import Path
import csv
import logging
import lxml.etree as etree
from .tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

def extract_translations(file_path: str) -> tuple[str, int]:
    """
    Extract all translations to CSV format.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to CSV file, Total translations extracted)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"translations_{input_path.stem}.csv"

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
                        # Handle creationdate and changedate attributes
                        if 'creationdate' in tuv_elem.attrib:
                            tuv.creationdate = tuv_elem.attrib['creationdate']
                        if 'changedate' in tuv_elem.attrib:
                            tuv.changedate = tuv_elem.attrib['changedate']
                        tu.tuvs.append(tuv)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        
        source_lang = tmx.header.srclang
        
        # Get all unique target languages
        target_langs = set()
        for tu in tmx.tus:
            for tuv in tu.tuvs:
                if tuv.lang != source_lang:
                    target_langs.add(tuv.lang)
        
        # Sort target languages for consistent output
        target_langs = sorted(target_langs)
        
        # Prepare CSV headers
        headers = ['Source Text', 'Source Creation Date', 'Source Change Date']
        for lang in target_langs:
            headers.extend([
                f'Target ({lang})',
                f'Creation Date ({lang})',
                f'Change Date ({lang})'
            ])

        total_tus = 0
        
        # Write translations to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for tu in tmx.tus:
                total_tus += 1
                row_data = []
                
                # Get source information
                source_text = source_creation = source_change = ''
                for tuv in tu.tuvs:
                    if tuv.lang == source_lang:
                        source_text = tuv.content if tuv.content else ''
                        source_creation = format_date(tuv.creationdate)
                        source_change = format_date(tuv.changedate)
                        break
                
                row_data.extend([source_text, source_creation, source_change])
                
                # Get target information for each language
                for lang in target_langs:
                    target_text = target_creation = target_change = ''
                    for tuv in tu.tuvs:
                        if tuv.lang == lang:
                            target_text = tuv.content if tuv.content else ''
                            target_creation = format_date(tuv.creationdate)
                            target_change = format_date(tuv.changedate)
                            break
                    row_data.extend([target_text, target_creation, target_change])
                
                writer.writerow(row_data)
        
        logger.info(f"Extracted {total_tus} translations")
        return str(output_path), total_tus

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

def format_date(date_str: str) -> str:
    """
    Format TMX date string to YYYY-MM-DD format.
    Returns empty string for None or invalid dates.
    """
    if not date_str:
        return ''
    
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return ''

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        output_file, count = extract_translations(file_path)
        print(f"Extracted {count} translations")
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
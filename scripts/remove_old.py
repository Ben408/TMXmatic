import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import lxml.etree as etree
from .tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

def remove_old_tus(file_path: str, cutoff_date) -> tuple[str, str]:
    """
    Remove TUs older than the cutoff date.
    
    Args:
        file_path: Path to TMX file
        cutoff_date: Date to compare against (datetime object or date string)
    
    Returns:
        tuple: (Path to clean TMX, Path to removed TMX)
    """
    # Convert string date to datetime if needed
    if isinstance(cutoff_date, str):
        try:
            cutoff_date = datetime.fromisoformat(cutoff_date)
        except ValueError:
            # Try alternative format
            try:
                cutoff_date = datetime.strptime(cutoff_date, "%Y-%m-%d")
            except ValueError:
                raise ValueError(f"Invalid date format: {cutoff_date}. Use YYYY-MM-DD format.")
    
    logger.info(f"Processing file: {file_path} with cutoff date: {cutoff_date}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        removed_path = output_dir / f"removed_{input_path.name}"

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
        removed_header = create_compatible_header(minimal_header, "TMX Cleaner", "1.0")
        
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
        tmx = PythonTmx.Tmx(header=clean_header, tus=tus)

        # Create TMX files for clean and removed TUs using correct constructor
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])
        removed_tmx = PythonTmx.Tmx(header=removed_header, tus=[])

        cutoff_str = cutoff_date.strftime("%Y%m%dT%H%M%SZ")
        clean_count = removed_count = 0

        # Process TUs
        for tu in tmx.tus:
            is_old = True
            
            for tuv in tu.tuvs:
                if tuv.creationdate and tuv.creationdate > cutoff_str:
                    is_old = False
                    break
                if tuv.changedate and tuv.changedate > cutoff_str:
                    is_old = False
                    break
            
            if is_old:
                removed_tmx.tus.append(tu)
                removed_count += 1
            else:
                clean_tmx.tus.append(tu)
                clean_count += 1

        # Save TMX files using the correct method
        try:
            # Use the to_tmx method which should exist
            clean_tmx.to_tmx(str(clean_path))
            removed_tmx.to_tmx(str(removed_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            clean_root = PythonTmx.to_element(clean_tmx, True)
            removed_root = PythonTmx.to_element(removed_tmx, True)
            etree.ElementTree(clean_root).write(str(clean_path), encoding="utf-8", xml_declaration=True)
            etree.ElementTree(removed_root).write(str(removed_path), encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Processed {clean_count + removed_count} TUs: {clean_count} kept, {removed_count} removed")
        return str(clean_path), str(removed_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    date_str = input("Enter cutoff date (YYYY-MM-DD): ")
    try:
        cutoff_date = datetime.strptime(date_str, "%Y-%m-%d")
        clean_file, removed_file = remove_old_tus(file_path, cutoff_date)
        print(f"Created clean file: {clean_file}")
        print(f"Created removed file: {removed_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
import PythonTmx
from datetime import datetime
from pathlib import Path
import csv
import logging
from collections import Counter
import lxml.etree as etree
from .tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

def count_creation_dates(file_path: str) -> tuple[str, int]:
    """
    Count TUs by creation date.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to CSV report, Total TUs counted)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"creation_dates_{input_path.stem}.csv"

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
                        # Handle creationdate attribute
                        if 'creationdate' in tuv_elem.attrib:
                            tuv.creationdate = tuv_elem.attrib['creationdate']
                        tu.tuvs.append(tuv)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        
        # Count creation dates
        date_counter = Counter()
        total_tus = 0
        
        for tu in tmx.tus:
            total_tus += 1
            creation_date = None
            
            # Check TUVs for creation date
            for tuv in tu.tuvs:
                if tuv.creationdate:
                    try:
                        # Convert to datetime for consistent formatting
                        date_obj = datetime.strptime(tuv.creationdate, "%Y%m%dT%H%M%SZ")
                        creation_date = date_obj.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        logger.warning(f"Invalid date format: {tuv.creationdate}")
                        continue
            
            if creation_date:
                date_counter[creation_date] += 1
            else:
                date_counter['No Date'] += 1

        # Write results to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Count', 'Percentage'])
            
            # Sort by date (with 'No Date' at the end)
            sorted_dates = sorted(
                [date for date in date_counter.keys() if date != 'No Date']
            )
            if 'No Date' in date_counter:
                sorted_dates.append('No Date')
            
            # Write counts and percentages
            for date in sorted_dates:
                count = date_counter[date]
                percentage = (count / total_tus) * 100
                writer.writerow([date, count, f"{percentage:.2f}%"])
            
            # Write total
            writer.writerow(['Total', total_tus, '100.00%'])
        
        logger.info(f"Analyzed {total_tus} TUs")
        return str(output_path), total_tus

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        output_file, count = count_creation_dates(file_path)
        print(f"Analyzed {count} TUs")
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
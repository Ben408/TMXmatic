import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict
import lxml.etree as etree
from .tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

def extract_non_true_duplicates(file_path: str) -> tuple[str, str]:
    """
    Extract non-true duplicates (same source, different target).
    Keeps one version in clean file, moves others to NTD file.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to clean TMX, Path to NTDs TMX)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        dups_path = output_dir / f"duplicates_{input_path.name}"

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
        ntds_header = create_compatible_header(minimal_header, "TMX Cleaner", "1.0")
        
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

        # Create TMX files for clean and duplicate TUs using correct constructor
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])
        ntds_tmx = PythonTmx.Tmx(header=ntds_header, tus=[])

        clean_segments = []
        ntds_segments = []

        duplicates = {}                                 #A dictionary of all non Non-True-Duplicates(this 
                                                        #includes non repeated segments, as well as True-Duplicates)

        ntds = {}                                       #A dictionary for all Non-True-Duplicates

        for tu in tmx.tus:
            source = ""
            target = ""

            for tuv in tu.tuvs:
                if tuv.lang.lower() in  ("en-us", "en_us", "en") :
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        source = source + str(seg)     
                else:
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        target = target + str(seg)

            if duplicates.get(source):                  #Evaluates if the source appears as a key in the duplicates dictionary

                if target not in duplicates[source]:    #If the target is not present in the duplicates dictionary entry for the source, but is a key in  
                    duplicates[source].append(target)   #the duplicates dictionary, adds the target in the list of values source (as key) holds in duplicates,
                    ntds[source] = duplicates[source]   #and replaces the entry of source in the ntds dictionary with the same list as duplicates
            else:
                duplicates[source] = []                 #If this is the first appearance of this source, adds the source as key and a new list with the target
                duplicates[source].append(target)       #as value

        for tu in tmx.tus:
            source = ""
            target = ""

            for tuv in tu.tuvs:
                if tuv.lang.lower() == "en-us":
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        source = source + str(seg)
                else:
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        target = target + str(seg)

            if ntds.get(source):                        #Checks if the source appears as key in the ntds dictionary
                if target in ntds[source]:              #Checks if the target is the value for the source as key, if it is,
                    ntds_segments.append(tu)            #removes the target from the list of ntds of that source, and adds
                    ntds[source].remove(target)         #the TU to the ntds_segments list
                else:
                    clean_segments.append(tu)           #If the target is not in the source's list of ntds, or if the source
            else:                                       #is not present in the ntds dictionary, then the TU is added to the
                clean_segments.append(tu)

        clean_tmx.tus = clean_segments
        ntds_tmx.tus = ntds_segments
        
        try:
            # Use the to_tmx method which should exist
            clean_tmx.to_tmx(str(clean_path))
            ntds_tmx.to_tmx(str(dups_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            clean_root = PythonTmx.to_element(clean_tmx, True)
            ntds_root = PythonTmx.to_element(ntds_tmx, True)
            etree.ElementTree(clean_root).write(str(clean_path), encoding="utf-8", xml_declaration=True)
            etree.ElementTree(ntds_root).write(str(dups_path), encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Processed {len(clean_segments)+ len(ntds_segments)} TUs: {len(clean_segments)} kept, {len(ntds_segments)} removed")
        
        return str(clean_path), str(dups_path)
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        clean_file, ntd_file = extract_non_true_duplicates(file_path)
        print(f"Created clean file: {clean_file}")
        print(f"Created NTDs file: {ntd_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
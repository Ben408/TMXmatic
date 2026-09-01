import PythonTmx
import os
from datetime import datetime
from pathlib import Path
import logging
import lxml.etree as etree
try:
    from .tmx_utils import create_compatible_header
except ImportError:
    from tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

class OperationLog:
    def __init__(self):
        self.messages = []
    
    def info(self, msg):
        self.messages.append(("info", msg))
    
    def error(self, msg):
        self.messages.append(("error", msg))
    
    def get_log(self):
        return self.messages

def find_true_duplicates(file_path: str) -> tuple[str, str]:
    """
    Remove true duplicate TUs (identical source and target).
    Keeps the most recent version based on changedate or creationdate.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to clean TMX, Path to duplicates TMX)
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
        
        # Store original segtype string for preservation
        original_segtype = header_attrs.get('segtype', 'sentence')
        
        # Convert string segtype to enum for PythonTmx compatibility (but preserve original)
        if original_segtype == 'sentence':
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE
        elif original_segtype == 'paragraph':
            segtype_enum = PythonTmx.SEGTYPE.PARAGRAPH
        elif original_segtype == 'phrase':
            segtype_enum = PythonTmx.SEGTYPE.PHRASE
        elif original_segtype == 'block':
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
        dups_header = create_compatible_header(minimal_header, "TMX Cleaner", "1.0")
        
        # Parse TUs manually from XML with FULL metadata preservation
        tus = []
        body_elem = tmx_root.find('body')
        if body_elem is not None:
            for tu_elem in body_elem.findall('tu'):
                # Create TU object and copy ALL attributes
                tu = PythonTmx.Tu()
                
                # Copy ALL TU-level attributes
                for attr_name, attr_value in tu_elem.attrib.items():
                    try:
                        if attr_name == 'creationdate':
                            tu.creationdate = attr_value
                        elif attr_name == 'changedate':
                            tu.changedate = attr_value
                        elif attr_name == 'creationid':
                            tu.creationid = attr_value
                        elif attr_name == 'changeid':
                            tu.changeid = attr_value
                        elif attr_name == 'tuid':
                            tu.tuid = attr_value
                        elif attr_name == 'lastusagedate':
                            tu.lastusagedate = attr_value
                        elif attr_name == 'previous':
                            tu.previous = attr_value
                        elif attr_name == 'next':
                            tu.next = attr_value
                    except Exception as attr_error:
                        logger.warning(f"Failed to set TU attribute {attr_name}: {attr_error}, skipping")
                        continue
                
                # Copy TU-level properties with full content
                for prop_elem in tu_elem.findall('prop'):
                    prop_type = prop_elem.get('type', 'unknown')
                    prop_text = prop_elem.text if prop_elem.text else 'no-content'
                    
                    # Ensure we have valid values to avoid validation errors
                    if not prop_type or prop_type.strip() == '':
                        prop_type = 'unknown'
                    if not prop_text or prop_text.strip() == '':
                        prop_text = 'no-content'
                    
                    try:
                        prop = PythonTmx.Prop(type=prop_type, text=prop_text)
                        if 'lang' in prop_elem.attrib:
                            prop.lang = prop_elem.get('lang')
                        tu.props.append(prop)
                    except Exception as prop_error:
                        logger.warning(f"Failed to create prop: {prop_error}, skipping")
                        continue
                
                # Copy TU-level notes
                for note_elem in tu_elem.findall('note'):
                    note = PythonTmx.Note()
                    if 'lang' in note_elem.attrib:
                        note.lang = note_elem.get('lang')
                    if note_elem.text:
                        note.content = note_elem.text
                    tu.notes.append(note)
                
                # Copy TUVs with ALL metadata
                for tuv_elem in tu_elem.findall('tuv'):
                    lang = tuv_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                    tuv = PythonTmx.Tuv(lang=lang)
                    
                    # Copy ALL TUV-level attributes
                    for attr_name, attr_value in tuv_elem.attrib.items():
                        try:
                            if attr_name == 'changedate':
                                tuv.changedate = attr_value
                            elif attr_name == 'creationdate':
                                tuv.creationdate = attr_value
                            elif attr_name == 'creationid':
                                tuv.creationid = attr_value
                            elif attr_name == 'changeid':
                                tuv.changeid = attr_value
                            elif attr_name == 'tuid':
                                tuv.tuid = attr_value
                            elif attr_name == 'previous':
                                tuv.previous = attr_value
                            elif attr_name == 'next':
                                tuv.next = attr_value
                        except Exception as attr_error:
                            logger.warning(f"Failed to set TUV attribute {attr_name}: {attr_error}, skipping")
                            continue
                    
                    # Copy TUV-level properties
                    for prop_elem in tuv_elem.findall('prop'):
                        prop_type = prop_elem.get('type', 'unknown')
                        prop_text = prop_elem.text if prop_elem.text else 'no-content'
                        
                        # Ensure we have valid values to avoid validation errors
                        if not prop_type or prop_type.strip() == '':
                            prop_type = 'unknown'
                        if not prop_text or prop_text.strip() == '':
                            prop_text = 'no-content'
                        
                        try:
                            prop = PythonTmx.Prop(type=prop_type, text=prop_text)
                            if 'lang' in prop_elem.attrib:
                                prop.lang = prop_elem.get('lang')
                            tuv.props.append(prop)
                        except Exception as prop_error:
                            logger.warning(f"Failed to create TUV prop: {prop_error}, skipping")
                            continue
                    
                    # Copy TUV-level notes
                    for note_elem in tuv_elem.findall('note'):
                        note = PythonTmx.Note()
                        if 'lang' in note_elem.attrib:
                            note.lang = note_elem.get('lang')
                        if note_elem.text:
                            note.content = note_elem.text
                        tuv.notes.append(note)
                    
                    # Get segment content
                    seg_elem = tuv_elem.find('seg')
                    if seg_elem is not None and seg_elem.text:
                        tuv.content = seg_elem.text
                    
                    tu.tuvs.append(tuv)
                
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=clean_header, tus=tus)

        # Create TMX files for clean and duplicate TUs using correct constructor
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])
        dups_tmx = PythonTmx.Tmx(header=dups_header, tus=[])

        clean_tm = []
        duplicates = []

        # New approach: Build a map of content -> (latest_date, latest_tu)
        content_map = {}

        for tu in tmx.tus:
            source = ""
            target = ""
            date = None
            
            # Extract source, target, and date for this TU
            for tuv in tu.tuvs:
                if tuv.lang.lower() in ("en-us", "en_us"):
                    source = str(tuv.content) if tuv.content else ""
                else:
                    target = str(tuv.content) if tuv.content else ""
                    if tuv.changedate:
                        date = tuv.changedate
                    else:
                        date = datetime(year=2000, month=1, day=1)
                        tuv.changedate = date.strftime("%Y%m%dT%H%M%SZ")

            content_key = source + target
            
            # If this content combination doesn't exist, or this TU is newer, keep it
            if content_key not in content_map or content_map[content_key][0] < date:
                # If there was a previous TU with this content, it becomes a duplicate
                if content_key in content_map:
                    duplicates.append(content_map[content_key][1])
                # Store this TU as the newest for this content
                content_map[content_key] = (date, tu)
            else:
                # This TU is older than the one we already have, so it's a duplicate
                duplicates.append(tu)

        # All TUs remaining in content_map are the newest versions (clean)
        clean_tm = [tu for date, tu in content_map.values()]

        # Assign the processed TUs to the TMX objects
        clean_tmx.tus = clean_tm
        dups_tmx.tus = duplicates

        # Save TMX files using the EXACT same method as remove_empty.py
        try:
            # Use the to_tmx method which should exist
            clean_tmx.to_tmx(str(clean_path))
            dups_tmx.to_tmx(str(dups_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            try:
                clean_root = PythonTmx.to_element(clean_tmx, True)
                dups_root = PythonTmx.to_element(dups_tmx, True)
                etree.ElementTree(clean_root).write(str(clean_path), encoding="utf-8", xml_declaration=True)
                etree.ElementTree(dups_root).write(str(dups_path), encoding="utf-8", xml_declaration=True)
            except Exception as element_error:
                # PythonTmx validation failed - use manual XML construction as final fallback
                logger.warning(f"PythonTmx validation failed: {element_error}, using manual XML construction")
                
                def create_tmx_xml_with_metadata(tmx_obj, output_path, original_segtype=None):
                    """Create TMX XML manually while preserving ALL metadata and structure"""
                    # Create root element
                    root = etree.Element('tmx', version='1.4')
                    
                    # Add header with ALL attributes and properties
                    header_elem = etree.SubElement(root, 'header')
                    header_elem.set('creationtool', tmx_obj.header.creationtool)
                    header_elem.set('creationtoolversion', tmx_obj.header.creationtoolversion)
                    # Use original segtype string if provided, otherwise fall back to PythonTmx value
                    segtype_value = original_segtype if original_segtype else str(tmx_obj.header.segtype)
                    header_elem.set('segtype', segtype_value)
                    header_elem.set('adminlang', tmx_obj.header.adminlang)
                    header_elem.set('srclang', tmx_obj.header.srclang)
                    header_elem.set('datatype', tmx_obj.header.datatype)
                    header_elem.set('o-tmf', tmx_obj.header.tmf)
                    header_elem.set('o-encoding', tmx_obj.header.encoding)
                    
                    # Preserve additional header attributes
                    if hasattr(tmx_obj.header, 'creationdate') and tmx_obj.header.creationdate:
                        header_elem.set('creationdate', str(tmx_obj.header.creationdate))
                    if hasattr(tmx_obj.header, 'creationid') and tmx_obj.header.creationid:
                        header_elem.set('creationid', str(tmx_obj.header.creationid))
                    
                    # Preserve header properties
                    if hasattr(tmx_obj.header, 'props') and tmx_obj.header.props:
                        for prop in tmx_obj.header.props:
                            prop_elem = etree.SubElement(header_elem, 'prop')
                            prop_elem.set('type', prop.type)
                            if hasattr(prop, 'lang') and prop.lang:
                                prop_elem.set('{http://www.w3.org/XML/1998/namespace}lang', prop.lang)
                            if hasattr(prop, 'text') and prop.text:
                                prop_elem.text = str(prop.text)
                    
                    # Preserve header notes
                    if hasattr(tmx_obj.header, 'notes') and tmx_obj.header.notes:
                        for note in tmx_obj.header.notes:
                            note_elem = etree.SubElement(header_elem, 'note')
                            if hasattr(note, 'lang') and note.lang:
                                note_elem.set('{http://www.w3.org/XML/1998/namespace}lang', note.lang)
                            if hasattr(note, 'content') and note.content:
                                note_elem.text = str(note.content)
                    
                    # Add body with TUs
                    body_elem = etree.SubElement(root, 'body')
                    for tu in tmx_obj.tus:
                        tu_elem = etree.SubElement(body_elem, 'tu')
                        
                        # Preserve TU-level attributes
                        if hasattr(tu, 'creationdate') and tu.creationdate:
                            tu_elem.set('creationdate', str(tu.creationdate))
                        if hasattr(tu, 'changedate') and tu.changedate:
                            tu_elem.set('changedate', str(tu.changedate))
                        if hasattr(tu, 'creationid') and tu.creationid:
                            tu_elem.set('creationid', str(tu.creationid))
                        if hasattr(tu, 'changeid') and tu.changeid:
                            tu_elem.set('changeid', str(tu.changeid))
                        if hasattr(tu, 'tuid') and tu.tuid:
                            tu_elem.set('tuid', str(tu.tuid))
                        if hasattr(tu, 'lastusagedate') and tu.lastusagedate:
                            tu_elem.set('lastusagedate', str(tu.lastusagedate))
                        if hasattr(tu, 'previous') and tu.previous:
                            tu_elem.set('previous', str(tu.previous))
                        if hasattr(tu, 'next') and tu.next:
                            tu_elem.set('next', str(tu.next))
                        
                        # Preserve TU-level properties
                        if hasattr(tu, 'props') and tu.props:
                            for prop in tu.props:
                                prop_elem = etree.SubElement(tu_elem, 'prop')
                                prop_elem.set('type', prop.type)
                                if hasattr(prop, 'lang') and prop.lang:
                                    prop_elem.set('{http://www.w3.org/XML/1998/namespace}lang', prop.lang)
                                if hasattr(prop, 'text') and prop.text:
                                    prop_elem.text = str(prop.text)
                        
                        # Preserve TU-level notes
                        if hasattr(tu, 'notes') and tu.notes:
                            for note in tu.notes:
                                note_elem = etree.SubElement(tu_elem, 'note')
                                if hasattr(note, 'lang') and note.lang:
                                    note_elem.set('{http://www.w3.org/XML/1998/namespace}lang', note.lang)
                                if hasattr(note, 'content') and note.content:
                                    note_elem.text = str(note.content)
                        
                        # Add TUVs with all metadata
                        for tuv in tu.tuvs:
                            tuv_elem = etree.SubElement(tu_elem, 'tuv')
                            tuv_elem.set('{http://www.w3.org/XML/1998/namespace}lang', tuv.lang)
                            
                            # Preserve TUV-level attributes
                            if hasattr(tuv, 'changedate') and tuv.changedate:
                                tuv_elem.set('changedate', str(tuv.changedate))
                            if hasattr(tuv, 'creationdate') and tuv.creationdate:
                                tuv_elem.set('creationdate', str(tuv.creationdate))
                            if hasattr(tuv, 'creationid') and tuv.creationid:
                                tuv_elem.set('creationid', str(tuv.creationid))
                            if hasattr(tuv, 'changeid') and tuv.changeid:
                                tuv_elem.set('changeid', str(tuv.changeid))
                            if hasattr(tuv, 'tuid') and tuv.tuid:
                                tuv_elem.set('tuid', str(tuv.tuid))
                            if hasattr(tuv, 'previous') and tuv.previous:
                                tuv_elem.set('previous', str(tuv.previous))
                            if hasattr(tuv, 'next') and tuv.next:
                                tuv_elem.set('next', str(tuv.next))
                            
                            # Preserve TUV-level properties
                            if hasattr(tuv, 'props') and tuv.props:
                                for prop in tuv.props:
                                    prop_elem = etree.SubElement(tuv_elem, 'prop')
                                    prop_elem.set('type', prop.type)
                                    if hasattr(prop, 'lang') and prop.lang:
                                        prop_elem.set('{http://www.w3.org/XML/1998/namespace}lang', prop.lang)
                                    if hasattr(prop, 'text') and prop.text:
                                        prop_elem.text = str(prop.text)
                            
                            # Preserve TUV-level notes
                            if hasattr(tuv, 'notes') and tuv.notes:
                                for note in tuv.notes:
                                    note_elem = etree.SubElement(tuv_elem, 'note')
                                    if hasattr(note, 'lang') and note.lang:
                                        note_elem.set('{http://www.w3.org/XML/1998/namespace}lang', note.lang)
                                    if hasattr(note, 'content') and note.content:
                                        note_elem.text = str(note.content)
                            
                            # Add segment with content
                            seg_elem = etree.SubElement(tuv_elem, 'seg')
                            if tuv.content:
                                seg_elem.text = str(tuv.content)
                    
                    # Write to file
                    tree = etree.ElementTree(root)
                    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)
                
                # Use manual XML construction as final fallback
                create_tmx_xml_with_metadata(clean_tmx, str(clean_path), original_segtype)
                create_tmx_xml_with_metadata(dups_tmx, str(dups_path), original_segtype)
                logger.info("Successfully saved using manual XML construction fallback")
        
        logger.info(f"Debug: Found {len(content_map)} unique content combinations")
        logger.info(f"Processed {len(clean_tm)+ len(duplicates)} TUs: {len(clean_tm)} kept, {len(duplicates)} removed")
        
        # Debug: Show some examples
        if len(clean_tm) < 5:
            logger.info(f"Debug: Clean TUs are very few ({len(clean_tm)}), this suggests a logic error")
        if len(duplicates) > len(clean_tm) * 10:
            logger.info(f"Debug: Too many duplicates ({len(duplicates)} vs {len(clean_tm)} clean), this suggests a logic error")
        
        return str(clean_path), str(dups_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

def process_directory(directory):
    """
    Process all TMX files in a directory.

    Args:
        directory (str): Directory containing TMX files

    Returns:
        list: List of tuples containing (target_file, duplicates_file, processed_count, duplicate_count)
    """
    logger = OperationLog()
    results = []
    
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.tmx'):
                source_file = os.path.join(directory, filename)
                logger.info(f"Processing file: {filename}")
                result = find_true_duplicates(source_file)
                results.append(result)
        return results, logger.get_log()
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        clean_file, dups_file = find_true_duplicates(file_path)
        print(f"Created clean file: {clean_file}")
        print(f"Created duplicates file: {dups_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
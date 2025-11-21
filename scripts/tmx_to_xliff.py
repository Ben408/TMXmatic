"""
Convert TMX file back to XLIFF format (1.2, 2.0, or 2.2).
Preserves original XLIFF version if available in TMX metadata.
"""

import lxml.etree as etree
from pathlib import Path
import logging
from datetime import datetime
from typing import Optional, Tuple
import json
import PythonTmx

logger = logging.getLogger(__name__)

# XLIFF namespaces
XLIFF_20_NS = 'urn:oasis:names:tc:xliff:document:2.0'
XLIFF_22_NS = 'urn:oasis:names:tc:xliff:document:2.2'
XML_NS = 'http://www.w3.org/XML/1998/namespace'


def get_xliff_version_from_tmx(tmx: PythonTmx.Tmx) -> str:
    """
    Extract original XLIFF version from TMX metadata.
    Checks header notes first, then TU properties as fallback.
    
    Args:
        tmx: TMX object
    
    Returns:
        str: XLIFF version ('1.2', '2.0', or '2.2')
    """
    # Check header notes first (primary method)
    for note in tmx.header.notes:
        # Try both 'content' and 'text' attributes (PythonTmx may use either)
        note_text = None
        if hasattr(note, 'content') and note.content:
            note_text = note.content
        elif hasattr(note, 'text') and note.text:
            note_text = note.text
        
        if note_text and 'Original XLIFF version' in note_text:
            version = note_text.split(':')[-1].strip()
            if version in ['1.2', '2.0', '2.2']:
                logger.info(f"Found original XLIFF version from header note: {version}")
                return version
    
    # Check all TUs for version property (fallback method)
    for tu in tmx.tus:
        for prop in tu.props:
            if prop.type == 'x-xliff-version':
                version = prop.text.strip() if prop.text else ''
                if version in ['1.2', '2.0', '2.2']:
                    logger.info(f"Found original XLIFF version from TU property: {version}")
                    return version
    
    # Default to 1.2 if not found
    logger.warning("Original XLIFF version not found in TMX metadata, defaulting to 1.2")
    return '1.2'


def get_tu_metadata(tu: PythonTmx.Tu) -> dict:
    """
    Extract XLIFF metadata from TU properties.
    Restores all attributes, contexts, alt-trans, etc.
    
    Args:
        tu: Translation unit
        
    Returns:
        dict: Metadata dictionary with all preserved information
    """
    metadata = {}
    source_attrs = {}
    target_attrs = {}
    segment_attrs = {}
    
    for prop in tu.props:
        if not prop.type.startswith('x-xliff-'):
            continue
        
        prop_type = prop.type
        prop_value = prop.text if prop.text else ''
        
        # Handle special cases
        if prop_type == 'x-xliff-version':
            continue  # Skip version, handled separately
        elif prop_type == 'x-xliff-context-groups':
            try:
                metadata['context_groups'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse context-groups JSON: {prop_value}")
        elif prop_type == 'x-xliff-contexts':
            try:
                metadata['contexts'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse contexts JSON: {prop_value}")
        elif prop_type == 'x-xliff-props':
            try:
                metadata['props'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse props JSON: {prop_value}")
        elif prop_type == 'x-xliff-alt-trans':
            try:
                metadata['alt_trans'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse alt-trans JSON: {prop_value}")
        elif prop_type.startswith('x-xliff-source-'):
            # Restore original attribute name (underscores were used to replace colons/spaces)
            attr_name = prop_type.replace('x-xliff-source-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            source_attrs[attr_name] = prop_value
        elif prop_type.startswith('x-xliff-target-'):
            attr_name = prop_type.replace('x-xliff-target-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            target_attrs[attr_name] = prop_value
        elif prop_type.startswith('x-xliff-segment-'):
            attr_name = prop_type.replace('x-xliff-segment-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            segment_attrs[attr_name] = prop_value
        else:
            # Regular attribute - restore original key name
            key = prop_type.replace('x-xliff-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            metadata[key] = prop_value
    
    if source_attrs:
        metadata['source_attributes'] = source_attrs
    if target_attrs:
        metadata['target_attributes'] = target_attrs
    if segment_attrs:
        metadata['segment_attributes'] = segment_attrs
    
    return metadata


def create_xliff12_document(tmx: PythonTmx.Tmx, output_path: str):
    """
    Create XLIFF 1.2 document from TMX.
    
    Args:
        tmx: TMX object
        output_path: Output file path
    """
    # Create root element
    xliff = etree.Element('xliff', version='1.2')
    xliff.set('xmlns', 'urn:oasis:names:tc:xliff:document:1.2')
    
    # Create file element
    file_elem = etree.SubElement(xliff, 'file')
    file_elem.set('original', 'converted_from_tmx')
    file_elem.set('source-language', tmx.header.srclang)
    
    # Determine target language from first TU
    target_lang = tmx.header.srclang
    if tmx.tus and len(tmx.tus[0].tuvs) > 1:
        for tuv in tmx.tus[0].tuvs:
            if tuv.lang != tmx.header.srclang:
                target_lang = tuv.lang
                break
    
    file_elem.set('target-language', target_lang)
    file_elem.set('datatype', tmx.header.datatype)
    
    # Create body
    body = etree.SubElement(file_elem, 'body')
    
    # Convert TUs to trans-units
    for tu in tmx.tus:
        trans_unit = etree.SubElement(body, 'trans-unit')
        
        # Get metadata
        metadata = get_tu_metadata(tu)
        
        # Restore ALL trans-unit attributes
        for key, value in metadata.items():
            if key not in ['id', 'source_attributes', 'target_attributes', 'contexts', 'context_groups', 'alt_trans', 'notes', 'props']:
                if value:
                    trans_unit.set(key, str(value))
        
        # Ensure id is set (required)
        if not trans_unit.get('id'):
            trans_unit.set('id', metadata.get('id', ''))
        
        # Find source and target TUVs
        source_tuv = None
        target_tuvs = []
        source_lang = tmx.header.srclang
        
        for tuv in tu.tuvs:
            # Normalize language codes for comparison
            tuv_lang = tuv.lang.lower().replace('_', '-')
            src_lang_norm = source_lang.lower().replace('_', '-')
            
            if tuv_lang == src_lang_norm or tuv_lang.startswith(src_lang_norm.split('-')[0]):
                source_tuv = tuv
            else:
                target_tuvs.append(tuv)
        
        # Use first target TUV (XLIFF typically has one target per unit)
        target_tuv = target_tuvs[0] if target_tuvs else None
        
        # Always create source element
        if source_tuv:
            source_elem = etree.SubElement(trans_unit, 'source')
            source_elem.text = str(source_tuv.content) if source_tuv.content else ""
            # Restore source attributes
            if 'source_attributes' in metadata:
                for attr_name, attr_value in metadata['source_attributes'].items():
                    source_elem.set(attr_name, str(attr_value))
        else:
            # Create empty source if not found
            source_elem = etree.SubElement(trans_unit, 'source')
        
        # Always create target element (even if empty)
        if target_tuv:
            target_elem = etree.SubElement(trans_unit, 'target')
            target_elem.text = str(target_tuv.content) if target_tuv.content else ""
            # Restore target attributes
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
        else:
            # Create empty target if not found (valid in XLIFF)
            target_elem = etree.SubElement(trans_unit, 'target')
        
        # Restore context-groups (XLIFF 1.2) - these contain nested context elements
        if 'context_groups' in metadata:
            for cg_data in metadata['context_groups']:
                cg_elem = etree.SubElement(trans_unit, 'context-group')
                # Restore all context-group attributes
                for attr_name, attr_value in cg_data.items():
                    if attr_name != 'contexts' and attr_value:
                        cg_elem.set(attr_name, str(attr_value))
                
                # Restore nested context elements
                if 'contexts' in cg_data:
                    for context_data in cg_data['contexts']:
                        context_elem = etree.SubElement(cg_elem, 'context')
                        if 'text' in context_data:
                            context_elem.text = context_data['text']
                        # Restore all context attributes
                        for attr_name, attr_value in context_data.items():
                            if attr_name != 'text' and attr_value:
                                context_elem.set(attr_name, str(attr_value))
        
        # Restore standalone contexts (XLIFF 2.0 style, but might appear in 1.2)
        if 'contexts' in metadata:
            for context_data in metadata['contexts']:
                context_elem = etree.SubElement(trans_unit, 'context')
                if 'text' in context_data:
                    context_elem.text = context_data['text']
                # Restore all context attributes
                for attr_name, attr_value in context_data.items():
                    if attr_name != 'text' and attr_value:
                        context_elem.set(attr_name, str(attr_value))
        
        # Restore prop elements (XLIFF 1.2)
        if 'props' in metadata:
            for prop_data in metadata['props']:
                prop_elem = etree.SubElement(trans_unit, 'prop')
                if 'text' in prop_data:
                    prop_elem.text = prop_data['text']
                # Restore all prop attributes
                for attr_name, attr_value in prop_data.items():
                    if attr_name != 'text' and attr_value:
                        prop_elem.set(attr_name, str(attr_value))
        
        # Restore alt-trans
        if 'alt_trans' in metadata:
            for alt_trans_data in metadata['alt_trans']:
                alt_trans_elem = etree.SubElement(trans_unit, 'alt-trans')
                # Restore all alt-trans attributes
                for attr_name, attr_value in alt_trans_data.items():
                    if attr_name not in ['source', 'target'] and attr_value:
                        alt_trans_elem.set(attr_name, str(attr_value))
                # Restore source and target from alt-trans
                if 'source' in alt_trans_data:
                    alt_source = etree.SubElement(alt_trans_elem, 'source')
                    alt_source.text = alt_trans_data['source']
                if 'target' in alt_trans_data:
                    alt_target = etree.SubElement(alt_trans_elem, 'target')
                    alt_target.text = alt_trans_data['target']
        
        # Add notes
        for note in tu.notes:
            note_elem = etree.SubElement(trans_unit, 'note')
            note_text = None
            if hasattr(note, 'content') and note.content:
                note_text = note.content
            elif hasattr(note, 'text') and note.text:
                note_text = note.text
            if note_text:
                note_elem.text = note_text
            if hasattr(note, 'lang') and note.lang:
                note_elem.set(f'{{{XML_NS}}}lang', note.lang)
    
    # Write to file
    tree = etree.ElementTree(xliff)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


def create_xliff20_document(tmx: PythonTmx.Tmx, output_path: str, version: str = '2.0'):
    """
    Create XLIFF 2.0 or 2.2 document from TMX.
    
    Args:
        tmx: TMX object
        output_path: Output file path
        version: XLIFF version ('2.0' or '2.2')
    """
    namespace = XLIFF_20_NS if version == '2.0' else XLIFF_22_NS
    
    # Create root element with namespace using nsmap
    xliff = etree.Element('xliff', version=version, nsmap={None: namespace})
    
    # Create file element
    file_elem = etree.SubElement(xliff, 'file')
    file_elem.set('id', 'f1')
    file_elem.set('original', 'converted_from_tmx')
    file_elem.set('source-language', tmx.header.srclang)
    
    # Determine target language from first TU
    target_lang = tmx.header.srclang
    if tmx.tus and len(tmx.tus[0].tuvs) > 1:
        for tuv in tmx.tus[0].tuvs:
            if tuv.lang != tmx.header.srclang:
                target_lang = tuv.lang
                break
    
    file_elem.set('target-language', target_lang)
    
    # Create skeleton element (required in XLIFF 2.0+)
    skeleton = etree.SubElement(file_elem, 'skeleton')
    skeleton.set('href', 'skeleton.xml')
    
    # Create unit elements
    unit_counter = 0
    for tu in tmx.tus:
        unit = etree.SubElement(file_elem, 'unit')
        unit_counter += 1
        
        # Get metadata
        metadata = get_tu_metadata(tu)
        
        # Restore ALL unit attributes
        for key, value in metadata.items():
            if key not in ['id', 'name', 'source_attributes', 'target_attributes', 'segment_attributes', 'contexts', 'alt_trans', 'notes']:
                if value:
                    unit.set(key, str(value))
        
        # Set id (required)
        if metadata.get('id'):
            unit.set('id', metadata['id'])
        elif metadata.get('name'):
            unit.set('id', metadata['name'])
        else:
            unit.set('id', f'u{unit_counter}')
        
        # Set name if present
        if metadata.get('name'):
            unit.set('name', metadata['name'])
        
        # Create segment
        segment = etree.SubElement(unit, 'segment')
        
        # Restore segment attributes
        if 'segment_attributes' in metadata:
            for attr_name, attr_value in metadata['segment_attributes'].items():
                segment.set(attr_name, str(attr_value))
        
        # Find source and target TUVs
        source_tuv = None
        target_tuvs = []
        source_lang = tmx.header.srclang
        
        for tuv in tu.tuvs:
            # Normalize language codes for comparison
            tuv_lang = tuv.lang.lower().replace('_', '-')
            src_lang_norm = source_lang.lower().replace('_', '-')
            
            if tuv_lang == src_lang_norm or tuv_lang.startswith(src_lang_norm.split('-')[0]):
                source_tuv = tuv
            else:
                target_tuvs.append(tuv)
        
        # Use first target TUV (XLIFF typically has one target per unit)
        target_tuv = target_tuvs[0] if target_tuvs else None
        
        # Always create source element
        if source_tuv:
            source_elem = etree.SubElement(segment, 'source')
            source_elem.text = str(source_tuv.content) if source_tuv.content else ""
            # Restore source attributes
            if 'source_attributes' in metadata:
                for attr_name, attr_value in metadata['source_attributes'].items():
                    source_elem.set(attr_name, str(attr_value))
        else:
            # Create empty source if not found
            source_elem = etree.SubElement(segment, 'source')
        
        # Always create target element (even if empty)
        if target_tuv:
            target_elem = etree.SubElement(segment, 'target')
            target_elem.text = str(target_tuv.content) if target_tuv.content else ""
            # Restore target attributes
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
        else:
            # Create empty target if not found (valid in XLIFF)
            target_elem = etree.SubElement(segment, 'target')
        
        # Restore contexts
        if 'contexts' in metadata:
            for context_data in metadata['contexts']:
                context_elem = etree.SubElement(unit, 'context')
                if 'text' in context_data:
                    context_elem.text = context_data['text']
                # Restore all context attributes
                for attr_name, attr_value in context_data.items():
                    if attr_name != 'text' and attr_value:
                        context_elem.set(attr_name, str(attr_value))
        
        # Add notes
        for note in tu.notes:
            note_elem = etree.SubElement(unit, 'note')
            note_text = None
            if hasattr(note, 'content') and note.content:
                note_text = note.content
            elif hasattr(note, 'text') and note.text:
                note_text = note.text
            if note_text:
                note_elem.text = note_text
            # Restore all note attributes
            if hasattr(note, 'category') and note.category:
                note_elem.set('category', note.category)
            if hasattr(note, 'lang') and note.lang:
                note_elem.set(f'{{{XML_NS}}}lang', note.lang)
    
    # Write to file
    tree = etree.ElementTree(xliff)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


def tmx_to_xliff(tmx_file: str, output_file: Optional[str] = None, xliff_version: Optional[str] = None) -> str:
    """
    Convert TMX file to XLIFF format.
    
    Args:
        tmx_file: Path to TMX file
        output_file: Optional output XLIFF file path. If None, creates based on input filename.
        xliff_version: Optional XLIFF version ('1.2', '2.0', or '2.2'). 
                      If None, tries to detect from TMX metadata.
        
    Returns:
        str: Path to created XLIFF file
    """
    logger.info(f"Converting TMX to XLIFF: {tmx_file}")
    
    try:
        input_path = Path(tmx_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"TMX file not found: {tmx_file}")
        
        # Always parse XML directly to ensure we get ALL TUs (PythonTmx may filter some)
        tmx_tree = etree.parse(str(input_path))
        tmx_root = tmx_tree.getroot()
        
        # Extract header
        header_elem = tmx_root.find('header')
        if header_elem is None:
            raise ValueError("No header element found in TMX file")
        
        # Create minimal header
        header_attrs = {}
        for attr_name in ['creationtool', 'creationtoolversion', 'adminlang', 'srclang', 'segtype', 'datatype']:
            if attr_name in header_elem.attrib:
                header_attrs[attr_name] = header_elem.attrib[attr_name]
        
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
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE
        
        minimal_header = PythonTmx.Header(
            creationtool=header_attrs.get('creationtool', 'Unknown'),
            creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
            adminlang=header_attrs.get('adminlang', 'en'),
            srclang=header_attrs.get('srclang', 'en'),
            segtype=segtype_enum,
            datatype=header_attrs.get('datatype', 'xml'),
            tmf="tmx",
            encoding="utf8"
        )
        
        # Parse TUs - preserve ALL TUs including those with empty targets
        tus = []
        body_elem = tmx_root.find('body')
        if body_elem is not None:
            for tu_elem in body_elem.findall('tu'):
                tu = PythonTmx.Tu()
                
                # Copy all TU attributes
                for attr_name, attr_value in tu_elem.attrib.items():
                    try:
                        if attr_name == 'srclang':
                            tu.srclang = attr_value
                        # Add other TU attributes as needed
                    except Exception:
                        pass
                
                # Parse all TUVs (including empty ones)
                for tuv_elem in tu_elem.findall('tuv'):
                    lang = tuv_elem.get(f'{{{XML_NS}}}lang', 'en')
                    seg_elem = tuv_elem.find('seg')
                    
                    # Always create TUV, even if empty
                    tuv = PythonTmx.Tuv(lang=lang)
                    if seg_elem is not None:
                        # Get text content (can be None/empty) - preserve empty strings
                        tuv.content = seg_elem.text if seg_elem.text is not None else ""
                    else:
                        tuv.content = ""
                    tu.tuvs.append(tuv)
                
                # Also parse properties from XML
                for prop_elem in tu_elem.findall('prop'):
                    prop_type = prop_elem.get('type', '')
                    prop_text = prop_elem.text or ""
                    if prop_type and prop_text:
                        prop = PythonTmx.Prop(type=prop_type, text=prop_text)
                        tu.props.append(prop)
                
                # Also parse notes from XML
                for note_elem in tu_elem.findall('note'):
                    note_text = note_elem.text or ""
                    if note_text:
                        note = PythonTmx.Note(text=note_text)
                        note_lang = note_elem.get(f'{{{XML_NS}}}lang', '')
                        if note_lang:
                            note.lang = note_lang
                        tu.notes.append(note)
                
                # Add TU even if it only has source (empty targets are valid in XLIFF)
                if len(tu.tuvs) >= 1:
                    tus.append(tu)
        
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        logger.info(f"Loaded {len(tus)} translation units from TMX file")
        
        # Determine XLIFF version
        if xliff_version is None:
            xliff_version = get_xliff_version_from_tmx(tmx)
            
            # If version still not found, try extracting from XML directly
            if xliff_version == '1.2':
                # Try to find the note in the XML directly
                header_elem = tmx_tree.getroot().find('header')
                if header_elem is not None:
                    for note_elem in header_elem.findall('note'):
                        note_text = note_elem.text or ""
                        if 'Original XLIFF version' in note_text:
                            version = note_text.split(':')[-1].strip()
                            if version in ['1.2', '2.0', '2.2']:
                                logger.info(f"Found original XLIFF version from XML note: {version}")
                                xliff_version = version
                                break
        
        logger.info(f"Using XLIFF version: {xliff_version}")
        
        # Determine output path
        if output_file is None:
            output_path = input_path.parent / f"{input_path.stem}.xlf"
        else:
            output_path = Path(output_file)
        
        # Create XLIFF document based on version
        if xliff_version == '1.2':
            create_xliff12_document(tmx, str(output_path))
        elif xliff_version in ['2.0', '2.2']:
            create_xliff20_document(tmx, str(output_path), xliff_version)
        else:
            raise ValueError(f"Unsupported XLIFF version: {xliff_version}")
        
        logger.info(f"Converted {len(tmx.tus)} translation units to XLIFF {xliff_version}: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error converting TMX to XLIFF: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    
    tmx_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    xliff_version = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        xliff_path = tmx_to_xliff(tmx_file, output_file, xliff_version)
        print(f"Successfully converted TMX to XLIFF: {xliff_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


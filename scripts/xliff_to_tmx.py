"""
Convert XLIFF 1.2, 2.0, and 2.2 files to TMX format.
Preserves metadata and stores original XLIFF version information.
"""

import lxml.etree as etree
from pathlib import Path
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import json
import PythonTmx

logger = logging.getLogger(__name__)

# XLIFF namespaces
XLIFF_12_NS_URI = 'urn:oasis:names:tc:xliff:document:1.2'
XLIFF_20_NS_URI = 'urn:oasis:names:tc:xliff:document:2.0'
XLIFF_22_NS_URI = 'urn:oasis:names:tc:xliff:document:2.2'
XLIFF_12_NS = {'xliff12': XLIFF_12_NS_URI}
XLIFF_20_NS = {'ns': XLIFF_20_NS_URI}
XLIFF_22_NS = {'ns': XLIFF_22_NS_URI}
XML_NS = {'xml': 'http://www.w3.org/XML/1998/namespace'}


def detect_xliff_version(xliff_root: etree.Element) -> Tuple[str, Dict[str, str], Optional[str]]:
    """
    Detect XLIFF version and return appropriate namespace mapping.
    
    Args:
        xliff_root: Root element of XLIFF document
        
    Returns:
        tuple: (version string, namespace dictionary, namespace URI or None)
    """
    version = xliff_root.get('version', '1.2')
    
    # Get namespace URI from root element
    ns_uri = None
    if xliff_root.tag.startswith('{'):
        ns_uri = xliff_root.tag[1:].split('}')[0]
    else:
        # Check xmlns attribute
        ns_uri = xliff_root.get('xmlns')
    
    if version == '2.0':
        return '2.0', XLIFF_20_NS, XLIFF_20_NS_URI
    elif version == '2.2':
        return '2.2', XLIFF_22_NS, XLIFF_22_NS_URI
    else:
        # Default to 1.2
        return '1.2', XLIFF_12_NS, ns_uri if ns_uri == XLIFF_12_NS_URI else None


def get_text_content(element: etree.Element) -> str:
    """
    Get text content from element, handling nested elements.
    
    Args:
        element: XML element
        
    Returns:
        str: Text content
    """
    if element is None:
        return ""
    
    # Get direct text
    text = element.text or ""
    
    # Get text from all child elements
    for child in element:
        if child.text:
            text += child.text
        if child.tail:
            text += child.tail
    
    return text.strip()


def get_target_language_from_element(elem: etree.Element) -> Optional[str]:
    """
    Extract target language from an element, checking multiple attribute names.
    
    Args:
        elem: XML element (xliff root or file element)
        
    Returns:
        str or None: Target language code if found, None otherwise
    """
    # Check for target-language (standard)
    target_lang = elem.get('target-language')
    if target_lang:
        logger.debug(f"Found target language from 'target-language' attribute: {target_lang}")
        return target_lang
    
    # Check for trgLang (alternative)
    target_lang = elem.get('trgLang')
    if target_lang:
        logger.debug(f"Found target language from 'trgLang' attribute: {target_lang}")
        return target_lang
    
    return None


def get_target_language(xliff_root: etree.Element, file_elem: Optional[etree.Element] = None) -> str:
    """
    Extract target language from XLIFF document, checking root xliff element and file elements.
    
    Args:
        xliff_root: Root xliff element
        file_elem: Optional file element to check
        
    Returns:
        str: Target language code
    """
    # First check the root xliff element
    target_lang = get_target_language_from_element(xliff_root)
    if target_lang:
        return target_lang
    
    # Then check the file element if provided
    if file_elem is not None:
        target_lang = get_target_language_from_element(file_elem)
        if target_lang:
            return target_lang
    
    # If no file element provided, check all direct file children of xliff
    # Try non-namespaced first
    for file_elem in xliff_root.findall('./file'):
        target_lang = get_target_language_from_element(file_elem)
        if target_lang:
            return target_lang
    
    # Try XLIFF 1.2 namespace
    for file_elem in xliff_root.findall(f'./{{{XLIFF_12_NS_URI}}}file'):
        target_lang = get_target_language_from_element(file_elem)
        if target_lang:
            return target_lang
    
    # For XLIFF 2.0/2.2, check namespaced file elements
    for ns_uri in [XLIFF_20_NS_URI, XLIFF_22_NS_URI]:
        for file_elem in xliff_root.findall(f'./{{{ns_uri}}}file'):
            target_lang = get_target_language_from_element(file_elem)
            if target_lang:
                return target_lang
    
    # Log warning if target language not found
    logger.warning(f"Target language not found. Checked root xliff element and file elements.")
    
    # Default fallback
    return 'en'


def extract_units_xliff12(xliff_root: etree.Element, ns_uri: Optional[str] = None) -> list:
    """
    Extract translation units from XLIFF 1.2 format.
    Handles both namespaced and non-namespaced XLIFF 1.2 files.
    
    Args:
        xliff_root: Root element of XLIFF 1.2 document
        ns_uri: Optional namespace URI for XLIFF 1.2
        
    Returns:
        list: List of (source_text, target_text, source_lang, target_lang, metadata) tuples
    """
    units = []
    
    # Determine if we need namespace-aware parsing
    use_namespace = ns_uri is not None and ns_uri == XLIFF_12_NS_URI
    
    # Find file elements (with or without namespace)
    if use_namespace:
        file_elems = xliff_root.findall(f'.//{{{ns_uri}}}file')
    else:
        # Try both namespaced and non-namespaced
        file_elems = xliff_root.findall('.//file')
        if not file_elems:
            # Try with namespace
            file_elems = xliff_root.findall(f'.//{{{XLIFF_12_NS_URI}}}file')
            use_namespace = len(file_elems) > 0
    
    for file_elem in file_elems:
        source_lang = file_elem.get('source-language', 'en')
        target_lang = get_target_language(xliff_root, file_elem)
        
        # Find trans-unit elements
        if use_namespace:
            trans_units = file_elem.findall(f'.//{{{ns_uri}}}trans-unit')
        else:
            trans_units = file_elem.findall('.//trans-unit')
            if not trans_units:
                trans_units = file_elem.findall(f'.//{{{XLIFF_12_NS_URI}}}trans-unit')
        
        for trans_unit in trans_units:
            # Capture ALL attributes from trans-unit
            metadata = {}
            for attr_name, attr_value in trans_unit.attrib.items():
                if attr_value:  # Only store non-empty values
                    metadata[attr_name] = attr_value
            
            # Ensure 'id' exists (even if empty)
            if 'id' not in metadata:
                metadata['id'] = trans_unit.get('id', '')
            
            # Find source and target elements
            if use_namespace:
                source_elem = trans_unit.find(f'{{{ns_uri}}}source')
                target_elem = trans_unit.find(f'{{{ns_uri}}}target')
            else:
                source_elem = trans_unit.find('source')
                if source_elem is None:
                    source_elem = trans_unit.find(f'{{{XLIFF_12_NS_URI}}}source')
                target_elem = trans_unit.find('target')
                if target_elem is None:
                    target_elem = trans_unit.find(f'{{{XLIFF_12_NS_URI}}}target')
            
            source_text = get_text_content(source_elem) if source_elem is not None else ""
            target_text = get_text_content(target_elem) if target_elem is not None else ""
            
            # Capture source and target attributes
            if source_elem is not None:
                source_attrs = {}
                for attr_name, attr_value in source_elem.attrib.items():
                    if attr_value:
                        source_attrs[attr_name] = attr_value
                if source_attrs:
                    metadata['source_attributes'] = source_attrs
            
            if target_elem is not None:
                target_attrs = {}
                for attr_name, attr_value in target_elem.attrib.items():
                    if attr_value:
                        target_attrs[attr_name] = attr_value
                if target_attrs:
                    metadata['target_attributes'] = target_attrs
            
            # Extract notes
            notes = []
            if use_namespace:
                note_elems = trans_unit.findall(f'{{{ns_uri}}}note')
            else:
                note_elems = trans_unit.findall('note')
                if not note_elems:
                    note_elems = trans_unit.findall(f'{{{XLIFF_12_NS_URI}}}note')
            
            for note_elem in note_elems:
                note_data = {}
                note_text = note_elem.text or ""
                if note_text:
                    note_data['text'] = note_text
                # Capture all note attributes
                for attr_name, attr_value in note_elem.attrib.items():
                    if attr_value:
                        note_data[attr_name] = attr_value
                notes.append(note_data)
            metadata['notes'] = notes
            
            # Extract context-group elements (XLIFF 1.2) - these contain nested context elements
            context_groups = []
            if use_namespace:
                context_group_elems = trans_unit.findall(f'{{{ns_uri}}}context-group')
            else:
                context_group_elems = trans_unit.findall('context-group')
                if not context_group_elems:
                    context_group_elems = trans_unit.findall(f'{{{XLIFF_12_NS_URI}}}context-group')
            
            for cg_elem in context_group_elems:
                cg_data = {}
                # Capture all context-group attributes
                for attr_name, attr_value in cg_elem.attrib.items():
                    if attr_value:
                        cg_data[attr_name] = attr_value
                
                # Extract nested context elements within this context-group
                contexts = []
                if use_namespace:
                    context_elems = cg_elem.findall(f'{{{ns_uri}}}context')
                else:
                    context_elems = cg_elem.findall('context')
                    if not context_elems:
                        context_elems = cg_elem.findall(f'{{{XLIFF_12_NS_URI}}}context')
                
                for context_elem in context_elems:
                    context_data = {}
                    context_text = get_text_content(context_elem)
                    if context_text:
                        context_data['text'] = context_text
                    # Capture all context attributes
                    for attr_name, attr_value in context_elem.attrib.items():
                        if attr_value:
                            context_data[attr_name] = attr_value
                    contexts.append(context_data)
                
                if contexts:
                    cg_data['contexts'] = contexts
                
                context_groups.append(cg_data)
            
            # Also check for standalone context elements (XLIFF 2.0 style, but might appear in 1.2)
            if not context_groups:
                if use_namespace:
                    context_elems = trans_unit.findall(f'{{{ns_uri}}}context')
                else:
                    context_elems = trans_unit.findall('context')
                    if not context_elems:
                        context_elems = trans_unit.findall(f'{{{XLIFF_12_NS_URI}}}context')
                
                for context_elem in context_elems:
                    context_data = {}
                    context_text = get_text_content(context_elem)
                    if context_text:
                        context_data['text'] = context_text
                    # Capture all context attributes
                    for attr_name, attr_value in context_elem.attrib.items():
                        if attr_value:
                            context_data[attr_name] = attr_value
                    context_groups.append(context_data)
            
            if context_groups:
                metadata['context_groups'] = context_groups
            
            # Extract alt-trans elements
            alt_trans_list = []
            if use_namespace:
                alt_trans_elems = trans_unit.findall(f'{{{ns_uri}}}alt-trans')
            else:
                alt_trans_elems = trans_unit.findall('alt-trans')
                if not alt_trans_elems:
                    alt_trans_elems = trans_unit.findall(f'{{{XLIFF_12_NS_URI}}}alt-trans')
            
            for alt_trans_elem in alt_trans_elems:
                alt_trans_data = {}
                # Capture all alt-trans attributes
                for attr_name, attr_value in alt_trans_elem.attrib.items():
                    if attr_value:
                        alt_trans_data[attr_name] = attr_value
                # Extract source and target from alt-trans
                alt_source = alt_trans_elem.find('source' if not use_namespace else f'{{{ns_uri}}}source')
                alt_target = alt_trans_elem.find('target' if not use_namespace else f'{{{ns_uri}}}target')
                if alt_source is not None:
                    alt_trans_data['source'] = get_text_content(alt_source)
                if alt_target is not None:
                    alt_trans_data['target'] = get_text_content(alt_target)
                alt_trans_list.append(alt_trans_data)
            if alt_trans_list:
                metadata['alt_trans'] = alt_trans_list
            
            # Extract prop elements (XLIFF 1.2)
            props = []
            if use_namespace:
                prop_elems = trans_unit.findall(f'{{{ns_uri}}}prop')
            else:
                prop_elems = trans_unit.findall('prop')
                if not prop_elems:
                    prop_elems = trans_unit.findall(f'{{{XLIFF_12_NS_URI}}}prop')
            
            for prop_elem in prop_elems:
                prop_data = {}
                prop_text = get_text_content(prop_elem)
                if prop_text:
                    prop_data['text'] = prop_text
                # Capture all prop attributes
                for attr_name, attr_value in prop_elem.attrib.items():
                    if attr_value:
                        prop_data[attr_name] = attr_value
                props.append(prop_data)
            if props:
                metadata['props'] = props
            
            units.append((source_text, target_text, source_lang, target_lang, metadata))
    
    return units


def extract_units_xliff20(xliff_root: etree.Element, ns: Dict[str, str]) -> list:
    """
    Extract translation units from XLIFF 2.0/2.2 format.
    
    Args:
        xliff_root: Root element of XLIFF 2.0/2.2 document
        ns: Namespace dictionary
        
    Returns:
        list: List of (source_text, target_text, source_lang, target_lang, metadata) tuples
    """
    units = []
    
    for file_elem in xliff_root.findall('.//ns:file', ns):
        source_lang = file_elem.get('source-language', 'en')
        target_lang = get_target_language(xliff_root, file_elem)
        
        for unit_elem in file_elem.findall('.//ns:unit', ns):
            # Capture ALL attributes from unit
            metadata = {}
            for attr_name, attr_value in unit_elem.attrib.items():
                if attr_value:  # Only store non-empty values
                    metadata[attr_name] = attr_value
            
            # Ensure 'id' exists (even if empty)
            if 'id' not in metadata:
                metadata['id'] = unit_elem.get('id', '')
            
            # Find segment (XLIFF 2.0+ uses segment element)
            segment = unit_elem.find('.//ns:segment', ns)
            if segment is None:
                continue
            
            source_elem = segment.find('ns:source', ns)
            target_elem = segment.find('ns:target', ns)
            
            source_text = get_text_content(source_elem) if source_elem is not None else ""
            target_text = get_text_content(target_elem) if target_elem is not None else ""
            
            # Capture source and target attributes
            if source_elem is not None:
                source_attrs = {}
                for attr_name, attr_value in source_elem.attrib.items():
                    if attr_value:
                        source_attrs[attr_name] = attr_value
                if source_attrs:
                    metadata['source_attributes'] = source_attrs
            
            if target_elem is not None:
                target_attrs = {}
                for attr_name, attr_value in target_elem.attrib.items():
                    if attr_value:
                        target_attrs[attr_name] = attr_value
                if target_attrs:
                    metadata['target_attributes'] = target_attrs
            
            # Capture segment attributes
            segment_attrs = {}
            for attr_name, attr_value in segment.attrib.items():
                if attr_value:
                    segment_attrs[attr_name] = attr_value
            if segment_attrs:
                metadata['segment_attributes'] = segment_attrs
            
            # Extract notes
            notes = []
            for note_elem in unit_elem.findall('.//ns:note', ns):
                note_data = {}
                note_text = get_text_content(note_elem)
                if note_text:
                    note_data['text'] = note_text
                # Capture all note attributes
                for attr_name, attr_value in note_elem.attrib.items():
                    if attr_value:
                        note_data[attr_name] = attr_value
                notes.append(note_data)
            metadata['notes'] = notes
            
            # Extract context elements (XLIFF 2.0+)
            contexts = []
            for context_elem in unit_elem.findall('.//ns:context', ns):
                context_data = {}
                context_text = get_text_content(context_elem)
                if context_text:
                    context_data['text'] = context_text
                # Capture all context attributes
                for attr_name, attr_value in context_elem.attrib.items():
                    if attr_value:
                        context_data[attr_name] = attr_value
                contexts.append(context_data)
            if contexts:
                metadata['contexts'] = contexts
            
            units.append((source_text, target_text, source_lang, target_lang, metadata))
    
    return units


def xliff_to_tmx(xliff_file: str, output_file: Optional[str] = None) -> Tuple[str, str]:
    """
    Convert XLIFF file (1.2, 2.0, or 2.2) to TMX format.
    
    Args:
        xliff_file: Path to XLIFF file
        output_file: Optional output TMX file path. If None, creates based on input filename.
        
    Returns:
        tuple: (output_tmx_path, original_xliff_version)
    """
    logger.info(f"Converting XLIFF to TMX: {xliff_file}")
    
    try:
        input_path = Path(xliff_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"XLIFF file not found: {xliff_file}")
        
        # Parse XLIFF file with robust encoding handling
        xliff_tree = None
        parsing_strategies = [
            lambda: etree.parse(str(input_path)),
            lambda: etree.parse(str(input_path), etree.XMLParser(recover=True)),
            lambda: etree.parse(str(input_path), etree.XMLParser(encoding="utf-8")),
            lambda: etree.parse(str(input_path), etree.XMLParser(encoding="cp1252")),
        ]
        
        for strategy in parsing_strategies:
            try:
                xliff_tree = strategy()
                if xliff_tree is not None and xliff_tree.getroot() is not None:
                    break
            except Exception:
                continue
        
        if xliff_tree is None:
            raise ValueError("Could not parse XLIFF file with any supported encoding")
        
        xliff_root = xliff_tree.getroot()
        
        # Detect XLIFF version
        xliff_version, ns, ns_uri = detect_xliff_version(xliff_root)
        logger.info(f"Detected XLIFF version: {xliff_version}")
        if ns_uri:
            logger.debug(f"Using namespace URI: {ns_uri}")
        
        # Extract translation units based on version
        if xliff_version == '1.2':
            units = extract_units_xliff12(xliff_root, ns_uri)
        else:  # 2.0 or 2.2
            units = extract_units_xliff20(xliff_root, ns)
        
        if not units:
            logger.warning("No translation units found in XLIFF file")
        
        # Create TMX structure
        # Determine source and target languages from first unit
        source_lang = units[0][2] if units else 'en'
        target_lang = units[0][3] if units else 'en'
        
        # Create TMX header
        segtype = PythonTmx.SEGTYPE.SENTENCE
        header = PythonTmx.Header(
            srclang=source_lang,
            segtype=segtype,
            adminlang=source_lang,
            creationtool="XLIFF to TMX Converter",
            creationtoolversion="1.0",
            tmf="tmx",
            datatype="unknown",
            encoding="utf8"
        )
        
        # Store original XLIFF version in header note
        header_note = PythonTmx.Note(text=f"Original XLIFF version: {xliff_version}")
        header.notes.append(header_note)
        
        # Create TMX object
        tmx = PythonTmx.Tmx(header=header)
        
        # Convert units to TMX TUs
        for source_text, target_text, src_lang, tgt_lang, metadata in units:
            # Create source TUV
            source_tuv = PythonTmx.Tuv(lang=src_lang)
            source_tuv.content = source_text
            
            # Create target TUV
            target_tuv = PythonTmx.Tuv(lang=tgt_lang)
            target_tuv.content = target_text
            
            # Create TU
            tu = PythonTmx.Tu(srclang=src_lang, tuvs=[source_tuv, target_tuv])
            
            # Store XLIFF version in property
            prop_version = PythonTmx.Prop(type="x-xliff-version", text=xliff_version)
            tu.props.append(prop_version)
            
            # Store ALL trans-unit/unit attributes as properties
            for key, value in metadata.items():
                # Skip special keys that are handled separately
                if key in ['notes', 'contexts', 'context_groups', 'alt_trans', 'source_attributes', 'target_attributes', 'segment_attributes', 'props', 'prop']:
                    continue
                
                if value:  # Only store non-empty values
                    # Use a safe property type name (replace special chars with placeholders)
                    prop_type = f"x-xliff-{key}".replace(':', '_COLON_').replace(' ', '_SPACE_')
                    prop = PythonTmx.Prop(type=prop_type, text=str(value))
                    tu.props.append(prop)
            
            # Store source attributes
            if 'source_attributes' in metadata:
                for attr_name, attr_value in metadata['source_attributes'].items():
                    prop_type = f"x-xliff-source-{attr_name}".replace(':', '_COLON_').replace(' ', '_SPACE_')
                    prop = PythonTmx.Prop(type=prop_type, text=str(attr_value))
                    tu.props.append(prop)
            
            # Store target attributes
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    prop_type = f"x-xliff-target-{attr_name}".replace(':', '_COLON_').replace(' ', '_SPACE_')
                    prop = PythonTmx.Prop(type=prop_type, text=str(attr_value))
                    tu.props.append(prop)
            
            # Store segment attributes (XLIFF 2.0+)
            if 'segment_attributes' in metadata:
                for attr_name, attr_value in metadata['segment_attributes'].items():
                    prop_type = f"x-xliff-segment-{attr_name}".replace(':', '_COLON_').replace(' ', '_SPACE_')
                    prop = PythonTmx.Prop(type=prop_type, text=str(attr_value))
                    tu.props.append(prop)
            
            # Store context-groups as JSON-like strings in properties (XLIFF 1.2)
            if 'context_groups' in metadata:
                context_groups_json = json.dumps(metadata['context_groups'], ensure_ascii=False)
                prop = PythonTmx.Prop(type="x-xliff-context-groups", text=context_groups_json)
                tu.props.append(prop)
            
            # Store contexts as JSON-like strings in properties (XLIFF 2.0+)
            if 'contexts' in metadata:
                contexts_json = json.dumps(metadata['contexts'], ensure_ascii=False)
                prop = PythonTmx.Prop(type="x-xliff-contexts", text=contexts_json)
                tu.props.append(prop)
            
            # Store alt-trans as JSON-like strings in properties
            if 'alt_trans' in metadata:
                alt_trans_json = json.dumps(metadata['alt_trans'], ensure_ascii=False)
                prop = PythonTmx.Prop(type="x-xliff-alt-trans", text=alt_trans_json)
                tu.props.append(prop)
            
            # Store props as JSON-like strings in properties (XLIFF 1.2)
            if 'props' in metadata:
                props_json = json.dumps(metadata['props'], ensure_ascii=False)
                prop = PythonTmx.Prop(type="x-xliff-props", text=props_json)
                tu.props.append(prop)
            
            # Add notes
            for note_data in metadata.get('notes', []):
                note_text = note_data.get('text', '')
                note = PythonTmx.Note(text=note_text)
                if 'lang' in note_data and note_data['lang']:
                    note.lang = note_data['lang']
                tu.notes.append(note)
            
            tmx.tus.append(tu)
        
        # Determine output path
        if output_file is None:
            output_path = input_path.parent / f"{input_path.stem}.tmx"
        else:
            output_path = Path(output_file)
        
        # Save TMX file
        try:
            tmx.to_tmx(str(output_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            root = PythonTmx.to_element(tmx, True)
            etree.ElementTree(root).write(str(output_path), encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Converted {len(units)} translation units to TMX: {output_path}")
        return str(output_path), xliff_version
        
    except Exception as e:
        logger.error(f"Error converting XLIFF to TMX: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    
    xliff_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        tmx_path, version = xliff_to_tmx(xliff_file, output_file)
        print(f"Successfully converted XLIFF {version} to TMX: {tmx_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


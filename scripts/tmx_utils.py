import base64
import json
import os
import shutil
import PythonTmx
import logging
import lxml.etree as etree
from typing import Optional

logger = logging.getLogger(__name__)

# TMX <prop> payload for full-element XLIFF markup (avoids JSON + raw < in XML issues)
MARKUP_XML_B64_PREFIX = 'b64:'

_XML_NS_LANG = '{http://www.w3.org/XML/1998/namespace}lang'


def local_name(tag) -> str:
    """XML element local name (works for default-namespace TMX)."""
    if not isinstance(tag, str):
        return ''
    return etree.QName(tag).localname


def children_by_local(parent: etree.ElementBase, local: str):
    """Direct children whose local name matches."""
    return [c for c in parent if isinstance(c.tag, str) and local_name(c.tag) == local]


def element_inner_text(elem: etree.ElementBase) -> str:
    """All text in elem (CDATA, split nodes, inline codes in <seg>)."""
    return ''.join(elem.itertext())


def prop_inner_text(prop_elem: etree.ElementBase) -> str:
    """
    Payload inside <prop>. If unescaped '<' split JSON into child elements, rebuild string.
    """
    if len(prop_elem) == 0:
        return prop_elem.text or ''
    chunks = []
    if prop_elem.text is not None:
        chunks.append(prop_elem.text)
    for child in prop_elem:
        chunks.append(etree.tostring(child, encoding='unicode', with_tail=False))
        if child.tail is not None:
            chunks.append(child.tail)
    return ''.join(chunks)


def encode_xliff_markup_for_tmx_prop(xml_unicode: str) -> str:
    """ASCII-safe <prop> text for round-trip (no embedded angle brackets)."""
    return MARKUP_XML_B64_PREFIX + base64.b64encode(xml_unicode.encode('utf-8')).decode('ascii')


def decode_xliff_markup_from_tmx_prop(prop_text: str) -> Optional[str]:
    """Inverse of encode_xliff_markup_for_tmx_prop; also accepts legacy json.dumps(string) props."""
    if prop_text is None:
        return None
    v = str(prop_text).strip()
    if not v:
        return None
    if v.startswith(MARKUP_XML_B64_PREFIX):
        try:
            return base64.b64decode(v[len(MARKUP_XML_B64_PREFIX) :].encode('ascii')).decode('utf-8')
        except (ValueError, UnicodeError, TypeError):
            return None
    try:
        parsed = json.loads(v)
        if isinstance(parsed, str):
            return parsed
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return v


def from_tmx(file_path):
    """Load a TMX file and return a TMX object"""
    try:
        return PythonTmx.Tmx(file_path)
    except Exception as e:
        raise Exception(f"Error loading TMX file: {e}")

def to_tmx(tmx_obj, output_path):
    """Save a TMX object to a file"""
    try:
        # Save TMX file using the correct method
        try:
            # Use the to_tmx method which should exist
            tmx_obj.to_tmx(output_path)
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            root = PythonTmx.to_element(tmx_obj, True)
            etree.ElementTree(root).write(output_path, encoding="utf-8", xml_declaration=True)
        return output_path
    except Exception as e:
        raise Exception(f"Error saving TMX file: {e}")

def validate_tmx(file_path):
    """Validate TMX file structure"""
    try:
        tmx = from_tmx(file_path)
        return True, tmx
    except Exception as e:
        return False, str(e)

def extract_header_attributes(header):
    """
    Extract all available attributes from a TMX header, handling missing attributes gracefully.
    
    Args:
        header: TMX header object from PythonTmx
    
    Returns:
        dict: Dictionary of header attributes with safe fallbacks
    """
    header_attrs = {}
    
    # Define attribute mappings with fallback values
    attribute_mappings = {
        # Required attributes with fallbacks
        'creationtool': ('creationtool', 'TMX Processor'),
        'creationtoolversion': ('creationtoolversion', '1.0'),
        'adminlang': ('adminlang', 'en'),
        'srclang': ('srclang', 'en'),
        'segtype': ('segtype', 'sentence'),
        'datatype': ('datatype', 'xml'),
        
        # Optional attributes (preserve if exists, don't set if missing)
        'o-tmf': ('o_tmf', None),
        'creationdate': ('creationdate', None),
        'creationid': ('creationid', None),
        'o-encoding': ('o_encoding', None),
        'ts': ('ts', None),
        'tuid': ('tuid', None),
        'changeid': ('changeid', None),
        'changedate': ('changedate', None),
        'prop': ('prop', None)
    }
    
    for attr_name, (python_attr, fallback) in attribute_mappings.items():
        try:
            if hasattr(header, python_attr):
                value = getattr(header, python_attr)
                if value is not None and str(value).strip():
                    header_attrs[attr_name] = str(value).strip()
                elif fallback is not None:
                    header_attrs[attr_name] = fallback
                    logger.debug(f"Using fallback for {attr_name}: {fallback}")
            elif fallback is not None:
                header_attrs[attr_name] = fallback
                logger.debug(f"Attribute {attr_name} not found, using fallback: {fallback}")
        except Exception as e:
            if fallback is not None:
                header_attrs[attr_name] = fallback
                logger.warning(f"Error accessing {attr_name}: {e}, using fallback: {fallback}")
    
    return header_attrs

def create_compatible_header(original_header, tool_name="TMX Processor", tool_version="1.0"):
    """
    Create a new TMX header that preserves original attributes while ensuring
    all required attributes exist for script compatibility.
    
    Args:
        original_header: Original TMX header object
        tool_name: Name of the processing tool (e.g., "TMX Cleaner", "TMX Splitter")
        tool_version: Version of the processing tool
    
    Returns:
        PythonTmx.Header: New header with preserved original attributes and required defaults
    """
    try:
        # Extract all available attributes from original header
        header_attrs = extract_header_attributes(original_header)
        
        # Override tool-specific attributes
        header_attrs['creationtool'] = tool_name
        header_attrs['creationtoolversion'] = tool_version
        
        # Create new header with all attributes including required ones
        # Handle segtype - ensure it's an enum not a string
        segtype_value = header_attrs['segtype']
        if isinstance(segtype_value, str):
            if segtype_value == 'sentence':
                segtype_value = PythonTmx.SEGTYPE.SENTENCE
            elif segtype_value == 'paragraph':
                segtype_value = PythonTmx.SEGTYPE.PARAGRAPH
            elif segtype_value == 'phrase':
                segtype_value = PythonTmx.SEGTYPE.PHRASE
            elif segtype_value == 'block':
                segtype_value = PythonTmx.SEGTYPE.BLOCK
            else:
                segtype_value = PythonTmx.SEGTYPE.SENTENCE  # Default fallback
        
        new_header = PythonTmx.Header(
            creationtool=header_attrs['creationtool'],
            creationtoolversion=header_attrs['creationtoolversion'],
            adminlang=header_attrs['adminlang'],
            srclang=header_attrs['srclang'],
            segtype=segtype_value,
            datatype=header_attrs['datatype'],
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )
        
        # Set optional attributes if they existed in original
        optional_attrs = ['o-tmf', 'creationdate', 'creationid', 'o-encoding', 'ts', 'tuid', 'changeid', 'changedate']
        for attr in optional_attrs:
            if attr in header_attrs and header_attrs[attr] is not None:
                try:
                    # Map attribute names to PythonTmx attribute names
                    python_attr_map = {
                        'o-tmf': 'o_tmf',
                        'o-encoding': 'o_encoding'
                    }
                    python_attr = python_attr_map.get(attr, attr)
                    if hasattr(new_header, python_attr):
                        setattr(new_header, python_attr, header_attrs[attr])
                except Exception as e:
                    logger.debug(f"Could not set optional attribute {attr}: {e}")
        
        logger.info(f"Created compatible header for {tool_name} preserving original attributes")
        return new_header
        
    except Exception as e:
        logger.error(f"Error creating compatible header: {e}")
        # Return minimal but valid header as last resort
        return PythonTmx.Header(
            creationtool=tool_name,
            creationtoolversion=tool_version,
            adminlang="en",
            srclang="en",
            segtype=PythonTmx.SEGTYPE.SENTENCE,
            datatype="xml",
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )

def copy_header_with_tool_info(original_header, tool_name, tool_version="1.0"):
    """
    Alternative function that copies the original header and only updates
    the tool-specific attributes, preserving everything else exactly.
    
    Args:
        original_header: Original TMX header object
        tool_name: Name of the processing tool
        tool_version: Version of the processing tool
    
    Returns:
        PythonTmx.Header: Copy of original header with updated tool info
    """
    try:
        # Create a copy of the original header with required parameters
        # Handle segtype properly
        original_segtype = getattr(original_header, 'segtype', PythonTmx.SEGTYPE.SENTENCE)
        if isinstance(original_segtype, str):
            if original_segtype == 'sentence':
                segtype_value = PythonTmx.SEGTYPE.SENTENCE
            elif original_segtype == 'paragraph':
                segtype_value = PythonTmx.SEGTYPE.PARAGRAPH
            elif original_segtype == 'phrase':
                segtype_value = PythonTmx.SEGTYPE.PHRASE
            elif original_segtype == 'block':
                segtype_value = PythonTmx.SEGTYPE.BLOCK
            else:
                segtype_value = PythonTmx.SEGTYPE.SENTENCE
        else:
            segtype_value = original_segtype
        
        new_header = PythonTmx.Header(
            creationtool=tool_name,
            creationtoolversion=tool_version,
            adminlang=getattr(original_header, 'adminlang', 'en'),
            srclang=getattr(original_header, 'srclang', 'en'),
            segtype=segtype_value,
            datatype=getattr(original_header, 'datatype', 'xml'),
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )
        
        # Copy all other attributes that exist in original
        for attr_name in ['o_tmf', 'creationdate', 'creationid', 'o_encoding', 'ts', 'tuid', 'changeid', 'changedate']:
            try:
                if hasattr(original_header, attr_name):
                    original_value = getattr(original_header, attr_name)
                    if original_value is not None:
                        setattr(new_header, attr_name, original_value)
            except Exception as e:
                logger.debug(f"Could not copy attribute {attr_name}: {e}")
        
        return new_header
        
    except Exception as e:
        logger.error(f"Error copying header: {e}")
        return create_compatible_header(original_header, tool_name, tool_version)


def append_header_notes_from_xml(header_elem, target_header: PythonTmx.Header) -> None:
    """Copy <note> children from parsed TMX <header> onto a PythonTmx header (XLIFF round-trip)."""
    if header_elem is None:
        return
    for note_elem in children_by_local(header_elem, 'note'):
        note_text = element_inner_text(note_elem)
        note = PythonTmx.Note(text=note_text)
        note_lang = note_elem.get(_XML_NS_LANG)
        if note_lang:
            note.lang = note_lang
        target_header.notes.append(note)


def append_tu_props_from_element(tu_elem, tu: PythonTmx.Tu) -> None:
    """Copy <prop> children from a <tu> element onto a PythonTmx Tu (XLIFF metadata)."""
    for prop_elem in children_by_local(tu_elem, 'prop'):
        ptype = prop_elem.get('type')
        if not ptype:
            continue
        ptext = prop_inner_text(prop_elem)
        prop = PythonTmx.Prop(type=ptype, text=ptext)
        lang = prop_elem.get(_XML_NS_LANG)
        if lang:
            prop.lang = lang
        tu.props.append(prop)


def copy_xliff_roundtrip_sidecar(source_tmx_path: str, *output_tmx_paths: str) -> None:
    """
    When a script writes clean_* or duplicates_* TMX files, copy *.xliff-origin.json
    from the input stem to each output stem so convert_tmx_to_xliff_if_needed can find it.
    """
    src = os.path.splitext(source_tmx_path)[0] + '.xliff-origin.json'
    if not os.path.isfile(src):
        return
    src_abs = os.path.abspath(src)
    for outp in output_tmx_paths:
        if not outp:
            continue
        dst = os.path.splitext(outp)[0] + '.xliff-origin.json'
        if os.path.abspath(dst) == src_abs:
            continue
        try:
            shutil.copy2(src, dst)
        except OSError as e:
            logger.warning(f"Could not copy XLIFF round-trip sidecar to {dst}: {e}")
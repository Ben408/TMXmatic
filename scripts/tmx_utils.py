import PythonTmx
import logging

logger = logging.getLogger(__name__)

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
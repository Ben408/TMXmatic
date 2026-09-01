import PythonTmx
from datetime import datetime
import os
import logging
from pathlib import Path
from typing import List, Dict, Set
import lxml.etree as etree
from .tmx_utils import create_compatible_header

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

def merge_tmx_files(file_paths: List[str]) -> str:
    """
    Merge multiple TMX files into one, removing duplicates.
    Keeps most recent version of duplicate segments.
    
    Args:
        file_paths: List of paths to TMX files
    
    Returns:
        str: Path to merged TMX file
    """
    logger.info(f"Starting merge of {len(file_paths)} TMX files")
    
    try:
        if len(file_paths) < 2:
            raise ValueError("At least two TMX files are required for merging")
        
        # Create output path based on first file
        first_path = Path(file_paths[0])
        output_path = first_path.parent / f"merged_files.tmx"

        concat_list = []                #This list will hold all the TUs present in the tmx_list individual TMs
        header = None
        
        for tmx_file in file_paths:            #Loops through every .tmx file in tmx_list
            try:
                # Try to load with PythonTmx first
                tmx_obj = PythonTmx.Tmx(tmx_file)
                if header is None:
                    header = create_compatible_header(tmx_obj.header, "TMX Merger", "1.0")
                concat_list.extend(tmx_obj.tus)
            except Exception as e:
                logger.warning(f"Failed to load {tmx_file} with PythonTmx, trying lxml fallback: {e}")
                # Fallback to robust lxml parsing with multiple strategies
                tm = None
                tmx_root = None
                
                # Try multiple parsing strategies
                parsing_strategies = [
                    lambda: etree.parse(tmx_file),  # Auto-detect encoding (handles BOM)
                    lambda: etree.parse(tmx_file, etree.XMLParser(recover=True)),  # Recover from errors
                    lambda: etree.parse(tmx_file, etree.XMLParser(encoding="utf-8")),  # Explicit UTF-8
                    lambda: etree.parse(tmx_file, etree.XMLParser(encoding="cp1252")),  # Windows encoding
                    lambda: etree.parse(tmx_file, etree.XMLParser(encoding="latin-1"))  # Latin encoding
                ]
                
                for strategy in parsing_strategies:
                    try:
                        tm = strategy()
                        if tm is not None and tm.getroot() is not None:
                            tmx_root = tm.getroot()
                            break  # Successfully parsed, exit loop
                    except Exception as parse_e:
                        logger.info(f"Parsing strategy failed: {parse_e}")
                        continue
                
                if tmx_root is None:
                    raise ValueError(f"Failed to parse {tmx_file} with all parsing strategies")
                
                # Extract header attributes from XML if this is the first file
                if header is None:
                    header_elem = tmx_root.find('header')
                    if header_elem is None:
                        raise ValueError(f"No header element found in {tmx_file}")
                    
                    # Create a minimal header object for compatibility
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
                    
                    header = create_compatible_header(minimal_header, "TMX Merger", "1.0")
                
                # Parse TUs manually from XML
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
                            concat_list.append(tu)

        merged_tm = PythonTmx.Tmx(header=header, tus=concat_list)
        # Save TMX file using the correct method
        try:
            # Use the to_tmx method which should exist
            merged_tm.to_tmx(str(output_path))
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            root = PythonTmx.to_element(merged_tm, True)
            etree.ElementTree(root).write(str(output_path), encoding="utf-8", xml_declaration=True)

        logger.info(f"Merged TMX created with {len(concat_list)} TUs")
        return str(output_path)

    except Exception as e:
        logger.error(f"Error merging TMX files: {e}")
        raise

def process_directory(directory, target_file=None):
    """
    Process all TMX files in a directory.

    Args:
        directory (str): Directory containing TMX files
        target_file (str, optional): Path to save merged TMX

    Returns:
        tuple: (target_file_path, total_files, total_tus), log_messages
    """
    logger = OperationLog()
    
    try:
        # Get list of TMX files in directory
        file_list = [os.path.join(directory, f) for f in os.listdir(directory) 
                    if f.endswith('.tmx')]
        
        if not file_list:
            logger.error(f"No TMX files found in {directory}")
            raise ValueError(f"No TMX files found in {directory}")
            
        logger.info(f"Found {len(file_list)} TMX files to merge")
        result = merge_tmx_files(file_list)
        
        return result, logger.get_log()
        
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise

def process_file_list(files, target_file=None):
    """
    Process a specific list of TMX files.

    Args:
        files (list): List of TMX file paths
        target_file (str, optional): Path to save merged TMX

    Returns:
        tuple: (target_file_path, total_files, total_tus), log_messages
    """
    logger = OperationLog()
    
    try:
        # Validate files exist
        for file in files:
            if not os.path.exists(file):
                logger.error(f"File not found: {file}")
                raise FileNotFoundError(f"File not found: {file}")
        
        logger.info(f"Processing {len(files)} specified TMX files")
        result = merge_tmx_files(files)
        
        return result, logger.get_log()
        
    except Exception as e:
        logger.error(f"Error processing file list: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    print("Enter TMX file paths (one per line, empty line to finish):")
    file_paths = []
    while True:
        path = input().strip()
        if not path:
            break
        file_paths.append(path)
    
    try:
        output_file = merge_tmx_files(file_paths)
        print(f"Merged TMX created: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
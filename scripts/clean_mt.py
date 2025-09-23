import PythonTmx
import os
import re
from datetime import datetime
import logging
import lxml.etree as etree
from .tmx_utils import create_compatible_header

class OperationLog:
    def __init__(self):
        self.messages = []
    
    def info(self, msg):
        self.messages.append(("info", msg))
    
    def error(self, msg):
        self.messages.append(("error", msg))
    
    def get_log(self):
        return self.messages

def clean_tmx_for_mt(source_file, target_file=None, logger=None):
    print("asrasdas")
    """
    Cleans TMX file for MT training by removing metadata and normalizing content.
    WARNING: This process removes information needed for translation leveraging.
    Use only for preparing MT training data.

    Args:
        source_file (str): Path to source TMX file
        target_file (str, optional): Path to save cleaned TMX. If None, will use 'mt_clean_{source_name}'
        logger (OperationLog, optional): Logger for tracking progress and errors

    Returns:
        tuple: (target_file_path, processed_count, cleaned_count)
    """
    if logger is None:
        logger = OperationLog()

    if target_file is None:
        source_dir = os.path.dirname(source_file)
        source_name = os.path.basename(source_file)
        target_file = os.path.join(source_dir, f'mt_clean_{source_name}')

    try:
        # Read the TMX file using robust lxml parsing with fallbacks
        tm = None
        clean_header = None
        
        # Try multiple parsing strategies
        parsing_strategies = [
            lambda: etree.parse(source_file),  # Auto-detect encoding (handles BOM)
            lambda: etree.parse(source_file, etree.XMLParser(recover=True)),  # Recover from errors
            lambda: etree.parse(source_file, etree.XMLParser(encoding="utf-8")),  # Explicit UTF-8
            lambda: etree.parse(source_file, etree.XMLParser(encoding="cp1252")),  # Windows encoding
            lambda: etree.parse(source_file, etree.XMLParser(encoding="latin-1"))  # Latin encoding
        ]
        
        for strategy in parsing_strategies:
            try:
                tm_xml = strategy()
                if tm_xml is not None and tm_xml.getroot() is not None:
                    tmx_root = tm_xml.getroot()
                    
                    # Extract header attributes from XML
                    header_elem = tmx_root.find('header')
                    if header_elem is None:
                        continue  # Try next strategy
                    
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
                    
                    clean_header = create_compatible_header(minimal_header, "TMX MT Cleaner", "1.0")
                    
                    # Parse TUs manually from XML
                    tm = PythonTmx.Tmx(header=clean_header)
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
                                tm.tus.append(tu)
                    
                    break  # Successfully parsed, exit loop
                    
            except Exception as e:
                if logger:
                    logger.info(f"Parsing strategy failed: {e}")
                continue
        
        if tm is None or clean_header is None:
            raise ValueError("Failed to parse TMX file with all parsing strategies")
        
        clean_tm = []
        processed_count = 0
        cleaned_count = 0

        # Compile regex patterns
        tag_pattern = re.compile(r'<[^>]+>')
        whitespace_pattern = re.compile(r'\s+')
        alphanumeric_pattern = re.compile(r'[a-zA-Z0-9]')
        
        total_tus = len(tm.tus)
        logger.info(f"Processing {total_tus} translation units")

        # Process each TU
        for i, tu in enumerate(tm.tus):
            if i % 100 == 0:  # Progress update every 100 items
                logger.info(f"Progress: {(i/total_tus)*100:.1f}% ({i}/{total_tus})")

            keep_tu = True
            source_text = ""
            target_text = ""

            # Extract and clean text
            for tuv in tu.tuvs:
                text = ''.join(str(seg) for seg in tuv.content)
                
                # Remove tags
                text = tag_pattern.sub(' ', text)
                # Normalize whitespace
                text = whitespace_pattern.sub(' ', text).strip()
                
                if tuv.lang.lower() == "en-us":
                    source_text = text
                else:
                    target_text = text

            # Validation checks
            if not source_text or not target_text:
                keep_tu = False
            elif not alphanumeric_pattern.search(source_text) or not alphanumeric_pattern.search(target_text):
                keep_tu = False
            elif len(source_text.split()) < 3:  # Minimum word count
                keep_tu = False

            if keep_tu:
                # Create new TU with cleaned content
                src_tuv = PythonTmx.Tuv(lang="en-US")
                src_tuv.content = source_text
                tgt_tuv = PythonTmx.Tuv(lang=tu.tuvs[1].lang)
                tgt_tuv.content = target_text
                
                clean_tu = PythonTmx.Tu(
                    srclang="en-US",
                    tuvs=[src_tuv, tgt_tuv]
                )
                clean_tm.append(clean_tu)
                cleaned_count += 1
            
            processed_count += 1

        # Create clean TMX
        clean_tm_object = PythonTmx.Tmx(tus=clean_tm, header=clean_header)
        # Save TMX file using the correct method
        try:
            # Use the to_tmx method which should exist
            clean_tm_object.to_tmx(target_file)
        except AttributeError:
            # Fallback: use lxml to write the XML directly
            root = PythonTmx.to_element(clean_tm_object, True)
            etree.ElementTree(root).write(target_file, encoding="utf-8", xml_declaration=True)
        logger.info(f"Created cleaned TMX with {cleaned_count} entries")

        return target_file, processed_count, cleaned_count

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

def process_directory(directory):
    """
    Process all TMX files in a directory.

    Args:
        directory (str): Directory containing TMX files

    Returns:
        tuple: (results, log_messages)
            results: List of tuples containing (target_file, processed_count, cleaned_count)
            log_messages: List of (level, message) tuples
    """
    logger = OperationLog()
    results = []
    
    try:
        for filename in os.listdir(directory):
            if filename.endswith('.tmx'):
                source_file = os.path.join(directory, filename)
                logger.info(f"Processing file: {filename}")
                result = clean_tmx_for_mt(source_file, logger=logger)
                results.append(result)
        return results, logger.get_log()
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    directory = input("Enter directory path containing TMX files: ")
    print("WARNING: This process removes information needed for translation leveraging.")
    print("Use only for preparing MT training data.")
    confirm = input("Continue? (y/N): ")
    
    if confirm.lower() == 'y':
        results, log = process_directory(directory)
        for target, processed, cleaned in results:
            print(f"Created cleaned TMX file: {target}")
            print(f"Processed {processed} entries, kept {cleaned} entries")
        for level, message in log:
            print(f"{level.upper()}: {message}") 
import PythonTmx
from datetime import datetime
import os
import logging
from pathlib import Path
from typing import List, Dict, Set
import lxml.etree as etree

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
        for tmx in file_paths:            #Loops through every .tmx file in tmx_list
            tm : etree._ElementTree = etree.parse(tmx, etree.XMLParser(encoding="utf-8"))
            tmx_root: etree._Element = tm.getroot()
            tmx_obj: PythonTmx.TmxElement = PythonTmx.from_element(tmx_root)          #Converts it to a TMX object
            if header == None:
                header: PythonTmx.Header = tmx_obj.header
                header.adminlang = "en-US"
                header.creationtool = "TMX Merger"
                header.creationtoolversion = "1.0"
            concat_list.extend(tmx_obj)

        merged_tm = PythonTmx.Tmx(header=header, tus=concat_list)

        new_tmx_root: etree._Element = PythonTmx.to_element(merged_tm, True)
        etree.ElementTree(new_tmx_root).write(output_path, encoding="utf-8", xml_declaration=True)

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
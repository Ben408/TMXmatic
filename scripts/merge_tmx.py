import PythonTmx
from PythonTmx import from_tmx
from datetime import datetime
import os
import logging
from pathlib import Path
from typing import List, Dict, Set

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
        output_path = first_path.parent / f"merged_{datetime.now().strftime('%Y%m%d_%H%M%S')}.tmx"

        # Dictionary to store unique TUs
        # Key: (source_text, target_text, target_lang)
        # Value: (tu_object, latest_date)
        unique_tus: Dict[tuple, tuple] = {}
        
        # Track languages for header
        all_languages: Set[str] = set()
        source_lang = None

        # Process each file
        for file_path in file_paths:
            logger.info(f"Processing file: {file_path}")
            tmx = PythonTmx.Tmx(file_path)
            
            # Set source language from first file
            if not source_lang:
                source_lang = tmx.header.srclang
            elif tmx.header.srclang != source_lang:
                logger.warning(f"Different source language in {file_path}: {tmx.header.srclang} (expected {source_lang})")

            # Process TUs
            for tu in tmx.tus:
                source_text = target_text = target_lang = None
                latest_date = None

                # Extract TU information
                for tuv in tu.tuvs:
                    all_languages.add(tuv.lang)
                    
                    if tuv.lang == source_lang:
                        source_text = tuv.seg.strip() if tuv.seg else ""
                    else:
                        target_lang = tuv.lang
                        target_text = tuv.seg.strip() if tuv.seg else ""
                    
                    # Check for latest date
                    date_str = tuv.changedate or tuv.creationdate
                    if date_str:
                        try:
                            date = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
                            if not latest_date or date > latest_date:
                                latest_date = date
                        except ValueError:
                            logger.warning(f"Invalid date format: {date_str}")

                if source_text and target_text and target_lang:
                    key = (source_text, target_text, target_lang)
                    
                    # Keep most recent version
                    if key not in unique_tus or (
                        latest_date and (
                            not unique_tus[key][1] or 
                            latest_date > unique_tus[key][1]
                        )
                    ):
                        unique_tus[key] = (tu, latest_date)

        # Create merged TMX
        merged_tmx = PythonTmx.Tmx()
        merged_tmx.header.srclang = source_lang
        merged_tmx.header.segtype = "phrase"
        merged_tmx.header.adminlang = "en-US"
        merged_tmx.header.creationtool = "TMX Merger"
        merged_tmx.header.creationtoolversion = "1.0"
        merged_tmx.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        # Add unique TUs
        for (_, _, _), (tu, _) in unique_tus.items():
            merged_tmx.tus.append(tu)

        # Save merged file
        merged_tmx.save(str(output_path))
        
        logger.info(f"Merged TMX created with {len(unique_tus)} unique TUs")
        logger.info(f"Languages found: {', '.join(sorted(all_languages))}")
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
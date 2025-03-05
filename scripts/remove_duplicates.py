import PythonTmx
from PythonTmx import from_tmx
import os
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict

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

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Create TMX files for clean and duplicate TUs
        clean_tmx = PythonTmx.Tmx()
        dups_tmx = PythonTmx.Tmx()
        
        # Copy header properties
        for tmx_file in [clean_tmx, dups_tmx]:
            tmx_file.header.srclang = tmx.header.srclang
            tmx_file.header.segtype = tmx.header.segtype
            tmx_file.header.adminlang = tmx.header.adminlang
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"
            tmx_file.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        # Group TUs by source and target content
        content_groups = defaultdict(list)
        source_lang = tmx.header.srclang

        for tu in tmx.tus:
            source_text = target_text = None
            
            # Extract source and target text
            for tuv in tu.tuvs:
                if tuv.lang == source_lang:
                    source_text = tuv.seg
                else:
                    target_text = tuv.seg
            
            if source_text and target_text:
                key = (source_text.strip(), target_text.strip())
                content_groups[key].append(tu)

        clean_count = dups_count = 0

        # Process each group of duplicates
        for group in content_groups.values():
            if len(group) == 1:
                clean_tmx.tus.append(group[0])
                clean_count += 1
                continue

            # Find most recent TU in the group
            latest_tu = None
            latest_date = None

            for tu in group:
                tu_date = None
                
                # Check TUVs for dates
                for tuv in tu.tuvs:
                    if tuv.changedate:
                        tu_date = tuv.changedate
                        break
                    elif tuv.creationdate:
                        tu_date = tuv.creationdate
                        break
                
                if tu_date:
                    if not latest_date or tu_date > latest_date:
                        latest_date = tu_date
                        latest_tu = tu

            # If no dates found, keep first TU
            if not latest_tu:
                latest_tu = group[0]

            # Add latest to clean, others to duplicates
            clean_tmx.tus.append(latest_tu)
            clean_count += 1
            
            for tu in group:
                if tu != latest_tu:
                    dups_tmx.tus.append(tu)
                    dups_count += 1

        # Save TMX files
        clean_tmx.save(str(clean_path))
        dups_tmx.save(str(dups_path))
        
        logger.info(f"Processed {clean_count + dups_count} TUs: {clean_count} kept, {dups_count} removed")
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
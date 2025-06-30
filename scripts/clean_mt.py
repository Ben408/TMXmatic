import PythonTmx
import os
import re
from datetime import datetime
import logging

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
        # Read the TMX file
        logger.info(f"Reading TMX file: {source_file}")
        tm = from_tmx(source_file)
        
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
                text = ''.join(str(seg) for seg in tuv.segment)
                
                # Remove tags
                text = tag_pattern.sub(' ', text)
                # Normalize whitespace
                text = whitespace_pattern.sub(' ', text).strip()
                
                if tuv.xmllang.lower() == "en-us":
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
                src_tuv = PythonTmx.Tuv(xmllang="en-US")
                src_tuv.segment.text = source_text
                tgt_tuv = PythonTmx.Tuv(xmllang=tu.tuvs[1].xmllang)
                tgt_tuv.segment.text = target_text
                
                clean_tu = PythonTmx.Tu(
                    srclang="en-US",
                    tuvs=[src_tuv, tgt_tuv]
                )
                clean_tm.append(clean_tu)
                cleaned_count += 1
            
            processed_count += 1

        # Create clean TMX
        clean_tm_object = PythonTmx.Tmx(tus=clean_tm)
        # Create minimal header
        clean_tm_object.header = PythonTmx.Header(
            creationdate=datetime.now(),
            srclang="en-US"
        )
        clean_tm_object.to_tmx(target_file)
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
import xml.etree.ElementTree as ET
import csv
from collections import defaultdict
from datetime import datetime
import os

class OperationLog:
    def __init__(self):
        self.messages = []
    
    def info(self, msg):
        self.messages.append(("info", msg))
    
    def error(self, msg):
        self.messages.append(("error", msg))
    
    def get_log(self):
        return self.messages

def parse_tmx(file_path, logger):
    """
    Parse TMX file and extract segments with their dates and filenames.
    
    Args:
        file_path (str): Path to TMX file
        logger (OperationLog): Logger for tracking progress and errors
    
    Returns:
        dict: Dictionary mapping segment keys to list of entries
    """
    segment_key_dict = defaultdict(list)
    
    try:
        logger.info(f"Parsing TMX file: {file_path}")
        tree = ET.parse(file_path)
        root = tree.getroot()
        
        # Count total TUs for progress tracking
        tus = list(root.iter('tu'))
        total_tus = len(tus)
        logger.info(f"Found {total_tus} translation units")

        # Iterate over all <tu> elements
        for i, tu in enumerate(tus):
            if i % 100 == 0:  # Progress update every 100 items
                logger.info(f"Progress: {(i/total_tus)*100:.1f}% ({i}/{total_tus})")

            segment_key = None
            creation_date = None
            seg_content = {}
            filename = None

            for tuv in tu.findall('tuv'):
                # Extract properties
                for prop in tuv.findall('prop'):
                    if prop.get('type') == "x-context_seg_key":
                        segment_key = prop.text
                    if prop.get('type') == "filename":
                        filename = prop.text

                # Store the creationdate and segment content
                creation_date = tuv.get('creationdate')
                lang = tuv.get('{http://www.w3.org/XML/1998/namespace}lang')
                seg = tuv.find('seg')
                seg_content[lang] = seg.text if seg is not None else None
            
            if segment_key and creation_date:
                segment_key_dict[segment_key].append({
                    "creation_date": creation_date,
                    "seg_content": seg_content,
                    "filename": filename
                })

        return segment_key_dict

    except ET.ParseError as e:
        logger.error(f"XML parsing error: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Error parsing TMX: {str(e)}")
        raise

def find_duplicates(segment_key_dict, comparison_date, logger):
    """
    Find segments that exist both before and after the comparison date.
    
    Args:
        segment_key_dict (dict): Dictionary of segments from parse_tmx
        comparison_date (str): Date string in format 'YYYYMMDDTHHmmssZ'
        logger (OperationLog): Logger for tracking progress and errors
    
    Returns:
        list: List of tuples (key, before_entries, after_entries)
    """
    try:
        logger.info(f"Finding duplicates around date: {comparison_date}")
        comparison_date = datetime.strptime(comparison_date, '%Y%m%dT%H%M%SZ')
        duplicates = []
        
        total_keys = len(segment_key_dict)
        for i, (key, tus) in enumerate(segment_key_dict.items()):
            if i % 100 == 0:  # Progress update every 100 items
                logger.info(f"Progress: {(i/total_keys)*100:.1f}% ({i}/{total_keys})")

            dates_before = []
            dates_after = []
            
            for tu in tus:
                try:
                    tu_date = datetime.strptime(tu['creation_date'], '%Y%m%dT%H%M%SZ')
                    if tu_date < comparison_date:
                        dates_before.append(tu)
                    else:
                        dates_after.append(tu)
                except ValueError:
                    logger.error(f"Invalid date format: {tu['creation_date']}")
                    continue
            
            if dates_before and dates_after:
                duplicates.append((key, dates_before, dates_after))
        
        logger.info(f"Found {len(duplicates)} segments with duplicates")
        return duplicates

    except Exception as e:
        logger.error(f"Error finding duplicates: {str(e)}")
        raise

def write_to_csv(duplicates, output_file, logger):
    """
    Write duplicate entries to CSV file.
    
    Args:
        duplicates (list): List of duplicates from find_duplicates
        output_file (str): Path to output CSV file
        logger (OperationLog): Logger for tracking progress and errors
    """
    try:
        logger.info(f"Writing results to: {output_file}")
        with open(output_file, 'w', newline='', encoding='utf-8-sig') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Segment Key', 'Date', 'Language', 'Content', 'Filename'])
            
            total_dups = len(duplicates)
            for i, (key, before, after) in enumerate(duplicates):
                if i % 100 == 0:  # Progress update every 100 items
                    logger.info(f"Progress: {(i/total_dups)*100:.1f}% ({i}/{total_dups})")

                for tu in before + after:
                    for lang, content in tu['seg_content'].items():
                        writer.writerow([
                            key,
                            tu['creation_date'],
                            lang,
                            content,
                            tu['filename']
                        ])
        
        logger.info("CSV file created successfully")

    except Exception as e:
        logger.error(f"Error writing CSV: {str(e)}")
        raise

def process_file(tmx_file, comparison_date, output_csv=None, logger=None):
    """
    Process a TMX file to find duplicates around a comparison date.
    
    Args:
        tmx_file (str): Path to TMX file
        comparison_date (str): Date string in format 'YYYYMMDDTHHMMSSZ'
        output_csv (str, optional): Path to output CSV file
        logger (OperationLog, optional): Logger for tracking progress and errors
    
    Returns:
        str: Path to created CSV file
    """
    if logger is None:
        logger = OperationLog()

    if output_csv is None:
        output_csv = f'duplicates_{os.path.splitext(os.path.basename(tmx_file))[0]}.csv'

    try:
        # Parse TMX and find duplicates
        segment_dict = parse_tmx(tmx_file, logger)
        duplicates = find_duplicates(segment_dict, comparison_date, logger)
        
        if duplicates:
            write_to_csv(duplicates, output_csv, logger)
            logger.info(f"Found and wrote {len(duplicates)} duplicate segments")
        else:
            logger.info("No duplicates found")
        
        return output_csv

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    tmx_file = input("Enter path to TMX file: ")
    comparison_date = input("Enter comparison date (YYYYMMDDTHHMMSSZ): ")
    
    logger = OperationLog()
    try:
        output_file = process_file(tmx_file, comparison_date, logger=logger)
        print(f"\nResults written to: {output_file}")
        for level, message in logger.get_log():
            print(f"{level.upper()}: {message}")
    except Exception as e:
        print(f"ERROR: {str(e)}")
        exit(1) 
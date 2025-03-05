import PythonTmx
from datetime import datetime
from pathlib import Path
import csv
import logging

logger = logging.getLogger(__name__)

def extract_translations(file_path: str) -> tuple[str, int]:
    """
    Extract all translations to CSV format.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to CSV file, Total translations extracted)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"translations_{input_path.stem}.csv"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        source_lang = tmx.header.srclang
        
        # Get all unique target languages
        target_langs = set()
        for tu in tmx.tus:
            for tuv in tu.tuvs:
                if tuv.lang != source_lang:
                    target_langs.add(tuv.lang)
        
        # Sort target languages for consistent output
        target_langs = sorted(target_langs)
        
        # Prepare CSV headers
        headers = ['Source Text', 'Source Creation Date', 'Source Change Date']
        for lang in target_langs:
            headers.extend([
                f'Target ({lang})',
                f'Creation Date ({lang})',
                f'Change Date ({lang})'
            ])

        total_tus = 0
        
        # Write translations to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(headers)
            
            for tu in tmx.tus:
                total_tus += 1
                row_data = []
                
                # Get source information
                source_text = source_creation = source_change = ''
                for tuv in tu.tuvs:
                    if tuv.lang == source_lang:
                        source_text = tuv.seg if tuv.seg else ''
                        source_creation = format_date(tuv.creationdate)
                        source_change = format_date(tuv.changedate)
                        break
                
                row_data.extend([source_text, source_creation, source_change])
                
                # Get target information for each language
                for lang in target_langs:
                    target_text = target_creation = target_change = ''
                    for tuv in tu.tuvs:
                        if tuv.lang == lang:
                            target_text = tuv.seg if tuv.seg else ''
                            target_creation = format_date(tuv.creationdate)
                            target_change = format_date(tuv.changedate)
                            break
                    row_data.extend([target_text, target_creation, target_change])
                
                writer.writerow(row_data)
        
        logger.info(f"Extracted {total_tus} translations")
        return str(output_path), total_tus

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

def format_date(date_str: str) -> str:
    """
    Format TMX date string to YYYY-MM-DD format.
    Returns empty string for None or invalid dates.
    """
    if not date_str:
        return ''
    
    try:
        date_obj = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
        return date_obj.strftime("%Y-%m-%d")
    except ValueError:
        logger.warning(f"Invalid date format: {date_str}")
        return ''

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        output_file, count = extract_translations(file_path)
        print(f"Extracted {count} translations")
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
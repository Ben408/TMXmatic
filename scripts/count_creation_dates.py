import PythonTmx
from datetime import datetime
from pathlib import Path
import csv
import logging
from collections import Counter

logger = logging.getLogger(__name__)

def count_creation_dates(file_path: str) -> tuple[str, int]:
    """
    Count TUs by creation date.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to CSV report, Total TUs counted)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"creation_dates_{input_path.stem}.csv"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Count creation dates
        date_counter = Counter()
        total_tus = 0
        
        for tu in tmx.tus:
            total_tus += 1
            creation_date = None
            
            # Check TUVs for creation date
            for tuv in tu.tuvs:
                if tuv.creationdate:
                    try:
                        # Convert to datetime for consistent formatting
                        date_obj = datetime.strptime(tuv.creationdate, "%Y%m%dT%H%M%SZ")
                        creation_date = date_obj.strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        logger.warning(f"Invalid date format: {tuv.creationdate}")
                        continue
            
            if creation_date:
                date_counter[creation_date] += 1
            else:
                date_counter['No Date'] += 1

        # Write results to CSV
        with open(output_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Date', 'Count', 'Percentage'])
            
            # Sort by date (with 'No Date' at the end)
            sorted_dates = sorted(
                [date for date in date_counter.keys() if date != 'No Date']
            )
            if 'No Date' in date_counter:
                sorted_dates.append('No Date')
            
            # Write counts and percentages
            for date in sorted_dates:
                count = date_counter[date]
                percentage = (count / total_tus) * 100
                writer.writerow([date, count, f"{percentage:.2f}%"])
            
            # Write total
            writer.writerow(['Total', total_tus, '100.00%'])
        
        logger.info(f"Analyzed {total_tus} TUs")
        return str(output_path), total_tus

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        output_file, count = count_creation_dates(file_path)
        print(f"Analyzed {count} TUs")
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
import PythonTmx
from datetime import datetime
from pathlib import Path
import csv
import logging
from collections import Counter

logger = logging.getLogger(__name__)

def count_last_usage_dates(file_path: str) -> tuple[str, int]:
    """
    Count TUs by last usage date (changedate or creationdate).
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to CSV report, Total TUs counted)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output path
        input_path = Path(file_path)
        output_path = input_path.parent / f"last_usage_{input_path.stem}.csv"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Count last usage dates
        date_counter = Counter()
        total_tus = 0
        
        for tu in tmx.tus:
            total_tus += 1
            latest_date = None
            
            # Check TUVs for dates
            for tuv in tu.tuvs:
                # Try changedate first, then creationdate
                date_str = tuv.changedate or tuv.creationdate
                if date_str:
                    try:
                        # Convert to datetime for comparison
                        date_obj = datetime.strptime(date_str, "%Y%m%dT%H%M%SZ")
                        if not latest_date or date_obj > latest_date:
                            latest_date = date_obj
                    except ValueError:
                        logger.warning(f"Invalid date format: {date_str}")
                        continue
            
            if latest_date:
                # Format date as YYYY-MM-DD for counter
                date_key = latest_date.strftime("%Y-%m-%d")
                date_counter[date_key] += 1
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
        output_file, count = count_last_usage_dates(file_path)
        print(f"Analyzed {count} TUs")
        print(f"Results written to: {output_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
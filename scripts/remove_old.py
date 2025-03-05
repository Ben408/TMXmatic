import PythonTmx
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def remove_old_tus(file_path: str, cutoff_date: datetime) -> tuple[str, str]:
    """
    Remove TUs older than the cutoff date.
    
    Args:
        file_path: Path to TMX file
        cutoff_date: Date to compare against
    
    Returns:
        tuple: (Path to clean TMX, Path to removed TMX)
    """
    logger.info(f"Processing file: {file_path} with cutoff date: {cutoff_date}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        removed_path = output_dir / f"removed_{input_path.name}"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Create TMX files for clean and removed TUs
        clean_tmx = PythonTmx.Tmx()
        removed_tmx = PythonTmx.Tmx()
        
        # Copy header properties
        for tmx_file in [clean_tmx, removed_tmx]:
            tmx_file.header.srclang = tmx.header.srclang
            tmx_file.header.segtype = tmx.header.segtype
            tmx_file.header.adminlang = tmx.header.adminlang
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"
            tmx_file.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        cutoff_str = cutoff_date.strftime("%Y%m%dT%H%M%SZ")
        clean_count = removed_count = 0

        # Process TUs
        for tu in tmx.tus:
            is_old = True
            
            for tuv in tu.tuvs:
                if tuv.creationdate and tuv.creationdate > cutoff_str:
                    is_old = False
                    break
                if tuv.changedate and tuv.changedate > cutoff_str:
                    is_old = False
                    break
            
            if is_old:
                removed_tmx.tus.append(tu)
                removed_count += 1
            else:
                clean_tmx.tus.append(tu)
                clean_count += 1

        # Save TMX files
        clean_tmx.save(str(clean_path))
        removed_tmx.save(str(removed_path))
        
        logger.info(f"Processed {clean_count + removed_count} TUs: {clean_count} kept, {removed_count} removed")
        return str(clean_path), str(removed_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    date_str = input("Enter cutoff date (YYYY-MM-DD): ")
    try:
        cutoff_date = datetime.strptime(date_str, "%Y-%m-%d")
        clean_file, removed_file = remove_old_tus(file_path, cutoff_date)
        print(f"Created clean file: {clean_file}")
        print(f"Created removed file: {removed_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
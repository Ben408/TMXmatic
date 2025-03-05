import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

def extract_non_true_duplicates(file_path: str) -> tuple[str, str]:
    """
    Extract non-true duplicates (same source, different target).
    Keeps one version in clean file, moves others to NTD file.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to clean TMX, Path to NTDs TMX)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        ntd_path = output_dir / f"ntd_{input_path.name}"

        # Load TMX file
        tmx = PythonTmx.Tmx(str(input_path))
        
        # Create TMX files for clean and NTD TUs
        clean_tmx = PythonTmx.Tmx()
        ntd_tmx = PythonTmx.Tmx()
        
        # Copy header properties
        for tmx_file in [clean_tmx, ntd_tmx]:
            tmx_file.header.srclang = tmx.header.srclang
            tmx_file.header.segtype = tmx.header.segtype
            tmx_file.header.adminlang = tmx.header.adminlang
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"
            tmx_file.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")

        # Group TUs by source content
        source_groups = defaultdict(list)
        source_lang = tmx.header.srclang

        for tu in tmx.tus:
            source_text = None
            target_text = None
            
            # Extract source and target text
            for tuv in tu.tuvs:
                if tuv.lang == source_lang:
                    source_text = tuv.seg.strip() if tuv.seg else ""
                else:
                    target_text = tuv.seg.strip() if tuv.seg else ""
            
            if source_text and target_text:  # Only process if both exist
                source_groups[source_text].append((target_text, tu))

        clean_count = ntd_count = 0

        # Process each group of potential NTDs
        for source_text, target_tus in source_groups.items():
            if len(target_tus) == 1:
                # Single translation, add to clean
                clean_tmx.tus.append(target_tus[0][1])
                clean_count += 1
                continue

            # Check for different translations
            translations = {target for target, _ in target_tus}
            
            if len(translations) == 1:
                # All translations identical, keep most recent
                latest_tu = None
                latest_date = None

                for _, tu in target_tus:
                    tu_date = None
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
                    latest_tu = target_tus[0][1]

                clean_tmx.tus.append(latest_tu)
                clean_count += 1
                
                # Add others to NTDs
                for _, tu in target_tus:
                    if tu != latest_tu:
                        ntd_tmx.tus.append(tu)
                        ntd_count += 1
            else:
                # Different translations exist, move all to NTDs
                for _, tu in target_tus:
                    ntd_tmx.tus.append(tu)
                    ntd_count += 1

        # Save TMX files
        clean_tmx.save(str(clean_path))
        ntd_tmx.save(str(ntd_path))
        
        logger.info(f"Processed {clean_count + ntd_count} TUs: {clean_count} kept, {ntd_count} extracted as NTDs")
        return str(clean_path), str(ntd_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        clean_file, ntd_file = extract_non_true_duplicates(file_path)
        print(f"Created clean file: {clean_file}")
        print(f"Created NTDs file: {ntd_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
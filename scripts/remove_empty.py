import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
import lxml.etree as etree

logger = logging.getLogger(__name__)

def empty_targets(file_path: str) -> tuple[str, str]:
    """
    Remove TUs with empty target segments.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to clean TMX, Path to empty TMX)
    """
    logger.info(f"Processing file: {file_path}")
    
    try:
        # Create output paths
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        empty_path = output_dir / f"empty_{input_path.name}"

        # Load TMX file
        tm : etree._ElementTree = etree.parse(str(input_path), etree.XMLParser(encoding="utf-8"))
        tmx_root: etree._Element = tm.getroot()
        tmx: PythonTmx.TmxElement = PythonTmx.from_element(tmx_root)


        # Create TMX files for clean and empty TUs
        clean_tmx = PythonTmx.Tmx(header = tmx.header)
        empty_tmx = PythonTmx.Tmx(header = tmx.header)
        
        # Copy header properties
        for tmx_file in [clean_tmx, empty_tmx]:
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"

        clean_count = empty_count = 0

        # Process TUs
        for tu in tmx.tus:
            has_empty_target = False
            source_lang = tmx.header.srclang
            
            # Get source text for comparison
            source_text = None
            for tuv in tu.tuvs:
                if tuv.lang == source_lang:
                    source_text = tuv.content
                    break
            
            if source_text:
                # Check target segments
                for tuv in tu.tuvs:
                    if tuv.lang != source_lang:
                        # Check if target is empty or same as source
                        if not tuv.content or str(tuv.content).isspace() or tuv.content == source_text:
                            has_empty_target = True
                            break
            
            if has_empty_target:
                empty_tmx.tus.append(tu)
                empty_count += 1
            else:
                clean_tmx.tus.append(tu)
                clean_count += 1

        # Save TMX files
        
        #TODO: revisar el save
        new_tmx_root: etree._Element = PythonTmx.to_element(clean_tmx, True)
        etree.ElementTree(new_tmx_root).write(clean_path, encoding="utf-8", xml_declaration=True)


        new_tmx_root2: etree._Element = PythonTmx.to_element(empty_tmx, True)
        etree.ElementTree(new_tmx_root2).write(empty_path, encoding="utf-8", xml_declaration=True)

        
        logger.info(f"Processed {clean_count + empty_count} TUs: {clean_count} kept, {empty_count} removed")
        return str(clean_path), str(empty_path)

    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    try:
        clean_file, empty_file = empty_targets(file_path)
        print(f"Created clean file: {clean_file}")
        print(f"Created empty file: {empty_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
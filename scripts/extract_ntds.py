import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict
import lxml.etree as etree


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
        dups_path = output_dir / f"duplicates_{input_path.name}"

        # Load TMX file
        tm : etree._ElementTree = etree.parse(input_path, etree.XMLParser(encoding="utf-8"))
        tmx_root: etree._Element = tm.getroot()
        tmx: PythonTmx.TmxElement = PythonTmx.from_element(tmx_root)
        
        

        # Create TMX files for clean and duplicate TUs
        clean_tmx = PythonTmx.Tmx(header = tmx.header)
        ntds_tmx = PythonTmx.Tmx(header = tmx.header)
        
        
        # Copy header properties
        for tmx_file in [clean_tmx, ntds_tmx]:
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"

        clean_segments = []
        ntds_segments = []

        duplicates = {}                                 #A dictionary of all non Non-True-Duplicates(this 
                                                        #includes non repeated segments, as well as True-Duplicates)
        ntds = {}                                       #A dictionary for all Non-True-Duplicates

        for tu in tmx:
            source = ""
            target = ""

            for tuv in tu.tuvs:
                if tuv.lang.lower() == "en-us":
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        source = source + str(seg)     
                else:
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        target = target + str(seg)

            if duplicates.get(source):                  #Evaluates if the source appears as a key in the duplicates dictionary

                if target not in duplicates[source]:    #If the target is not present in the duplicates dictionary entry for the source, but is a key in  
                    duplicates[source].append(target)   #the duplicates dictionary, adds the target in the list of values source (as key) holds in duplicates,
                    ntds[source] = duplicates[source]   #and replaces the entry of source in the ntds dictionary with the same list as duplicates
            else:
                duplicates[source] = []                 #If this is the first appearance of this source, adds the source as key and a new list with the target
                duplicates[source].append(target)       #as value

        for tu in tmx:
            source = ""
            target = ""

            for tuv in tu.tuvs:
                if tuv.lang.lower() == "en-us":
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        source = source + str(seg)
                else:
                    for seg in tuv.content:             #Assuming the source has tags, this part concatenates each part into a new string
                        target = target + str(seg)

            if ntds.get(source):                        #Checks if the source appears as key in the ntds dictionary
                if target in ntds[source]:              #Checks if the target is the value for the source as key, if it is,
                    ntds_segments.append(tu)            #removes the target from the list of ntds of that source, and adds
                    ntds[source].remove(target)         #the TU to the ntds_segments list
                else:
                    clean_segments.append(tu)           #If the target is not in the source's list of ntds, or if the source
            else:                                       #is not present in the ntds dictionary, then the TU is added to the
                clean_segments.append(tu)

        clean_tmx.tus = clean_segments
        new_tmx_root: etree._Element = PythonTmx.to_element(clean_tmx, True)
        etree.ElementTree(new_tmx_root).write(clean_path, encoding="utf-8", xml_declaration=True)

        ntds_tmx.tus = ntds_segments
        new_tmx_root2: etree._Element = PythonTmx.to_element(ntds_tmx, True)
        etree.ElementTree(new_tmx_root2).write(dups_path, encoding="utf-8", xml_declaration=True)
        print("llego aca")
        logger.info(f"Processed {len(clean_segments)+ len(ntds_segments)} TUs: {len(clean_segments)} kept, {len(ntds_segments)} removed")
        
        
        return str(clean_path), str(dups_path)
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
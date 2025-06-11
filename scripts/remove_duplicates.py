import PythonTmx
import os
from datetime import datetime
from pathlib import Path
import logging
from collections import defaultdict
import lxml.etree as etree

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
        tm : etree._ElementTree = etree.parse(input_path, etree.XMLParser(encoding="utf-8"))
        tmx_root: etree._Element = tm.getroot()
        tmx: PythonTmx.TmxElement = PythonTmx.from_element(tmx_root)
        
        

        # Create TMX files for clean and duplicate TUs
        clean_tmx = PythonTmx.Tmx(header = tmx.header)
        dups_tmx = PythonTmx.Tmx(header = tmx.header)
        
        
        # Copy header properties
        for tmx_file in [clean_tmx, dups_tmx]:
            tmx_file.header.creationtool = "TMX Cleaner"
            tmx_file.header.creationtoolversion = "1.0"

        


        clean_tm = []
        duplicates = []

        newer_values = {}                                       #A dictionary to store the latest instance of every entry
        source = ""
        target = ""
        date = ""

        for tu in tmx:                                      #Loop through every TU in the TMX
            for tuv in tu.tuvs:                                 #Inside every TU, loop through every TUV (source and target TUVs)
                if tuv.lang.lower() == "en-us":              #Checks for TUV language, and if it is english, saves the source in the variable "source"
                    for seg in tuv.content:
                        source = source + str(seg)              #Assuming the source has tags, this part concatenates each part into a new string

                else:
                    for seg in tuv.content:                     #Assuming the target has tags, this part concatenates each part into a new string
                        target = target + str(seg)
                    if tuv.changedate:
                        date = tuv.changedate
                    else:
                        date = datetime(year=2000, month=1,day=1)
                        tuv.changedate = date.strftime("%Y%m%dT%H%M%SZ")

            if newer_values.get(source+target):                 #Evaluates if the dictionary contains an entry with the same key (source+target)
                if newer_values.get(source+target) < date:      #If that key has a value (date) older than the current TU's, the value is updated with the current TU's date
                    newer_values[source+target] = date
            else:
                newer_values[source+target] = date              #If the dictionary does not contain any key as (source+target), creates an
                                                                #entry with (source+target) as key and date as value
            source = ""                                          
            target = ""

        for tu in tmx:                                      #Loop a second time through every TU in the TMX
            for tuv in tu.tuvs:                                 #Repeats the same assignment of source, target and date as before
                if tuv.lang.lower() == "en-us":
                    for seg in tuv.content:
                        source = source + str(seg)
                else:
                    for seg in tuv.content:
                        target = target + str(seg)
                    date = tuv.changedate

            if newer_values.get(source+target) == date:         #Attempts to match the current TU's date with the source+target dictionary entry. If
                                                                #the value matches, the TU is added to the clean_tm list. Otherwise, is considered as
                                                                #an older TU and added to the duplicates list.
                clean_tm.append(tu)
                newer_values.pop(source+target)
            else:
                duplicates.append(tu)

            source = ""
            target = ""

        ## Save TMX files
        clean_tmx.tus = clean_tm
        new_tmx_root: etree._Element = PythonTmx.to_element(clean_tmx, True)
        etree.ElementTree(new_tmx_root).write(clean_path, encoding="utf-8", xml_declaration=True)
        
        dups_tmx.tus = duplicates
        new_tmx_root2: etree._Element = PythonTmx.to_element(dups_tmx, True)
        etree.ElementTree(new_tmx_root2).write(dups_path, encoding="utf-8", xml_declaration=True)
        
        logger.info(f"Processed {len(clean_tm)+ len(duplicates)} TUs: {len(clean_tm)} kept, {len(duplicates)} removed")
        
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
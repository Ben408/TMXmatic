import PythonTmx
from datetime import datetime
import os
import openpyxl
import openpyxl.utils
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Update language codes to match MT Glossary Software Main.xlsx exactly
LANGUAGE_CODES = {
    "English (US)": "en-US",
    "Arabic": "ar-SA",
    "Bulgarian": "bg-BG",
    "Chinese (Simplified)": "zh-CN",
    "Chinese (Traditional)": "zh-TW",
    "Croatian": "hr-HR",
    "Czech": "cs-CZ",
    "Danish": "da-DK",
    "Dutch": "nl-NL",
    "Estonian": "et-EE",
    "Finnish": "fi-FI",
    "French": "fr-FR",
    "German": "de-DE",
    "Greek": "el-GR",
    "Hebrew": "he-IL",
    "Hungarian": "hu-HU",
    "Indonesian": "id-ID",
    "Italian": "it-IT",
    "Japanese": "ja-JP",
    "Korean": "ko-KR",
    "Latvian": "lv-LV",
    "Lithuanian": "lt-LT",
    "Malay": "ms-MY",
    "Norwegian": "nb-NO",
    "Polish": "pl-PL",
    "Portuguese (Brazil)": "pt-BR",
    "Romanian": "ro-RO",
    "Russian": "ru-RU",
    "Serbian": "sr-Cyrl-RS",
    "Slovak": "sk-SK",
    "Slovenian": "sl-SI",
    "Spanish": "es-ES",
    "Swedish": "sv-SE",
    "Thai": "th-TH",
    "Turkish": "tr-TR",
    "Ukrainian": "uk-UA",
    "Vietnamese": "vi-VN"
}

class OperationLog:
    def __init__(self):
        self.messages = []
    
    def info(self, msg):
        self.messages.append(("info", msg))
    
    def error(self, msg):
        self.messages.append(("error", msg))
    
    def get_log(self):
        return self.messages

def process_excel_file(file_path: str, output_dir: Path) -> tuple[list[str], list[tuple[str, str]]]:
    """
    Process TermWeb Excel file and convert to TMX.
    
    Args:
        file_path: Path to Excel file
        output_dir: Directory for output files
    
    Returns:
        tuple: (List of created TMX files, List of (level, message) log entries)
    """
    logger.info(f"Processing Excel file: {file_path}")
    logs = []
    created_files = []
    
    try:
        # Load workbook with data_only=True to get values instead of formulas
        wb = openpyxl.load_workbook(file_path, data_only=True)
        
        # Process each worksheet
        for ws in wb.worksheets:
            logger.info(f"Processing worksheet: {ws.title}")
            
            # Create TMX for this worksheet
            tmx = PythonTmx.Tmx()
            tmx.header.srclang = "en-US"  # TermWeb always uses English (US) as source
            tmx.header.segtype = "phrase"
            tmx.header.adminlang = "en-US"
            tmx.header.creationtool = "TermWeb Converter"
            tmx.header.creationtoolversion = "1.0"
            tmx.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")
            
            # Find header row and language columns
            header_row = None
            lang_cols = {}
            date_cols = {}
            
            for row in ws.iter_rows(min_row=1, max_row=10):  # Check first 10 rows for headers
                for cell in row:
                    if cell.value in LANGUAGE_CODES:
                        header_row = cell.row
                        lang_cols[cell.column] = LANGUAGE_CODES[cell.value]
                    elif cell.value == "Creation Date":
                        date_cols[cell.column] = "creation"
                    elif cell.value == "Last Modified":
                        date_cols[cell.column] = "change"
            
            if not header_row:
                logs.append(("warning", f"No language columns found in worksheet: {ws.title}"))
                continue
            
            # Process content rows
            row_count = 0
            skipped_count = 0
            
            for row in ws.iter_rows(min_row=header_row + 1):
                row_count += 1
                source_text = None
                target_texts = {}
                dates = {}
                
                # Get text and dates for each language
                for col in lang_cols:
                    text = row[openpyxl.utils.column_index_from_string(col) - 1].value
                    if text:
                        text = str(text).strip()
                        if lang_cols[col] == "en-US":
                            source_text = text
                        else:
                            target_texts[lang_cols[col]] = text
                
                # Get dates if available
                for col in date_cols:
                    date_cell = row[openpyxl.utils.column_index_from_string(col) - 1]
                    if date_cell.value:
                        try:
                            if isinstance(date_cell.value, datetime):
                                date_str = date_cell.value.strftime("%Y%m%dT%H%M%SZ")
                            else:
                                date_str = datetime.strptime(str(date_cell.value), "%Y-%m-%d").strftime("%Y%m%dT%H%M%SZ")
                            dates[date_cols[col]] = date_str
                        except ValueError:
                            logger.warning(f"Invalid date format in row {row_count}: {date_cell.value}")
                
                # Create TU if we have source and at least one target
                if source_text and target_texts:
                    tu = PythonTmx.Tu()
                    
                    # Add source TUV
                    source_tuv = PythonTmx.Tuv(lang="en-US")
                    source_tuv.seg = source_text
                    if "creation" in dates:
                        source_tuv.creationdate = dates["creation"]
                    if "change" in dates:
                        source_tuv.changedate = dates["change"]
                    tu.tuvs.append(source_tuv)
                    
                    # Add target TUVs
                    for lang, text in target_texts.items():
                        target_tuv = PythonTmx.Tuv(lang=lang)
                        target_tuv.seg = text
                        if "creation" in dates:
                            target_tuv.creationdate = dates["creation"]
                        if "change" in dates:
                            target_tuv.changedate = dates["change"]
                        tu.tuvs.append(target_tuv)
                    
                    tmx.tus.append(tu)
                else:
                    skipped_count += 1
            
            if tmx.tus:
                # Save TMX file
                output_file = output_dir / f"{ws.title}.tmx"
                tmx.save(str(output_file))
                created_files.append(str(output_file))
                logs.append(("info", f"Created TMX for {ws.title} with {len(tmx.tus)} TUs"))
            
            if skipped_count:
                logs.append(("warning", f"Skipped {skipped_count} rows in {ws.title} (no source or targets)"))
        
        return created_files, logs

    except Exception as e:
        logger.error(f"Error processing Excel file: {e}", exc_info=True)
        raise

def process_directory(directory):
    """
    Process all TermWeb Excel files in a directory.
    
    Args:
        directory (str): Directory containing TermWeb Excel files
    
    Returns:
        tuple: (results, log_messages)
            results: List of created TMX file paths
            log_messages: List of (level, message) tuples
    """
    logger = OperationLog()
    results = []
    
    try:
        for filename in os.listdir(directory):
            if filename.endswith(('.xlsx', '.xls')):
                source_file = os.path.join(directory, filename)
                logger.info(f"Processing file: {filename}")
                result = process_excel_file(source_file, Path(directory))
                results.extend(result[0])
        return results, logger.get_log()
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    directory = input("Enter directory path containing TermWeb Excel files: ")
    results, log = process_directory(directory)
    for tmx_file in results:
        print(f"Created TMX file: {tmx_file}")
    for level, message in log:
        print(f"{level.upper()}: {message}") 
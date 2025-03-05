import PythonTmx
from datetime import datetime
import csv
from pathlib import Path
import logging
from typing import Optional, TextIO

logger = logging.getLogger(__name__)

# Language codes from original VATV files
LANGUAGE_CODES = {
    "Arabic_VATV": "ar-SA",
    "Bulgarian (Bulgaria)_VATV": "bg-BG",
    "Croatian (Croatia)_VATV": "hr-HR",
    "Czech (Czechia)_VATV": "cs-CZ",
    "Danish (Denmark)_VATV": "da-DK",
    "Dutch (Netherlands)_VATV": "nl-NL",
    "Estonian (Estonia)_VATV": "et-EE",
    "Finnish (Finland)_VATV": "fi-FI",
    "French (Canada)_VATV": "fr-CA",
    "French (France)_VATV": "fr-FR",
    "German (Germany)_VATV": "de-DE",
    "Greek (Greece)_VATV": "el-GR",
    "Hebrew (Israel)_VATV": "he-IL",
    "Hungarian (Hungary)_VATV": "hu-HU",
    "Indonesian (Indonesia)⛑_VATV": "id-ID",
    "Italian (Italy)_VATV": "it-IT",
    "Japanese (Japan)_VATV": "ja-JP",
    "Korean (Korea)_VATV": "ko-KR",
    "Latvian (Latvia)_VATV": "lv-LV",
    "Lithuanian (Lithuania)_VATV": "lt-LT",
    "Malay (Malaysia)_VATV": "ms-MY",
    "Mongolian (Mongolia)_VATV": "mn-MN",
    "Norwegian (Norway)_VATV": "nb-NO",
    "Polish (Poland)_VATV": "pl-PL",
    "Portuguese (Brazil)_VATV": "pt-BR",
    "Romanian (Romania)_VATV": "ro-RO",
    "Russian (Russia)_VATV": "ru-RU",
    "Serbian (Serbia)_VATV": "sr-Cyrl-RS",
    "Simplified Chinese_VATV": "zh-CN",
    "Slovak (Slovakia)_VATV": "sk-SK",
    "Slovenian (Slovenia)_VATV": "sl-SI",
    "Spanish (Latin America)_VATV": "es-419",
    "Spanish (Neutral)_VATV": "es-ES",
    "Swedish (Sweden)_VATV": "sv-SE",
    "Thai (Thailand)_VATV": "th-TH",
    "Traditional Chinese (Hong Kong)_VATV": "zh-HK",
    "Traditional Chinese_VATV": "zh-TW",
    "Turkish (Türkiye)_VATV": "tr-TR",
    "Ukrainian (Ukraine)_VATV": "uk-UA",
    "Vietnamese (Vietnam)_VATV": "vi-VN"
}

def open_csv_with_encoding(file_path: str) -> tuple[TextIO, str]:
    """
    Try to open CSV file with different encodings.
    
    Args:
        file_path: Path to CSV file
    
    Returns:
        tuple: (File object, encoding used)
    
    Raises:
        ValueError: If file cannot be opened with any supported encoding
    """
    encodings = ['utf-8', 'utf-8-sig', 'cp1252', 'utf-16']
    
    for encoding in encodings:
        try:
            file = open(file_path, 'r', encoding=encoding)
            # Try to read first line to verify encoding
            file.readline()
            file.seek(0)
            return file, encoding
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"Error opening file with {encoding}: {e}")
            continue
    
    raise ValueError(f"Could not open file with any supported encoding: {encodings}")

def validate_csv_headers(headers: list) -> bool:
    """
    Validate that required columns exist in CSV.
    
    Args:
        headers: List of column headers
    
    Returns:
        bool: True if valid, False otherwise
    """
    required_columns = {"Base Value", "Translated Value"}
    return all(col in headers for col in required_columns)

def process_csv_file(file_path: str) -> tuple[str, list[tuple[str, str]]]:
    """
    Process VATV CSV file and convert to TMX.
    Each file contains English source and one target language.
    
    Args:
        file_path: Path to CSV file ([language]_VATV.csv)
    
    Returns:
        tuple: (Path to created TMX file, List of (level, message) log entries)
    """
    logger.info(f"Processing CSV file: {file_path}")
    logs = []
    
    try:
        # Get target language from filename
        input_path = Path(file_path)
        target_lang = input_path.stem
        if target_lang not in LANGUAGE_CODES:
            raise ValueError(f"Unknown language in filename: {target_lang}")
        
        logger.info(f"Detected target language: {target_lang} ({LANGUAGE_CODES[target_lang]})")
        
        # Create output path
        output_path = input_path.parent / f"{input_path.stem}.tmx"
        
        # Open file with correct encoding
        csvfile, encoding = open_csv_with_encoding(file_path)
        logger.info(f"File opened successfully with {encoding} encoding")
        
        with csvfile:
            # Validate CSV structure
            reader = csv.DictReader(csvfile)
            if not validate_csv_headers(reader.fieldnames):
                raise ValueError("CSV is missing required columns: 'Base Value' and/or 'Translated Value'")
            
            # Create TMX
            tmx = PythonTmx.Tmx()
            tmx.header.srclang = "en-us"
            tmx.header.segtype = "phrase"
            tmx.header.adminlang = "en-us"
            tmx.header.creationtool = "VATV Converter"
            tmx.header.creationtoolversion = "1.0"
            tmx.header.creationdate = datetime.now().strftime("%Y%m%dT%H%M%SZ")
            
            # Process rows
            row_count = skipped_count = empty_source = empty_target = 0
            
            for row in reader:
                row_count += 1
                if row_count % 100 == 0:
                    logger.info(f"Processing row {row_count}")
                
                source_text = row.get("Base Value", "").strip()
                target_text = row.get("Translated Value", "").strip()
                
                # Track specific issues
                if not source_text:
                    empty_source += 1
                    skipped_count += 1
                    continue
                    
                if not target_text:
                    empty_target += 1
                    skipped_count += 1
                    continue
                
                # Create TU
                tu = PythonTmx.Tu()
                
                # Add source TUV
                source_tuv = PythonTmx.Tuv(lang="en-us")
                source_tuv.seg = source_text
                tu.tuvs.append(source_tuv)
                
                # Add target TUV
                target_tuv = PythonTmx.Tuv(lang=LANGUAGE_CODES[target_lang])
                target_tuv.seg = target_text
                tu.tuvs.append(target_tuv)
                
                tmx.tus.append(tu)
            
            # Save TMX file
            tmx.save(str(output_path))
            
            # Log results
            logs.append(("info", f"Created TMX with {len(tmx.tus)} TUs"))
            logs.append(("info", f"Total rows processed: {row_count}"))
            if skipped_count:
                logs.append(("warning", f"Skipped {skipped_count} rows:"))
                logs.append(("warning", f"  - Empty source: {empty_source}"))
                logs.append(("warning", f"  - Empty target: {empty_target}"))
        
        return str(output_path), logs

    except Exception as e:
        logger.error(f"Error processing CSV file: {e}", exc_info=True)
        raise

if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Example usage when run directly
    file_path = input("Enter VATV CSV file path: ")
    
    try:
        output_file, logs = process_csv_file(file_path)
        print(f"\nCreated TMX file: {output_file}")
        print("\nProcessing logs:")
        for level, message in logs:
            print(f"{level.upper()}: {message}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
import logging
import os
import re
import shutil
from pathlib import Path

import PythonTmx
import lxml.etree as etree

from .tmx_utils import (
    append_header_notes_from_xml,
    append_tu_props_from_element,
    children_by_local,
    copy_xliff_roundtrip_sidecar,
    create_compatible_header,
    element_inner_text,
)

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


def _build_minimal_header_from_xml(header_elem: etree.ElementBase) -> PythonTmx.Header:
    header_attrs = {}
    for attr_name in ['creationtool', 'creationtoolversion', 'adminlang', 'srclang', 'segtype', 'datatype']:
        if attr_name in header_elem.attrib:
            header_attrs[attr_name] = header_elem.attrib[attr_name]

    segtype_str = header_attrs.get('segtype', 'sentence')
    if segtype_str == 'sentence':
        segtype_enum = PythonTmx.SEGTYPE.SENTENCE
    elif segtype_str == 'paragraph':
        segtype_enum = PythonTmx.SEGTYPE.PARAGRAPH
    elif segtype_str == 'phrase':
        segtype_enum = PythonTmx.SEGTYPE.PHRASE
    elif segtype_str == 'block':
        segtype_enum = PythonTmx.SEGTYPE.BLOCK
    else:
        segtype_enum = PythonTmx.SEGTYPE.SENTENCE

    return PythonTmx.Header(
        creationtool=header_attrs.get('creationtool', 'Unknown Tool'),
        creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
        adminlang=header_attrs.get('adminlang', 'en'),
        srclang=header_attrs.get('srclang', 'en'),
        segtype=segtype_enum,
        datatype=header_attrs.get('datatype', 'xml'),
        tmf="tmx",
        encoding="utf8",
    )


def _tu_plain_text_by_lang(tu: PythonTmx.Tu, source_lang: str) -> tuple[str, str]:
    source_text = ""
    target_text = ""
    for tuv in tu.tuvs:
        text = ''.join(part for part in tuv.content if isinstance(part, str)).strip()
        if tuv.lang.lower() == source_lang.lower():
            source_text = text
        else:
            target_text = text
    return source_text, target_text


def check_balanced_pairs(text: str) -> bool:
    """Check if parentheses and brackets are balanced in text."""
    stack = []
    pairs = {')': '(', ']': '[', '}': '{'}

    for char in text:
        if char in '([{':
            stack.append(char)
        elif char in ')]}':
            if not stack or stack.pop() != pairs[char]:
                return False

    return len(stack) == 0


def clean_tmx_for_mt(file_path: str) -> tuple[str, str]:
    """
    Clean TMX file for machine translation by:
    1. Removing tags and placeholders
    2. Removing segments with special characters
    3. Removing segments with unbalanced parentheses/brackets
    4. Removing segments with unusual patterns
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        tuple: (Path to cleaned TMX, Path to removed TMX)
    """
    logger.info(f"Starting MT cleaning for: {file_path}")
    
    try:
        # Create output paths similar to other cleaning scripts
        input_path = Path(file_path)
        output_dir = input_path.parent
        clean_path = output_dir / f"clean_{input_path.name}"
        removed_path = output_dir / f"removed_{input_path.name}"
      
        # Load TMX file using lxml XML parsing (more reliable)
        # Try multiple parsing approaches
        tm = None
        
        # First try: let lxml auto-detect encoding (works best with BOM files)
        try:
            tm = etree.parse(str(input_path))
            if tm is not None and tm.getroot() is not None:
                logger.info("Successfully parsed with auto-detected encoding")
        except Exception as parse_error:
            logger.debug(f"Failed with auto-detection: {parse_error}")
        
        # Second try: use recover mode if auto-detection failed
        if tm is None:
            try:
                parser = etree.XMLParser(recover=True)
                tm = etree.parse(str(input_path), parser)
                if tm is not None and tm.getroot() is not None:
                    logger.info("Successfully parsed with recovery mode")
            except Exception as parse_error:
                logger.debug(f"Failed with recovery mode: {parse_error}")
        
        # Third try: explicit encodings as last resort
        if tm is None:
            for encoding in ['utf-8', 'cp1252', 'latin-1']:
                try:
                    parser = etree.XMLParser(encoding=encoding, recover=True)
                    tm = etree.parse(str(input_path), parser)
                    if tm is not None and tm.getroot() is not None:
                        logger.info(f"Successfully parsed with encoding: {encoding}")
                        break
                except Exception as parse_error:
                    logger.debug(f"Failed to parse with {encoding}: {parse_error}")
                    continue
        
        if tm is None or tm.getroot() is None:
            raise ValueError("Could not parse TMX file with any supported encoding")
        
        tmx_root = tm.getroot()
        
        # Extract header attributes from XML (namespace-agnostic)
        header_elems = children_by_local(tmx_root, 'header')
        header_elem = header_elems[0] if header_elems else None
        if header_elem is None:
            raise ValueError("No header element found in TMX file")

        minimal_header = _build_minimal_header_from_xml(header_elem)
        clean_header = create_compatible_header(minimal_header, "TMX MT Cleaner", "1.0")
        removed_header = create_compatible_header(minimal_header, "TMX MT Cleaner", "1.0")
        append_header_notes_from_xml(header_elem, clean_header)
        append_header_notes_from_xml(header_elem, removed_header)

        # Parse TUs manually from XML (namespace-agnostic; preserve props)
        tus = []
        body_elems = children_by_local(tmx_root, 'body')
        body_elem = body_elems[0] if body_elems else None
        if body_elem is not None:
            for tu_elem in children_by_local(body_elem, 'tu'):
                tu = PythonTmx.Tu()
                for tuv_elem in children_by_local(tu_elem, 'tuv'):
                    lang = tuv_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                    seg_elems = children_by_local(tuv_elem, 'seg')
                    seg_elem = seg_elems[0] if seg_elems else None
                    if seg_elem is not None:
                        tuv = PythonTmx.Tuv(lang=lang)
                        tuv.content = element_inner_text(seg_elem)
                        tu.tuvs.append(tuv)
                append_tu_props_from_element(tu_elem, tu)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=clean_header, tus=tus)

        # Create clean/removed TMX objects
        clean_tmx = PythonTmx.Tmx(header=clean_header, tus=[])
        removed_tmx = PythonTmx.Tmx(header=removed_header, tus=[])

        # Compile regex patterns
        tag_pattern = re.compile(r'(<[^>]+>|(Ept|Bpt|It|Hi|Ut|Ph)\(.*?\))')
        placeholder_pattern = re.compile(r'\{[0-9]+\}|\[\[.*?\]\]|\{\{.*?\}\}')
        special_chars_pattern = re.compile(r'[^a-zA-Z0-9\s\.,;:!?\'\"\-\(\)\[\]{}]')
        
        total_tus = kept_tus = removed_tus = 0
        source_lang = (tmx.header.srclang or 'en').lower()

        # Process TUs
        for tu in tmx.tus:
            total_tus += 1
            keep_tu = True
            source_text, target_text = _tu_plain_text_by_lang(tu, source_lang)
            
            if not source_text or not target_text:
                keep_tu = False

            # Check each TUV text
            for text in (source_text, target_text):
                normalized = tag_pattern.sub(' ', text)
                normalized = placeholder_pattern.sub(' ', normalized)
                if special_chars_pattern.search(normalized):
                    keep_tu = False
                    break
                if not check_balanced_pairs(normalized):
                    keep_tu = False
                    break
                words = [w for w in normalized.split() if len(w) > 1]
                if len(words) < 2:
                    keep_tu = False
                    break

            # Additional checks if both source and target exist
            if keep_tu and source_text and target_text:
                # Check length ratio
                source_words = len(source_text.split())
                target_words = len(target_text.split())
                if max(source_words, target_words) / min(source_words, target_words) > 3:
                    keep_tu = False
                
                # Check for identical source and target
                if source_text == target_text:
                    keep_tu = False

            if keep_tu:
                clean_tmx.tus.append(tu)
                kept_tus += 1
            else:
                removed_tmx.tus.append(tu)
                removed_tus += 1
        
        clean_root = PythonTmx.to_element(clean_tmx, True)
        removed_root = PythonTmx.to_element(removed_tmx, True)
        etree.ElementTree(clean_root).write(str(clean_path), encoding="utf-8", xml_declaration=True)
        etree.ElementTree(removed_root).write(str(removed_path), encoding="utf-8", xml_declaration=True)
        copy_xliff_roundtrip_sidecar(str(input_path), str(clean_path), str(removed_path))

        logger.info(f"Cleaned {total_tus} TUs: kept {kept_tus}, removed {removed_tus}")
        return str(clean_path), str(removed_path)

    except Exception as e:
        logger.error(f"Error cleaning TMX for MT: {e}")
        raise


def clean_tmx_for_mt_legacy(
    source_file, target_file=None, logger=None
) -> tuple[str, int, int]:
    """
    Optional path + logging wrapper around clean_tmx_for_mt (formerly scripts.clean_mt).

    Returns (target_file_path, processed_count, kept_count); counts are 0,0 for compatibility.
    """
    if logger is None:
        logger = OperationLog()

    try:
        clean_path, _removed_path = clean_tmx_for_mt(source_file)
        if target_file and os.path.abspath(target_file) != os.path.abspath(clean_path):
            try:
                shutil.copy2(clean_path, target_file)
                clean_path = target_file
            except OSError as copy_error:
                logger.error(f"Error copying cleaned file to target path: {copy_error}")
                raise
        return clean_path, 0, 0
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise


def process_directory(directory):
    """
    Process all TMX files in a directory.

    Returns:
        tuple: (results, log_messages)
            results: list of (target_file, processed_count, cleaned_count)
            log_messages: list of (level, message) tuples
    """
    logger = OperationLog()
    results = []

    try:
        for filename in os.listdir(directory):
            if filename.endswith('.tmx'):
                source_file = os.path.join(directory, filename)
                logger.info(f"Processing file: {filename}")
                result = clean_tmx_for_mt_legacy(source_file, logger=logger)
                results.append(result)
        return results, logger.get_log()
    except Exception as e:
        logger.error(f"Error processing directory: {str(e)}")
        raise


if __name__ == "__main__":
    mode = input("[f] single TMX file or [d] directory? ").strip().lower()[:1]
    try:
        if mode == "d":
            directory = input("Enter directory path containing TMX files: ").strip()
            print("WARNING: This process removes information needed for translation leveraging.")
            print("Use only for preparing MT training data.")
            confirm = input("Continue? (y/N): ")
            if confirm.lower() != "y":
                raise SystemExit(0)
            results, log = process_directory(directory)
            for target, processed, cleaned in results:
                print(f"Created cleaned TMX file: {target}")
                print(f"Processed {processed} entries, kept {cleaned} entries")
            for level, message in log:
                print(f"{level.upper()}: {message}")
        else:
            file_path = input("Enter TMX file path: ").strip()
            clean_file, removed_file = clean_tmx_for_mt(file_path)
            print(f"Cleaned TMX created: {clean_file}")
            print(f"Removed segments TMX: {removed_file}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1)

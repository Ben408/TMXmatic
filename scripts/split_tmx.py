import sys
import os
import lxml.etree as etree

# Add the parent directory of PythonTmx to the path
tmx_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tmx', 'Lib', 'site-packages')
if tmx_path not in sys.path:
    sys.path.insert(0, tmx_path)

import PythonTmx
from datetime import datetime
from pathlib import Path
import logging
from typing import List, Dict, Set
import math
from .tmx_utils import create_compatible_header

logger = logging.getLogger(__name__)

def split_by_language(file_path: str) -> List[str]:
    """
    Split TMX file into separate files by target language.
    
    Args:
        file_path: Path to TMX file
    
    Returns:
        List[str]: Paths to created TMX files
    """
    logger.info(f"Splitting by language: {file_path}")
    
    try:
        input_path = Path(file_path)
        
        # Load TMX file using lxml XML parsing (more reliable)
        tm = etree.parse(str(input_path))
        tmx_root = tm.getroot()
        
        # Extract header attributes from XML
        header_elem = tmx_root.find('header')
        if header_elem is None:
            raise ValueError("No header element found in TMX file")
        
        # Create a minimal header object for compatibility
        header_attrs = {}
        for attr_name in ['creationtool', 'creationtoolversion', 'adminlang', 'srclang', 'segtype', 'datatype']:
            if attr_name in header_elem.attrib:
                header_attrs[attr_name] = header_elem.attrib[attr_name]
        
        # Convert string segtype to enum if needed
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
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE  # Default fallback
        
        minimal_header = PythonTmx.Header(
            creationtool=header_attrs.get('creationtool', 'Unknown Tool'),
            creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
            adminlang=header_attrs.get('adminlang', 'en'),
            srclang=header_attrs.get('srclang', 'en'),
            segtype=segtype_enum,
            datatype=header_attrs.get('datatype', 'xml'),
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )
        
        # Parse TUs manually from XML
        tus = []
        body_elem = tmx_root.find('body')
        if body_elem is not None:
            for tu_elem in body_elem.findall('tu'):
                tu = PythonTmx.Tu()
                for tuv_elem in tu_elem.findall('tuv'):
                    lang = tuv_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                    seg_elem = tuv_elem.find('seg')
                    if seg_elem is not None and seg_elem.text:
                        tuv = PythonTmx.Tuv(lang=lang)
                        tuv.content = seg_elem.text
                        tu.tuvs.append(tuv)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        
        # Create compatible headers preserving original attributes
        base_header = create_compatible_header(tmx.header, "TMX Splitter", "1.0")
        
        source_lang = tmx.header.srclang
        
        # Track languages and their TUs
        language_tus: Dict[str, PythonTmx.Tmx] = {}
        created_files: List[str] = []
        
        # Process TUs
        for tu in tmx.tus:
            # Validate TU structure
            if not tu.tuvs or len(tu.tuvs) < 2:
                logger.warning(f"Skipping TU with insufficient TUVs: {len(tu.tuvs) if tu.tuvs else 0} TUVs")
                continue
                
            target_langs: Set[str] = set()
            src_tuv = None
            # Find target languages in TU
            for tuv in tu.tuvs:
                if tuv.lang == source_lang:
                    src_tuv = tuv
                else:
                    target_langs.add(tuv.lang)
            
            # Skip if no source TUV found
            if not src_tuv:
                logger.warning(f"Skipping TU without source language TUV for {source_lang}")
                continue
            
            # Create TMX for each target language
            for lang in target_langs:
                if lang not in language_tus:
                    new_tmx = PythonTmx.Tmx(header=base_header)
                    language_tus[lang] = new_tmx
                
            for tuv in tu.tuvs:
                if tuv.lang != source_lang:
                    current_tu = PythonTmx.Tu()
                    current_tu.props = tu.props
                    current_tu.tuvs = [src_tuv, tuv]
                    language_tus[tuv.lang].tus.append(current_tu)
        
        # Save language-specific TMX files
        for lang, lang_tmx in language_tus.items():
            output_path = input_path.parent / f"{input_path.stem}_{lang}.tmx"
            # Save TMX file using the correct method
            try:
                # Use the to_tmx method which should exist
                lang_tmx.to_tmx(str(output_path))
            except AttributeError:
                # Fallback: use lxml to write the XML directly
                root = PythonTmx.to_element(lang_tmx, True)
                etree.ElementTree(root).write(str(output_path), encoding="utf-8", xml_declaration=True)
            created_files.append(str(output_path))
            logger.info(f"Created {lang} TMX with {len(lang_tmx.tus)} TUs")
        
        return created_files

    except Exception as e:
        logger.error(f"Error splitting TMX by language: {e}")
        raise

def split_by_size(file_path: str, max_tus: int = 50000) -> List[str]:
    """
    Split TMX file into smaller files with specified maximum TUs.
    
    Args:
        file_path: Path to TMX file
        max_tus: Maximum TUs per file
    
    Returns:
        List[str]: Paths to created TMX files
    """
    logger.info(f"Splitting by size: {file_path} (max {max_tus} TUs)")
    
    try:
        input_path = Path(file_path)

        # Load TMX file using lxml XML parsing (more reliable)
        tm = etree.parse(str(input_path))
        tmx_root = tm.getroot()
        
        # Extract header attributes from XML
        header_elem = tmx_root.find('header')
        if header_elem is None:
            raise ValueError("No header element found in TMX file")
        
        # Create a minimal header object for compatibility
        header_attrs = {}
        for attr_name in ['creationtool', 'creationtoolversion', 'adminlang', 'srclang', 'segtype', 'datatype']:
            if attr_name in header_elem.attrib:
                header_attrs[attr_name] = header_elem.attrib[attr_name]
        
        # Convert string segtype to enum if needed
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
            segtype_enum = PythonTmx.SEGTYPE.SENTENCE  # Default fallback
        
        minimal_header = PythonTmx.Header(
            creationtool=header_attrs.get('creationtool', 'Unknown Tool'),
            creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
            adminlang=header_attrs.get('adminlang', 'en'),
            srclang=header_attrs.get('srclang', 'en'),
            segtype=segtype_enum,
            datatype=header_attrs.get('datatype', 'xml'),
            tmf="tmx",  # Required parameter
            encoding="utf8"  # Required parameter
        )
        
        # Parse TUs manually from XML
        tus = []
        body_elem = tmx_root.find('body')
        if body_elem is not None:
            for tu_elem in body_elem.findall('tu'):
                tu = PythonTmx.Tu()
                for tuv_elem in tu_elem.findall('tuv'):
                    lang = tuv_elem.get('{http://www.w3.org/XML/1998/namespace}lang', 'en')
                    seg_elem = tuv_elem.find('seg')
                    if seg_elem is not None and seg_elem.text:
                        tuv = PythonTmx.Tuv(lang=lang)
                        tuv.content = seg_elem.text
                        tu.tuvs.append(tuv)
                if len(tu.tuvs) >= 2:  # Only add TUs with both source and target
                    tus.append(tu)
        
        # Create TMX object with correct constructor
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        
        # Create compatible headers preserving original attributes
        base_header = create_compatible_header(tmx.header, "TMX Splitter", "1.0")
        
        created_files: List[str] = []
        
        # Calculate number of parts needed
        total_tus = len(tmx.tus)
        num_parts = math.ceil(total_tus / int(max_tus))
        
        for part in range(num_parts):
            # Create new TMX for this part
            part_tmx = PythonTmx.Tmx(header=base_header)

            # Add TUs for this part
            start_idx = part * int(max_tus)
            end_idx = min((part + 1) * int(max_tus), total_tus)
            part_tmx.tus.extend(tmx.tus[start_idx:end_idx])
            
            # Save part file
            output_path = input_path.parent / f"{input_path.stem}_part{part + 1}.tmx"
            # Save TMX file using the correct method
            try:
                # Use the to_tmx method which should exist
                part_tmx.to_tmx(str(output_path))
            except AttributeError:
                # Fallback: use lxml to write the XML directly
                root = PythonTmx.to_element(part_tmx, True)
                etree.ElementTree(root).write(str(output_path), encoding="utf-8", xml_declaration=True)
            created_files.append(str(output_path))
            logger.info(f"Created part {part + 1} with {len(part_tmx.tus)} TUs")
        
        return created_files

    except Exception as e:
        logger.error(f"Error splitting TMX by size: {e}")
        raise

if __name__ == "__main__":
    # Example usage when run directly
    file_path = input("Enter TMX file path: ")
    split_type = input("Split by (l)anguage or (s)ize? ").lower()
    
    try:
        if split_type == 'l':
            files = split_by_language(file_path)
            print("Created language-specific files:")
        else:
            max_tus = int(input("Enter maximum TUs per file: "))
            files = split_by_size(file_path, max_tus)
            print("Created size-specific files:")
        
        for f in files:
            print(f"- {f}")
    except Exception as e:
        print(f"ERROR: {e}")
        exit(1) 
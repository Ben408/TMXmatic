#!/usr/bin/env python3
"""
TBX Cleaner Script

This script processes a TBX (TermBase eXchange) file and creates two new files:
1. A file containing unique concepts (one per en-us term, preferring those with definitions)
2. A file containing the concepts that were removed (duplicates)
"""

import xml.etree.ElementTree as ET
import sys
import argparse
import re
from pathlib import Path
from collections import defaultdict


def find_namespace(root):
    """Extract namespace from root element if present."""
    if root.tag.startswith('{'):
        return root.tag[1:root.tag.index('}')]
    # Also check xmlns attribute for default namespace
    if 'xmlns' in root.attrib:
        return root.attrib['xmlns']
    return None


def get_en_us_term(concept_entry, ns):
    """Extract the en-us term from a concept entry."""
    # Try langSec (TBX-Basic dialect) first, then langSet (other dialects)
    lang_sec_paths = []
    lang_set_paths = []
    
    if ns:
        lang_sec_paths.append(f'.//{{{ns}}}langSec')
        lang_set_paths.append(f'.//{{{ns}}}langSet')
    
    # Add common namespace variants
    lang_sec_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSec',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSec',
        './/langSec',
    ])
    
    lang_set_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSet',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSet',
        './/langSet',
    ])
    
    # Try langSec first (TBX-Basic dialect)
    for lang_sec_path in lang_sec_paths:
        for lang_sec in concept_entry.findall(lang_sec_path):
            lang_attr = lang_sec.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_sec.get('xml:lang')
            if lang_attr and lang_attr.lower() in ('en-us', 'en_us', 'enus'):
                # Find termSec > term structure (TBX-Basic)
                term_sec_paths = []
                if ns:
                    term_sec_paths.append(f'.//{{{ns}}}termSec')
                term_sec_paths.extend([
                    './/{urn:iso:std:iso:30042:ed-2}termSec',
                    './/{http://www.lisa.org/TBX-Specification.3.0}termSec',
                    './/termSec',
                ])
                
                for term_sec_path in term_sec_paths:
                    term_sec = lang_sec.find(term_sec_path)
                    if term_sec is not None:
                        # Find term within termSec
                        term_paths = []
                        if ns:
                            term_paths.append(f'.//{{{ns}}}term')
                        term_paths.extend([
                            './/{urn:iso:std:iso:30042:ed-2}term',
                            './/{http://www.lisa.org/TBX-Specification.3.0}term',
                            './/term',
                        ])
                        
                        for term_path in term_paths:
                            term_elem = term_sec.find(term_path)
                            if term_elem is not None:
                                term_text = term_elem.text
                                if term_text:
                                    return term_text.strip()
                
                # Also try direct term (fallback)
                term_paths = []
                if ns:
                    term_paths.append(f'.//{{{ns}}}term')
                term_paths.extend([
                    './/{urn:iso:std:iso:30042:ed-2}term',
                    './/{http://www.lisa.org/TBX-Specification.3.0}term',
                    './/term',
                ])
                
                for term_path in term_paths:
                    term_elem = lang_sec.find(term_path)
                    if term_elem is not None:
                        term_text = term_elem.text
                        if term_text:
                            return term_text.strip()
    
    # Try langSet (other TBX dialects)
    for lang_set_path in lang_set_paths:
        for lang_set in concept_entry.findall(lang_set_path):
            lang_attr = lang_set.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_set.get('xml:lang')
            if lang_attr and lang_attr.lower() in ('en-us', 'en_us', 'enus'):
                # Find term element
                term_paths = []
                if ns:
                    term_paths.append(f'.//{{{ns}}}term')
                term_paths.extend([
                    './/{urn:iso:std:iso:30042:ed-2}term',
                    './/{http://www.lisa.org/TBX-Specification.3.0}term',
                    './/term',
                ])
                
                for term_path in term_paths:
                    term_elem = lang_set.find(term_path)
                    if term_elem is not None:
                        term_text = term_elem.text
                        if term_text:
                            return term_text.strip()
    
    return None


def copy_element_without_prefix(elem, target_ns=None):
    """Copy an element and all its children, removing namespace prefixes.
    
    Creates new elements with local names only, using default namespace if provided.
    """
    # Get local name (without namespace)
    if '}' in elem.tag:
        local_name = elem.tag.split('}')[1]
    else:
        local_name = elem.tag
    
    # Create new element WITHOUT namespace in tag - rely on default namespace from root
    new_elem = ET.Element(local_name)
    
    # Copy attributes (but skip xmlns:prefix attributes, we'll use default namespace)
    for key, value in elem.attrib.items():
        # Skip prefixed namespace declarations (like xmlns:tbx, xmlns:ns0)
        if key.startswith('{http://www.w3.org/2000/xmlns/}'):
            ns_attr_name = key.split('}')[1]
            if ':' in ns_attr_name:
                continue  # Skip prefixed namespace declarations
            # Keep default xmlns if it's the target namespace
            if ns_attr_name == 'xmlns' and value == target_ns:
                continue  # Will be set on root
        # Keep xml:lang and other xml:* attributes
        elif key.startswith('{http://www.w3.org/XML/1998/namespace}'):
            # Convert to xml:lang format
            attr_name = key.split('}')[1]
            new_elem.set(f'xml:{attr_name}', value)
        else:
            new_elem.set(key, value)
    
    # Copy text
    if elem.text:
        new_elem.text = elem.text
    
    # Copy tail
    if elem.tail:
        new_elem.tail = elem.tail
    
    # Recursively copy children
    for child in elem:
        new_child = copy_element_without_prefix(child, target_ns)
        new_elem.append(new_child)
    
    return new_elem


def has_definition(concept_entry, ns):
    """Check if a concept entry has a definition."""
    # Try different namespace prefixes and definition paths
    # First, try direct descrip elements at conceptEntry level
    descrip_paths = []
    if ns:
        descrip_paths.append(f'.//{{{ns}}}descrip[@type="definition"]')
        descrip_paths.append(f'{{{ns}}}descrip[@type="definition"]')
    
    descrip_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}descrip[@type="definition"]',
        './/{http://www.lisa.org/TBX-Specification.3.0}descrip[@type="definition"]',
        './/descrip[@type="definition"]',
        'descrip[@type="definition"]',
    ])
    
    for descrip_path in descrip_paths:
        descrip = concept_entry.find(descrip_path)
        if descrip is not None:
            descrip_text = descrip.text
            if descrip_text and descrip_text.strip():
                return True
    
    # Also try findall to get all descrip elements and check their type attribute
    all_descrip_paths = []
    if ns:
        all_descrip_paths.append(f'.//{{{ns}}}descrip')
        all_descrip_paths.append(f'{{{ns}}}descrip')
    
    all_descrip_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}descrip',
        './/{http://www.lisa.org/TBX-Specification.3.0}descrip',
        './/descrip',
        'descrip',
    ])
    
    for descrip_path in all_descrip_paths:
        for descrip in concept_entry.findall(descrip_path):
            descrip_type = descrip.get('type')
            if descrip_type and descrip_type.lower() == 'definition':
                descrip_text = descrip.text
                if descrip_text and descrip_text.strip():
                    return True
    
    # Also check in langSec/langSet elements
    lang_sec_paths = []
    lang_set_paths = []
    
    if ns:
        lang_sec_paths.append(f'.//{{{ns}}}langSec')
        lang_set_paths.append(f'.//{{{ns}}}langSet')
    
    lang_sec_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSec',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSec',
        './/langSec',
    ])
    
    lang_set_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSet',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSet',
        './/langSet',
    ])
    
    for lang_sec_path in lang_sec_paths:
        for lang_sec in concept_entry.findall(lang_sec_path):
            for descrip_path in descrip_paths:
                descrip = lang_sec.find(descrip_path)
                if descrip is not None:
                    descrip_text = descrip.text
                    if descrip_text and descrip_text.strip():
                        return True
    
    for lang_set_path in lang_set_paths:
        for lang_set in concept_entry.findall(lang_set_path):
            for descrip_path in descrip_paths:
                descrip = lang_set.find(descrip_path)
                if descrip is not None:
                    descrip_text = descrip.text
                    if descrip_text and descrip_text.strip():
                        return True
    
    return False


def get_languages_in_concept(concept_entry, ns):
    """Get a set of all language codes present in a concept entry."""
    languages = set()
    
    # Try langSec (TBX-Basic) and langSet (other dialects)
    lang_sec_paths = []
    lang_set_paths = []
    
    if ns:
        lang_sec_paths.append(f'.//{{{ns}}}langSec')
        lang_set_paths.append(f'.//{{{ns}}}langSet')
    
    lang_sec_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSec',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSec',
        './/langSec',
    ])
    
    lang_set_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSet',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSet',
        './/langSet',
    ])
    
    for lang_sec_path in lang_sec_paths:
        for lang_sec in concept_entry.findall(lang_sec_path):
            lang_attr = lang_sec.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_sec.get('xml:lang')
            if lang_attr:
                languages.add(lang_attr.lower())
    
    for lang_set_path in lang_set_paths:
        for lang_set in concept_entry.findall(lang_set_path):
            lang_attr = lang_set.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_set.get('xml:lang')
            if lang_attr:
                languages.add(lang_attr.lower())
    
    return languages


def get_language_section(concept_entry, lang_code, ns):
    """Get a specific language section (langSec or langSet) from a concept entry.
    
    Returns the langSec/langSet element if found, None otherwise.
    """
    lang_code_lower = lang_code.lower()
    
    # Try langSec (TBX-Basic) and langSet (other dialects)
    lang_sec_paths = []
    lang_set_paths = []
    
    if ns:
        lang_sec_paths.append(f'.//{{{ns}}}langSec')
        lang_set_paths.append(f'.//{{{ns}}}langSet')
    
    lang_sec_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSec',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSec',
        './/langSec',
    ])
    
    lang_set_paths.extend([
        './/{urn:iso:std:iso:30042:ed-2}langSet',
        './/{http://www.lisa.org/TBX-Specification.3.0}langSet',
        './/langSet',
    ])
    
    for lang_sec_path in lang_sec_paths:
        for lang_sec in concept_entry.findall(lang_sec_path):
            lang_attr = lang_sec.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_sec.get('xml:lang')
            if lang_attr and lang_attr.lower() == lang_code_lower:
                return lang_sec
    
    for lang_set_path in lang_set_paths:
        for lang_set in concept_entry.findall(lang_set_path):
            lang_attr = lang_set.get('{http://www.w3.org/XML/1998/namespace}lang') or lang_set.get('xml:lang')
            if lang_attr and lang_attr.lower() == lang_code_lower:
                return lang_set
    
    return None


def merge_languages_from_discarded(unique_concept, discarded_concepts, ns):
    """Merge language sections from discarded concepts into unique concept.
    
    Adds any language sections that exist in discarded concepts but not in unique concept.
    """
    unique_languages = get_languages_in_concept(unique_concept, ns)
    
    # Track which languages we've already added (to avoid duplicates)
    added_languages = set(unique_languages)
    
    for discarded_concept in discarded_concepts:
        discarded_languages = get_languages_in_concept(discarded_concept, ns)
        
        # Find languages in discarded concept that are not in unique concept
        missing_languages = discarded_languages - added_languages
        
        # Skip en-us/en-US as we already have it (it's how we matched them)
        missing_languages = {lang for lang in missing_languages if lang not in ('en-us', 'en_us', 'enus')}
        
        for lang_code in missing_languages:
            lang_section = get_language_section(discarded_concept, lang_code, ns)
            if lang_section is not None:
                # Copy the language section
                copied_section = copy_element_without_prefix(lang_section, ns)
                # Add it to the unique concept
                unique_concept.append(copied_section)
                added_languages.add(lang_code)


def process_tbx(input_file):
    """Process TBX file and create two output files."""
    try:
        # Parse the input TBX file

        input_path = Path(input_file)
        output_dir = input_path.parent
        output_unique = output_dir / f"clean_{input_path.name}"
        output_remaining = output_dir / f"remaining_{input_path.name}"

        
        tree = ET.parse(input_file)
        root = tree.getroot()
        
        # Get namespace
        ns = find_namespace(root)
        
        # Don't register namespace with prefix - we want default namespace in output
        
        print(f"Detected namespace: {ns if ns else 'None'}")
        
        # Find all concept entries - try multiple approaches
        concept_entries = []
        
        # Method 1: With namespace
        if ns:
            concept_entries = root.findall(f'.//{{{ns}}}conceptEntry')
            if not concept_entries:
                # Try with body/text wrapper
                body = root.find(f'.//{{{ns}}}body')
                if body is not None:
                    concept_entries = body.findall(f'.//{{{ns}}}conceptEntry')
        
        # Method 2: Common namespace variants
        if not concept_entries:
            for test_ns in ['urn:iso:std:iso:30042:ed-2', 'http://www.lisa.org/TBX-Specification.3.0']:
                concept_entries = root.findall(f'.//{{{test_ns}}}conceptEntry')
                if concept_entries:
                    ns = test_ns
                    break
        
        # Method 3: Without namespace (if no default namespace)
        if not concept_entries:
            concept_entries = root.findall('.//conceptEntry')
            # Also try in body
            if not concept_entries:
                body = root.find('.//body')
                if body is not None:
                    concept_entries = body.findall('.//conceptEntry')
        
        if not concept_entries:
            print("Error: Could not find any conceptEntry elements in the TBX file.")
            print(f"Root tag: {root.tag}")
            print(f"Root attributes: {root.attrib}")
            # Debug: print first few children
            print("First few root children:")
            for i, child in enumerate(list(root)[:5]):
                print(f"  {i}: {child.tag}")
            return False
        
        print(f"Found {len(concept_entries)} concept entries")
        
        # Dictionary to track unique en-us terms
        # Key: en-us term (lowercase for case-insensitive comparison)
        # Value: tuple of (concept_entry, has_definition, original_term)
        unique_terms = {}
        # Dictionary to track remaining concepts by term (for language merging)
        # Key: en-us term (lowercase)
        # Value: list of discarded concepts with that term
        remaining_by_term = {}
        concepts_without_en_us = []
        
        # Process each concept entry
        for idx, concept in enumerate(concept_entries):
            en_us_term = get_en_us_term(concept, ns)
            has_def = has_definition(concept, ns)
            
            # Debug output for first few entries
            if idx < 3:
                print(f"  Concept {idx+1}: en-us term = {en_us_term}, has definition = {has_def}")
            
            if not en_us_term:
                # Concept without en-us term goes to remaining
                concepts_without_en_us.append(concept)
                continue
            
            term_key = en_us_term.lower()
            
            if term_key not in unique_terms:
                # First occurrence of this term
                unique_terms[term_key] = (concept, has_def, en_us_term)
                remaining_by_term[term_key] = []
            else:
                # Duplicate term found
                existing_concept, existing_has_def, existing_term = unique_terms[term_key]
                
                if not existing_has_def and has_def:
                    # Replace with the one that has a definition
                    unique_terms[term_key] = (concept, has_def, en_us_term)
                    # Add the old one to remaining for this term
                    remaining_by_term[term_key].append(existing_concept)
                else:
                    # Keep the existing one, add current to remaining for this term
                    remaining_by_term[term_key].append(concept)
        
        # Merge languages from discarded concepts into unique concepts
        print("Merging languages from discarded concepts...")
        merged_count = 0
        for term_key, (unique_concept, has_def, en_us_term) in unique_terms.items():
            discarded_for_term = remaining_by_term.get(term_key, [])
            if discarded_for_term:
                languages_before = get_languages_in_concept(unique_concept, ns)
                merge_languages_from_discarded(unique_concept, discarded_for_term, ns)
                languages_after = get_languages_in_concept(unique_concept, ns)
                added = len(languages_after) - len(languages_before)
                if added > 0:
                    merged_count += added
        
        print(f"Added {merged_count} language sections from discarded concepts")
        
        # Collect all remaining concepts (for the remaining file)
        remaining_concepts = []
        for discarded_list in remaining_by_term.values():
            remaining_concepts.extend(discarded_list)
        remaining_concepts.extend(concepts_without_en_us)
        
        print(f"Unique concepts: {len(unique_terms)}")
        print(f"Remaining/duplicate concepts: {len(remaining_concepts)}")
        
        # Create new TBX trees
        # Get local name for root element
        if '}' in root.tag:
            root_local_name = root.tag.split('}')[1]
        else:
            root_local_name = root.tag
        
        # Create root elements WITHOUT namespace in tag - use default namespace via xmlns
        unique_root = ET.Element(root_local_name)
        remaining_root = ET.Element(root_local_name)
        
        # Set default namespace as xmlns attribute (not xmlns:tbx or xmlns:ns0)
        if ns:
            unique_root.set('xmlns', ns)
            remaining_root.set('xmlns', ns)
        
        # Copy root attributes (but skip xmlns:prefix attributes)
        for key, value in root.attrib.items():
            # Skip prefixed namespace declarations
            if key.startswith('{http://www.w3.org/2000/xmlns/}') and ':' in key.split('}')[1]:
                continue
            # Keep xml:lang and other attributes
            if key.startswith('{http://www.w3.org/XML/1998/namespace}'):
                attr_name = key.split('}')[1]
                unique_root.set(f'xml:{attr_name}', value)
                remaining_root.set(f'xml:{attr_name}', value)
            elif key != 'xmlns':  # Don't copy xmlns if we're setting it above
                unique_root.set(key, value)
                remaining_root.set(key, value)
        
        # Copy header if present
        header_paths = [
            '{http://www.lisa.org/TBX-Specification.3.0}tbxHeader',
            'tbxHeader',
            '{urn:iso:std:iso:30042:ed-2}tbxHeader',
        ]
        
        if ns:
            header_paths.insert(0, f'{{{ns}}}tbxHeader')
        
        header = None
        for path in header_paths:
            header = root.find(path)
            if header is not None:
                break
        
        if header is not None:
            # Copy header without namespace prefix
            unique_header = copy_element_without_prefix(header, ns)
            remaining_header = copy_element_without_prefix(header, ns)
            unique_root.append(unique_header)
            remaining_root.append(remaining_header)
        
        # Find text body or similar container
        body_paths = []
        if ns:
            body_paths.append(f'{{{ns}}}text')
        body_paths.extend([
            '{urn:iso:std:iso:30042:ed-2}text',
            '{http://www.lisa.org/TBX-Specification.3.0}text',
            'text',
        ])
        
        body = None
        for path in body_paths:
            body = root.find(path)
            if body is not None:
                break
        
        if body is not None:
            # Check if body has a 'body' child (TBX structure: text > body > conceptEntry)
            body_child_paths = []
            if ns:
                body_child_paths.append(f'{{{ns}}}body')
            body_child_paths.extend([
                '{urn:iso:std:iso:30042:ed-2}body',
                '{http://www.lisa.org/TBX-Specification.3.0}body',
                'body',
            ])
            
            inner_body = None
            for path in body_child_paths:
                inner_body = body.find(path)
                if inner_body is not None:
                    break
            
            if inner_body is not None:
                # Create text > body structure
                # Create new text elements (copy attributes but not children)
                unique_text = ET.Element('text')
                remaining_text = ET.Element('text')
                for key, value in body.attrib.items():
                    if not key.startswith('{http://www.w3.org/2000/xmlns/}'):
                        unique_text.set(key, value)
                        remaining_text.set(key, value)
                
                # Create new empty body elements (copy attributes but not children)
                unique_body_elem = ET.Element('body')
                remaining_body_elem = ET.Element('body')
                for key, value in inner_body.attrib.items():
                    if not key.startswith('{http://www.w3.org/2000/xmlns/}'):
                        unique_body_elem.set(key, value)
                        remaining_body_elem.set(key, value)
                
                # Add concepts to body elements
                for concept, _, _ in unique_terms.values():
                    unique_concept = copy_element_without_prefix(concept, ns)
                    unique_body_elem.append(unique_concept)
                
                for concept in remaining_concepts:
                    remaining_concept = copy_element_without_prefix(concept, ns)
                    remaining_body_elem.append(remaining_concept)
                
                # Add body to text
                unique_text.append(unique_body_elem)
                remaining_text.append(remaining_body_elem)
                
                unique_root.append(unique_text)
                remaining_root.append(remaining_text)
            else:
                # No inner body, add concepts directly to text element
                # Create new text elements (copy attributes but not children)
                unique_text = ET.Element('text')
                remaining_text = ET.Element('text')
                for key, value in body.attrib.items():
                    if not key.startswith('{http://www.w3.org/2000/xmlns/}'):
                        unique_text.set(key, value)
                        remaining_text.set(key, value)
                
                # Add concepts to text elements
                for concept, _, _ in unique_terms.values():
                    unique_concept = copy_element_without_prefix(concept, ns)
                    unique_text.append(unique_concept)
                
                for concept in remaining_concepts:
                    remaining_concept = copy_element_without_prefix(concept, ns)
                    remaining_text.append(remaining_concept)
                
                unique_root.append(unique_text)
                remaining_root.append(remaining_text)
        else:
            # No body element, add concepts directly to root
            for concept, _, _ in unique_terms.values():
                unique_concept = copy_element_without_prefix(concept, ns)
                unique_root.append(unique_concept)
            
            for concept in remaining_concepts:
                remaining_concept = copy_element_without_prefix(concept, ns)
                remaining_root.append(remaining_concept)
        
        # Write output files
        unique_tree = ET.ElementTree(unique_root)
        remaining_tree = ET.ElementTree(remaining_root)
        
        # Pretty print helper
        def indent(elem, level=0):
            i = "\n" + level * "  "
            if len(elem):
                if not elem.text or not elem.text.strip():
                    elem.text = i + "  "
                if not elem.tail or not elem.tail.strip():
                    elem.tail = i
                for child in elem:
                    indent(child, level+1)
                if not child.tail or not child.tail.strip():
                    child.tail = i
            else:
                if level and (not elem.tail or not elem.tail.strip()):
                    elem.tail = i
        
        indent(unique_root)
        indent(remaining_root)
        
        # Write XML and remove namespace prefixes
        def write_xml_without_prefixes(tree, filename, ns):
            """Write XML file removing any automatically generated namespace prefixes."""
            # Get XML as string
            xml_string = ET.tostring(tree.getroot(), encoding='unicode', method='xml')
            
            # Remove namespace prefix declarations (like xmlns:ns0="..." or xmlns:tbx="...")
            # But keep the default xmlns="..." declaration
            xml_string = re.sub(r' xmlns:\w+="[^"]*"', '', xml_string)
            
            # Remove prefixes from opening tags: <prefix:tag -> <tag
            xml_string = re.sub(r'<(\w+):(\w+)([^>]*)>', r'<\2\3>', xml_string)
            
            # Remove prefixes from closing tags: </prefix:tag -> </tag
            xml_string = re.sub(r'</(\w+):(\w+)>', r'</\2>', xml_string)
            
            # Write to file
            with open(filename, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write(xml_string)
        
        write_xml_without_prefixes(unique_tree, output_unique, ns)
        write_xml_without_prefixes(remaining_tree, output_remaining, ns)
        
        print(f"\nSuccessfully created:")
        print(f"  - Unique concepts: {output_unique}")
        print(f"  - Remaining concepts: {output_remaining}")

        return (str(output_unique), str(output_remaining))
        
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        return False
    except Exception as e:
        print(f"Error processing TBX file: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Process TBX file to create unique and remaining concept files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python tbx_cleaner.py input.tbx
  python tbx_cleaner.py input.tbx -o unique.tbx -r remaining.tbx
        """
    )
    
    parser.add_argument('input_file', help='Input TBX file path')
    parser.add_argument('-o', '--output-unique', 
                       help='Output file for unique concepts (default: <input>_unique.tbx)',
                       default=None)
    parser.add_argument('-r', '--output-remaining',
                       help='Output file for remaining/duplicate concepts (default: <input>_remaining.tbx)',
                       default=None)
    
    args = parser.parse_args()
    
    # Validate input file
    input_path = Path(args.input_file)
    if not input_path.exists():
        print(f"Error: Input file '{args.input_file}' does not exist.")
        sys.exit(1)
    
    # Generate output file names if not provided
    if args.output_unique is None:
        args.output_unique = input_path.stem + '_unique.tbx'
    
    if args.output_remaining is None:
        args.output_remaining = input_path.stem + '_remaining.tbx'
    
    # Process the file
    success = process_tbx(args.input_file)
    
    if not success:
        sys.exit(1)


if __name__ == '__main__':
    main()


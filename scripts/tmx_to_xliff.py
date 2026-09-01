"""
Convert TMX file back to XLIFF format (1.2, 2.0, or 2.2).
Preserves original XLIFF version if available in TMX metadata.
"""

import lxml.etree as etree
from pathlib import Path
import logging
from typing import Optional, List
from itertools import groupby
import json
import PythonTmx

from .tmx_utils import (
    children_by_local,
    decode_xliff_markup_from_tmx_prop,
    element_inner_text,
    local_name,
    prop_inner_text,
)
from .xliff_xml_fragment import (
    build_target_element_mirroring_seg_source,
    build_target_element_mirroring_source_markup,
    normalize_seg_source_storage_xml,
    normalize_xliff_inline_fragment_xml,
)

logger = logging.getLogger(__name__)

# XLIFF namespaces
XLIFF_20_NS = 'urn:oasis:names:tc:xliff:document:2.0'
XLIFF_22_NS = 'urn:oasis:names:tc:xliff:document:2.2'
XML_NS = 'http://www.w3.org/XML/1998/namespace'


def _tuv_content_plain(content) -> str:
    """
    Plain segment string from a PythonTmx Tuv.content value.
    Parsed TMX uses a list of strings (and sometimes inline TMX tags); str(list) breaks round-trip.
    """
    if content is None:
        return ''
    if isinstance(content, str):
        return content
    if isinstance(content, (list, tuple)):
        return ''.join(x for x in content if isinstance(x, str))
    return str(content)


def get_xliff_version_from_tmx(tmx: PythonTmx.Tmx) -> str:
    """
    Extract original XLIFF version from TMX metadata.
    Checks header notes first, then TU properties as fallback.
    
    Args:
        tmx: TMX object
    
    Returns:
        str: XLIFF version ('1.2', '2.0', or '2.2')
    """
    # Check header notes first (primary method)
    for note in tmx.header.notes:
        # Try both 'content' and 'text' attributes (PythonTmx may use either)
        note_text = None
        if hasattr(note, 'content') and note.content:
            note_text = note.content
        elif hasattr(note, 'text') and note.text:
            note_text = note.text
        
        if note_text and 'Original XLIFF version' in note_text:
            version = note_text.split(':')[-1].strip()
            if version in ['1.2', '2.0', '2.2']:
                logger.info(f"Found original XLIFF version from header note: {version}")
                return version
    
    # Check all TUs for version property (fallback method)
    for tu in tmx.tus:
        for prop in tu.props:
            if prop.type == 'x-xliff-version':
                version = prop.text.strip() if prop.text else ''
                if version in ['1.2', '2.0', '2.2']:
                    logger.info(f"Found original XLIFF version from TU property: {version}")
                    return version
    
    # Default to 1.2 if not found
    logger.warning("Original XLIFF version not found in TMX metadata, defaulting to 1.2")
    return '1.2'


def get_tu_metadata(tu: PythonTmx.Tu) -> dict:
    """
    Extract XLIFF metadata from TU properties.
    Restores all attributes, contexts, alt-trans, etc.
    
    Args:
        tu: Translation unit
        
    Returns:
        dict: Metadata dictionary with all preserved information
    """
    metadata = {}
    source_attrs = {}
    target_attrs = {}
    segment_attrs = {}
    
    for prop in tu.props:
        if not prop.type.startswith('x-xliff-'):
            continue
        
        prop_type = prop.type
        prop_value = prop.text if prop.text else ''
        
        # Handle special cases
        if prop_type == 'x-xliff-version':
            continue  # Skip version, handled separately
        elif prop_type == 'x-xliff-context-groups':
            try:
                metadata['context_groups'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse context-groups JSON: {prop_value}")
        elif prop_type == 'x-xliff-contexts':
            try:
                metadata['contexts'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse contexts JSON: {prop_value}")
        elif prop_type == 'x-xliff-props':
            try:
                metadata['props'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse props JSON: {prop_value}")
        elif prop_type == 'x-xliff-alt-trans':
            try:
                metadata['alt_trans'] = json.loads(prop_value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"Could not parse alt-trans JSON: {prop_value}")
        elif prop_type == 'x-xliff-file-attributes':
            try:
                metadata['file_attributes'] = json.loads(prop_value)
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning(f"Could not parse file-attributes JSON: {prop_value}")
        elif prop_type == 'x-xliff-seg-sources':
            try:
                parsed = json.loads(prop_value)
                if isinstance(parsed, list):
                    metadata['seg_sources'] = [str(x) for x in parsed if x is not None]
                elif isinstance(parsed, str) and parsed.strip():
                    metadata['seg_sources'] = [parsed]
            except (json.JSONDecodeError, TypeError, ValueError):
                logger.warning(f"Could not parse seg-sources JSON: {prop_value}")
        elif prop_type == 'x-xliff-source-markup':
            dec = decode_xliff_markup_from_tmx_prop(prop_value)
            if dec:
                metadata['source_markup_xml'] = dec
        elif prop_type == 'x-xliff-target-markup':
            dec = decode_xliff_markup_from_tmx_prop(prop_value)
            if dec:
                metadata['target_markup_xml'] = dec
        elif prop_type.startswith('x-xliff-source-'):
            # Restore original attribute name (underscores were used to replace colons/spaces)
            attr_name = prop_type.replace('x-xliff-source-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            source_attrs[attr_name] = prop_value
        elif prop_type.startswith('x-xliff-target-'):
            attr_name = prop_type.replace('x-xliff-target-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            target_attrs[attr_name] = prop_value
        elif prop_type.startswith('x-xliff-segment-'):
            attr_name = prop_type.replace('x-xliff-segment-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            segment_attrs[attr_name] = prop_value
        else:
            # Regular attribute - restore original key name
            key = prop_type.replace('x-xliff-', '').replace('_COLON_', ':').replace('_SPACE_', ' ')
            metadata[key] = prop_value
    
    if source_attrs:
        metadata['source_attributes'] = source_attrs
    if target_attrs:
        metadata['target_attributes'] = target_attrs
    if segment_attrs:
        metadata['segment_attributes'] = segment_attrs
    
    return metadata


def _file_attributes_group_key(tu: PythonTmx.Tu) -> str:
    """Stable key for grouping TUs that shared the same original XLIFF <file> attributes."""
    md = get_tu_metadata(tu)
    fa = md.get('file_attributes') or {}
    return json.dumps(fa, sort_keys=True, ensure_ascii=False)


def _infer_target_lang_from_tus(tus: List[PythonTmx.Tu], header_srclang: str) -> str:
    target_lang = header_srclang
    if tus and len(tus[0].tuvs) > 1:
        for tuv in tus[0].tuvs:
            if tuv.lang != header_srclang:
                target_lang = tuv.lang
                break
    return target_lang


def _create_xliff12_file_with_body(
    xliff: etree.Element,
    tmx: PythonTmx.Tmx,
    tus_in_file: List[PythonTmx.Tu],
) -> etree.Element:
    """Add a <file> element with preserved attributes and return its <body>."""
    file_attrs = {}
    if tus_in_file:
        file_attrs = get_tu_metadata(tus_in_file[0]).get('file_attributes') or {}

    file_elem = etree.SubElement(xliff, 'file')
    for attr_name, attr_value in file_attrs.items():
        if attr_value is not None and str(attr_value) != '':
            file_elem.set(str(attr_name), str(attr_value))

    if not file_elem.get('source-language'):
        file_elem.set('source-language', tmx.header.srclang)

    target_lang = _infer_target_lang_from_tus(tus_in_file, tmx.header.srclang)
    if not file_elem.get('target-language'):
        file_elem.set('target-language', target_lang)

    if not file_elem.get('datatype'):
        file_elem.set('datatype', str(tmx.header.datatype))

    if not file_elem.get('original'):
        file_elem.set('original', 'converted_from_tmx')

    return etree.SubElement(file_elem, 'body')


def _append_trans_unit_xliff12(body: etree.Element, tu: PythonTmx.Tu, tmx: PythonTmx.Tmx) -> None:
    """Append one <trans-unit> under <body> from a TMX TU (XLIFF 1.2)."""
    trans_unit = etree.SubElement(body, 'trans-unit')

    metadata = get_tu_metadata(tu)

    for key, value in metadata.items():
        if key not in [
            'id', 'source_attributes', 'target_attributes', 'contexts', 'context_groups',
            'alt_trans', 'notes', 'props', 'file_attributes', 'segment_attributes', 'seg_sources',
            'source_markup_xml', 'target_markup_xml',
        ]:
            if value:
                trans_unit.set(key, str(value))

    if not trans_unit.get('id'):
        trans_unit.set('id', metadata.get('id', ''))

    source_tuv = None
    target_tuvs = []
    source_lang = tmx.header.srclang

    for tuv in tu.tuvs:
        tuv_lang = tuv.lang.lower().replace('_', '-')
        src_lang_norm = source_lang.lower().replace('_', '-')

        if tuv_lang == src_lang_norm or tuv_lang.startswith(src_lang_norm.split('-')[0]):
            source_tuv = tuv
        else:
            target_tuvs.append(tuv)

    target_tuv = target_tuvs[0] if target_tuvs else None

    if metadata.get('source_markup_xml'):
        try:
            s = normalize_xliff_inline_fragment_xml(metadata['source_markup_xml'], 'source')
            trans_unit.append(etree.fromstring(s))
        except etree.XMLSyntaxError as e:
            logger.warning(f"Could not parse stored source markup, using plain text: {e}")
            if source_tuv:
                source_elem = etree.SubElement(trans_unit, 'source')
                source_elem.text = _tuv_content_plain(source_tuv.content)
                if 'source_attributes' in metadata:
                    for attr_name, attr_value in metadata['source_attributes'].items():
                        source_elem.set(attr_name, str(attr_value))
            else:
                etree.SubElement(trans_unit, 'source')
    elif source_tuv:
        source_elem = etree.SubElement(trans_unit, 'source')
        source_elem.text = _tuv_content_plain(source_tuv.content)
        if 'source_attributes' in metadata:
            for attr_name, attr_value in metadata['source_attributes'].items():
                source_elem.set(attr_name, str(attr_value))
    else:
        etree.SubElement(trans_unit, 'source')

    # Restore <seg-source> after <source>, before <target> (XLIFF 1.2 segmentation)
    if metadata.get('seg_sources'):
        for xml_str in metadata['seg_sources']:
            if not (xml_str and str(xml_str).strip()):
                continue
            try:
                s = normalize_seg_source_storage_xml(str(xml_str).strip())
                frag = etree.fromstring(s)
                trans_unit.append(frag)
            except etree.XMLSyntaxError as e:
                logger.warning(f"Could not parse stored seg-source fragment: {e}")

    if metadata.get('target_markup_xml'):
        try:
            t = normalize_xliff_inline_fragment_xml(metadata['target_markup_xml'], 'target')
            trans_unit.append(etree.fromstring(t))
        except etree.XMLSyntaxError as e:
            logger.warning(f"Could not parse stored target markup, using plain text: {e}")
            if target_tuv:
                target_elem = etree.SubElement(trans_unit, 'target')
                target_elem.text = _tuv_content_plain(target_tuv.content)
                if 'target_attributes' in metadata:
                    for attr_name, attr_value in metadata['target_attributes'].items():
                        target_elem.set(attr_name, str(attr_value))
            else:
                etree.SubElement(trans_unit, 'target')
    elif metadata.get('source_markup_xml') and target_tuv:
        t_plain = _tuv_content_plain(target_tuv.content)
        try:
            built = build_target_element_mirroring_source_markup(metadata['source_markup_xml'], t_plain)
            trans_unit.append(built)
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    built.set(attr_name, str(attr_value))
        except (etree.XMLSyntaxError, ValueError) as e:
            logger.warning(f"Could not mirror source markup onto target, using plain text: {e}")
            target_elem = etree.SubElement(trans_unit, 'target')
            target_elem.text = t_plain
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
    elif metadata.get('seg_sources') and target_tuv:
        t_plain = _tuv_content_plain(target_tuv.content)
        first_seg = (metadata['seg_sources'][0] or '').strip()
        try:
            if first_seg:
                ss_norm = normalize_seg_source_storage_xml(first_seg)
                frag = etree.fromstring(ss_norm)
                if len(frag) > 0:
                    built = build_target_element_mirroring_seg_source(first_seg, t_plain)
                    trans_unit.append(built)
                    if 'target_attributes' in metadata:
                        for attr_name, attr_value in metadata['target_attributes'].items():
                            built.set(attr_name, str(attr_value))
                else:
                    target_elem = etree.SubElement(trans_unit, 'target')
                    target_elem.text = t_plain
                    if 'target_attributes' in metadata:
                        for attr_name, attr_value in metadata['target_attributes'].items():
                            target_elem.set(attr_name, str(attr_value))
            else:
                target_elem = etree.SubElement(trans_unit, 'target')
                target_elem.text = t_plain
                if 'target_attributes' in metadata:
                    for attr_name, attr_value in metadata['target_attributes'].items():
                        target_elem.set(attr_name, str(attr_value))
        except (etree.XMLSyntaxError, ValueError) as e:
            logger.warning(f"Could not mirror seg-source onto target, using plain text: {e}")
            target_elem = etree.SubElement(trans_unit, 'target')
            target_elem.text = t_plain
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
    elif target_tuv:
        target_elem = etree.SubElement(trans_unit, 'target')
        target_elem.text = _tuv_content_plain(target_tuv.content)
        if 'target_attributes' in metadata:
            for attr_name, attr_value in metadata['target_attributes'].items():
                target_elem.set(attr_name, str(attr_value))
    else:
        etree.SubElement(trans_unit, 'target')

    if 'context_groups' in metadata:
        for cg_data in metadata['context_groups']:
            cg_elem = etree.SubElement(trans_unit, 'context-group')
            for attr_name, attr_value in cg_data.items():
                if attr_name != 'contexts' and attr_value:
                    cg_elem.set(attr_name, str(attr_value))

            if 'contexts' in cg_data:
                for context_data in cg_data['contexts']:
                    context_elem = etree.SubElement(cg_elem, 'context')
                    if 'text' in context_data:
                        context_elem.text = context_data['text']
                    for attr_name, attr_value in context_data.items():
                        if attr_name != 'text' and attr_value:
                            context_elem.set(attr_name, str(attr_value))

    if 'contexts' in metadata:
        for context_data in metadata['contexts']:
            context_elem = etree.SubElement(trans_unit, 'context')
            if 'text' in context_data:
                context_elem.text = context_data['text']
            for attr_name, attr_value in context_data.items():
                if attr_name != 'text' and attr_value:
                    context_elem.set(attr_name, str(attr_value))

    if 'props' in metadata:
        for prop_data in metadata['props']:
            prop_elem = etree.SubElement(trans_unit, 'prop')
            if 'text' in prop_data:
                prop_elem.text = prop_data['text']
            for attr_name, attr_value in prop_data.items():
                if attr_name != 'text' and attr_value:
                    prop_elem.set(attr_name, str(attr_value))

    if 'alt_trans' in metadata:
        for alt_trans_data in metadata['alt_trans']:
            alt_trans_elem = etree.SubElement(trans_unit, 'alt-trans')
            for attr_name, attr_value in alt_trans_data.items():
                if attr_name not in ['source', 'target'] and attr_value:
                    alt_trans_elem.set(attr_name, str(attr_value))
            if 'source' in alt_trans_data:
                alt_source = etree.SubElement(alt_trans_elem, 'source')
                alt_source.text = alt_trans_data['source']
            if 'target' in alt_trans_data:
                alt_target = etree.SubElement(alt_trans_elem, 'target')
                alt_target.text = alt_trans_data['target']

    for note in tu.notes:
        note_elem = etree.SubElement(trans_unit, 'note')
        note_text = None
        if hasattr(note, 'content') and note.content:
            note_text = note.content
        elif hasattr(note, 'text') and note.text:
            note_text = note.text
        if note_text:
            note_elem.text = note_text
        if hasattr(note, 'lang') and note.lang:
            note_elem.set(f'{{{XML_NS}}}lang', note.lang)


def create_xliff12_document(tmx: PythonTmx.Tmx, output_path: str):
    """
    Create XLIFF 1.2 document from TMX.
    
    Args:
        tmx: TMX object
        output_path: Output file path
    """
    xliff = etree.Element('xliff', version='1.2')
    xliff.set('xmlns', 'urn:oasis:names:tc:xliff:document:1.2')

    sorted_tus = sorted(tmx.tus, key=_file_attributes_group_key)
    for _, group_iter in groupby(sorted_tus, key=_file_attributes_group_key):
        tus_group = list(group_iter)
        body = _create_xliff12_file_with_body(xliff, tmx, tus_group)
        for tu in tus_group:
            _append_trans_unit_xliff12(body, tu, tmx)

    tree = etree.ElementTree(xliff)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


def _create_xliff20_file_element(
    xliff: etree.Element,
    tmx: PythonTmx.Tmx,
    tus_in_file: List[PythonTmx.Tu],
    file_index: int,
) -> etree.Element:
    """Add one namespaced XLIFF 2.x <file> with preserved attributes; return the element for <unit> children."""
    file_attrs = {}
    if tus_in_file:
        file_attrs = get_tu_metadata(tus_in_file[0]).get('file_attributes') or {}

    file_elem = etree.SubElement(xliff, 'file')
    for attr_name, attr_value in file_attrs.items():
        if attr_value is not None and str(attr_value) != '':
            file_elem.set(str(attr_name), str(attr_value))

    if not file_elem.get('source-language'):
        file_elem.set('source-language', tmx.header.srclang)

    target_lang = _infer_target_lang_from_tus(tus_in_file, tmx.header.srclang)
    if not file_elem.get('target-language'):
        file_elem.set('target-language', target_lang)

    if not file_elem.get('id'):
        file_elem.set('id', f'f{file_index}')

    if not file_elem.get('original'):
        file_elem.set('original', 'converted_from_tmx')

    skeleton = etree.SubElement(file_elem, 'skeleton')
    skeleton.set('href', 'skeleton.xml')

    return file_elem


def _append_unit_xliff20(file_elem: etree.Element, tu: PythonTmx.Tu, tmx: PythonTmx.Tmx, unit_counter: int) -> None:
    """Append one <unit> with segment/source/target under a XLIFF 2.x <file>."""
    unit = etree.SubElement(file_elem, 'unit')

    metadata = get_tu_metadata(tu)

    for key, value in metadata.items():
        if key not in (
            'id',
            'name',
            'source_attributes',
            'target_attributes',
            'segment_attributes',
            'contexts',
            'alt_trans',
            'notes',
            'props',
            'file_attributes',
            'context_groups',
            'seg_sources',
            'source_markup_xml',
            'target_markup_xml',
        ):
            if value:
                unit.set(key, str(value))

    if metadata.get('id'):
        unit.set('id', metadata['id'])
    elif metadata.get('name'):
        unit.set('id', metadata['name'])
    else:
        unit.set('id', f'u{unit_counter}')

    if metadata.get('name'):
        unit.set('name', metadata['name'])

    segment = etree.SubElement(unit, 'segment')

    if 'segment_attributes' in metadata:
        for attr_name, attr_value in metadata['segment_attributes'].items():
            segment.set(attr_name, str(attr_value))

    source_tuv = None
    target_tuvs = []
    source_lang = tmx.header.srclang

    for tuv in tu.tuvs:
        tuv_lang = tuv.lang.lower().replace('_', '-')
        src_lang_norm = source_lang.lower().replace('_', '-')

        if tuv_lang == src_lang_norm or tuv_lang.startswith(src_lang_norm.split('-')[0]):
            source_tuv = tuv
        else:
            target_tuvs.append(tuv)

    target_tuv = target_tuvs[0] if target_tuvs else None

    if metadata.get('source_markup_xml'):
        try:
            s = normalize_xliff_inline_fragment_xml(metadata['source_markup_xml'], 'source')
            segment.append(etree.fromstring(s))
        except etree.XMLSyntaxError as e:
            logger.warning(f"Could not parse stored source markup (2.x), using plain text: {e}")
            if source_tuv:
                source_elem = etree.SubElement(segment, 'source')
                source_elem.text = _tuv_content_plain(source_tuv.content)
                if 'source_attributes' in metadata:
                    for attr_name, attr_value in metadata['source_attributes'].items():
                        source_elem.set(attr_name, str(attr_value))
            else:
                etree.SubElement(segment, 'source')
    elif source_tuv:
        source_elem = etree.SubElement(segment, 'source')
        source_elem.text = _tuv_content_plain(source_tuv.content)
        if 'source_attributes' in metadata:
            for attr_name, attr_value in metadata['source_attributes'].items():
                source_elem.set(attr_name, str(attr_value))
    else:
        etree.SubElement(segment, 'source')

    if metadata.get('target_markup_xml'):
        try:
            t = normalize_xliff_inline_fragment_xml(metadata['target_markup_xml'], 'target')
            segment.append(etree.fromstring(t))
        except etree.XMLSyntaxError as e:
            logger.warning(f"Could not parse stored target markup (2.x), using plain text: {e}")
            if target_tuv:
                target_elem = etree.SubElement(segment, 'target')
                target_elem.text = _tuv_content_plain(target_tuv.content)
                if 'target_attributes' in metadata:
                    for attr_name, attr_value in metadata['target_attributes'].items():
                        target_elem.set(attr_name, str(attr_value))
            else:
                etree.SubElement(segment, 'target')
    elif metadata.get('source_markup_xml') and target_tuv:
        t_plain = _tuv_content_plain(target_tuv.content)
        try:
            built = build_target_element_mirroring_source_markup(metadata['source_markup_xml'], t_plain)
            segment.append(built)
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    built.set(attr_name, str(attr_value))
        except (etree.XMLSyntaxError, ValueError) as e:
            logger.warning(f"Could not mirror source markup onto target (2.x), using plain text: {e}")
            target_elem = etree.SubElement(segment, 'target')
            target_elem.text = t_plain
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
    elif metadata.get('seg_sources') and target_tuv:
        t_plain = _tuv_content_plain(target_tuv.content)
        first_seg = (metadata['seg_sources'][0] or '').strip()
        try:
            if first_seg:
                ss_norm = normalize_seg_source_storage_xml(first_seg)
                frag = etree.fromstring(ss_norm)
                if len(frag) > 0:
                    built = build_target_element_mirroring_seg_source(first_seg, t_plain)
                    segment.append(built)
                    if 'target_attributes' in metadata:
                        for attr_name, attr_value in metadata['target_attributes'].items():
                            built.set(attr_name, str(attr_value))
                else:
                    target_elem = etree.SubElement(segment, 'target')
                    target_elem.text = t_plain
                    if 'target_attributes' in metadata:
                        for attr_name, attr_value in metadata['target_attributes'].items():
                            target_elem.set(attr_name, str(attr_value))
            else:
                target_elem = etree.SubElement(segment, 'target')
                target_elem.text = t_plain
                if 'target_attributes' in metadata:
                    for attr_name, attr_value in metadata['target_attributes'].items():
                        target_elem.set(attr_name, str(attr_value))
        except (etree.XMLSyntaxError, ValueError) as e:
            logger.warning(f"Could not mirror seg-source onto target (2.x), using plain text: {e}")
            target_elem = etree.SubElement(segment, 'target')
            target_elem.text = t_plain
            if 'target_attributes' in metadata:
                for attr_name, attr_value in metadata['target_attributes'].items():
                    target_elem.set(attr_name, str(attr_value))
    elif target_tuv:
        target_elem = etree.SubElement(segment, 'target')
        target_elem.text = _tuv_content_plain(target_tuv.content)
        if 'target_attributes' in metadata:
            for attr_name, attr_value in metadata['target_attributes'].items():
                target_elem.set(attr_name, str(attr_value))
    else:
        etree.SubElement(segment, 'target')

    if 'contexts' in metadata:
        for context_data in metadata['contexts']:
            context_elem = etree.SubElement(unit, 'context')
            if 'text' in context_data:
                context_elem.text = context_data['text']
            for attr_name, attr_value in context_data.items():
                if attr_name != 'text' and attr_value:
                    context_elem.set(attr_name, str(attr_value))

    for note in tu.notes:
        note_elem = etree.SubElement(unit, 'note')
        note_text = None
        if hasattr(note, 'content') and note.content:
            note_text = note.content
        elif hasattr(note, 'text') and note.text:
            note_text = note.text
        if note_text:
            note_elem.text = note_text
        if hasattr(note, 'category') and note.category:
            note_elem.set('category', note.category)
        if hasattr(note, 'lang') and note.lang:
            note_elem.set(f'{{{XML_NS}}}lang', note.lang)


def create_xliff20_document(tmx: PythonTmx.Tmx, output_path: str, version: str = '2.0'):
    """
    Create XLIFF 2.0 or 2.2 document from TMX.
    
    Args:
        tmx: TMX object
        output_path: Output file path
        version: XLIFF version ('2.0' or '2.2')
    """
    namespace = XLIFF_20_NS if version == '2.0' else XLIFF_22_NS

    xliff = etree.Element('xliff', version=version, nsmap={None: namespace})

    sorted_tus = sorted(tmx.tus, key=_file_attributes_group_key)
    file_index = 0
    for _, group_iter in groupby(sorted_tus, key=_file_attributes_group_key):
        tus_group = list(group_iter)
        file_index += 1
        file_elem = _create_xliff20_file_element(xliff, tmx, tus_group, file_index)
        unit_counter = 0
        for tu in tus_group:
            unit_counter += 1
            _append_unit_xliff20(file_elem, tu, tmx, unit_counter)

    tree = etree.ElementTree(xliff)
    tree.write(output_path, encoding='utf-8', xml_declaration=True, pretty_print=True)


def tmx_to_xliff(tmx_file: str, output_file: Optional[str] = None, xliff_version: Optional[str] = None) -> str:
    """
    Convert TMX file to XLIFF format.
    
    Args:
        tmx_file: Path to TMX file
        output_file: Optional output XLIFF file path. If None, creates based on input filename.
        xliff_version: Optional XLIFF version ('1.2', '2.0', or '2.2'). 
                      If None, tries to detect from TMX metadata.
        
    Returns:
        str: Path to created XLIFF file
    """
    logger.info(f"Converting TMX to XLIFF: {tmx_file}")
    
    try:
        input_path = Path(tmx_file)
        
        if not input_path.exists():
            raise FileNotFoundError(f"TMX file not found: {tmx_file}")
        
        # Always parse XML directly to ensure we get ALL TUs (PythonTmx may filter some)
        tmx_tree = etree.parse(str(input_path))
        tmx_root = tmx_tree.getroot()
        
        # Header / body (namespace-agnostic — some TMX files use a default xmlns)
        header_elem = None
        body_elem = None
        for ch in tmx_root:
            if not isinstance(ch.tag, str):
                continue
            ln = local_name(ch.tag)
            if ln == 'header':
                header_elem = ch
            elif ln == 'body':
                body_elem = ch
        if header_elem is None:
            raise ValueError("No header element found in TMX file")
        
        # Create minimal header
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
        
        minimal_header = PythonTmx.Header(
            creationtool=header_attrs.get('creationtool', 'Unknown'),
            creationtoolversion=header_attrs.get('creationtoolversion', '1.0'),
            adminlang=header_attrs.get('adminlang', 'en'),
            srclang=header_attrs.get('srclang', 'en'),
            segtype=segtype_enum,
            datatype=header_attrs.get('datatype', 'xml'),
            tmf="tmx",
            encoding="utf8"
        )
        
        # Parse TUs - preserve ALL TUs including those with empty targets
        tus = []
        if body_elem is not None:
            for tu_elem in children_by_local(body_elem, 'tu'):
                tu = PythonTmx.Tu()
                
                # Copy all TU attributes
                for attr_name, attr_value in tu_elem.attrib.items():
                    try:
                        if attr_name == 'srclang':
                            tu.srclang = attr_value
                        # Add other TU attributes as needed
                    except Exception:
                        pass
                
                # Parse all TUVs (including empty ones)
                for tuv_elem in children_by_local(tu_elem, 'tuv'):
                    lang = tuv_elem.get(f'{{{XML_NS}}}lang')
                    if not lang:
                        lang = 'en'
                    seg_elems = children_by_local(tuv_elem, 'seg')
                    seg_elem = seg_elems[0] if seg_elems else None
                    
                    # Always create TUV, even if empty
                    tuv = PythonTmx.Tuv(lang=lang)
                    if seg_elem is not None:
                        tuv.content = element_inner_text(seg_elem)
                    else:
                        tuv.content = ''
                    tu.tuvs.append(tuv)
                
                # Properties: use full text (CDATA / split nodes); do not drop empty body
                for prop_elem in children_by_local(tu_elem, 'prop'):
                    prop_type = prop_elem.get('type', '')
                    prop_text = prop_inner_text(prop_elem)
                    if prop_type:
                        tu.props.append(PythonTmx.Prop(type=prop_type, text=prop_text))
                
                for note_elem in children_by_local(tu_elem, 'note'):
                    note_text = element_inner_text(note_elem)
                    if note_text:
                        note = PythonTmx.Note(text=note_text)
                        note_lang = note_elem.get(f'{{{XML_NS}}}lang', '')
                        if note_lang:
                            note.lang = note_lang
                        tu.notes.append(note)
                
                # Add TU even if it only has source (empty targets are valid in XLIFF)
                if len(tu.tuvs) >= 1:
                    tus.append(tu)
        
        tmx = PythonTmx.Tmx(header=minimal_header, tus=tus)
        logger.info(f"Loaded {len(tus)} translation units from TMX file")
        
        # Determine XLIFF version
        if xliff_version is None:
            xliff_version = get_xliff_version_from_tmx(tmx)
            
            # If version still not found, try extracting from XML directly
            if xliff_version == '1.2':
                # Try to find the note in the XML directly
                hr = tmx_tree.getroot()
                header_elem2 = None
                for ch in hr:
                    if isinstance(ch.tag, str) and local_name(ch.tag) == 'header':
                        header_elem2 = ch
                        break
                if header_elem2 is not None:
                    for note_elem in children_by_local(header_elem2, 'note'):
                        note_text = element_inner_text(note_elem)
                        if 'Original XLIFF version' in note_text:
                            version = note_text.split(':')[-1].strip()
                            if version in ['1.2', '2.0', '2.2']:
                                logger.info(f"Found original XLIFF version from XML note: {version}")
                                xliff_version = version
                                break
        
        logger.info(f"Using XLIFF version: {xliff_version}")
        
        # Determine output path
        if output_file is None:
            output_path = input_path.parent / f"{input_path.stem}.xlf"
        else:
            output_path = Path(output_file)
        
        # Create XLIFF document based on version
        if xliff_version == '1.2':
            create_xliff12_document(tmx, str(output_path))
        elif xliff_version in ['2.0', '2.2']:
            create_xliff20_document(tmx, str(output_path), xliff_version)
        else:
            raise ValueError(f"Unsupported XLIFF version: {xliff_version}")
        
        logger.info(f"Converted {len(tmx.tus)} translation units to XLIFF {xliff_version}: {output_path}")
        return str(output_path)
        
    except Exception as e:
        logger.error(f"Error converting TMX to XLIFF: {e}")
        raise


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    
    tmx_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    xliff_version = sys.argv[3] if len(sys.argv) > 3 else None
    
    try:
        xliff_path = tmx_to_xliff(tmx_file, output_file, xliff_version)
        print(f"Successfully converted TMX to XLIFF: {xliff_path}")
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(1)


"""Helpers for preserving XLIFF inline fragments (seg-source, source, target) without redundant xmlns noise."""

import re
from copy import deepcopy
import lxml.etree as etree

_XMLNS_ATT = 'http://www.w3.org/2000/xmlns/'


def strip_fragment_root_xmlns(elem: etree.ElementBase) -> None:
    """
    Remove xmlns / xmlns:* from the element's attrib (lxml sometimes exposes them here).
    Default namespace on the root often lives only in nsmap; tostring still prints it unless
    we strip the opening tag textually — see strip_xmlns_from_inline_element_opening.
    """
    for k in list(elem.attrib.keys()):
        if k == 'xmlns' or k.startswith('xmlns:') or k.startswith(f'{{{_XMLNS_ATT}}}'):
            del elem.attrib[k]


def strip_xmlns_from_inline_element_opening(xml: str, tag: str) -> str:
    """
    Remove all xmlns / xmlns:* declarations from the opening <tag ...> or <tag .../> only.
    tag must be a simple local name (e.g. seg-source, source, target).
    """
    xml = xml.lstrip('\ufeff').strip()
    open_tag = f'<{tag}'
    if not xml.startswith(open_tag):
        return xml

    i = len(open_tag)
    n = len(xml)
    in_dq = in_sq = False
    while i < n:
        c = xml[i]
        if c == '"' and not in_sq:
            in_dq = not in_dq
        elif c == "'" and not in_dq:
            in_sq = not in_sq
        elif not in_dq and not in_sq:
            if c == '/' and i + 1 < n and xml[i + 1] == '>':
                attr_blob = xml[len(open_tag) : i]
                rest = xml[i:]
                break
            if c == '>':
                attr_blob = xml[len(open_tag) : i]
                rest = xml[i:]
                break
        i += 1
    else:
        return xml

    ab = _strip_xmlns_attribute_blob(attr_blob).strip()
    if ab:
        return f'<{tag} {ab}{rest}'
    return f'<{tag}{rest}'


def strip_xmlns_from_seg_source_markup(xml: str) -> str:
    """Backward-compatible name for seg-source opening-tag xmlns strip."""
    return strip_xmlns_from_inline_element_opening(xml, 'seg-source')


def _strip_xmlns_attribute_blob(blob: str) -> str:
    """Remove every xmlns / xmlns:* attribute from a fragment of XML attribute text."""
    b = blob.strip()
    start_pat = r'^\s*xmlns(?::[a-zA-Z0-9_.-]+)?\s*=\s*(?:"[^"]*"|\'[^\']*\')\s*'
    rest_pat = r'\s+xmlns(?::[a-zA-Z0-9_.-]+)?\s*=\s*(?:"[^"]*"|\'[^\']*\')'
    while True:
        nb = re.sub(start_pat, '', b)
        nb = re.sub(rest_pat, '', nb)
        nb = nb.strip()
        if nb == b:
            break
        b = nb
    return b


def normalize_xliff_inline_fragment_xml(xml_unicode: str, root_tag: str) -> str:
    """
    Parse optional round-trip, strip attrib xmlns, strip opening-tag xmlns on root_tag, re-serialize.
    root_tag: 'seg-source' | 'source' | 'target'
    """
    xml_unicode = xml_unicode.lstrip('\ufeff').strip()
    if not xml_unicode:
        return xml_unicode
    try:
        frag = etree.fromstring(xml_unicode)
    except etree.XMLSyntaxError:
        return strip_xmlns_from_inline_element_opening(xml_unicode, root_tag)
    strip_fragment_root_xmlns(frag)
    raw = etree.tostring(frag, encoding='unicode', with_tail=False)
    return strip_xmlns_from_inline_element_opening(raw, root_tag)


def normalize_seg_source_storage_xml(xml_unicode: str) -> str:
    """Preserve <seg-source> for TMX round-trip without redundant xmlns on the element."""
    return normalize_xliff_inline_fragment_xml(xml_unicode, 'seg-source')


def element_has_inline_markup(elem: etree.ElementBase) -> bool:
    """True if element has child elements (e.g. mrk, bpt) — worth preserving full XML."""
    return elem is not None and len(elem) > 0


def build_target_mirroring_inline_root(
    markup_xml: str,
    template_root_tag: str,
    target_plain: str,
) -> etree.ElementBase:
    """
    Build a <target> whose child tree matches <source> or <seg-source> (same mrk layout).
    template_root_tag: 'source' | 'seg-source'
    Full target text goes in the first leaf in document order (same rule as CAT plain targets).
    """
    s = normalize_xliff_inline_fragment_xml(markup_xml, template_root_tag)
    root = etree.fromstring(s)
    if etree.QName(root).localname != template_root_tag:
        raise ValueError(f'expected <{template_root_tag}> root, got {etree.QName(root).localname!r}')

    q = etree.QName(root)
    ns = q.namespace
    tag = f'{{{ns}}}target' if ns else 'target'
    tgt = etree.Element(tag)
    for k, v in root.attrib.items():
        tgt.set(k, v)
    for c in root:
        tgt.append(deepcopy(c))

    for el in tgt.iter():
        el.text = None
        el.tail = None

    plain = target_plain if target_plain is not None else ''
    first_leaf = None
    for el in tgt.iter():
        if len(el) == 0:
            first_leaf = el
            break
    if first_leaf is not None:
        first_leaf.text = plain
    elif plain:
        tgt.text = plain
    return tgt


def build_target_element_mirroring_source_markup(source_markup_xml: str, target_plain: str) -> etree.ElementBase:
    """When <source> had inline markup but <target> was plain — same tree as <source>."""
    return build_target_mirroring_inline_root(source_markup_xml, 'source', target_plain)


def build_target_element_mirroring_seg_source(seg_source_xml: str, target_plain: str) -> etree.ElementBase:
    """Okapi-style: <seg-source> has <mrk>, <target> is plain — same tree as <seg-source>."""
    return build_target_mirroring_inline_root(seg_source_xml, 'seg-source', target_plain)

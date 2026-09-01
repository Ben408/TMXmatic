"""XLIFF leverage and validation — exact TMX match into empty targets."""

from __future__ import annotations

import logging
import os
import re
from typing import Dict, Tuple

from lxml import etree

logger = logging.getLogger(__name__)

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _norm_lang(code: str | None) -> str:
    return (code or "").strip().lower().replace("-", "_")


def _lang_matches(actual: str, expected: str) -> bool:
    """Match BCP47 variants: en_us ~ en-us ~ en."""
    a = _norm_lang(actual)
    e = _norm_lang(expected)
    if not a or not e:
        return False
    if a == e:
        return True
    a_base = a.split("_")[0]
    e_base = e.split("_")[0]
    return a_base == e_base and (a == e or e.startswith(a_base))


def _element_text(elem: etree._Element | None) -> str:
    if elem is None:
        return ""
    return "".join(elem.itertext()).strip()


def _collapse_ws(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def build_tmx_lookup(
    tmx_path: str,
    *,
    source_lang: str,
    target_lang: str,
) -> tuple[dict[str, str], int]:
    """Build exact source→target map from TMX for the requested language pair."""
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    root = etree.parse(tmx_path, parser).getroot()
    lookup: dict[str, str] = {}
    tu_count = 0

    for tu in root.findall(".//{*}tu"):
        by_lang: dict[str, str] = {}
        for tuv in tu.findall(".//{*}tuv"):
            lang = tuv.get(_XML_LANG) or tuv.get("lang") or ""
            seg = tuv.find(".//{*}seg")
            if seg is None:
                continue
            text = _element_text(seg)
            if text:
                by_lang[_norm_lang(lang)] = text

        src_text = None
        tgt_text = None
        for lang, text in by_lang.items():
            if _lang_matches(lang, source_lang) and src_text is None:
                src_text = text
        for lang, text in by_lang.items():
            if _lang_matches(lang, target_lang) and tgt_text is None:
                tgt_text = text

        if src_text and tgt_text:
            lookup[src_text] = tgt_text
            lookup[_collapse_ws(src_text)] = tgt_text
            tu_count += 1

    logger.info(
        "TMX lookup: %s TU pairs for %s → %s (%s unique keys)",
        tu_count,
        source_lang,
        target_lang,
        len(lookup),
    )
    return lookup, tu_count


def _target_needs_leverage(source_text: str, target_text: str) -> bool:
    """True when target is empty or still an untranslated copy of the source."""
    if not target_text:
        return True
    if source_text == target_text:
        return True
    return _collapse_ws(source_text) == _collapse_ws(target_text)


def _xliff_langs(root: etree._Element) -> tuple[str, str]:
    """Infer source/target langs from XLIFF 1.2 or 2.0 root."""
    src = root.get("source-language") or root.get("srcLang") or "en"
    tgt = root.get("target-language") or root.get("trgLang") or ""
    file_el = root.find(".//{*}file")
    if file_el is not None:
        src = file_el.get("source-language") or file_el.get("sourceLanguage") or src
        tgt = file_el.get("target-language") or file_el.get("targetLanguage") or tgt
    if not tgt or _norm_lang(tgt) in {"und", "zxx"}:
        for tu in root.findall(".//{*}trans-unit"):
            tgt_el = tu.find(".//{*}target")
            if tgt_el is not None:
                candidate = tgt_el.get(_XML_LANG) or tgt_el.get("xml:lang") or ""
                if candidate and _norm_lang(candidate) not in {"und", "zxx"}:
                    tgt = candidate
                    break
    return src, tgt or src


def _iter_xliff_segments(root: etree._Element):
    """Yield (source_elem, target_elem) for XLIFF 1.2 trans-units and 2.0 units."""
    # XLIFF 1.2
    for tu in root.findall(".//{*}trans-unit"):
        src = tu.find(".//{*}source")
        tgt = tu.find(".//{*}target")
        if src is not None:
            if tgt is None:
                tgt = etree.SubElement(tu, "target")
            yield src, tgt

    # XLIFF 2.0
    for unit in root.findall(".//{*}unit"):
        src = unit.find(".//{*}source")
        tgt = unit.find(".//{*}target")
        if src is not None:
            if tgt is None:
                seg = unit.find(".//{*}segment")
                parent = seg if seg is not None else unit
                tgt = etree.SubElement(parent, "target")
            yield src, tgt


def leverage_tmx_into_xliff(
    tmx_file: str,
    xliff_file: str,
    *,
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> Tuple[str, Dict[str, int]]:
    """Fill empty XLIFF targets from exact TMX source matches (100% only)."""
    try:
        logger.info("Leveraging TMX %s into XLIFF %s", tmx_file, xliff_file)
        parser = etree.XMLParser(recover=True, remove_blank_text=False)
        xliff_tree = etree.parse(xliff_file, parser)
        root = xliff_tree.getroot()

        inferred_src, inferred_tgt = _xliff_langs(root)
        src_lang = source_lang or inferred_src
        tgt_lang = target_lang or inferred_tgt

        lookup, translation_count = build_tmx_lookup(
            tmx_file, source_lang=src_lang, target_lang=tgt_lang
        )

        updates_made = 0
        empty_segments = 0
        total_segments = 0

        for src_el, tgt_el in _iter_xliff_segments(root):
            total_segments += 1
            src_text = _element_text(src_el)
            tgt_text = _element_text(tgt_el)
            if not _target_needs_leverage(src_text, tgt_text):
                continue
            empty_segments += 1
            hit = lookup.get(src_text) or lookup.get(_collapse_ws(src_text))
            if hit:
                tgt_el.text = hit
                updates_made += 1
                empty_segments -= 1

        base, ext = os.path.splitext(xliff_file)
        output_file = f"{base}_leveraged{ext or '.xlf'}"
        xliff_tree.write(
            output_file,
            encoding="utf-8",
            xml_declaration=True,
            pretty_print=False,
        )

        stats = {
            "tm_entries": translation_count,
            "updates_made": updates_made,
            "remaining_untranslated": empty_segments,
            "total_segments": total_segments,
            "source_lang": src_lang,
            "target_lang": tgt_lang,
            # Legacy keys consumed by the LDW UI
            "translations_found": translation_count,
            "remaining_empty": empty_segments,
        }
        logger.info("Leverage complete: %s", stats)
        return output_file, stats
    except Exception as exc:
        logger.error("Error in leverage_tmx_into_xliff: %s", exc)
        raise


def check_empty_targets(xliff_file: str) -> Dict[str, int]:
    """Count empty target segments in XLIFF 1.2 or 2.0."""
    try:
        parser = etree.XMLParser(recover=True)
        root = etree.parse(xliff_file, parser).getroot()
        empty_count = 0
        total_segments = 0
        for src_el, tgt_el in _iter_xliff_segments(root):
            total_segments += 1
            if not _element_text(tgt_el):
                empty_count += 1
        rate = round((total_segments - empty_count) / total_segments * 100, 2) if total_segments else 0.0
        stats = {
            "total_segments": total_segments,
            "empty_segments": empty_count,
            "completion_rate": rate,
        }
        logger.info("XLIFF check: %s", stats)
        return stats
    except Exception as exc:
        logger.error("Error in check_empty_targets: %s", exc)
        raise

"""Standalone language retagging for XLIFF and TMX (TMS migration).

XLIFF: only file-level ``source-language`` / ``target-language`` (and XLIFF 2.0
``srcLang`` / ``trgLang``) declarations — never inside ``seg``, ``prop``, etc.

TMX: header ``srclang`` / ``adminlang`` plus positional ``tuv`` ``xml:lang`` on
direct children of each ``tu`` (first = source, second = target). Optional per-lang
mappings for multilingual TMs. Never regex the whole file.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from typing import Any

from lxml import etree

logger = logging.getLogger(__name__)

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def _local_name(tag: str | bytes) -> str:
    if not isinstance(tag, str):
        return ""
    return etree.QName(tag).localname


def _norm_lang(code: str | None) -> str:
    return (code or "").strip().lower().replace("-", "_")


def _lang_matches(actual: str | None, expected: str | None) -> bool:
    """Match BCP47-ish tags for find/replace (en_us ~ en-US ~ en)."""
    a = _norm_lang(actual)
    e = _norm_lang(expected)
    if not a or not e:
        return False
    if a == e:
        return True
    a_base = a.split("_")[0]
    e_base = e.split("_")[0]
    return a_base == e_base and (a == e or e.startswith(a_base))


def _direct_children(parent: etree._Element, local: str) -> list[etree._Element]:
    return [c for c in parent if isinstance(c.tag, str) and _local_name(c.tag) == local]


@dataclass
class LangRetagResult:
    output_path: str
    changes: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "output_path": self.output_path,
            "changes": self.changes,
            "warnings": self.warnings,
        }


def _write_tree(tree: etree._ElementTree, path: str) -> None:
    tree.write(
        path,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=False,
    )


def retag_xliff_languages(
    input_path: str,
    *,
    source_lang: str | None = None,
    target_lang: str | None = None,
    output_path: str | None = None,
) -> LangRetagResult:
    """Update XLIFF file-level language declarations only.

    Touches ``<file>`` attributes:
    - XLIFF 1.2: ``source-language``, ``target-language``
    - XLIFF 2.0: ``srcLang``, ``trgLang`` (and common camelCase variants)

    Does **not** modify ``seg``, inline markup, ``prop``, or segment ``xml:lang``.
    """
    if not source_lang and not target_lang:
        raise ValueError("At least one of source_lang or target_lang is required")

    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()
    changes: list[dict[str, Any]] = []

    file_attr_map: list[tuple[str, str | None]] = [
        ("source-language", source_lang),
        ("target-language", target_lang),
        ("sourceLanguage", source_lang),
        ("targetLanguage", target_lang),
        ("srcLang", source_lang),
        ("trgLang", target_lang),
    ]

    for file_el in root.iter():
        if _local_name(file_el.tag) != "file":
            continue
        for attr, new_value in file_attr_map:
            if not new_value or attr not in file_el.attrib:
                continue
            old = file_el.get(attr)
            if old == new_value:
                continue
            file_el.set(attr, new_value)
            changes.append(
                {
                    "element": "file",
                    "attribute": attr,
                    "old": old,
                    "new": new_value,
                }
            )

    dest = output_path or _default_output_path(input_path, suffix="_retagged")
    if output_path is None and dest != input_path:
        shutil.copy2(input_path, dest)
    _write_tree(tree, dest)
    logger.info("XLIFF lang retag: %s change(s) → %s", len(changes), dest)
    return LangRetagResult(output_path=dest, changes=changes)


def retag_tmx_languages(
    input_path: str,
    *,
    source_find: str | None = None,
    source_replace: str | None = None,
    target_find: str | None = None,
    target_replace: str | None = None,
    tuv_mappings: dict[str, str] | None = None,
    output_path: str | None = None,
) -> LangRetagResult:
    """Retag TMX header and positional ``tuv`` languages without touching segment text.

    **Positional mode** (typical bilingual TMX):
    - ``source_find`` / ``source_replace``: header ``srclang`` & ``adminlang`` when they
      match find; first direct-child ``tuv`` of each ``tu`` when its ``xml:lang`` matches.
    - ``target_find`` / ``target_replace``: second direct-child ``tuv`` only.

    **Multilingual mode** (``tuv_mappings``):
    - Dict of old→new language codes applied only to ``xml:lang`` on direct-child
      ``tuv`` elements (any position) and header ``srclang`` / ``adminlang`` when matched.
    - Use when migrating e.g. ``de``→``de-DE``, ``fr``→``fr-FR``, ``es``→``es-419``.

    Never modifies ``seg``, ``prop`` bodies, or ``xml:lang`` outside header / ``tuv``.
    """
    has_pair = (source_find and source_replace) or (target_find and target_replace)
    if not has_pair and not tuv_mappings:
        raise ValueError(
            "Provide source_find/source_replace, target_find/target_replace, or tuv_mappings"
        )

    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(input_path, parser)
    root = tree.getroot()
    changes: list[dict[str, Any]] = []
    warnings: list[str] = []

    header = next((el for el in root.iter() if _local_name(el.tag) == "header"), None)
    if header is not None:
        for attr in ("srclang", "adminlang"):
            old = header.get(attr)
            if not old:
                continue
            new_val = _resolve_tmx_header_replacement(
                old,
                source_find=source_find,
                source_replace=source_replace,
                tuv_mappings=tuv_mappings,
            )
            if new_val and new_val != old:
                header.set(attr, new_val)
                changes.append({"element": "header", "attribute": attr, "old": old, "new": new_val})

    body = next((el for el in root.iter() if _local_name(el.tag) == "body"), None)
    if body is None:
        warnings.append("TMX has no <body>; header-only changes applied")
    else:
        for tu_index, tu in enumerate(_direct_children(body, "tu")):
            tuvs = _direct_children(tu, "tuv")
            if not tuvs:
                continue
            if len(tuvs) < 2:
                warnings.append(f"tu[{tu_index}] has fewer than 2 tuv children; target slot skipped")

            for slot, tuv in enumerate(tuvs):
                old_lang = tuv.get(_XML_LANG) or tuv.get("lang")
                if not old_lang:
                    continue
                new_lang = _resolve_tmx_tuv_replacement(
                    old_lang,
                    slot=slot,
                    source_find=source_find,
                    source_replace=source_replace,
                    target_find=target_find,
                    target_replace=target_replace,
                    tuv_mappings=tuv_mappings,
                )
                if new_lang and new_lang != old_lang:
                    tuv.set(_XML_LANG, new_lang)
                    if "lang" in tuv.attrib:
                        del tuv.attrib["lang"]
                    changes.append(
                        {
                            "element": "tuv",
                            "tu_index": tu_index,
                            "slot": slot,
                            "role": "source" if slot == 0 else "target" if slot == 1 else "extra",
                            "old": old_lang,
                            "new": new_lang,
                        }
                    )

            tu_srclang = tu.get("srclang")
            if tu_srclang:
                new_tu_src = _resolve_tmx_header_replacement(
                    tu_srclang,
                    source_find=source_find,
                    source_replace=source_replace,
                    tuv_mappings=tuv_mappings,
                )
                if new_tu_src and new_tu_src != tu_srclang:
                    tu.set("srclang", new_tu_src)
                    changes.append(
                        {
                            "element": "tu",
                            "tu_index": tu_index,
                            "attribute": "srclang",
                            "old": tu_srclang,
                            "new": new_tu_src,
                        }
                    )

    dest = output_path or _default_output_path(input_path, suffix="_retagged")
    if output_path is None and dest != input_path:
        shutil.copy2(input_path, dest)
    _write_tree(tree, dest)
    logger.info("TMX lang retag: %s change(s) → %s", len(changes), dest)
    return LangRetagResult(output_path=dest, changes=changes, warnings=warnings)


def inspect_xliff_languages(input_path: str) -> dict[str, str]:
    """Return declared file-level language tags (read-only)."""
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    root = etree.parse(input_path, parser).getroot()
    src = tgt = ""
    for file_el in root.iter():
        if _local_name(file_el.tag) != "file":
            continue
        src = (
            file_el.get("source-language")
            or file_el.get("sourceLanguage")
            or file_el.get("srcLang")
            or src
        )
        tgt = (
            file_el.get("target-language")
            or file_el.get("targetLanguage")
            or file_el.get("trgLang")
            or tgt
        )
    return {"source_lang": src, "target_lang": tgt}


def inspect_tmx_languages(input_path: str) -> dict[str, Any]:
    """Return header langs and distinct positional tuv langs (read-only)."""
    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    root = etree.parse(input_path, parser).getroot()
    header = next((el for el in root.iter() if _local_name(el.tag) == "header"), None)
    info: dict[str, Any] = {
        "srclang": header.get("srclang") if header is not None else "",
        "adminlang": header.get("adminlang") if header is not None else "",
        "source_tuv_langs": [],
        "target_tuv_langs": [],
        "other_tuv_langs": [],
    }
    body = next((el for el in root.iter() if _local_name(el.tag) == "body"), None)
    if body is None:
        return info

    src_set: set[str] = set()
    tgt_set: set[str] = set()
    other_set: set[str] = set()
    for tu in _direct_children(body, "tu"):
        tuvs = _direct_children(tu, "tuv")
        for idx, tuv in enumerate(tuvs):
            lang = tuv.get(_XML_LANG) or tuv.get("lang") or ""
            if not lang:
                continue
            if idx == 0:
                src_set.add(lang)
            elif idx == 1:
                tgt_set.add(lang)
            else:
                other_set.add(lang)

    info["source_tuv_langs"] = sorted(src_set)
    info["target_tuv_langs"] = sorted(tgt_set)
    info["other_tuv_langs"] = sorted(other_set)
    return info


def _resolve_tmx_header_replacement(
    current: str,
    *,
    source_find: str | None,
    source_replace: str | None,
    tuv_mappings: dict[str, str] | None,
) -> str | None:
    if tuv_mappings:
        for old, new in tuv_mappings.items():
            if _lang_matches(current, old):
                return new
    if source_find and source_replace and _lang_matches(current, source_find):
        return source_replace
    return None


def _resolve_tmx_tuv_replacement(
    current: str,
    *,
    slot: int,
    source_find: str | None,
    source_replace: str | None,
    target_find: str | None,
    target_replace: str | None,
    tuv_mappings: dict[str, str] | None,
) -> str | None:
    if tuv_mappings:
        for old, new in tuv_mappings.items():
            if _lang_matches(current, old):
                return new
        return None
    if slot == 0 and source_find and source_replace and _lang_matches(current, source_find):
        return source_replace
    if slot == 1 and target_find and target_replace and _lang_matches(current, target_find):
        return target_replace
    return None


def _default_output_path(input_path: str, *, suffix: str) -> str:
    base, ext = os.path.splitext(input_path)
    return f"{base}{suffix}{ext or '.tmx'}"


def retag_tmx_operation(
    filepath: str,
    source_find: str | None = None,
    source_replace: str | None = None,
    target_find: str | None = None,
    target_replace: str | None = None,
    tuv_mappings_json: str | None = None,
    **kwargs: Any,
) -> str:
    """OPERATIONS entry point for TMX lang retag (returns output path)."""
    _ = kwargs
    mappings = None
    if tuv_mappings_json:
        parsed = json.loads(tuv_mappings_json)
        if not isinstance(parsed, dict):
            raise ValueError("tuv_mappings_json must be a JSON object")
        mappings = {str(k): str(v) for k, v in parsed.items()}
    result = retag_tmx_languages(
        filepath,
        source_find=source_find or None,
        source_replace=source_replace or None,
        target_find=target_find or None,
        target_replace=target_replace or None,
        tuv_mappings=mappings,
    )
    return result.output_path

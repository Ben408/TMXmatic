"""Fill empty XLIFF targets with local Ollama translategemma (segment-by-segment)."""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from lxml import etree

from scripts.xliff_operations import (
    _element_text,
    _iter_xliff_segments,
    _target_needs_leverage,
    _xliff_langs,
)

logger = logging.getLogger(__name__)

_DEFAULT_MODEL = "translategemma:12b"

_LANG_DISPLAY: dict[str, str] = {
    "fr": "French",
    "fr_fr": "French",
    "fr_ca": "French (Canada)",
    "de": "German",
    "de_de": "German",
    "es": "Spanish",
    "es_es": "Spanish",
    "it": "Italian",
    "it_it": "Italian",
    "en": "English",
    "en_us": "English",
    "en_gb": "English (UK)",
    "pt": "Portuguese",
    "pt_br": "Portuguese (Brazil)",
}


def _norm(code: str | None) -> str:
    return (code or "").strip().lower().replace("-", "_")


def _lang_display_name(code: str | None) -> str:
    key = _norm(code)
    if key in _LANG_DISPLAY:
        return _LANG_DISPLAY[key]
    if "_" in key:
        base = key.split("_")[0]
        if base in _LANG_DISPLAY:
            return _LANG_DISPLAY[base]
    return code or "the target language"


def _run_translategemma(source: str, target_lang: str, *, model: str) -> str:
    lang_name = _lang_display_name(target_lang)
    prompt = (
        f"You are a translation engine. Translate into {lang_name}.\n"
        "Output ONLY the translation of the source text below. "
        "No quotes, no labels, no explanations.\n"
        f"Source:\n{source}"
    )
    env = os.environ.copy()
    env.setdefault("PYTHONIOENCODING", "utf-8")
    completed = subprocess.run(
        ["ollama", "run", model, prompt],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
        check=False,
    )
    if completed.returncode != 0:
        err = (completed.stderr or completed.stdout or "").strip()
        raise RuntimeError(f"ollama translategemma failed: {err[:500]}")
    return (completed.stdout or "").strip()


def _set_target_text(tgt_el: etree._Element, text: str) -> None:
    """Set plain target text; clears inline children (pilot — markup not preserved)."""
    for child in list(tgt_el):
        tgt_el.remove(child)
    tgt_el.text = text
    tgt_el.tail = None


def translate_xliff_with_gemma(
    xliff_path: str,
    *,
    target_lang: str | None = None,
    source_lang: str | None = None,
    output_path: str | None = None,
    model: str | None = None,
    max_segments: int | None = None,
    skip_translated: bool = True,
) -> tuple[str, dict[str, Any]]:
    """Translate empty XLIFF segments via Ollama translategemma."""
    if not os.path.isfile(xliff_path):
        raise FileNotFoundError(xliff_path)

    parser = etree.XMLParser(recover=True, remove_blank_text=False)
    tree = etree.parse(xliff_path, parser)
    root = tree.getroot()
    inferred_src, inferred_tgt = _xliff_langs(root)
    src_lang = source_lang or inferred_src
    tgt_lang = target_lang or inferred_tgt
    if not tgt_lang or _norm(tgt_lang) in {"und", "zxx", ""}:
        raise ValueError("target_lang is required (not found in XLIFF)")

    model_name = (model or os.environ.get("LDW_GEMMA_MODEL") or _DEFAULT_MODEL).strip()
    translated = 0
    skipped = 0
    empty = 0
    errors = 0
    total = 0

    for src_el, tgt_el in _iter_xliff_segments(root):
        total += 1
        if max_segments is not None and translated >= max_segments:
            skipped += 1
            continue
        src_text = _element_text(src_el)
        if not src_text:
            skipped += 1
            continue
        tgt_text = _element_text(tgt_el)
        if skip_translated and not _target_needs_leverage(src_text, tgt_text):
            skipped += 1
            continue
        empty += 1
        try:
            mt = _run_translategemma(src_text, tgt_lang, model=model_name)
            if mt:
                _set_target_text(tgt_el, mt)
                translated += 1
        except Exception as exc:  # noqa: BLE001
            errors += 1
            logger.warning("segment MT failed: %s", exc)

    base, ext = os.path.splitext(xliff_path)
    dest = output_path or f"{base}_gemma{ext or '.xlf'}"
    tree.write(dest, encoding="utf-8", xml_declaration=True, pretty_print=False)

    stats = {
        "total_segments": total,
        "translated": translated,
        "skipped": skipped,
        "empty_candidates": empty,
        "errors": errors,
        "source_lang": src_lang,
        "target_lang": tgt_lang,
        "model": model_name,
    }
    logger.info("XLIFF gemma MT: %s", stats)
    return dest, stats


def xliff_gemma_mt_operation(
    filepath: str,
    *,
    target_lang: str | None = None,
    source_lang: str | None = None,
    max_segments: int | None = None,
    model: str | None = None,
    **kwargs: Any,
) -> str:
    """OPERATIONS / pipeline entry — returns output XLIFF path."""
    _ = kwargs
    out, _stats = translate_xliff_with_gemma(
        filepath,
        target_lang=target_lang,
        source_lang=source_lang,
        max_segments=max_segments,
        model=model,
    )
    return out

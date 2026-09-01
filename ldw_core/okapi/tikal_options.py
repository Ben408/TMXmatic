"""Shared tikal CLI options (language pair, etc.) for Docker, local, and GHA backends."""

from __future__ import annotations

import os
from typing import Any

DEFAULT_SOURCE_LANG = "en-us"
DEFAULT_TARGET_LANG = "fr-fr"


def normalize_lang(value: str | None, default: str) -> str:
    """Normalize BCP47-ish tags for tikal (-sl / -tl)."""
    raw = (value or default).strip()
    return raw.replace("_", "-") if raw else default


def resolve_lang_options(options: dict[str, Any] | None) -> tuple[str, str]:
    opts = options or {}
    source = normalize_lang(opts.get("source_lang"), DEFAULT_SOURCE_LANG)
    target = normalize_lang(opts.get("target_lang"), DEFAULT_TARGET_LANG)
    return source, target


def tikal_lang_args(options: dict[str, Any] | None, *, for_merge: bool = False) -> list[str]:
    """Return ``-sl`` / ``-tl`` flags for tikal extract/merge."""
    _ = for_merge
    source, target = resolve_lang_options(options)
    return ["-sl", source, "-tl", target]


def merge_xliff_path(work_dir: str, xliff_input: str) -> str:
    """Resolve the on-disk XLIFF path tikal expects for merge (``doc.docx.xlf``)."""
    name = os.path.basename(xliff_input)
    if name == "converted.xlf":
        for candidate in sorted(os.listdir(work_dir)):
            if candidate.endswith(".xlf") and candidate != "converted.xlf":
                return os.path.join(work_dir, candidate)
    path = os.path.join(work_dir, name)
    return path


def merge_output_path(work_dir: str, xliff_input: str) -> str | None:
    """Predict merged document path from XLIFF filename (``smoke.docx.xlf`` → ``smoke.docx``)."""
    name = os.path.basename(merge_xliff_path(work_dir, xliff_input))
    if not name.endswith(".xlf"):
        return None
    doc_name = name[: -len(".xlf")]
    path = os.path.join(work_dir, doc_name)
    return path if os.path.isfile(path) else None

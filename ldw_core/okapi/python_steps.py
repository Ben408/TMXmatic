"""Python-native LDW operations inside hybrid Okapi pipelines."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Any

from ldw_core.okapi.runners import OkapiRunResult

# Operations exposed to hybrid pipelines (maps to app.py OPERATIONS keys).
PIPELINE_PYTHON_OPERATIONS: frozenset[str] = frozenset(
    {
        "convert_vatv",
        "convert_termweb",
        "remove_empty",
        "find_duplicates",
        "non_true_duplicates",
        "remove_sentence",
        "remove_old",
        "clean_mt",
        "merge_tmx",
        "split_language",
        "split_size",
        "batch_process_tms",
        "batch_process_mt",
        "process_tbx",
        "find_date_duplicates",
        "remove_context_props",
        "retag_tmx",
    }
)


def run_python_operation(
    operation_id: str,
    input_path: str,
    work_dir: str,
    app_path: str,
    options: dict[str, Any] | None = None,
) -> OkapiRunResult:
    """Run one LDW script operation and stage outputs under ``work_dir``."""
    opts = options or {}
    if operation_id not in PIPELINE_PYTHON_OPERATIONS:
        return OkapiRunResult(
            False,
            [],
            "",
            f"python operation not allowed in pipeline: {operation_id}",
        )
    if app_path not in sys.path:
        sys.path.insert(0, app_path)
    try:
        import app as ldw_app  # noqa: WPS433 — Flask app module owns OPERATIONS map
    except ImportError as exc:
        return OkapiRunResult(False, [], "", f"cannot import LDW app module: {exc}")

    if operation_id not in ldw_app.OPERATIONS:
        return OkapiRunResult(False, [], "", f"unknown LDW operation: {operation_id}")

    kwargs: dict[str, Any] = {}
    if opts.get("cutoff_date"):
        kwargs["cutoff_date"] = opts["cutoff_date"]
    if opts.get("batch_mt_steps"):
        kwargs["batch_mt_steps"] = opts["batch_mt_steps"]

    try:
        result = ldw_app.process_file(operation_id, input_path, **kwargs)
    except Exception as exc:  # noqa: BLE001
        return OkapiRunResult(False, [], "", str(exc))

    os.makedirs(work_dir, exist_ok=True)
    output_paths: list[str] = []

    def _stage(path: str) -> None:
        if not path or not os.path.isfile(path):
            return
        dest = os.path.join(work_dir, os.path.basename(path))
        if os.path.abspath(path) != os.path.abspath(dest):
            shutil.copy2(path, dest)
        output_paths.append(dest)

    if isinstance(result, str):
        _stage(result)
    elif isinstance(result, tuple):
        for item in result:
            if isinstance(item, str):
                _stage(item)
            elif isinstance(item, list):
                for sub in item:
                    if isinstance(sub, str):
                        _stage(sub)
    elif isinstance(result, list):
        for item in result:
            if isinstance(item, str):
                _stage(item)

    if not output_paths:
        return OkapiRunResult(False, [], "", "python operation produced no output files")
    return OkapiRunResult(True, output_paths, f"python {operation_id} ok")

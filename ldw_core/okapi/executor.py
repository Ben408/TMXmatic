"""Execute a single Okapi registry operation via the configured runner."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
from typing import Any

from ldw_core.okapi.config import load_okapi_config
from ldw_core.okapi.operation_registry import OkapiOperationRegistry
from ldw_core.okapi.runners import OkapiRunResult, build_runner, _validate_xliff_output


def _content_hash(path: str, operation_id: str, options: dict[str, Any]) -> str:
    """Hash input + options for idempotent artifact reuse (spec S001 follow-up)."""
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    digest.update(operation_id.encode("utf-8"))
    digest.update(json.dumps(options, sort_keys=True).encode("utf-8"))
    return digest.hexdigest()


class OkapiExecutor:
    """Preflight validation + runner dispatch + artifact staging."""

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._registry = OkapiOperationRegistry(app_path)

    @property
    def registry(self) -> OkapiOperationRegistry:
        return self._registry

    def preflight(self, operation_id: str, input_path: str, backend: str | None = None) -> tuple[bool, str]:
        """Validate operation id and input extension before enqueueing a job."""
        op = self._registry.get(operation_id)
        if not op:
            return False, f"unknown operation: {operation_id}"
        if not os.path.isfile(input_path):
            return False, f"input file not found: {input_path}"
        ext = os.path.splitext(input_path)[1].lstrip(".")
        if not self._registry.supports_input_extension(operation_id, ext):
            return False, f"operation {operation_id} does not accept .{ext}"
        cfg = load_okapi_config(self._app_path)
        active = backend or cfg.get("backend") or "docker"
        runner = build_runner(active, self._app_path, cfg)
        health = runner.health_check()
        if not health.available:
            return False, health.message
        return True, "ok"

    def execute(
        self,
        operation_id: str,
        input_path: str,
        work_dir: str,
        backend: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        """Run operation and optionally reuse cached artifacts by content hash."""
        opts = options or {}
        op = self._registry.get(operation_id)
        if not op:
            return OkapiRunResult(False, [], "", f"unknown operation: {operation_id}")
        cfg = load_okapi_config(self._app_path)
        active = backend or cfg.get("backend") or "docker"
        cache_root = os.path.join(self._app_path, "data", "okapi_cache")
        cache_key = _content_hash(input_path, operation_id, opts)
        cache_dir = os.path.join(cache_root, cache_key)
        cached_marker = os.path.join(cache_dir, "done.json")
        if os.path.isfile(cached_marker):
            with open(cached_marker, encoding="utf-8") as handle:
                cached = json.load(handle)
            outputs = [os.path.join(cache_dir, name) for name in cached.get("artifacts", [])]
            if all(os.path.isfile(p) for p in outputs) and all(
                not p.lower().endswith((".xlf", ".xliff")) or _validate_xliff_output(p) for p in outputs
            ):
                os.makedirs(work_dir, exist_ok=True)
                copied: list[str] = []
                for src in outputs:
                    dest = os.path.join(work_dir, os.path.basename(src))
                    shutil.copy2(src, dest)
                    copied.append(dest)
                return OkapiRunResult(True, copied, "cache hit")

        runner = build_runner(active, self._app_path, cfg)
        result = runner.run_operation(op, input_path, work_dir, opts)
        if result.success and result.output_files:
            valid_outputs = [
                p
                for p in result.output_files
                if not p.lower().endswith((".xlf", ".xliff")) or _validate_xliff_output(p)
            ]
            if len(valid_outputs) != len(result.output_files):
                result = OkapiRunResult(False, [], result.log, "Okapi produced invalid XLIFF output")
            else:
                os.makedirs(cache_dir, exist_ok=True)
                names: list[str] = []
                for src in result.output_files:
                    name = os.path.basename(src)
                    dest = os.path.join(cache_dir, name)
                    shutil.copy2(src, dest)
                    names.append(name)
                with open(cached_marker, "w", encoding="utf-8") as handle:
                    json.dump({"operation": operation_id, "artifacts": names}, handle, indent=2)
        return result

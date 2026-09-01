"""Load and validate the core-owned ``modules.json`` registry."""

from __future__ import annotations

import json
import os
from typing import Any

from ldw_core.paths import modules_json_path
from ldw_core.semver import version_in_range
from ldw_core.version import LDW_CORE_VERSION

# Schema v1 required keys on each module row.
_MODULE_REQUIRED = ("id", "version", "ldw_min", "manifest_path")


class ModuleRegistry:
    """Reads ``modules.json`` and exposes Hermes/UI-friendly module metadata."""

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._registry_path = modules_json_path(app_path)

    @property
    def registry_path(self) -> str:
        return self._registry_path

    def load_raw(self) -> dict[str, Any]:
        """Return parsed registry; empty modules list when file is missing."""
        if not os.path.isfile(self._registry_path):
            return {"schema_version": 1, "modules": []}
        with open(self._registry_path, encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError("modules.json root must be an object")
        data.setdefault("schema_version", 1)
        data.setdefault("modules", [])
        return data

    def validate_entry(self, entry: dict[str, Any]) -> None:
        """Raise ``ValueError`` when a module row is malformed."""
        if not isinstance(entry, dict):
            raise ValueError("module entry must be an object")
        missing = [key for key in _MODULE_REQUIRED if not entry.get(key)]
        if missing:
            raise ValueError(f"module entry missing required keys: {missing}")

    def list_for_api(self, core_version: str | None = None) -> dict[str, Any]:
        """Build ``GET /api/modules`` payload with compatibility flags."""
        version = core_version or LDW_CORE_VERSION
        raw = self.load_raw()
        modules_out: list[dict[str, Any]] = []
        for entry in raw.get("modules", []):
            if not isinstance(entry, dict):
                continue
            try:
                self.validate_entry(entry)
            except ValueError:
                # Skip corrupt rows but keep the API usable for Hermes wake probes.
                continue
            compatible = version_in_range(
                version,
                entry.get("ldw_min"),
                entry.get("ldw_max"),
            )
            modules_out.append(
                {
                    "id": entry["id"],
                    "version": entry["version"],
                    "ldw_min": entry.get("ldw_min"),
                    "ldw_max": entry.get("ldw_max"),
                    "gpu_required": bool(entry.get("gpu_required", False)),
                    "installed_at": entry.get("installed_at"),
                    "manifest_path": entry.get("manifest_path"),
                    "compatible": compatible,
                }
            )
        return {
            "schema_version": raw.get("schema_version", 1),
            "ldw_core_version": version,
            "modules": modules_out,
        }

    def register_module(self, entry: dict[str, Any]) -> None:
        """Append or replace a module row — used by ``install.bat`` helpers/tests."""
        self.validate_entry(entry)
        raw = self.load_raw()
        modules: list[dict[str, Any]] = list(raw.get("modules", []))
        modules = [row for row in modules if row.get("id") != entry["id"]]
        modules.append(entry)
        raw["modules"] = modules
        raw["schema_version"] = raw.get("schema_version", 1)
        os.makedirs(os.path.dirname(self._registry_path) or self._app_path, exist_ok=True)
        with open(self._registry_path, "w", encoding="utf-8") as handle:
            json.dump(raw, handle, indent=2)
            handle.write("\n")

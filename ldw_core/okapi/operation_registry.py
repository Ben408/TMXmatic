"""Canonical Okapi operation registry (YAML) for API + UI discovery."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from ldw_core.paths import get_application_path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover — optional until pip install pyyaml
    yaml = None


@dataclass
class OkapiOperation:
    """One row from ``config/okapi_operations.yml``."""

    id: str
    label: str
    description: str
    component: str
    complexity: str
    tikal_mode: str
    input_formats: list[str] = field(default_factory=list)
    output_primary: str = "output.bin"
    output_mime: str = "application/octet-stream"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "component": self.component,
            "complexity": self.complexity,
            "tikal_mode": self.tikal_mode,
            "inputs": {"formats": self.input_formats},
            "outputs": {"primary": self.output_primary, "mime": self.output_mime},
        }


class OkapiOperationRegistry:
    """Reads ``config/okapi_operations.yml`` once per app path."""

    def __init__(self, app_path: str | None = None) -> None:
        self._app_path = app_path or get_application_path()
        self._registry_path = os.path.join(self._app_path, "config", "okapi_operations.yml")
        self._operations: dict[str, OkapiOperation] = {}
        self._schema_version = 1
        self._reload()

    @property
    def registry_path(self) -> str:
        return self._registry_path

    def _reload(self) -> None:
        if not os.path.isfile(self._registry_path):
            return
        if yaml is None:
            raise RuntimeError("PyYAML is required for Okapi operation registry")
        with open(self._registry_path, encoding="utf-8") as handle:
            raw = yaml.safe_load(handle) or {}
        self._schema_version = int(raw.get("schema_version", 1))
        self._operations.clear()
        for row in raw.get("operations", []):
            op = OkapiOperation(
                id=row["id"],
                label=row.get("label", row["id"]),
                description=row.get("description", ""),
                component=row.get("component", "tikal"),
                complexity=row.get("complexity", "medium"),
                tikal_mode=row.get("tikal_mode", "extract"),
                input_formats=list((row.get("inputs") or {}).get("formats", [])),
                output_primary=(row.get("outputs") or {}).get("primary", "output.bin"),
                output_mime=(row.get("outputs") or {}).get("mime", "application/octet-stream"),
            )
            self._operations[op.id] = op

    def get(self, operation_id: str) -> OkapiOperation | None:
        return self._operations.get(operation_id)

    def list_operations(self) -> list[OkapiOperation]:
        return list(self._operations.values())

    def list_for_api(self) -> dict[str, Any]:
        return {
            "schema_version": self._schema_version,
            "operations": [op.to_dict() for op in self.list_operations()],
        }

    def supports_input_extension(self, operation_id: str, extension: str) -> bool:
        """Return True when the operation accepts the file extension (no leading dot)."""
        op = self.get(operation_id)
        if not op or not op.input_formats:
            return True
        ext = (extension or "").lower().lstrip(".")
        return ext in {fmt.lower() for fmt in op.input_formats}

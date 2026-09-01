"""External Longhorn runner — stock Okapi Longhorn REST via ``LonghornProjectClient``."""

from __future__ import annotations

import os
from typing import Any

from ldw_core.okapi.longhorn_project_client import LonghornProjectClient
from ldw_core.okapi.operation_registry import OkapiOperation
from ldw_core.okapi.runners import OkapiRunResult, OkapiRunner, RunnerHealth


class LonghornRunner(OkapiRunner):
    """Run registry operations on stock ``okapiframework/okapi-longhorn`` (beta)."""

    backend_id = "longhorn"

    def __init__(self, base_url: str) -> None:
        self._base = (base_url or "").rstrip("/")
        self._client = LonghornProjectClient(self._base)

    def health_check(self) -> RunnerHealth:
        ok, message = self._client.probe_health()
        label = "longhorn (beta)" if ok else self.backend_id
        return RunnerHealth(label, ok, message)

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        success, outputs, log = self._client.run_operation(
            operation.id,
            input_path,
            work_dir,
            options=options,
        )
        if not success:
            return OkapiRunResult(False, [], log, log)
        # Prefer registry primary artifact when present.
        primary = operation.output_primary
        ordered = list(outputs)
        if primary:
            for path in outputs:
                if os.path.basename(path) == primary:
                    ordered = [path] + [p for p in outputs if p != path]
                    break
        return OkapiRunResult(True, ordered, log)

    def discover_operations(self) -> list[dict[str, Any]]:
        """Longhorn uses the LDW registry; dynamic discovery is backlog."""
        return []

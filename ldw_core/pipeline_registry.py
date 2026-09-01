"""Built-in pipeline step catalog for local job API v1.

Modules may extend this list via their ``manifest.json`` ``pipeline_steps`` field.
"""

from __future__ import annotations

from typing import Any

# Core-only steps shipped in Phase 1; Okapi + module steps register later.
CORE_PIPELINE_STEPS: list[dict[str, Any]] = [
    {
        "id": "noop",
        "description": "Health-check job that completes immediately.",
        "owner": "ldw-core",
    },
    {
        "id": "echo",
        "description": "Write params.text to a result artifact (integration smoke).",
        "owner": "ldw-core",
    },
    {
        "id": "xliff-leverage",
        "description": "Leverage TMX into XLIFF (existing LDW operation).",
        "owner": "ldw-core",
    },
]


def list_pipeline_steps(extra_steps: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Return merged step catalog for ``GET /api/pipeline-steps`` (optional v1 helper)."""
    merged = list(CORE_PIPELINE_STEPS)
    for step in extra_steps or []:
        if isinstance(step, dict) and step.get("id"):
            merged = [row for row in merged if row.get("id") != step["id"]]
            merged.append(step)
    return {"schema_version": 1, "steps": merged}

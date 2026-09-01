"""Hybrid Python + Okapi pipeline orchestration."""

from __future__ import annotations

import json
import os
from typing import Any

from ldw_core.okapi.executor import OkapiExecutor


class HybridPipelineManager:
    """Execute mixed pipelines — Okapi steps today; Python steps via operation id map."""

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._executor = OkapiExecutor(app_path)
        self._templates_dir = os.path.join(app_path, "config", "pipeline_templates")

    def list_templates(self) -> list[dict[str, Any]]:
        """Load JSON pipeline templates shipped with LDW core."""
        templates: list[dict[str, Any]] = []
        if not os.path.isdir(self._templates_dir):
            return templates
        for name in sorted(os.listdir(self._templates_dir)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self._templates_dir, name)
            with open(path, encoding="utf-8") as handle:
                templates.append(json.load(handle))
        return templates

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        for row in self.list_templates():
            if row.get("id") == template_id:
                return row
        return None

    def execute_steps(
        self,
        steps: list[dict[str, Any]],
        input_files: list[str],
        work_dir: str,
        backend: str | None = None,
    ) -> dict[str, Any]:
        """Run steps sequentially; pass outputs forward as next step inputs."""
        current_files = list(input_files)
        step_results: list[dict[str, Any]] = []
        for index, step in enumerate(steps):
            step_type = step.get("type", "okapi")
            step_id = step.get("id", f"step-{index + 1}")
            if not current_files:
                return {
                    "success": False,
                    "error": f"no input files before step {step_id}",
                    "steps": step_results,
                }
            if step_type == "okapi":
                operation = step.get("operation")
                if not operation:
                    return {"success": False, "error": f"step {step_id} missing operation", "steps": step_results}
                step_work = os.path.join(work_dir, step_id)
                os.makedirs(step_work, exist_ok=True)
                result = self._executor.execute(
                    operation,
                    current_files[0],
                    step_work,
                    backend=backend,
                    options=step.get("options") or {},
                )
                step_results.append(
                    {
                        "id": step_id,
                        "type": step_type,
                        "operation": operation,
                        "success": result.success,
                        "log": result.log,
                        "error": result.error,
                        "outputs": [os.path.basename(p) for p in result.output_files],
                    }
                )
                if not result.success:
                    return {"success": False, "error": result.error, "steps": step_results}
                current_files = result.output_files
            elif step_type == "python":
                # Python-native steps delegate to LDW scripts (minimal map for Phase 2).
                step_results.append(
                    {
                        "id": step_id,
                        "type": step_type,
                        "operation": step.get("operation"),
                        "success": False,
                        "error": "python pipeline steps: use queue API for now (Phase 2.1)",
                    }
                )
                return {"success": False, "error": "python pipeline step not implemented in job runner", "steps": step_results}
            else:
                return {"success": False, "error": f"unknown step type: {step_type}", "steps": step_results}
        return {"success": True, "final_outputs": current_files, "steps": step_results}

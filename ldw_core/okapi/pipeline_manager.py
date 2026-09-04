"""Hybrid Python + Okapi pipeline orchestration."""

from __future__ import annotations

import os
import shutil
from typing import Any

from ldw_core.okapi.executor import OkapiExecutor
from ldw_core.okapi.python_steps import run_python_operation
from ldw_core.okapi.template_manager import PipelineTemplateManager

_PACKAGE_EXTENSIONS = frozenset({".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".idml"})


class HybridPipelineManager:
    """Execute mixed Python/Okapi pipelines with sequential file handoff."""

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._executor = OkapiExecutor(app_path)
        self._templates = PipelineTemplateManager(app_path)

    def list_templates(self) -> list[dict[str, Any]]:
        return self._templates.list_all()

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        return self._templates.get(template_id)

    def save_template(self, template: dict[str, Any]) -> dict[str, Any]:
        return self._templates.save_user_template(template)

    def delete_template(self, template_id: str) -> bool:
        return self._templates.delete_user_template(template_id)

    def execute_steps(
        self,
        steps: list[dict[str, Any]],
        input_files: list[str],
        work_dir: str,
        backend: str | None = None,
        pipeline_options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run steps sequentially; pass outputs forward as next step inputs."""
        current_files = list(input_files)
        original_inputs = list(input_files)
        shared_options = dict(pipeline_options or {})
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
            step_work = os.path.join(work_dir, step_id)
            os.makedirs(step_work, exist_ok=True)

            if step_type in ("okapi", "okapi_github", "okapi_external", "okapi_pipeline"):
                operation = step.get("operation")
                if not operation:
                    return {"success": False, "error": f"step {step_id} missing operation", "steps": step_results}
                step_backend = backend or step.get("backend")
                step_options = {**shared_options, **(step.get("options") or {})}
                step_input = current_files[0]
                if operation == "merge":
                    staged_xliff = self._stage_merge_companions(
                        work_dir, step_work, original_inputs, current_files[0]
                    )
                    if not staged_xliff:
                        return {
                            "success": False,
                            "error": (
                                f"step {step_id}: could not stage package + XLIFF for merge "
                                f"(need original .docx/.xlsx/… beside translated XLIFF)"
                            ),
                            "steps": step_results,
                        }
                    step_input = staged_xliff
                result = self._executor.execute(
                    operation,
                    step_input,
                    step_work,
                    backend=step_backend,
                    options=step_options,
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

            elif step_type in ("python", "python_native"):
                operation = step.get("operation")
                if not operation:
                    return {"success": False, "error": f"step {step_id} missing operation", "steps": step_results}
                result = run_python_operation(
                    operation,
                    current_files[0],
                    step_work,
                    self._app_path,
                    options={**shared_options, **(step.get("options") or {})},
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
            else:
                return {"success": False, "error": f"unknown step type: {step_type}", "steps": step_results}

        return {"success": True, "final_outputs": current_files, "steps": step_results}

    @staticmethod
    def _stage_merge_companions(
        work_dir: str,
        step_work: str,
        original_inputs: list[str],
        xliff_path: str,
    ) -> str | None:
        """Stage package + XLIFF so tikal ``-m`` sees ``doc.docx`` + ``doc.docx.xlf``.

        Pipeline extract normalizes XLIFF to ``converted.xlf``. Gemma keeps that
        basename. Tikal merge strips ``.xlf`` and opens the companion package, so
        ``converted.xlf`` becomes ``/work/converted`` (no filter) and fails.
        """
        os.makedirs(step_work, exist_ok=True)
        package_src: str | None = None
        for orig in original_inputs:
            ext = os.path.splitext(orig)[1].lower()
            if ext not in _PACKAGE_EXTENSIONS:
                continue
            for candidate in (orig, os.path.join(work_dir, os.path.basename(orig))):
                if os.path.isfile(candidate):
                    package_src = candidate
                    break
            if package_src:
                break
        if not package_src or not os.path.isfile(xliff_path):
            return None

        package_name = os.path.basename(package_src)
        package_dest = os.path.join(step_work, package_name)
        if os.path.abspath(package_src) != os.path.abspath(package_dest):
            shutil.copy2(package_src, package_dest)

        # Prefer package.docx.xlf; never leave gemma output as converted.xlf for -m.
        xliff_dest = os.path.join(step_work, f"{package_name}.xlf")
        if os.path.abspath(xliff_path) != os.path.abspath(xliff_dest):
            shutil.copy2(xliff_path, xliff_dest)
        # Drop a stale converted.xlf so merge_xliff_path / tikal cannot prefer it.
        stale = os.path.join(step_work, "converted.xlf")
        if os.path.isfile(stale) and os.path.abspath(stale) != os.path.abspath(xliff_dest):
            try:
                os.remove(stale)
            except OSError:
                pass
        return xliff_dest

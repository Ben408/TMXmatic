"""Register Okapi + pipeline handlers on the Phase 1 job manager."""

from __future__ import annotations

import json
import os
import shutil
from typing import Any

from ldw_core.job_manager import JobManager, register_job_handler
from ldw_core.okapi.executor import OkapiExecutor
from ldw_core.okapi.pipeline_manager import HybridPipelineManager


def _stage_input(manager: JobManager, job_id: str, params: dict[str, Any]) -> tuple[str, str]:
    """Copy uploaded/staged input into the job folder; return (input_path, work_dir)."""
    job_dir = manager._job_dir(job_id)
    work_dir = os.path.join(job_dir, "work")
    os.makedirs(work_dir, exist_ok=True)
    input_path = params.get("input_path")
    if not input_path or not os.path.isfile(input_path):
        raise ValueError("params.input_path must point to an existing file")
    staged = os.path.join(work_dir, os.path.basename(input_path))
    if os.path.abspath(input_path) != os.path.abspath(staged):
        shutil.copy2(input_path, staged)
    return staged, work_dir


def make_okapi_job_handler(app_path: str):
    """Factory — closes over app_path for executor config."""

    executor = OkapiExecutor(app_path)

    def _handle_okapi_operation(manager: JobManager, job_id: str, params: dict[str, Any]) -> None:
        operation_id = params.get("operation")
        if not operation_id:
            raise ValueError("params.operation is required")
        input_path, work_dir = _stage_input(manager, job_id, params)
        ok, msg = executor.preflight(operation_id, input_path, params.get("backend"))
        if not ok:
            raise ValueError(msg)
        result = executor.execute(
            operation_id,
            input_path,
            work_dir,
            backend=params.get("backend"),
            options=params.get("options") or {},
        )
        if not result.success:
            raise RuntimeError(result.error or "okapi operation failed")
        artifact_dir = os.path.join(manager._job_dir(job_id), "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        for src in result.output_files:
            dest = os.path.join(artifact_dir, os.path.basename(src))
            shutil.copy2(src, dest)
            manager._add_artifact(job_id, os.path.basename(dest))
        sidecar = os.path.join(manager._job_dir(job_id), "okapi-log.txt")
        with open(sidecar, "w", encoding="utf-8") as handle:
            handle.write(result.log or "")
        manager._add_artifact(job_id, "okapi-log.txt")
        meta = manager._read_meta(job_id)
        meta["message"] = f"okapi {operation_id} complete"
        meta["progress"] = 95
        manager._write_meta(job_id, meta)

    return _handle_okapi_operation


def make_pipeline_job_handler(app_path: str):
    """Factory for hybrid pipeline jobs."""

    pipelines = HybridPipelineManager(app_path)

    def _handle_pipeline(manager: JobManager, job_id: str, params: dict[str, Any]) -> None:
        steps = params.get("steps")
        template_id = params.get("template_id")
        if template_id and not steps:
            template = pipelines.get_template(template_id)
            if not template:
                raise ValueError(f"unknown pipeline template: {template_id}")
            steps = template.get("steps", [])
        if not steps:
            raise ValueError("params.steps or params.template_id is required")
        input_path, work_dir = _stage_input(manager, job_id, params)
        outcome = pipelines.execute_steps(
            steps,
            [input_path],
            work_dir,
            backend=params.get("backend"),
        )
        sidecar = os.path.join(manager._job_dir(job_id), "pipeline-result.json")
        with open(sidecar, "w", encoding="utf-8") as handle:
            json.dump(outcome, handle, indent=2)
        manager._add_artifact(job_id, "pipeline-result.json")
        if not outcome.get("success"):
            raise RuntimeError(outcome.get("error") or "pipeline failed")
        artifact_dir = os.path.join(manager._job_dir(job_id), "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)
        for src in outcome.get("final_outputs") or []:
            if os.path.isfile(src):
                dest = os.path.join(artifact_dir, os.path.basename(src))
                shutil.copy2(src, dest)
                manager._add_artifact(job_id, os.path.basename(dest))
        meta = manager._read_meta(job_id)
        meta["message"] = "pipeline complete"
        meta["progress"] = 95
        manager._write_meta(job_id, meta)

    return _handle_pipeline


def register_okapi_job_handlers(app_path: str) -> None:
    """Wire Okapi job types into the shared job manager registry."""
    register_job_handler("okapi-operation", make_okapi_job_handler(app_path))
    register_job_handler("pipeline", make_pipeline_job_handler(app_path))

"""Flask routes for Okapi Phase 2 — discovery, submit, status, pipelines."""

from __future__ import annotations

import os
import tempfile
from typing import TYPE_CHECKING

from flask import Blueprint, jsonify, request
from werkzeug.utils import secure_filename

from ldw_core.job_manager import JobManager, supported_job_types
from ldw_core.okapi.config import ALL_BACKENDS, load_okapi_config
from ldw_core.okapi.executor import OkapiExecutor
from ldw_core.okapi.job_handlers import register_okapi_job_handlers
from ldw_core.okapi.operation_registry import OkapiOperationRegistry
from ldw_core.okapi.pipeline_manager import HybridPipelineManager
from ldw_core.okapi.runners import build_runner, resolve_active_backend

if TYPE_CHECKING:
    from flask import Flask


def create_okapi_blueprint(app_path: str, jobs: JobManager) -> Blueprint:
    """Okapi API blueprint — shares the Phase 1 ``JobManager`` instance."""
    bp = Blueprint("ldw_okapi", __name__)
    register_okapi_job_handlers(app_path)
    registry = OkapiOperationRegistry(app_path)
    executor = OkapiExecutor(app_path)
    pipelines = HybridPipelineManager(app_path)
    uploads_dir = os.path.join(app_path, "uploads", "okapi_inbox")
    os.makedirs(uploads_dir, exist_ok=True)

    @bp.route("/api/okapi/operations", methods=["GET"])
    def okapi_operations():
        """Registry-driven operation list for UI discovery."""
        try:
            payload = registry.list_for_api()
            payload["active_backend"] = resolve_active_backend(app_path)
            return jsonify(payload)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": str(exc)}), 500

    @bp.route("/api/okapi/backends/status", methods=["GET"])
    def okapi_backends_status():
        """Probe each backend for Settings + Hermes wake matrix."""
        cfg = load_okapi_config(app_path)
        active = resolve_active_backend(app_path)
        rows = []
        for backend in ALL_BACKENDS:
            try:
                runner = build_runner(backend, app_path, cfg)
                health = runner.health_check()
            except Exception as exc:  # noqa: BLE001 — one backend must not break discovery
                health = type("H", (), {"available": False, "message": str(exc)})()
            rows.append(
                {
                    "backend": backend,
                    "available": health.available,
                    "message": health.message,
                    "active": backend == active,
                }
            )
        return jsonify({"active_backend": active, "backends": rows})

    @bp.route("/api/okapi/submit-upload", methods=["POST"])
    def okapi_submit_upload():
        """Multipart upload → local job (spec: separate from URL flow)."""
        if "file" not in request.files:
            return jsonify({"error": "file is required"}), 400
        operation = (request.form.get("operation") or "").strip()
        if not operation:
            return jsonify({"error": "operation is required"}), 400
        backend = (request.form.get("backend") or "").strip() or None
        options_raw = request.form.get("options_json") or "{}"
        try:
            import json

            options = json.loads(options_raw)
            if not isinstance(options, dict):
                raise ValueError("options_json must be an object")
        except (ValueError, json.JSONDecodeError) as exc:
            return jsonify({"error": f"invalid options_json: {exc}"}), 400

        file = request.files["file"]
        filename = secure_filename(file.filename or "input.bin")
        save_path = os.path.join(uploads_dir, filename)
        file.save(save_path)
        ok, msg = executor.preflight(operation, save_path, backend)
        if not ok:
            return jsonify({"error": msg}), 400
        job = jobs.create_job(
            "okapi-operation",
            {
                "operation": operation,
                "input_path": save_path,
                "backend": backend,
                "options": options,
            },
        )
        return jsonify({"job": job, "poll_url": f"/api/jobs/{job['id']}"}), 202

    @bp.route("/api/okapi/submit-url", methods=["POST"])
    def okapi_submit_url():
        """URL-based submission — downloads to temp file then enqueues (GHA path prep)."""
        data = request.get_json(silent=True) or {}
        input_url = (data.get("input_url") or "").strip()
        operation = (data.get("operation") or "").strip()
        if not input_url or not operation:
            return jsonify({"error": "input_url and operation are required"}), 400
        backend = (data.get("backend") or "").strip() or None
        options = data.get("options") or {}
        if not isinstance(options, dict):
            return jsonify({"error": "options must be an object"}), 400
        try:
            import requests

            response = requests.get(input_url, timeout=120)
            response.raise_for_status()
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": f"download failed: {exc}"}), 400
        suffix = os.path.splitext(input_url.split("?")[0])[1] or ".bin"
        fd, temp_path = tempfile.mkstemp(suffix=suffix, dir=uploads_dir)
        try:
            os.close(fd)
            with open(temp_path, "wb") as handle:
                handle.write(response.content)
            ok, msg = executor.preflight(operation, temp_path, backend)
            if not ok:
                return jsonify({"error": msg}), 400
            job = jobs.create_job(
                "okapi-operation",
                {
                    "operation": operation,
                    "input_path": temp_path,
                    "backend": backend,
                    "options": options,
                },
            )
            return jsonify({"job": job, "poll_url": f"/api/jobs/{job['id']}"}), 202
        except Exception:
            if os.path.isfile(temp_path):
                os.remove(temp_path)
            raise

    @bp.route("/api/okapi/status/<job_id>", methods=["GET"])
    def okapi_status(job_id: str):
        """Alias for job poll — keeps spec parity with ``GET /api/jobs/{id}``."""
        try:
            return jsonify(jobs.get_job(job_id))
        except KeyError:
            return jsonify({"error": "job not found"}), 404

    @bp.route("/api/okapi/results/<job_id>", methods=["GET"])
    def okapi_results(job_id: str):
        """Return artifact download paths for a finished Okapi job."""
        try:
            job = jobs.get_job(job_id)
        except KeyError:
            return jsonify({"error": "job not found"}), 404
        artifacts = [
            {"name": row["name"], "download_url": f"/api/jobs/{job_id}/artifacts/{row['name']}"}
            for row in job.get("artifacts", [])
            if isinstance(row, dict) and row.get("name")
        ]
        return jsonify({"job_id": job_id, "status": job.get("status"), "artifacts": artifacts})

    @bp.route("/api/pipeline-templates", methods=["GET"])
    def pipeline_templates():
        """Predefined hybrid pipeline templates."""
        return jsonify({"templates": pipelines.list_templates()})

    @bp.route("/api/pipelines/execute", methods=["POST"])
    def pipelines_execute():
        """Execute a template or ad-hoc pipeline via the job manager."""
        if "file" not in request.files:
            return jsonify({"error": "file is required"}), 400
        template_id = (request.form.get("template_id") or "").strip() or None
        steps_raw = request.form.get("steps_json") or "[]"
        backend = (request.form.get("backend") or "").strip() or None
        try:
            import json

            steps = json.loads(steps_raw)
            if not isinstance(steps, list):
                raise ValueError("steps_json must be an array")
        except (ValueError, json.JSONDecodeError) as exc:
            return jsonify({"error": f"invalid steps_json: {exc}"}), 400
        if not template_id and not steps:
            return jsonify({"error": "template_id or steps_json is required"}), 400
        file = request.files["file"]
        filename = secure_filename(file.filename or "input.bin")
        save_path = os.path.join(uploads_dir, filename)
        file.save(save_path)
        job = jobs.create_job(
            "pipeline",
            {
                "template_id": template_id,
                "steps": steps,
                "input_path": save_path,
                "backend": backend,
            },
        )
        return jsonify({"job": job, "poll_url": f"/api/jobs/{job['id']}"}), 202

    @bp.route("/api/okapi/supported-job-types", methods=["GET"])
    def okapi_supported_job_types():
        """Debug/helper — lists job types after Okapi handler registration."""
        return jsonify({"types": sorted(supported_job_types())})

    return bp


def register_okapi_api(app: Flask, app_path: str, jobs: JobManager) -> None:
    """Attach Okapi routes to the running Flask app."""
    app.register_blueprint(create_okapi_blueprint(app_path, jobs))

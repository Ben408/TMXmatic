"""Flask routes for LDW core Phase 1: health, modules, local jobs."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from flask import Blueprint, jsonify, request, send_file

from ldw_core.job_manager import JobManager, supported_job_types
from ldw_core.module_registry import ModuleRegistry
from ldw_core.pipeline_registry import list_pipeline_steps
from ldw_core.version import LDW_CORE_VERSION

if TYPE_CHECKING:
    from flask import Flask

# Phase 1 built-in job types always available before Okapi handlers register.
_CORE_JOB_TYPES = {"noop", "echo", "sleep"}


def create_ldw_api_blueprint(app_path: str) -> Blueprint:
    """Build blueprint with app-path-scoped managers (shared venv, no Hermes imports)."""
    bp = Blueprint("ldw_api", __name__)
    registry = ModuleRegistry(app_path)
    jobs = JobManager(app_path)

    @bp.route("/health", methods=["GET"])
    def health():
        """Hermes wake probe — must stay lightweight and dependency-free."""
        return jsonify(
            {
                "status": "ok",
                "ldw_core_version": LDW_CORE_VERSION,
                "timestamp": datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z"),
            }
        )

    @bp.route("/api/modules", methods=["GET"])
    def api_modules():
        """Installed module manifest for UI + Hermes routing ladder."""
        try:
            payload = registry.list_for_api()
            return jsonify(payload)
        except Exception as exc:  # noqa: BLE001
            return jsonify({"error": str(exc)}), 500

    @bp.route("/api/pipeline-steps", methods=["GET"])
    def api_pipeline_steps():
        """Optional catalog endpoint — core steps only until modules register."""
        return jsonify(list_pipeline_steps())

    @bp.route("/api/jobs", methods=["POST"])
    def api_jobs_create():
        """Create a local background job (poll status via GET /api/jobs/<id>)."""
        data = request.get_json(silent=True) or {}
        job_type = (data.get("type") or "").strip()
        if not job_type:
            return jsonify({"error": "type is required"}), 400
        allowed = _CORE_JOB_TYPES | supported_job_types()
        if job_type not in allowed:
            return jsonify(
                {
                    "error": f"unsupported job type: {job_type}",
                    "supported_types": sorted(allowed),
                }
            ), 400
        params = data.get("params")
        if params is not None and not isinstance(params, dict):
            return jsonify({"error": "params must be an object"}), 400
        job = jobs.create_job(job_type, params or {})
        return jsonify(job), 202

    @bp.route("/api/jobs/<job_id>", methods=["GET"])
    def api_jobs_get(job_id: str):
        """Poll job status — Hermes Slack glue uses this in local v1."""
        try:
            return jsonify(jobs.get_job(job_id))
        except KeyError:
            return jsonify({"error": "job not found"}), 404

    @bp.route("/api/jobs/<job_id>/cancel", methods=["POST"])
    def api_jobs_cancel(job_id: str):
        """Best-effort cancel for long-running local jobs."""
        try:
            return jsonify(jobs.cancel_job(job_id))
        except KeyError:
            return jsonify({"error": "job not found"}), 404

    @bp.route("/api/jobs/<job_id>/artifacts/<artifact_name>", methods=["GET"])
    def api_jobs_artifact(job_id: str, artifact_name: str):
        """Download a finished job artifact by filename."""
        try:
            path = jobs.artifact_path(job_id, artifact_name)
            return send_file(
                path,
                as_attachment=True,
                download_name=os.path.basename(artifact_name),
            )
        except KeyError:
            return jsonify({"error": "job not found"}), 404
        except FileNotFoundError:
            return jsonify({"error": "artifact not found"}), 404
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

    # Expose for tests that need direct manager access.
    bp.ldw_registry = registry  # type: ignore[attr-defined]
    bp.ldw_jobs = jobs  # type: ignore[attr-defined]
    return bp


def register_ldw_api(app: Flask, app_path: str) -> None:
    """Register Phase 1 routes on the main LDW Flask app."""
    blueprint = create_ldw_api_blueprint(app_path)
    app.register_blueprint(blueprint)
    # Phase 2 Okapi routes share the same JobManager instance.
    from ldw_core.okapi_routes import register_okapi_api

    register_okapi_api(app, app_path, blueprint.ldw_jobs)  # type: ignore[attr-defined]

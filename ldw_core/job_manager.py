"""Local v1 background job store — file-backed metadata + artifact folder per job."""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

from ldw_core.paths import jobs_root

# Job lifecycle states for Hermes poll loop (SaaS may add webhooks later — see LDW-Planning).
JOB_QUEUED = "queued"
JOB_RUNNING = "running"
JOB_COMPLETED = "completed"
JOB_FAILED = "failed"
JOB_CANCELLED = "cancelled"

TERMINAL_STATES = {JOB_COMPLETED, JOB_FAILED, JOB_CANCELLED}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class JobManager:
    """Creates jobs under ``data/jobs/<id>/`` and runs handlers on a worker thread."""

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path
        self._root = jobs_root(app_path)
        self._lock = threading.Lock()
        os.makedirs(self._root, exist_ok=True)

    @property
    def root(self) -> str:
        return self._root

    def _job_dir(self, job_id: str) -> str:
        return os.path.join(self._root, job_id)

    def _meta_path(self, job_id: str) -> str:
        return os.path.join(self._job_dir(job_id), "meta.json")

    def _read_meta(self, job_id: str) -> dict[str, Any]:
        path = self._meta_path(job_id)
        if not os.path.isfile(path):
            raise KeyError(job_id)
        with open(path, encoding="utf-8") as handle:
            return json.load(handle)

    def _write_meta(self, job_id: str, meta: dict[str, Any]) -> None:
        meta["updated_at"] = _utc_now_iso()
        path = self._meta_path(job_id)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(meta, handle, indent=2)
            handle.write("\n")

    def create_job(self, job_type: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        """Enqueue a job and start the worker thread."""
        job_id = uuid.uuid4().hex
        job_dir = self._job_dir(job_id)
        os.makedirs(job_dir, exist_ok=True)
        meta: dict[str, Any] = {
            "id": job_id,
            "type": job_type,
            "params": params or {},
            "status": JOB_QUEUED,
            "progress": 0,
            "message": "queued",
            "artifacts": [],
            "error": None,
            "created_at": _utc_now_iso(),
            "updated_at": _utc_now_iso(),
        }
        self._write_meta(job_id, meta)
        thread = threading.Thread(
            target=self._run_job,
            args=(job_id, job_type, params or {}),
            daemon=True,
            name=f"ldw-job-{job_id[:8]}",
        )
        thread.start()
        return self.public_view(meta)

    def get_job(self, job_id: str) -> dict[str, Any]:
        """Return job status for polling."""
        return self.public_view(self._read_meta(job_id))

    def cancel_job(self, job_id: str) -> dict[str, Any]:
        """Mark a non-terminal job as cancelled (best-effort for in-flight work)."""
        with self._lock:
            meta = self._read_meta(job_id)
            if meta["status"] in TERMINAL_STATES:
                return self.public_view(meta)
            meta["status"] = JOB_CANCELLED
            meta["message"] = "cancelled by client"
            meta["progress"] = meta.get("progress", 0)
            self._write_meta(job_id, meta)
            return self.public_view(meta)

    def artifact_path(self, job_id: str, name: str) -> str:
        """Resolve artifact file path after sanitizing the download name."""
        safe = os.path.basename(name)
        if not safe or safe in (".", ".."):
            raise ValueError("invalid artifact name")
        path = os.path.join(self._job_dir(job_id), "artifacts", safe)
        if not os.path.isfile(path):
            raise FileNotFoundError(safe)
        return path

    def public_view(self, meta: dict[str, Any]) -> dict[str, Any]:
        """Strip internal fields before JSON responses."""
        return {
            "id": meta["id"],
            "type": meta["type"],
            "status": meta["status"],
            "progress": meta.get("progress", 0),
            "message": meta.get("message", ""),
            "params": meta.get("params", {}),
            "artifacts": list(meta.get("artifacts", [])),
            "error": meta.get("error"),
            "created_at": meta.get("created_at"),
            "updated_at": meta.get("updated_at"),
        }

    def _add_artifact(self, job_id: str, filename: str) -> None:
        meta = self._read_meta(job_id)
        names = {row["name"] for row in meta.get("artifacts", []) if isinstance(row, dict)}
        if filename not in names:
            meta.setdefault("artifacts", []).append({"name": filename})
        self._write_meta(job_id, meta)

    def _run_job(self, job_id: str, job_type: str, params: dict[str, Any]) -> None:
        """Worker entry — dispatches to built-in handlers."""
        try:
            with self._lock:
                meta = self._read_meta(job_id)
                if meta["status"] == JOB_CANCELLED:
                    return
                meta["status"] = JOB_RUNNING
                meta["message"] = "running"
                meta["progress"] = 10
                self._write_meta(job_id, meta)

            handler = _HANDLERS.get(job_type)
            if not handler:
                raise ValueError(f"unknown job type: {job_type}")

            handler(self, job_id, params)

            with self._lock:
                meta = self._read_meta(job_id)
                if meta["status"] == JOB_CANCELLED:
                    return
                meta["status"] = JOB_COMPLETED
                meta["message"] = "completed"
                meta["progress"] = 100
                self._write_meta(job_id, meta)
        except Exception as exc:  # noqa: BLE001 — surface error on job record for Hermes
            with self._lock:
                meta = self._read_meta(job_id)
                if meta["status"] == JOB_CANCELLED:
                    return
                meta["status"] = JOB_FAILED
                meta["message"] = "failed"
                meta["error"] = str(exc)
                self._write_meta(job_id, meta)


def _handle_noop(manager: JobManager, job_id: str, params: dict[str, Any]) -> None:
    """Immediate success — used by Hermes/LDW wake integration tests."""
    _ = params
    manager._write_meta(
        job_id,
        {**manager._read_meta(job_id), "progress": 100, "message": "noop complete"},
    )


def _handle_echo(manager: JobManager, job_id: str, params: dict[str, Any]) -> None:
    """Write ``params['text']`` (or default) to ``artifacts/result.txt``."""
    text = str(params.get("text", "echo"))
    artifact_dir = os.path.join(manager._job_dir(job_id), "artifacts")
    os.makedirs(artifact_dir, exist_ok=True)
    filename = "result.txt"
    path = os.path.join(artifact_dir, filename)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)
    manager._add_artifact(job_id, filename)
    meta = manager._read_meta(job_id)
    meta["progress"] = 90
    meta["message"] = "artifact written"
    manager._write_meta(job_id, meta)


def _handle_sleep(manager: JobManager, job_id: str, params: dict[str, Any]) -> None:
    """Sleep for ``params['seconds']`` — test helper for poll/cancel races."""
    seconds = float(params.get("seconds", 0.2))
    time.sleep(max(0.0, seconds))


Handler = Callable[[JobManager, str, dict[str, Any]], None]

_HANDLERS: dict[str, Handler] = {
    "noop": _handle_noop,
    "echo": _handle_echo,
    "sleep": _handle_sleep,
}

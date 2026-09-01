"""HTTP tests for Phase 1 LDW API routes."""

from __future__ import annotations

import time

from ldw_core.job_manager import JOB_COMPLETED
from ldw_core.version import LDW_CORE_VERSION


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.get_json()
    assert body["status"] == "ok"
    assert body["ldw_core_version"] == LDW_CORE_VERSION
    assert "timestamp" in body


def test_api_modules_empty_by_default(client):
    response = client.get("/api/modules")
    assert response.status_code == 200
    body = response.get_json()
    assert body["modules"] == []
    assert body["ldw_core_version"] == LDW_CORE_VERSION


def test_api_pipeline_steps_lists_core_steps(client):
    response = client.get("/api/pipeline-steps")
    assert response.status_code == 200
    ids = {row["id"] for row in response.get_json()["steps"]}
    assert "noop" in ids
    assert "echo" in ids


def test_create_job_requires_type(client):
    response = client.post("/api/jobs", json={})
    assert response.status_code == 400


def test_create_and_poll_echo_job(client):
    response = client.post("/api/jobs", json={"type": "echo", "params": {"text": "api-test"}})
    assert response.status_code == 202
    job_id = response.get_json()["id"]
    deadline = time.time() + 5.0
    status = "queued"
    while status != JOB_COMPLETED and time.time() < deadline:
        time.sleep(0.05)
        status = client.get(f"/api/jobs/{job_id}").get_json()["status"]
    assert status == JOB_COMPLETED
    artifact = client.get(f"/api/jobs/{job_id}/artifacts/result.txt")
    assert artifact.status_code == 200
    assert b"api-test" in artifact.data


def test_get_missing_job_returns_404(client):
    response = client.get("/api/jobs/does-not-exist")
    assert response.status_code == 404

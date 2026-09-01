"""HTTP tests for Okapi Phase 2 API routes."""

from __future__ import annotations

import io
import os
import time

import pytest

from ldw_core.job_manager import JOB_COMPLETED
from ldw_core.okapi.runners import MockOkapiRunner


@pytest.fixture(autouse=True)
def _mock_okapi_backend(monkeypatch):
    def _build_runner(backend, app_path, config=None):
        _ = (backend, app_path, config)
        return MockOkapiRunner(True)

    monkeypatch.setattr("ldw_core.okapi.executor.build_runner", _build_runner)
    monkeypatch.setattr("ldw_core.okapi.runners.build_runner", _build_runner)


@pytest.fixture(autouse=True)
def _copy_okapi_registry(app_path):
    import shutil

    src = os.path.join(os.path.dirname(__file__), "..", "config", "okapi_operations.yml")
    dest_dir = os.path.join(app_path, "config")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "okapi_operations.yml"))


def test_okapi_operations_list(client):
    response = client.get("/api/okapi/operations")
    assert response.status_code == 200
    ids = {row["id"] for row in response.get_json()["operations"]}
    assert "convert" in ids


def test_okapi_backends_status(client):
    response = client.get("/api/okapi/backends/status")
    assert response.status_code == 200
    body = response.get_json()
    assert "backends" in body
    assert body["backends"][0]["backend"] == "docker"


def test_okapi_submit_upload_job(client):
    data = {
        "file": (io.BytesIO(b"fake-docx-content"), "sample.docx"),
        "operation": "convert",
    }
    response = client.post("/api/okapi/submit-upload", data=data, content_type="multipart/form-data")
    assert response.status_code == 202
    job_id = response.get_json()["job"]["id"]
    deadline = time.time() + 8.0
    status = "queued"
    while status != JOB_COMPLETED and time.time() < deadline:
        time.sleep(0.05)
        status = client.get(f"/api/okapi/status/{job_id}").get_json()["status"]
    assert status == JOB_COMPLETED
    results = client.get(f"/api/okapi/results/{job_id}")
    assert results.status_code == 200
    names = {row["name"] for row in results.get_json()["artifacts"]}
    assert "converted.xlf" in names


def test_pipeline_templates(client):
    response = client.get("/api/pipeline-templates")
    assert response.status_code == 200
    templates = response.get_json()["templates"]
    assert any(t.get("id") == "docx_xliff_roundtrip" for t in templates)

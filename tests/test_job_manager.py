"""Unit tests for local job manager."""

from __future__ import annotations

import time

from ldw_core.job_manager import JOB_CANCELLED, JOB_COMPLETED, JOB_FAILED, JobManager


def test_noop_job_completes(app_path):
    jobs = JobManager(app_path)
    created = jobs.create_job("noop", {})
    deadline = time.time() + 5.0
    status = created["status"]
    while status not in (JOB_COMPLETED, JOB_FAILED) and time.time() < deadline:
        time.sleep(0.05)
        status = jobs.get_job(created["id"])["status"]
    final = jobs.get_job(created["id"])
    assert final["status"] == JOB_COMPLETED
    assert final["progress"] == 100


def test_echo_job_writes_artifact(app_path):
    jobs = JobManager(app_path)
    created = jobs.create_job("echo", {"text": "hello-phase1"})
    deadline = time.time() + 5.0
    while jobs.get_job(created["id"])["status"] != JOB_COMPLETED and time.time() < deadline:
        time.sleep(0.05)
    final = jobs.get_job(created["id"])
    assert final["artifacts"] == [{"name": "result.txt"}]
    path = jobs.artifact_path(final["id"], "result.txt")
    with open(path, encoding="utf-8") as handle:
        assert handle.read() == "hello-phase1"


def test_unknown_job_type_fails(app_path):
    jobs = JobManager(app_path)
    created = jobs.create_job("not-a-real-type", {})
    deadline = time.time() + 5.0
    while jobs.get_job(created["id"])["status"] not in (JOB_COMPLETED, JOB_FAILED) and time.time() < deadline:
        time.sleep(0.05)
    final = jobs.get_job(created["id"])
    assert final["status"] == JOB_FAILED
    assert "unknown job type" in (final.get("error") or "")


def test_cancel_sleep_job(app_path):
    jobs = JobManager(app_path)
    created = jobs.create_job("sleep", {"seconds": 2.0})
    jobs.cancel_job(created["id"])
    time.sleep(0.3)
    final = jobs.get_job(created["id"])
    assert final["status"] == JOB_CANCELLED

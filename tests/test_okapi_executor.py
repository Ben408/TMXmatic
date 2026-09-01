"""Integration tests for Okapi executor with mock runner."""

from __future__ import annotations

import os

import pytest

from ldw_core.okapi.executor import OkapiExecutor
from ldw_core.okapi.runners import MockOkapiRunner


@pytest.fixture(autouse=True)
def _mock_okapi_backend(monkeypatch):
    """Force mock runner so CI/dev boxes without Docker/Java still pass."""

    def _build_runner(backend, app_path, config=None):
        _ = (backend, app_path, config)
        return MockOkapiRunner(True)

    monkeypatch.setattr("ldw_core.okapi.executor.build_runner", _build_runner)
    monkeypatch.setattr("ldw_core.okapi.runners.build_runner", _build_runner)


def test_executor_preflight_and_run(app_path, tmp_path):
    import shutil

    src = os.path.join(os.path.dirname(__file__), "..", "config", "okapi_operations.yml")
    dest_dir = os.path.join(app_path, "config")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "okapi_operations.yml"))

    input_file = tmp_path / "input.docx"
    input_file.write_bytes(b"docx")
    executor = OkapiExecutor(app_path)
    ok, msg = executor.preflight("convert", str(input_file))
    assert ok is True, msg
    work = tmp_path / "work"
    result = executor.execute("convert", str(input_file), str(work))
    assert result.success is True
    assert len(result.output_files) == 1
    # Idempotent second run should hit cache.
    result2 = executor.execute("convert", str(input_file), str(tmp_path / "work2"))
    assert result2.success is True
    assert "cache hit" in (result2.log or "")

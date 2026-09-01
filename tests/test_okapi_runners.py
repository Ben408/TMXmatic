"""Unit tests for Okapi runners (mock + health probes)."""

import os

from ldw_core.okapi.operation_registry import OkapiOperationRegistry
from ldw_core.okapi.runners import MockOkapiRunner, StubRemoteRunner


def test_mock_runner_extract_creates_xliff(app_path, tmp_path):
    import shutil

    src = os.path.join(os.path.dirname(__file__), "..", "config", "okapi_operations.yml")
    dest_dir = os.path.join(app_path, "config")
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copy2(src, os.path.join(dest_dir, "okapi_operations.yml"))

    registry = OkapiOperationRegistry(app_path)
    op = registry.get("convert")
    assert op is not None
    input_file = tmp_path / "sample.docx"
    input_file.write_bytes(b"fake-docx")
    work_dir = tmp_path / "work"
    runner = MockOkapiRunner(True)
    health = runner.health_check()
    assert health.available is True
    result = runner.run_operation(op, str(input_file), str(work_dir))
    assert result.success is True
    assert any(name.endswith(".xlf") for name in [os.path.basename(p) for p in result.output_files])


def test_stub_github_runner_reports_not_configured():
    runner = StubRemoteRunner("github", "not configured")
    health = runner.health_check()
    assert health.available is False
    result = runner.run_operation(None, "in.bin", "/tmp")  # type: ignore[arg-type]
    assert result.success is False

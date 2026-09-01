"""Okapi runner abstraction — Docker, local tikal, GHA, Longhorn, hosted."""

from __future__ import annotations

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ldw_core.okapi.config import (
    ALL_BACKENDS,
    BACKEND_DOCKER,
    BACKEND_GITHUB,
    BACKEND_HOSTED,
    BACKEND_LOCAL_TIKAL,
    BACKEND_LONGHORN,
    load_okapi_config,
)
from ldw_core.okapi.operation_registry import OkapiOperation


@dataclass
class RunnerHealth:
    """Health probe result for ``GET /api/okapi/backends/status``."""

    backend: str
    available: bool
    message: str


@dataclass
class OkapiRunResult:
    """Normalized runner output consumed by the job manager."""

    success: bool
    output_files: list[str] = field(default_factory=list)
    log: str = ""
    error: str | None = None


class OkapiRunner(ABC):
    """Base runner — each backend implements tikal-equivalent operations."""

    backend_id: str = "base"

    @abstractmethod
    def health_check(self) -> RunnerHealth:
        """Return availability for Hermes wake / UI badges."""

    @abstractmethod
    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        """Execute one registry operation and write artifacts under ``work_dir``."""


def _build_tikal_args(operation: OkapiOperation, input_name: str, output_name: str) -> list[str]:
    """Map registry ``tikal_mode`` to tikal CLI arguments."""
    mode = operation.tikal_mode
    if mode == "extract":
        return ["-x", input_name, "-o", output_name]
    if mode == "merge":
        return ["-m", input_name, "-o", output_name]
    if mode == "qa":
        return ["-x", input_name, "-o", output_name, "-seg", "-check"]
    if mode == "terms":
        return ["-x", input_name, "-o", output_name, "-tt", "terms.tbx"]
    return ["-x", input_name, "-o", output_name]


class MockOkapiRunner(OkapiRunner):
    """Deterministic runner for unit tests — copies input or writes stub XLIFF."""

    backend_id = "mock"

    def __init__(self, available: bool = True) -> None:
        self._available = available

    def health_check(self) -> RunnerHealth:
        if self._available:
            return RunnerHealth(self.backend_id, True, "mock runner ready")
        return RunnerHealth(self.backend_id, False, "mock runner disabled")

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        _ = options
        os.makedirs(work_dir, exist_ok=True)
        output_name = operation.output_primary
        if output_name == "merged-output":
            base = os.path.splitext(os.path.basename(input_path))[0]
            output_name = f"{base}-merged.out"
        output_path = os.path.join(work_dir, output_name)
        if operation.tikal_mode == "extract":
            with open(output_path, "w", encoding="utf-8") as handle:
                handle.write('<?xml version="1.0"?><xliff version="1.2"></xliff>')
        else:
            shutil.copy2(input_path, output_path)
        return OkapiRunResult(success=True, output_files=[output_path], log="mock ok")


class LocalTikalRunner(OkapiRunner):
    """Invoke tikal on the host (pilot box with JRE + Okapi installed)."""

    backend_id = BACKEND_LOCAL_TIKAL

    def __init__(self, tikal_path: str) -> None:
        self._tikal_path = tikal_path

    def health_check(self) -> RunnerHealth:
        if self._tikal_path and os.path.isfile(self._tikal_path):
            return RunnerHealth(self.backend_id, True, f"tikal at {self._tikal_path}")
        return RunnerHealth(
            self.backend_id,
            False,
            "Set okapi.tikal_path in settings to tikal.bat or tikal.sh",
        )

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        _ = options
        input_name = os.path.basename(input_path)
        staged_input = os.path.join(work_dir, input_name)
        os.makedirs(work_dir, exist_ok=True)
        if os.path.abspath(input_path) != os.path.abspath(staged_input):
            shutil.copy2(input_path, staged_input)
        output_name = operation.output_primary
        args = _build_tikal_args(operation, input_name, output_name)
        cmd = [self._tikal_path, *args]
        try:
            completed = subprocess.run(
                cmd,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=600,
                check=False,
            )
            log = (completed.stdout or "") + (completed.stderr or "")
            output_path = os.path.join(work_dir, output_name)
            if completed.returncode != 0:
                return OkapiRunResult(False, [], log, f"tikal exit {completed.returncode}")
            if not os.path.isfile(output_path):
                return OkapiRunResult(False, [], log, f"missing output {output_name}")
            return OkapiRunResult(True, [output_path], log)
        except subprocess.TimeoutExpired:
            return OkapiRunResult(False, [], "", "tikal timed out after 600s")
        except OSError as exc:
            return OkapiRunResult(False, [], "", str(exc))


class DockerTikalRunner(OkapiRunner):
    """Run tikal inside Docker — primary pilot backend (no host Java install)."""

    backend_id = BACKEND_DOCKER

    def __init__(self, docker_image: str) -> None:
        self._image = docker_image

    def health_check(self) -> RunnerHealth:
        if not shutil.which("docker"):
            return RunnerHealth(self.backend_id, False, "docker CLI not found on PATH")
        try:
            completed = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            if completed.returncode == 0:
                return RunnerHealth(self.backend_id, True, f"docker ok; image={self._image}")
            return RunnerHealth(self.backend_id, False, "docker daemon not running")
        except (subprocess.TimeoutExpired, OSError) as exc:
            return RunnerHealth(self.backend_id, False, str(exc))

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        _ = options
        os.makedirs(work_dir, exist_ok=True)
        input_name = os.path.basename(input_path)
        staged_input = os.path.join(work_dir, input_name)
        if os.path.abspath(input_path) != os.path.abspath(staged_input):
            shutil.copy2(input_path, staged_input)
        output_name = operation.output_primary
        tikal_args = _build_tikal_args(operation, f"/work/{input_name}", f"/work/{output_name}")
        cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{os.path.abspath(work_dir)}:/work",
            self._image,
            "tikal",
            *tikal_args,
        ]
        try:
            completed = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=900,
                check=False,
            )
            log = (completed.stdout or "") + (completed.stderr or "")
            output_path = os.path.join(work_dir, output_name)
            if completed.returncode != 0:
                return OkapiRunResult(False, [], log, f"docker tikal exit {completed.returncode}")
            if not os.path.isfile(output_path):
                return OkapiRunResult(False, [], log, f"missing output {output_name}")
            return OkapiRunResult(True, [output_path], log)
        except subprocess.TimeoutExpired:
            return OkapiRunResult(False, [], "", "docker tikal timed out")
        except OSError as exc:
            return OkapiRunResult(False, [], "", str(exc))


class StubRemoteRunner(OkapiRunner):
    """Placeholder for GHA / Longhorn backends — returns actionable configuration errors."""

    def __init__(self, backend_id: str, hint: str) -> None:
        self.backend_id = backend_id
        self._hint = hint

    def health_check(self) -> RunnerHealth:
        return RunnerHealth(self.backend_id, False, self._hint)

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        _ = (operation, input_path, work_dir, options)
        return OkapiRunResult(False, [], "", self._hint)


class HostedWorkspaceRunner(OkapiRunner):
    """Existing hosted Okapi workspace API — upload/download, not full tikal catalog."""

    backend_id = BACKEND_HOSTED

    def __init__(self, app_path: str) -> None:
        self._app_path = app_path

    def health_check(self) -> RunnerHealth:
        # Lazy import keeps ldw_core free of requests when hosted backend unused.
        from scripts.integration_apis import get_okapi_client  # noqa: WPS433

        client = get_okapi_client()
        if not client:
            return RunnerHealth(
                self.backend_id,
                False,
                "Hosted Okapi not configured (api_key, api_url, workspace_id)",
            )
        ok, msg = client.test_connection()
        return RunnerHealth(self.backend_id, ok, msg or "hosted okapi")

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        _ = (operation, work_dir, options)
        from scripts.integration_apis import get_okapi_client  # noqa: WPS433

        client = get_okapi_client()
        if not client:
            return OkapiRunResult(False, [], "", "Hosted Okapi not configured")
        ext = os.path.splitext(input_path)[1].lstrip(".") or "bin"
        ok, data = client.upload_file(input_path, file_type=ext)
        if not ok:
            err = (data or {}).get("error", "upload failed")
            return OkapiRunResult(False, [], "", err)
        return OkapiRunResult(
            True,
            [],
            log=f"uploaded to hosted workspace: {data}",
            error=None,
        )


def build_runner(backend: str, app_path: str, config: dict[str, Any] | None = None) -> OkapiRunner:
    """Factory used by API routes and pipeline manager."""
    cfg = config or load_okapi_config(app_path)
    if backend == BACKEND_DOCKER:
        return DockerTikalRunner(cfg.get("docker_image") or "okapiframework/okapi:latest")
    if backend == BACKEND_LOCAL_TIKAL:
        return LocalTikalRunner(cfg.get("tikal_path") or "")
    if backend == BACKEND_GITHUB:
        return StubRemoteRunner(
            BACKEND_GITHUB,
            "GitHub Actions runner not wired yet — fork ldw-okapi-workflows and set github_repo",
        )
    if backend == BACKEND_LONGHORN:
        url = cfg.get("longhorn_url") or ""
        hint = f"Longhorn URL not configured (longhorn_url). Current: {url or 'empty'}"
        return StubRemoteRunner(BACKEND_LONGHORN, hint)
    if backend == BACKEND_HOSTED:
        return HostedWorkspaceRunner(app_path)
    return StubRemoteRunner(backend, f"Unknown Okapi backend: {backend}")


def resolve_active_backend(app_path: str) -> str:
    """Pick configured backend from integration settings."""
    cfg = load_okapi_config(app_path)
    backend = (cfg.get("backend") or BACKEND_DOCKER).strip()
    if backend not in ALL_BACKENDS:
        return BACKEND_DOCKER
    return backend

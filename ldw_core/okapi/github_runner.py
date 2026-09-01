"""GitHub Actions Okapi runner — user-fork workflow with raw URL file handoff."""

from __future__ import annotations

import base64
import json
import os
import time
import uuid
import zipfile
from typing import Any

import requests

from ldw_core.okapi.github_policy import validate_github_repo
from ldw_core.okapi.operation_registry import OkapiOperation
from ldw_core.okapi.runners import OkapiRunResult, OkapiRunner, RunnerHealth


class GitHubActionsRunner(OkapiRunner):
    """Trigger ``okapi-ops.yml`` on the user's fork; poll artifacts (no shared org runner)."""

    backend_id = "github"

    def __init__(
        self,
        token: str,
        repo: str,
        workflow: str = "okapi-ops.yml",
        branch: str = "main",
    ) -> None:
        self._token = token
        self._repo = repo.strip()
        self._workflow = workflow
        self._branch = branch
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )

    def health_check(self) -> RunnerHealth:
        if not self._token:
            return RunnerHealth(
                self.backend_id,
                False,
                "Add a GitHub personal access token with repo and workflow permissions.",
            )
        ok, message = validate_github_repo(self._repo)
        if not ok:
            return RunnerHealth(self.backend_id, False, message)
        try:
            response = self._session.get(
                f"https://api.github.com/repos/{self._repo}",
                timeout=20,
            )
            if response.status_code == 401:
                return RunnerHealth(self.backend_id, False, "GitHub token was rejected. Check the PAT and its scopes.")
            if response.status_code == 404:
                return RunnerHealth(
                    self.backend_id,
                    False,
                    f"Repository {self._repo} was not found or your token cannot access it.",
                )
            if response.status_code != 200:
                return RunnerHealth(self.backend_id, False, f"GitHub API returned {response.status_code}")
            workflow_resp = self._session.get(
                f"https://api.github.com/repos/{self._repo}/actions/workflows/{self._workflow}",
                timeout=20,
            )
            if workflow_resp.status_code == 404:
                return RunnerHealth(
                    self.backend_id,
                    False,
                    f"Workflow {self._workflow} was not found in {self._repo}. "
                    "Fork the ldw-okapi-workflows template and use the default workflow file.",
                )
            if workflow_resp.status_code != 200:
                return RunnerHealth(
                    self.backend_id,
                    False,
                    f"Could not verify workflow ({workflow_resp.status_code}).",
                )
            return RunnerHealth(
                self.backend_id,
                True,
                f"GitHub ready — {self._repo} ({self._workflow} on {self._branch})",
            )
        except requests.RequestException as exc:
            return RunnerHealth(self.backend_id, False, str(exc))

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        ok, message = validate_github_repo(self._repo)
        if not ok:
            return OkapiRunResult(False, [], "", message)
        if not self._token:
            return OkapiRunResult(False, [], "", "GitHub token is not configured.")
        opts = options or {}
        input_url = opts.get("input_url")
        if not input_url:
            input_url = self._publish_inbox_file(input_path)
        dispatch_time = time.time()
        ok, log = self._dispatch_workflow(operation.id, input_url, opts)
        if not ok:
            return OkapiRunResult(False, [], log, "workflow dispatch failed")
        run_id = self._wait_for_run(dispatch_time)
        if not run_id:
            return OkapiRunResult(False, [], log, "workflow run failed or timed out")
        outputs = self._download_artifacts(run_id, work_dir, operation)
        if not outputs:
            return OkapiRunResult(False, [], log, "no artifacts from workflow run")
        return OkapiRunResult(True, outputs, log)

    def _publish_inbox_file(self, local_path: str) -> str:
        """Upload input to ``.ldw-okapi-inbox/`` on the user fork; return raw.githubusercontent URL."""
        file_name = os.path.basename(local_path)
        inbox_path = f".ldw-okapi-inbox/{uuid.uuid4().hex}/{file_name}"
        with open(local_path, "rb") as handle:
            encoded = base64.b64encode(handle.read()).decode("ascii")
        payload = {
            "message": f"LDW Okapi inbox {file_name}",
            "content": encoded,
            "branch": self._branch,
        }
        url = f"https://api.github.com/repos/{self._repo}/contents/{inbox_path}"
        response = self._session.put(url, json=payload, timeout=120)
        response.raise_for_status()
        return f"https://raw.githubusercontent.com/{self._repo}/{self._branch}/{inbox_path}"

    def _dispatch_workflow(self, operation_id: str, input_url: str, options: dict[str, Any]) -> tuple[bool, str]:
        body = {
            "ref": self._branch,
            "inputs": {
                "operation": operation_id,
                "input_url": input_url,
                "options_json": json.dumps(options),
            },
        }
        url = f"https://api.github.com/repos/{self._repo}/actions/workflows/{self._workflow}/dispatches"
        response = self._session.post(url, json=body, timeout=30)
        log = response.text
        return response.status_code == 204, log

    def _wait_for_run(self, after_epoch: float, timeout_s: int = 900) -> int | None:
        """Poll workflow runs created after dispatch."""
        from datetime import datetime

        deadline = time.time() + timeout_s
        tracked_run_id: int | None = None
        while time.time() < deadline:
            response = self._session.get(
                f"https://api.github.com/repos/{self._repo}/actions/runs",
                params={"event": "workflow_dispatch", "per_page": 10},
                timeout=30,
            )
            if response.status_code == 200:
                for run in response.json().get("workflow_runs", []):
                    created_at = run.get("created_at", "")
                    try:
                        created_ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                    except ValueError:
                        continue
                    if created_ts < after_epoch - 10:
                        continue
                    run_id = int(run["id"])
                    status = run.get("status")
                    if status == "completed":
                        if run.get("conclusion") == "success":
                            return run_id
                        if run.get("conclusion") == "failure":
                            return None
                        continue
                    if status in ("in_progress", "queued", "pending", "waiting"):
                        tracked_run_id = run_id
                if tracked_run_id and self._poll_run_until_done(tracked_run_id):
                    return tracked_run_id if self._run_succeeded(tracked_run_id) else None
            time.sleep(8)
        return None

    def _poll_run_until_done(self, run_id: int, timeout_s: int = 900) -> bool:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            response = self._session.get(
                f"https://api.github.com/repos/{self._repo}/actions/runs/{run_id}",
                timeout=20,
            )
            if response.status_code == 200:
                status = response.json().get("status")
                if status == "completed":
                    return True
            time.sleep(5)
        return False

    def _run_succeeded(self, run_id: int) -> bool:
        response = self._session.get(
            f"https://api.github.com/repos/{self._repo}/actions/runs/{run_id}",
            timeout=20,
        )
        return response.status_code == 200 and response.json().get("conclusion") == "success"

    def _download_artifacts(self, run_id: int, work_dir: str, operation: OkapiOperation) -> list[str]:
        os.makedirs(work_dir, exist_ok=True)
        response = self._session.get(
            f"https://api.github.com/repos/{self._repo}/actions/runs/{run_id}/artifacts",
            timeout=30,
        )
        if response.status_code != 200:
            return []
        outputs: list[str] = []
        expected = operation.output_primary
        for artifact in response.json().get("artifacts", []):
            artifact_id = artifact.get("id")
            if not artifact_id:
                continue
            zip_resp = self._session.get(
                f"https://api.github.com/repos/{self._repo}/actions/artifacts/{artifact_id}/zip",
                timeout=120,
            )
            if zip_resp.status_code != 200:
                continue
            zip_path = os.path.join(work_dir, f"artifact-{artifact_id}.zip")
            with open(zip_path, "wb") as handle:
                handle.write(zip_resp.content)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extractall(work_dir)
            for root, _, files in os.walk(work_dir):
                for name in files:
                    path = os.path.join(root, name)
                    if path in outputs:
                        continue
                    if name == expected:
                        outputs.append(path)
                    elif operation.tikal_mode == "merge" and name.endswith((".docx", ".doc", ".xlsx", ".pptx")):
                        outputs.append(path)
                    elif operation.tikal_mode == "extract" and (
                        name.endswith((".xlf", ".xliff")) or name == expected
                    ):
                        outputs.append(path)
                    elif name.endswith((".html", ".tbx")):
                        outputs.append(path)
        return outputs

"""External Longhorn / Okapi HTTP API runner."""

from __future__ import annotations

import json
import os
from typing import Any

import requests

from ldw_core.okapi.operation_registry import OkapiOperation
from ldw_core.okapi.runners import OkapiRunResult, OkapiRunner, RunnerHealth


class LonghornRunner(OkapiRunner):
    """POST multipart jobs to an external Longhorn-compatible Okapi server."""

    backend_id = "longhorn"

    def __init__(self, base_url: str) -> None:
        self._base = (base_url or "").rstrip("/")
        self._session = requests.Session()

    def health_check(self) -> RunnerHealth:
        if not self._base:
            return RunnerHealth(self.backend_id, False, "longhorn_url is not configured")
        try:
            response = self._session.get(f"{self._base}/health", timeout=10)
            if response.status_code == 200:
                return RunnerHealth(self.backend_id, True, f"longhorn {self._base} ok")
            # Some deployments only expose /api/operations.
            response = self._session.get(f"{self._base}/api/operations", timeout=10)
            if response.status_code == 200:
                return RunnerHealth(self.backend_id, True, f"longhorn {self._base} api ok")
            return RunnerHealth(self.backend_id, False, f"health check HTTP {response.status_code}")
        except requests.RequestException as exc:
            return RunnerHealth(self.backend_id, False, str(exc))

    def run_operation(
        self,
        operation: OkapiOperation,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> OkapiRunResult:
        opts = options or {}
        os.makedirs(work_dir, exist_ok=True)
        endpoints = [
            f"{self._base}/api/okapi/run",
            f"{self._base}/pipeline/execute",
        ]
        last_error = "no endpoint succeeded"
        for endpoint in endpoints:
            try:
                with open(input_path, "rb") as handle:
                    response = self._session.post(
                        endpoint,
                        files={"file": (os.path.basename(input_path), handle)},
                        data={
                            "operation": operation.id,
                            "options_json": json.dumps(opts),
                        },
                        timeout=900,
                    )
                if response.status_code >= 400:
                    last_error = response.text[:500]
                    continue
                # JSON body with output path/url or raw bytes.
                content_type = response.headers.get("Content-Type", "")
                if "application/json" in content_type:
                    payload = response.json()
                    output_name = payload.get("output_file") or operation.output_primary
                    output_path = os.path.join(work_dir, os.path.basename(output_name))
                    download_url = payload.get("download_url")
                    if download_url:
                        file_resp = self._session.get(download_url, timeout=300)
                        file_resp.raise_for_status()
                        with open(output_path, "wb") as out:
                            out.write(file_resp.content)
                    elif payload.get("output_base64"):
                        import base64

                        with open(output_path, "wb") as out:
                            out.write(base64.b64decode(payload["output_base64"]))
                    else:
                        last_error = "longhorn JSON missing download_url/output_base64"
                        continue
                    return OkapiRunResult(True, [output_path], json.dumps(payload)[:2000])
                output_path = os.path.join(work_dir, operation.output_primary)
                with open(output_path, "wb") as out:
                    out.write(response.content)
                return OkapiRunResult(True, [output_path], f"POST {endpoint}")
            except requests.RequestException as exc:
                last_error = str(exc)
        return OkapiRunResult(False, [], "", last_error)

    def discover_operations(self) -> list[dict[str, Any]]:
        """Optional Longhorn capability discovery for UI."""
        try:
            response = self._session.get(f"{self._base}/api/operations", timeout=15)
            if response.status_code == 200:
                data = response.json()
                return data.get("operations", data if isinstance(data, list) else [])
        except requests.RequestException:
            pass
        return []

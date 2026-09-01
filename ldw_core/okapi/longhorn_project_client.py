"""Stock Okapi Longhorn REST client (Rainbow project lifecycle).

Replaces the fantasy ``/api/okapi/run`` gateway. See LDW-Planning ``docs/OKAPI_ROADMAP.md``.
"""

from __future__ import annotations

import logging
import os
import zipfile
from pathlib import Path
from typing import Any

import requests

from ldw_core.okapi.tikal_options import resolve_lang_options

logger = logging.getLogger(__name__)

_BATCH_CONFIG_DIR = Path(__file__).resolve().parent / "batch_configs"

# Registry operation id → embedded batch configuration filename.
OPERATION_BCONF: dict[str, str] = {
    "convert": "xliff_creation.bconf",
    "merge": "xliff_merging.bconf",
}

_PACKAGE_EXTENSIONS = frozenset({".docx", ".doc", ".xlsx", ".xls", ".pptx", ".ppt", ".idml", ".zip"})


class LonghornProjectClient:
    """Ephemeral Rainbow projects against stock ``okapiframework/okapi-longhorn``."""

    def __init__(self, base_url: str, *, timeout: float = 900.0) -> None:
        self._base = (base_url or "").rstrip("/")
        self._timeout = timeout
        self._session = requests.Session()

    def _url(self, path: str) -> str:
        return f"{self._base}{path}"

    def probe_health(self) -> tuple[bool, str]:
        if not self._base:
            return False, "longhorn_url is not configured"
        try:
            response = self._session.get(self._url("/projects"), timeout=15)
            if response.status_code in (200, 204):
                return True, f"longhorn {self._base} ok"
        except requests.RequestException:
            pass
        project_id: str | None = None
        try:
            project_id = self.create_project()
            return True, f"longhorn {self._base} project lifecycle ok"
        except requests.RequestException as exc:
            return False, str(exc)
        finally:
            if project_id:
                try:
                    self.delete_project(project_id)
                except requests.RequestException:
                    logger.debug("longhorn health cleanup failed for %s", project_id)

    def create_project(self) -> str:
        response = self._session.post(self._url("/projects/new"), timeout=60)
        response.raise_for_status()
        project_id = self._parse_project_id(response)
        if not project_id:
            raise RuntimeError("Longhorn did not return a project id")
        return project_id

    @staticmethod
    def _parse_project_id(response: requests.Response) -> str | None:
        if response.text:
            text = response.text.strip().strip('"')
            if text and "/" not in text:
                return text
        try:
            payload = response.json()
        except ValueError:
            return None
        if isinstance(payload, str):
            return payload
        if isinstance(payload, dict):
            for key in ("id", "projectId", "project_id"):
                if payload.get(key):
                    return str(payload[key])
        return None

    def upload_batch_configuration(self, project_id: str, bconf_name: str) -> None:
        path = _BATCH_CONFIG_DIR / bconf_name
        if not path.is_file():
            raise FileNotFoundError(f"missing batch config: {path}")
        with path.open("rb") as handle:
            response = self._session.post(
                self._url(f"/projects/{project_id}/batchConfiguration"),
                files={"file": (bconf_name, handle, "application/octet-stream")},
                timeout=120,
            )
        response.raise_for_status()

    def upload_input_file(self, project_id: str, file_path: str) -> None:
        name = os.path.basename(file_path)
        with open(file_path, "rb") as handle:
            response = self._session.put(
                self._url(f"/projects/{project_id}/inputFiles/{name}"),
                data=handle,
                timeout=300,
            )
        response.raise_for_status()

    def upload_input_zip(self, project_id: str, zip_path: str) -> None:
        with open(zip_path, "rb") as handle:
            response = self._session.post(
                self._url(f"/projects/{project_id}/inputFiles.zip"),
                data=handle,
                headers={"Content-Type": "application/zip"},
                timeout=300,
            )
        response.raise_for_status()

    def execute_task(self, project_id: str, source_lang: str, target_lang: str) -> None:
        src = source_lang.replace("_", "-")
        tgt = target_lang.replace("_", "-")
        response = self._session.post(
            self._url(f"/projects/{project_id}/tasks/execute/{src}/{tgt}"),
            timeout=self._timeout,
        )
        response.raise_for_status()

    def list_output_files(self, project_id: str) -> list[str]:
        response = self._session.get(
            self._url(f"/projects/{project_id}/outputFiles"),
            timeout=60,
        )
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return [str(x) for x in payload]
        if isinstance(payload, dict):
            files = payload.get("files") or payload.get("outputFiles") or []
            return [str(x) for x in files]
        return []

    def download_output_file(self, project_id: str, name: str, dest_path: str) -> None:
        response = self._session.get(
            self._url(f"/projects/{project_id}/outputFiles/{name}"),
            timeout=300,
            stream=True,
        )
        response.raise_for_status()
        os.makedirs(os.path.dirname(dest_path) or ".", exist_ok=True)
        with open(dest_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)

    def download_output_zip(self, project_id: str, dest_path: str) -> None:
        response = self._session.get(
            self._url(f"/projects/{project_id}/outputFiles.zip"),
            timeout=300,
            stream=True,
        )
        response.raise_for_status()
        with open(dest_path, "wb") as handle:
            for chunk in response.iter_content(chunk_size=65536):
                if chunk:
                    handle.write(chunk)

    def delete_project(self, project_id: str) -> None:
        response = self._session.delete(
            self._url(f"/projects/{project_id}"),
            timeout=60,
        )
        if response.status_code not in (200, 204, 404):
            response.raise_for_status()

    def run_operation(
        self,
        operation_id: str,
        input_path: str,
        work_dir: str,
        options: dict[str, Any] | None = None,
    ) -> tuple[bool, list[str], str]:
        """Run one registry operation via ephemeral Longhorn project."""
        opts = options or {}
        bconf = OPERATION_BCONF.get(operation_id)
        if not bconf:
            return False, [], f"no Longhorn batch config for operation: {operation_id}"

        os.makedirs(work_dir, exist_ok=True)
        source_lang, target_lang = resolve_lang_options(opts)
        project_id: str | None = None
        outputs: list[str] = []
        try:
            project_id = self.create_project()
            self.upload_batch_configuration(project_id, bconf)
            ext = os.path.splitext(input_path)[1].lower()
            if ext == ".zip":
                self.upload_input_zip(project_id, input_path)
            else:
                self.upload_input_file(project_id, input_path)
            self.execute_task(project_id, source_lang, target_lang)

            names = self.list_output_files(project_id)
            if not names:
                zip_path = os.path.join(work_dir, "longhorn-output.zip")
                self.download_output_zip(project_id, zip_path)
                self._extract_zip(zip_path, work_dir, outputs)
            else:
                for name in names:
                    dest = os.path.join(work_dir, os.path.basename(name))
                    self.download_output_file(project_id, name, dest)
                    outputs.append(dest)

            if not outputs:
                return False, [], "Longhorn produced no output files"
            return True, outputs, f"longhorn {operation_id} ok"
        except requests.RequestException as exc:
            return False, [], str(exc)
        finally:
            if project_id:
                try:
                    self.delete_project(project_id)
                except requests.RequestException:
                    logger.warning("failed to delete Longhorn project %s", project_id)

    @staticmethod
    def _extract_zip(zip_path: str, work_dir: str, outputs: list[str]) -> None:
        with zipfile.ZipFile(zip_path) as archive:
            archive.extractall(work_dir)
        for root, _, files in os.walk(work_dir):
            for name in files:
                if name == os.path.basename(zip_path):
                    continue
                path = os.path.join(root, name)
                if path not in outputs:
                    outputs.append(path)

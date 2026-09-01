"""Load Okapi backend settings from integration_settings + secrets files."""

from __future__ import annotations

import json
import os
from typing import Any

from ldw_core.paths import get_application_path

# Backend identifiers — Docker tikal is the pilot default per LDW-Planning.
BACKEND_DOCKER = "docker"
BACKEND_LOCAL_TIKAL = "local_tikal"
BACKEND_GITHUB = "github"
BACKEND_LONGHORN = "longhorn"
BACKEND_HOSTED = "hosted"

ALL_BACKENDS = (
    BACKEND_DOCKER,
    BACKEND_LOCAL_TIKAL,
    BACKEND_GITHUB,
    BACKEND_LONGHORN,
    BACKEND_HOSTED,
)

# Built from docker/okapi-tikal/Dockerfile — not a Docker Hub image.
DEFAULT_OKAPI_DOCKER_IMAGE = "ldw-okapi-tikal:1.48"
DEFAULT_OKAPI_VERSION = "1.48.0"


def _settings_paths(app_path: str) -> tuple[str, str]:
    return (
        os.path.join(app_path, "integration_settings.json"),
        os.path.join(app_path, "integration_secrets.json"),
    )


def load_okapi_config(app_path: str | None = None) -> dict[str, Any]:
    """Merge public + secret Okapi settings for runner selection."""
    root = app_path or get_application_path()
    public_path, secrets_path = _settings_paths(root)
    config: dict[str, Any] = {
        "enabled": False,
        "backend": BACKEND_DOCKER,
        "docker_image": DEFAULT_OKAPI_DOCKER_IMAGE,
        "tikal_path": "",
        "github_repo": "",
        "github_workflow": "okapi-ops.yml",
        "github_branch": "main",
        "github_token": "",
        "longhorn_url": "",
        # Hosted workspace client (existing integration_apis.py)
        "api_key": "",
        "api_url": "",
        "workspace_id": "",
    }
    if os.path.isfile(public_path):
        with open(public_path, encoding="utf-8-sig") as handle:
            public = json.load(handle)
        config.update(public.get("okapi", {}))
    if os.path.isfile(secrets_path):
        with open(secrets_path, encoding="utf-8-sig") as handle:
            secrets = json.load(handle)
        config.update(secrets.get("okapi", {}))
    return config

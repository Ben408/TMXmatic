"""Shared path helpers for LDW core (Flask app + launcher)."""

from __future__ import annotations

import os
import sys


def get_application_path() -> str:
    """Return the LDW install root (development tree or frozen executable dir)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    # ldw_core lives one level below the Flask app root (app.py).
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def modules_json_path(app_path: str) -> str:
    """Core-owned registry file path (created by module install.bat)."""
    return os.path.join(app_path, "modules.json")


def jobs_root(app_path: str) -> str:
    """Directory for local v1 job metadata and artifacts."""
    return os.path.join(app_path, "data", "jobs")

"""Pytest fixtures for LDW core Phase 1 API tests."""

from __future__ import annotations

import os
import shutil

import pytest
from flask import Flask

from ldw_core.api_routes import register_ldw_api


@pytest.fixture()
def app_path(tmp_path):
    """Isolated LDW home directory for each test."""
    root = str(tmp_path)
    # Ship Okapi registry + one pipeline template into the temp app root.
    repo_root = os.path.dirname(os.path.dirname(__file__))
    config_src = os.path.join(repo_root, "config")
    if os.path.isdir(config_src):
        shutil.copytree(config_src, os.path.join(root, "config"))
    return root


@pytest.fixture()
def flask_app(app_path):
    """Flask app with Phase 1 + Okapi Phase 2 routes."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    register_ldw_api(app, app_path)
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()

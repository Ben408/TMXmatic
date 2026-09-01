"""Pytest fixtures for LDW core Phase 1 API tests."""

from __future__ import annotations

import os
import tempfile

import pytest
from flask import Flask

from ldw_core.api_routes import create_ldw_api_blueprint


@pytest.fixture()
def app_path(tmp_path):
    """Isolated LDW home directory for each test."""
    return str(tmp_path)


@pytest.fixture()
def flask_app(app_path):
    """Minimal Flask app with only Phase 1 LDW routes (fast unit/integration tests)."""
    app = Flask(__name__)
    app.config["TESTING"] = True
    blueprint = create_ldw_api_blueprint(app_path)
    app.register_blueprint(blueprint)
    return app


@pytest.fixture()
def client(flask_app):
    return flask_app.test_client()

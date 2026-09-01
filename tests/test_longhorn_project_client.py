"""Tests for stock Longhorn REST client."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from ldw_core.okapi.longhorn_project_client import LonghornProjectClient


def test_probe_health_uses_projects_list() -> None:
    client = LonghornProjectClient("http://longhorn.test")
    mock = MagicMock()
    mock.get.return_value.status_code = 200
    client._session = mock
    ok, msg = client.probe_health()
    assert ok is True
    assert "ok" in msg.lower()
    mock.get.assert_called_with("http://longhorn.test/projects", timeout=15)


def test_create_project_parses_plain_text_id() -> None:
    client = LonghornProjectClient("http://longhorn.test")
    mock = MagicMock()
    response = MagicMock()
    response.text = "proj-42"
    mock.post.return_value = response
    client._session = mock
    assert client.create_project() == "proj-42"

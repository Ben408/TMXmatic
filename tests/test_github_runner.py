"""Tests for GitHub Actions runner (mocked HTTP)."""

from unittest.mock import MagicMock, patch

from ldw_core.okapi.github_runner import GitHubActionsRunner
from ldw_core.okapi.operation_registry import OkapiOperation


def test_github_health_requires_token():
    runner = GitHubActionsRunner("", "")
    health = runner.health_check()
    assert health.available is False


def test_github_health_ok_when_repo_reachable():
    runner = GitHubActionsRunner("token", "user/repo")
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    with patch.object(runner._session, "get", return_value=mock_resp):
        health = runner.health_check()
    assert health.available is True


def test_github_dispatch_builds_inbox_url(tmp_path):
    runner = GitHubActionsRunner("token", "user/repo")
    input_file = tmp_path / "in.docx"
    input_file.write_bytes(b"data")
    mock_put = MagicMock()
    mock_put.status_code = 201
    mock_put.json.return_value = {}
    mock_put.raise_for_status = MagicMock()
    with patch.object(runner._session, "put", return_value=mock_put) as put_mock:
        url = runner._publish_inbox_file(str(input_file))
    assert "raw.githubusercontent.com/user/repo" in url
    put_mock.assert_called_once()

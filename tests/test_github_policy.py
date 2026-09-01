"""Tests for GitHub Okapi repo policy."""

from ldw_core.okapi.github_policy import validate_github_repo


def test_blocks_upstream_tmxmatic():
    ok, msg = validate_github_repo("Ben408/TMXmatic")
    assert ok is False
    assert "Fork" in msg or "fork" in msg


def test_blocks_upstream_workflows_template():
    ok, msg = validate_github_repo("ben408/ldw-okapi-workflows")
    assert ok is False


def test_allows_org_fork():
    ok, msg = validate_github_repo("acme-corp/ldw-okapi-workflows")
    assert ok is True
    assert msg == ""


def test_rejects_invalid_format():
    ok, msg = validate_github_repo("not-a-repo")
    assert ok is False

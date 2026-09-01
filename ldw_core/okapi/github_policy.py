"""GitHub Actions Okapi repo policy — block shared upstream run targets."""

from __future__ import annotations

import re

# Upstream repos LDW must never dispatch to (shared org runners / template only).
BLOCKED_GITHUB_REPOS: frozenset[str] = frozenset(
    {
        "ben408/tmxmatic",
        "ben408/ldw-okapi-workflows",
    }
)

OKAPI_WORKFLOWS_TEMPLATE_REPO = "Ben408/ldw-okapi-workflows"
OKAPI_WORKFLOWS_FORK_URL = "https://github.com/Ben408/ldw-okapi-workflows/fork"

_REPO_PATTERN = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def normalize_github_repo(repo: str) -> str:
    return (repo or "").strip()


def validate_github_repo(repo: str) -> tuple[bool, str]:
    """
    Return (ok, message). ``message`` is empty on success or a user-facing error.
    """
    normalized = normalize_github_repo(repo)
    if not normalized:
        return False, (
            "Enter your GitHub repository (for example your-company/ldw-okapi-workflows). "
            "Use a fork you control — not the main TMXmatic app repo."
        )
    if not _REPO_PATTERN.fullmatch(normalized):
        return False, "Repository must look like owner/name (for example acme-corp/ldw-okapi-workflows)."
    key = normalized.lower()
    if key in BLOCKED_GITHUB_REPOS:
        return False, (
            f"{normalized} cannot be used for Okapi jobs. Fork the workflow template to your "
            f"GitHub account or organization, then enter that fork here "
            f"({OKAPI_WORKFLOWS_FORK_URL})."
        )
    return True, ""

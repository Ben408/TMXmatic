#!/usr/bin/env python3
"""Smoke-test Okapi backends: local Docker tikal and optional GitHub Actions."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ldw_core.okapi.config import DEFAULT_OKAPI_DOCKER_IMAGE, load_okapi_config
from ldw_core.okapi.executor import OkapiExecutor
from ldw_core.okapi.github_runner import GitHubActionsRunner
from ldw_core.okapi.runners import DockerTikalRunner, build_runner


def minimal_docx_bytes() -> bytes:
    """Tiny valid DOCX for tikal extract smoke tests."""
    buf = io.BytesIO()
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""
    document = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body><w:p><w:r><w:t>LDW Okapi smoke test.</w:t></w:r></w:p></w:body>
</w:document>"""
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", content_types)
        archive.writestr("_rels/.rels", rels)
        archive.writestr("word/document.xml", document)
    return buf.getvalue()


def smoke_docker(app_path: str, image: str | None) -> int:
    cfg = load_okapi_config(app_path)
    image = image or cfg.get("docker_image") or DEFAULT_OKAPI_DOCKER_IMAGE
    runner = DockerTikalRunner(image)
    health = runner.health_check()
    print("docker health:", json.dumps({"available": health.available, "message": health.message}))
    if not health.available:
        print("Build image: .\\scripts\\build_okapi_tikal_image.ps1", file=sys.stderr)
        return 1

    fixture_dir = Path(app_path) / "data" / "okapi_smoke"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    docx = fixture_dir / "smoke.docx"
    docx.write_bytes(minimal_docx_bytes())
    work_dir = fixture_dir / "work"
    work_dir.mkdir(exist_ok=True)

    executor = OkapiExecutor(app_path)
    result = executor.execute("convert", str(docx), str(work_dir), backend="docker")
    print(
        "convert:",
        json.dumps(
            {
                "success": result.success,
                "outputs": [os.path.basename(p) for p in result.output_files],
                "error": result.error,
            }
        ),
    )
    if not result.success:
        print(result.log[:2000] if result.log else "", file=sys.stderr)
        return 1
    return 0


def smoke_github(app_path: str, *, full: bool = False) -> int:
    cfg = load_okapi_config(app_path)
    token = (cfg.get("github_token") or os.environ.get("OKAPI_GITHUB_TOKEN") or "").strip()
    repo = (cfg.get("github_repo") or os.environ.get("OKAPI_GITHUB_REPO") or "").strip()
    if not token or not repo:
        print(
            "github: SKIP — set github_token + github_repo in integration_secrets.json "
            "or OKAPI_GITHUB_TOKEN / OKAPI_GITHUB_REPO env vars",
        )
        return 0

    runner = GitHubActionsRunner(
        token,
        repo,
        workflow=cfg.get("github_workflow") or "okapi-ops.yml",
        branch=cfg.get("github_branch") or "main",
    )
    health = runner.health_check()
    print("github health:", json.dumps({"available": health.available, "message": health.message}))
    if not health.available:
        return 1

    if not full:
        print("github: repo reachable — pass --full to run convert E2E via workflow dispatch")
        return 0

    fixture_dir = Path(app_path) / "data" / "okapi_smoke"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    docx = fixture_dir / "smoke.docx"
    docx.write_bytes(minimal_docx_bytes())
    work_dir = fixture_dir / "github_work"
    work_dir.mkdir(exist_ok=True)

    from ldw_core.okapi.operation_registry import OkapiOperationRegistry

    convert_op = OkapiOperationRegistry(app_path).get("convert")
    if not convert_op:
        print("github: convert operation missing from registry", file=sys.stderr)
        return 1

    print("github: dispatching convert workflow (may take several minutes)...")
    result = runner.run_operation(convert_op, str(docx), str(work_dir))
    print(
        "convert:",
        json.dumps(
            {
                "success": result.success,
                "outputs": [os.path.basename(p) for p in result.output_files],
                "error": result.error,
            }
        ),
    )
    if not result.success:
        if result.log:
            print(result.log[:3000], file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Okapi backend smoke tests")
    parser.add_argument(
        "target",
        nargs="?",
        choices=("docker", "github", "all"),
        default="all",
    )
    parser.add_argument("--image", help="Docker image tag (default from settings)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="GitHub: run full convert workflow dispatch (slow)",
    )
    parser.add_argument("--app-path", default=str(ROOT))
    args = parser.parse_args()

    code = 0
    if args.target in ("docker", "all"):
        code = smoke_docker(args.app_path, args.image) or code
    if args.target in ("github", "all"):
        code = smoke_github(args.app_path, full=args.full) or code
    return code


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Smoke-test Okapi backends: local Docker tikal and optional GitHub Actions."""

from __future__ import annotations

import argparse
import filecmp
import hashlib
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
from ldw_core.okapi.operation_registry import OkapiOperationRegistry
from ldw_core.okapi.runners import DockerTikalRunner, build_runner
from ldw_core.okapi.tikal_options import DEFAULT_SOURCE_LANG, DEFAULT_TARGET_LANG, merge_xliff_path


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


def default_lang_options() -> dict[str, str]:
    return {"source_lang": DEFAULT_SOURCE_LANG, "target_lang": DEFAULT_TARGET_LANG}


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_xlf_for_compare(path: str) -> str:
    """Compare semantic XLIFF content without caring about attribute order."""
    from lxml import etree

    tree = etree.parse(path)
    root = tree.getroot()
    ns = {"x": "urn:oasis:names:tc:xliff:document:1.2"}
    units: list[tuple[str, str, str, str]] = []
    for file_elem in root.findall(".//x:file", ns):
        src_lang = file_elem.get("source-language", "")
        tgt_lang = file_elem.get("target-language", "")
        for tu in file_elem.findall(".//x:trans-unit", ns):
            source = tu.find("x:source", ns)
            target = tu.find("x:target", ns)
            units.append(
                (
                    src_lang,
                    tgt_lang,
                    (source.text or "") if source is not None else "",
                    (target.text or "") if target is not None else "",
                )
            )
    return json.dumps(units, sort_keys=True)


def smoke_docker(app_path: str, image: str | None, *, roundtrip: bool = False) -> int:
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
    work_dir = fixture_dir / "docker_work"
    if work_dir.exists():
        for child in work_dir.iterdir():
            if child.is_file():
                child.unlink()
    work_dir.mkdir(exist_ok=True)

    lang_opts = default_lang_options()
    executor = OkapiExecutor(app_path)
    result = executor.execute("convert", str(docx), str(work_dir), backend="docker", options=lang_opts)
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

    if not roundtrip:
        return 0

    xliff_path = merge_xliff_path(str(work_dir), str(work_dir / "converted.xlf"))
    merge_result = executor.execute("merge", xliff_path, str(work_dir), backend="docker", options=lang_opts)
    print(
        "merge:",
        json.dumps(
            {
                "success": merge_result.success,
                "outputs": [os.path.basename(p) for p in merge_result.output_files],
                "error": merge_result.error,
            }
        ),
    )
    return 0 if merge_result.success else 1


def smoke_github(app_path: str, *, full: bool = False, roundtrip: bool = False) -> int:
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

    registry = OkapiOperationRegistry(app_path)
    convert_op = registry.get("convert")
    merge_op = registry.get("merge")
    if not convert_op or not merge_op:
        print("github: convert/merge operations missing from registry", file=sys.stderr)
        return 1

    lang_opts = default_lang_options()
    print("github: dispatching convert workflow (may take several minutes)...")
    result = runner.run_operation(convert_op, str(docx), str(work_dir), options=lang_opts)
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

    if not roundtrip:
        return 0

    xliff_path = merge_xliff_path(str(work_dir), str(work_dir / "converted.xlf"))
    if not os.path.isfile(xliff_path):
        print(f"github merge: missing XLIFF at {xliff_path}", file=sys.stderr)
        return 1
    companion_url = runner._publish_inbox_file(str(docx))
    merge_opts = {**lang_opts, "companion_url": companion_url}
    print("github: dispatching merge workflow...")
    merge_result = runner.run_operation(merge_op, xliff_path, str(work_dir), options=merge_opts)
    print(
        "merge:",
        json.dumps(
            {
                "success": merge_result.success,
                "outputs": [os.path.basename(p) for p in merge_result.output_files],
                "error": merge_result.error,
            }
        ),
    )
    return 0 if merge_result.success else 1


def _merged_docx_text_match(docker_docx: Path, github_docx: Path) -> bool:
    import zipfile

    def document_xml(path: Path) -> bytes:
        with zipfile.ZipFile(path) as archive:
            return archive.read("word/document.xml")

    return document_xml(docker_docx) == document_xml(github_docx)


def compare_outputs(app_path: str) -> int:
    docker_xlf = Path(app_path) / "data" / "okapi_smoke" / "docker_work" / "converted.xlf"
    github_xlf = Path(app_path) / "data" / "okapi_smoke" / "github_work" / "converted.xlf"
    docker_docx = Path(app_path) / "data" / "okapi_smoke" / "docker_work" / "smoke.docx"
    github_docx = Path(app_path) / "data" / "okapi_smoke" / "github_work" / "merged-output" / "smoke.docx"
    if not github_docx.is_file():
        github_docx = Path(app_path) / "data" / "okapi_smoke" / "github_work" / "smoke.docx"

    report: dict[str, object] = {}
    if docker_xlf.is_file() and github_xlf.is_file():
        report["xliff_semantic_match"] = _normalize_xlf_for_compare(str(docker_xlf)) == _normalize_xlf_for_compare(
            str(github_xlf)
        )
        report["xliff_bytes_match"] = filecmp.cmp(str(docker_xlf), str(github_xlf), shallow=False)
    else:
        report["xliff_compare"] = "missing converted.xlf from one or both backends"

    if docker_docx.is_file() and github_docx.is_file():
        report["merged_docx_bytes_match"] = filecmp.cmp(str(docker_docx), str(github_docx), shallow=False)
        report["merged_docx_content_match"] = _merged_docx_text_match(docker_docx, github_docx)
        report["merged_docx_sha256"] = {
            "docker": _file_sha256(str(docker_docx)),
            "github": _file_sha256(str(github_docx)),
        }
    else:
        report["merged_docx_compare"] = "missing merged smoke.docx from one or both backends"

    print("compare:", json.dumps(report, indent=2))
    ok = (
        report.get("xliff_semantic_match") is True
        and report.get("merged_docx_content_match") is True
    )
    return 0 if ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Okapi backend smoke tests")
    parser.add_argument(
        "target",
        nargs="?",
        choices=("docker", "github", "all", "compare"),
        default="all",
    )
    parser.add_argument("--image", help="Docker image tag (default from settings)")
    parser.add_argument(
        "--full",
        action="store_true",
        help="GitHub: run full convert workflow dispatch (slow)",
    )
    parser.add_argument(
        "--roundtrip",
        action="store_true",
        help="Run convert + merge on the same smoke.docx fixture",
    )
    parser.add_argument("--app-path", default=str(ROOT))
    args = parser.parse_args()

    code = 0
    roundtrip = args.roundtrip or args.target == "compare"
    full = args.full or args.target in ("all", "compare") or roundtrip

    if args.target in ("docker", "all"):
        code = smoke_docker(args.app_path, args.image, roundtrip=roundtrip) or code
    if args.target in ("github", "all"):
        code = smoke_github(args.app_path, full=full, roundtrip=roundtrip) or code
    if args.target == "compare":
        code = compare_outputs(args.app_path) or code
    elif args.target == "all" and roundtrip and full:
        code = compare_outputs(args.app_path) or code
    return code


if __name__ == "__main__":
    raise SystemExit(main())

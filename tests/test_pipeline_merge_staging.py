"""Pipeline merge companion staging for tikal -m."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ldw_core.okapi.pipeline_manager import HybridPipelineManager  # noqa: E402


def test_stage_merge_companions_renames_converted_xliff(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    step = work / "okapi-merge"
    package = tmp_path / "Outline.docx"
    package.write_bytes(b"PK")
    xliff = work / "gemma-mt" / "converted.xlf"
    xliff.parent.mkdir()
    xliff.write_text("<xliff/>", encoding="utf-8")

    staged = HybridPipelineManager._stage_merge_companions(
        str(work),
        str(step),
        [str(package)],
        str(xliff),
    )

    assert staged is not None
    assert Path(staged).name == "Outline.docx.xlf"
    assert (step / "Outline.docx").is_file()
    assert (step / "Outline.docx.xlf").is_file()
    assert not (step / "converted.xlf").exists()
    assert (step / "Outline.docx.xlf").read_text(encoding="utf-8") == "<xliff/>"


def test_stage_merge_companions_missing_package_returns_none(tmp_path: Path) -> None:
    work = tmp_path / "work"
    work.mkdir()
    step = work / "okapi-merge"
    xliff = work / "converted.xlf"
    xliff.write_text("<xliff/>", encoding="utf-8")

    staged = HybridPipelineManager._stage_merge_companions(
        str(work),
        str(step),
        [],
        str(xliff),
    )
    assert staged is None

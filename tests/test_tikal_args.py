"""Tikal CLI argument mapping for Okapi 1.48+."""

from ldw_core.okapi.operation_registry import OkapiOperation
from ldw_core.okapi.runners import _build_tikal_args


def test_extract_uses_output_directory_flag():
    op = OkapiOperation(
        id="convert",
        label="Convert",
        description="",
        component="tikal",
        complexity="medium",
        tikal_mode="extract",
        input_formats=["docx"],
        output_primary="converted.xlf",
        output_mime="application/xliff+xml",
    )
    args = _build_tikal_args(op, "/work/sample.docx", "converted.xlf", output_dir="/work")
    assert args == ["-x", "/work/sample.docx", "-od", "/work"]

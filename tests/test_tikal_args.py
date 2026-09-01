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
    assert args == ["-x", "/work/sample.docx", "-od", "/work", "-nocopy", "-sl", "en-us", "-tl", "fr-fr"]


def test_extract_html_uses_lenient_filter():
    op = OkapiOperation(
        id="convert",
        label="Convert",
        description="",
        component="tikal",
        complexity="medium",
        tikal_mode="extract",
        input_formats=["xhtml"],
        output_primary="converted.xlf",
        output_mime="application/xliff+xml",
    )
    args = _build_tikal_args(
        op,
        "/work/page.xhtml",
        "converted.xlf",
        output_dir="/work",
        input_path="/work/page.xhtml",
    )
    assert args == [
        "-x",
        "/work/page.xhtml",
        "-od",
        "/work",
        "-nocopy",
        "-sl",
        "en-us",
        "-tl",
        "fr-fr",
        "-fc",
        "okf_html",
    ]


def test_qa_and_terms_also_use_nocopy():
    for mode in ("qa", "terms"):
        op = OkapiOperation(
            id=mode,
            label=mode,
            description="",
            component="tikal",
            complexity="low",
            tikal_mode=mode,
            input_formats=["xlf"],
            output_primary="out",
            output_mime="application/octet-stream",
        )
        args = _build_tikal_args(op, "/work/file.xlf", "out", output_dir="/work")
        assert "-nocopy" in args


def test_merge_does_not_use_nocopy():
    op = OkapiOperation(
        id="merge",
        label="Merge",
        description="",
        component="tikal",
        complexity="medium",
        tikal_mode="merge",
        input_formats=["xlf"],
        output_primary="merged-output",
        output_mime="application/octet-stream",
    )
    args = _build_tikal_args(op, "/work/file.xlf", "merged-output", output_dir="/work")
    assert "-nocopy" not in args

"""Tests for safe XLIFF/TMX language retagging."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from lxml import etree

_ROOT = Path(__file__).resolve().parents[1]
_LR_PATH = _ROOT / "scripts" / "lang_retag.py"
_spec = importlib.util.spec_from_file_location("lang_retag_test", _LR_PATH)
assert _spec and _spec.loader
_lr = importlib.util.module_from_spec(_spec)
sys.modules["lang_retag_test"] = _lr
_spec.loader.exec_module(_lr)

inspect_tmx_languages = _lr.inspect_tmx_languages
inspect_xliff_languages = _lr.inspect_xliff_languages
retag_tmx_languages = _lr.retag_tmx_languages
retag_xliff_languages = _lr.retag_xliff_languages

_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"


def test_retag_xliff_only_file_level_attributes(tmp_path: Path) -> None:
    xliff = tmp_path / "sample.xlf"
    xliff.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file source-language="en-US" target-language="es" datatype="xml">
    <body>
      <trans-unit id="1">
        <source xml:lang="en-US">Visit https://example.com?lang=en-US</source>
        <target xml:lang="es">Visite https://example.com?lang=en-US</target>
      </trans-unit>
    </body>
  </file>
</xliff>
""",
        encoding="utf-8",
    )

    out = tmp_path / "out.xlf"
    result = retag_xliff_languages(
        str(xliff),
        source_lang="en-GB",
        target_lang="es-MX",
        output_path=str(out),
    )

    assert len(result.changes) == 2
    tree = etree.parse(str(out))
    file_el = tree.find(".//{*}file")
    assert file_el is not None
    assert file_el.get("source-language") == "en-GB"
    assert file_el.get("target-language") == "es-MX"

    src = tree.find(".//{*}source")
    tgt = tree.find(".//{*}target")
    assert src is not None and tgt is not None
    assert src.get(_XML_LANG) == "en-US"
    assert "lang=en-US" in (src.text or "")
    assert tgt.get(_XML_LANG) == "es"
    assert "lang=en-US" in (tgt.text or "")


def test_retag_tmx_positional_source_and_target(tmp_path: Path) -> None:
    tmx = tmp_path / "sample.tmx"
    tmx.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header srclang="en_US" adminlang="en_US" datatype="xml" segtype="sentence"/>
  <body>
    <tu>
      <prop type="x-Plural-Source-Group">00d37e599454cb1c207bd0903e8d207d</prop>
      <tuv xml:lang="en_US"><seg>%d Popular Routes</seg></tuv>
      <tuv xml:lang="de"><seg>%d beliebte Routen</seg></tuv>
    </tu>
  </body>
</tmx>
""",
        encoding="utf-8",
    )

    out = tmp_path / "out.tmx"
    result = retag_tmx_languages(
        str(tmx),
        source_find="en_US",
        source_replace="en-US",
        target_find="de",
        target_replace="de-DE",
        output_path=str(out),
    )

    assert result.changes
    tree = etree.parse(str(out))
    header = tree.find(".//{*}header")
    assert header is not None
    assert header.get("srclang") == "en-US"
    assert header.get("adminlang") == "en-US"

    tuvs = tree.findall(".//{*}tu/{*}tuv")
    assert len(tuvs) == 2
    assert tuvs[0].get(_XML_LANG) == "en-US"
    assert tuvs[1].get(_XML_LANG) == "de-DE"
    assert "%d Popular Routes" in (tuvs[0].find(".//{*}seg").text or "")
    prop = tree.find(".//{*}prop")
    assert prop is not None
    assert "00d37e599454cb1c207bd0903e8d207d" in (prop.text or "")


def test_retag_tmx_multilingual_mappings(tmp_path: Path) -> None:
    tmx = tmp_path / "multi.tmx"
    tmx.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <header srclang="en" adminlang="en" datatype="xml" segtype="sentence"/>
  <body>
    <tu>
      <tuv xml:lang="en"><seg>Hello</seg></tuv>
      <tuv xml:lang="fr"><seg>Bonjour</seg></tuv>
    </tu>
    <tu>
      <tuv xml:lang="en"><seg>Bye</seg></tuv>
      <tuv xml:lang="es"><seg>Adiós</seg></tuv>
    </tu>
  </body>
</tmx>
""",
        encoding="utf-8",
    )

    out = tmp_path / "multi_out.tmx"
    retag_tmx_languages(
        str(tmx),
        tuv_mappings={"fr": "fr-FR", "es": "es-419"},
        output_path=str(out),
    )

    tree = etree.parse(str(out))
    langs = [t.get(_XML_LANG) for t in tree.findall(".//{*}tuv")]
    assert "fr-FR" in langs
    assert "es-419" in langs
    assert "fr" not in langs
    assert "es" not in langs


def test_inspect_helpers(tmp_path: Path) -> None:
    xlf = tmp_path / "a.xlf"
    xlf.write_text(
        '<xliff version="1.2"><file source-language="en-US" target-language="fr-FR"/></xliff>',
        encoding="utf-8",
    )
    assert inspect_xliff_languages(str(xlf)) == {
        "source_lang": "en-US",
        "target_lang": "fr-FR",
    }

    tmx = tmp_path / "a.tmx"
    tmx.write_text(
        """<tmx><header srclang="en" adminlang="en"/><body>
    <tu><tuv xml:lang="en"><seg>A</seg></tuv><tuv xml:lang="de"><seg>B</seg></tuv></tu>
    </body></tmx>""",
        encoding="utf-8",
    )
    info = inspect_tmx_languages(str(tmx))
    assert info["srclang"] == "en"
    assert info["source_tuv_langs"] == ["en"]
    assert info["target_tuv_langs"] == ["de"]

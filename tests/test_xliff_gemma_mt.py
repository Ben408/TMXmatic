"""Tests for XLIFF segment MT via translategemma."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from unittest.mock import patch

from lxml import etree

_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_ROOT))

_XO_PATH = _ROOT / "scripts" / "xliff_operations.py"
_xo_spec = importlib.util.spec_from_file_location("xliff_operations_test", _XO_PATH)
assert _xo_spec and _xo_spec.loader
_xo = importlib.util.module_from_spec(_xo_spec)
sys.modules["xliff_operations_test"] = _xo
_xo_spec.loader.exec_module(_xo)
sys.modules["scripts.xliff_operations"] = _xo

_XG_PATH = _ROOT / "scripts" / "xliff_gemma_mt.py"
_xg_spec = importlib.util.spec_from_file_location("xliff_gemma_mt_test", _XG_PATH)
assert _xg_spec and _xg_spec.loader
_xg = importlib.util.module_from_spec(_xg_spec)
sys.modules["xliff_gemma_mt_test"] = _xg
_xg_spec.loader.exec_module(_xg)

translate_xliff_with_gemma = _xg.translate_xliff_with_gemma


def test_translate_xliff_segments_mock_ollama(tmp_path: Path) -> None:
    xlf = tmp_path / "doc.xlf"
    xlf.write_text(
        """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2">
  <file source-language="en-US" target-language="fr-FR">
    <body>
      <trans-unit id="1">
        <source>Hello</source>
        <target></target>
      </trans-unit>
      <trans-unit id="2">
        <source>World</source>
        <target></target>
      </trans-unit>
    </body>
  </file>
</xliff>
""",
        encoding="utf-8",
    )

    def fake_run(source: str, target_lang: str, *, model: str) -> str:
        return {"Hello": "Bonjour", "World": "Monde"}.get(source, source)

    with patch.object(_xg, "_run_translategemma", side_effect=fake_run):
        out, stats = translate_xliff_with_gemma(str(xlf), target_lang="fr-FR")

    assert stats["translated"] == 2
    tree = etree.parse(out)
    targets = [t.text for t in tree.findall(".//{*}target")]
    assert "Bonjour" in targets
    assert "Monde" in targets

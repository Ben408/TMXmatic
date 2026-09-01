"""Tests for exact TMX → XLIFF leverage."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_XL_PATH = _ROOT / "scripts" / "xliff_operations.py"
_spec = importlib.util.spec_from_file_location("xliff_operations", _XL_PATH)
assert _spec and _spec.loader
_xl = importlib.util.module_from_spec(_spec)
sys.modules["xliff_operations_test"] = _xl
_spec.loader.exec_module(_xl)
build_tmx_lookup = _xl.build_tmx_lookup
leverage_tmx_into_xliff = _xl.leverage_tmx_into_xliff


def _write(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8")


def test_leverage_xliff_12_exact_match(tmp_path: Path) -> None:
    tmx = tmp_path / "help.tmx"
    xlf = tmp_path / "page.xlf"
    _write(
        tmx,
        """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4">
  <body>
    <tu>
      <tuv xml:lang="en-US"><seg>Hello world</seg></tuv>
      <tuv xml:lang="fr-CA"><seg>Bonjour le monde</seg></tuv>
    </tu>
  </body>
</tmx>""",
    )
    _write(
        xlf,
        """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en-US" target-language="fr-CA">
    <body>
      <trans-unit id="1">
        <source>Hello world</source>
        <target></target>
      </trans-unit>
      <trans-unit id="2">
        <source>Missing segment</source>
        <target></target>
      </trans-unit>
    </body>
  </file>
</xliff>""",
    )
    out, stats = leverage_tmx_into_xliff(str(tmx), str(xlf))
    assert Path(out).is_file()
    assert stats["updates_made"] == 1
    assert stats["remaining_untranslated"] == 1 or stats["remaining_empty"] == 1
    text = Path(out).read_text(encoding="utf-8")
    assert "Bonjour le monde" in text


def test_build_tmx_lookup_lang_variants(tmp_path: Path) -> None:
    tmx = tmp_path / "tm.tmx"
    _write(
        tmx,
        """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4"><body><tu>
  <tuv xml:lang="en_us"><seg>Account</seg></tuv>
  <tuv xml:lang="fr_ca"><seg>Compte</seg></tuv>
</tu></body></tmx>""",
    )
    lookup, count = build_tmx_lookup(str(tmx), source_lang="en-US", target_lang="fr-CA")
    assert count == 1
    assert lookup["Account"] == "Compte"


def test_leverage_treats_source_copy_as_untranslated(tmp_path: Path) -> None:
    tmx = tmp_path / "help.tmx"
    xlf = tmp_path / "page.xlf"
    _write(
        tmx,
        """<?xml version="1.0" encoding="UTF-8"?>
<tmx version="1.4"><body><tu>
  <tuv xml:lang="en-US"><seg>Settings</seg></tuv>
  <tuv xml:lang="fr-FR"><seg>Paramètres</seg></tuv>
</tu></body></tmx>""",
    )
    _write(
        xlf,
        """<?xml version="1.0" encoding="UTF-8"?>
<xliff version="1.2" xmlns="urn:oasis:names:tc:xliff:document:1.2">
  <file source-language="en-US" target-language="fr-FR">
    <body>
      <trans-unit id="1">
        <source>Settings</source>
        <target>Settings</target>
      </trans-unit>
    </body>
  </file>
</xliff>""",
    )
    out, stats = leverage_tmx_into_xliff(str(tmx), str(xlf))
    assert stats["updates_made"] == 1
    assert "Paramètres" in Path(out).read_text(encoding="utf-8")

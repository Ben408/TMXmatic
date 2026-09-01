"""Tests for xliff_gemma_mt pipeline python step."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Load scripts without package side effects (PythonTmx optional).
_xo_path = ROOT / "scripts" / "xliff_operations.py"
_xo_spec = importlib.util.spec_from_file_location("xliff_operations_ps_test", _xo_path)
assert _xo_spec and _xo_spec.loader
_xo = importlib.util.module_from_spec(_xo_spec)
sys.modules["scripts.xliff_operations"] = _xo
_xo_spec.loader.exec_module(_xo)

_xg_path = ROOT / "scripts" / "xliff_gemma_mt.py"
_xg_spec = importlib.util.spec_from_file_location("xliff_gemma_mt_ps_test", _xg_path)
assert _xg_spec and _xg_spec.loader
_xg = importlib.util.module_from_spec(_xg_spec)
sys.modules["scripts.xliff_gemma_mt"] = _xg
_xg_spec.loader.exec_module(_xg)

from ldw_core.okapi.python_steps import run_python_operation  # noqa: E402


def test_xliff_gemma_mt_python_step_returns_log_json(tmp_path: Path) -> None:
    xlf = tmp_path / "doc.xlf"
    xlf.write_text(
        """<?xml version="1.0"?>
<xliff version="1.2">
  <file source-language="en-US" target-language="pt-BR">
    <body>
      <trans-unit id="1"><source>Hi</source><target></target></trans-unit>
    </body>
  </file>
</xliff>""",
        encoding="utf-8",
    )
    work = tmp_path / "work"
    work.mkdir()

    with patch.object(_xg, "_run_translategemma", return_value="Oi"):
        result = run_python_operation(
            "xliff_gemma_mt",
            str(xlf),
            str(work),
            str(ROOT),
            options={"target_lang": "pt-br"},
        )

    assert result.success is True
    assert result.log
    assert '"translated": 1' in result.log

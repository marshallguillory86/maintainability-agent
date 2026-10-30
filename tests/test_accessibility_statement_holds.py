"""What ACCESSIBILITY.md says about the outputs stays true.

Covers existing behaviour: the statement was written from the code as it is,
so these pass at the base. They exist so that a change which breaks a claim
fails here and the statement is corrected in the same change.
"""
from __future__ import annotations

import copy
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    (root / "src").mkdir(parents=True)
    (root / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    return root


def test_the_html_report_declares_its_language_loads_nothing_and_uses_table_headers(
    tmp_path: Path,
) -> None:
    from maintainability_audit.config import load_config
    from maintainability_audit.renderers import render_html
    from maintainability_audit.report import build_report

    html = render_html(build_report(_tree(tmp_path), copy.deepcopy(load_config(None)),
                                    run_analyzers=False), [])

    assert '<html lang="en"' in html
    assert not re.search(r"<script[^>]+src=|<link[^>]+href=\"https?:", html)
    assert "<th" in html


def test_terminal_output_carries_no_colour_codes(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "-m", "maintainability_audit", "--root", str(_tree(tmp_path))],
        capture_output=True, text=True, env={"PYTHONPATH": str(ROOT / "src"), "PATH": "/usr/bin:/bin"},
        check=False,
    )

    assert result.stdout
    assert "\x1b[" not in result.stdout + result.stderr

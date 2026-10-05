"""D226's fixes, against the installed tools.

Covers existing behaviour: these run the real interrogate and cohesion and
skip where a tool is not installed, so in an environment without them they
pass without proving anything. The falsifiers for the same changes are in
`test_analyzers_report_what_actually_failed.py` and need no tool; these
check that the fixes hold against the tools themselves.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit import _analysis
from maintainability_audit._runner import Outcome
from maintainability_audit._tool_adapters import ADAPTERS


@pytest.mark.skipif(shutil.which("cohesion") is None, reason="cohesion is not installed here")
def test_cohesions_availability_probe_is_a_flag_it_has() -> None:
    probe = subprocess.run(list(ADAPTERS["cohesion"]().version_argv()), capture_output=True, text=True)

    assert probe.returncode == 0, probe.stderr


@pytest.mark.skipif(shutil.which("interrogate") is None, reason="interrogate is not installed here")
def test_an_excluded_unparseable_file_no_longer_hides_the_percentage(tmp_path: Path) -> None:
    (tmp_path / "app.py").write_text('"""Documented."""\n\n\ndef f():\n    """Yes."""\n', encoding="utf-8")
    (tmp_path / "vendor_corpus").mkdir()
    (tmp_path / "vendor_corpus" / "old.py").write_text('print "python 2"\n', encoding="utf-8")
    probe = SimpleNamespace(check=lambda slug, argv: SimpleNamespace(
        usable=True, version="interrogate", outcome=Outcome.RAN, detail=""))

    coverage = _analysis._attempt(tmp_path, ADAPTERS["interrogate"](), probe, 60, _analysis.Analysis(),
                                  ("vendor_corpus/",))

    assert coverage.outcome == "ran" and coverage.measurements == 1, coverage.detail or coverage.parse_error

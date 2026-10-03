"""Cohesion on a tree with no Python is not applicable, not failed.

cohesion is handed explicit `.py` files. With none, it was spawned with an
empty `--files` and exited 2 with a usage error, so every repository
without Python — FFmpeg, most of the corpus — recorded cohesion as a
*failed* tool: a false failure in the analyzer coverage of the report and
of every corpus row. PMD and Checkstyle already answer this with
`has_targets`, which `_attempt` checks before spawning anything.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from maintainability_audit import _analysis
from maintainability_audit._runner import Outcome
from maintainability_audit._tool_adapters import ADAPTERS


def test_no_python_means_not_applicable_and_nothing_spawned(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
    spawned = []
    monkeypatch.setattr(_analysis, "run", lambda *a, **k: spawned.append(a) or None)
    probe = SimpleNamespace(check=lambda slug, argv: SimpleNamespace(
        usable=True, version="1", outcome=Outcome.RAN, detail=""))

    coverage = _analysis._attempt(tmp_path, ADAPTERS["cohesion"](), probe, 60, _analysis.Analysis())

    assert coverage.outcome == "not-applicable"
    assert spawned == []


def test_a_tree_with_python_still_has_targets(tmp_path: Path) -> None:
    (tmp_path / "m.py").write_text("class A:\n    pass\n", encoding="utf-8")

    assert ADAPTERS["cohesion"]().has_targets(tmp_path, ())

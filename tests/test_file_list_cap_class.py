"""Claim 7: no caller silently RANs past the file-list cap (derived class).

The cap itself shipped on 84ff002 (#5): `expand_files` bounds the file
list by the real argv budget and logs a truncation instead of dropping
files silently. That behaviour is pinned in
`test_analyzer_provenance.py::test_expand_files_states_a_truncation...`.

This adds the missing half: the *population of callers*. Every adapter
that turns a directory into an explicit file list goes through the one
`expand_files`, so the single truncation-is-stated guarantee covers all
of them -- but only if they all route through it. The callers are derived
by AST, not hand-listed, so a new adapter that grew its own uncapped
`rglob` file list (silently RAN past any budget) is caught here.

Unnamed member: the **JVM adapters** (`_jvm_adapters`). They are not
exercised by the #5 functional test, but they appear in the derived
caller set and are therefore covered by the shared guarantee; a new JVM
adapter that built its own file list instead would drop out of this set.
"""

from __future__ import annotations

import ast
import logging
from pathlib import Path

from maintainability_audit._metric_adapters import _ARGV_BYTE_BUDGET, expand_files

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _expand_files_callers() -> set[str]:
    callers: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == "expand_files"):
                callers.add(path.name)
    return callers


def test_the_caller_population_is_derived_and_not_empty() -> None:
    callers = _expand_files_callers()
    assert len(callers) >= 2, (
        f"expected several adapters to route file lists through expand_files, "
        f"found {callers}; a caller building its own rglob list would not appear"
    )


def test_truncation_is_stated_so_no_caller_runs_past_it_silently(tmp_path, caplog) -> None:
    """The shared guarantee every caller relies on: a truncation is logged."""
    big = tmp_path / "big"
    (big / "pkg").mkdir(parents=True)
    for i in range((_ARGV_BYTE_BUDGET // 24) + 500):
        (big / "pkg" / f"f_{i:06d}.py").write_text("x", encoding="utf-8")
    with caplog.at_level(logging.WARNING, logger="maintainability_audit._metric_adapters"):
        kept = expand_files(big, ())
    assert any("truncated" in r.message for r in caplog.records), (
        "expand_files truncated without stating it; a caller would RAN past the cap silently"
    )
    assert kept, "the budget must still yield some files"

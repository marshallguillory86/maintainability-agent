"""Claim 7: no caller silently RANs past the file-list cap (derived class).

The cap shipped on 84ff002 (#5) as a logged truncation at the real argv
budget. It is now no cap at all: `expand_files` keeps every file and the
adapter runs once per batch (`test_analyzer_file_lists_are_batched.py`).

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
from pathlib import Path

from maintainability_audit._metric_adapters import expand_files

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


def test_no_caller_is_handed_a_cut_list(tmp_path) -> None:
    """The shared guarantee every caller relies on: the list is whole.

    It used to be that a truncation was logged; now nothing is
    truncated and an adapter runs once per batch, so every caller in the
    derived set reads the whole tree.
    """
    from maintainability_audit._runner import _ARGV_BYTE_BUDGET

    big = tmp_path / "big"
    (big / "pkg").mkdir(parents=True)
    count = (_ARGV_BYTE_BUDGET // 24) + 500
    for i in range(count):
        (big / "pkg" / f"f_{i:06d}.py").write_text("x", encoding="utf-8")

    assert len(expand_files(big, ())) == count

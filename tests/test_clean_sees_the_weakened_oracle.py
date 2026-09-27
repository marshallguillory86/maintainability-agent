"""`clean` fails when the remediating diff weakened the tests (Decision 12).

`clean` failed only on a suppression added to a file the work order named.
The paired test file — the one the pairing rule lets into scope so the
failing test can ship with its fix — could be skipped, aliased, emptied or
made tautological, and `clean` stayed true: the suite went green and the
record said the diff was obedient.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace

from maintainability_audit._conformance import scope_conformance

REPORT = {"work_order": [{"path": "src/pkg/pay.py"}]}
CHANGED = {"src/pkg/pay.py", "tests/test_pay.py"}


def test_a_skip_in_the_paired_test_fails_clean() -> None:
    added = {"tests/test_pay.py": [(3, "@pytest.mark.skip")]}

    record = scope_conformance(REPORT, CHANGED, "main...HEAD", added)

    assert record["conformant"] is True
    assert record["clean"] is False


def test_a_tautology_in_the_paired_test_fails_clean_and_is_named() -> None:
    added = {"tests/test_pay.py": [(9, "    assert True")]}
    removed = {"tests/test_pay.py": [(9, "    assert pay(3) == 9")]}

    record = scope_conformance(REPORT, CHANGED, "main...HEAD", added, removed)

    assert record["clean"] is False
    assert record["oracle_weakened"][0]["kind"] == "assertion that cannot fail"


def test_a_deleted_assertion_fails_clean() -> None:
    removed = {"tests/test_pay.py": [(9, "    assert pay(3) == 9")]}

    record = scope_conformance(REPORT, CHANGED, "main...HEAD", {}, removed)

    assert record["clean"] is False


def test_an_honest_fix_with_a_new_test_stays_clean() -> None:
    added = {"src/pkg/pay.py": [(4, "    return x * 3")],
             "tests/test_pay.py": [(9, "def test_pay():"), (10, "    assert pay(3) == 9")]}

    record = scope_conformance(REPORT, CHANGED, "main...HEAD", added, {})

    assert record["clean"] is True
    assert record["oracle_weakened"] == []


def test_the_real_diff_carries_removed_lines(tmp_path: Path) -> None:
    """End to end: a commit that deletes the assertion fails `clean`."""
    from maintainability_audit._gates import attach_conformance

    def run(*args: str) -> None:
        subprocess.run(args, cwd=tmp_path, check=True, capture_output=True, timeout=120)  # noqa: S603

    run("git", "init", "--quiet", "-b", "main")
    run("git", "config", "user.email", "test@example.invalid")
    run("git", "config", "user.name", "Test")
    run("git", "config", "commit.gpgsign", "false")
    (tmp_path / "tests").mkdir()
    (tmp_path / "pay.py").write_text("def pay(x):\n    return x * 3\n", encoding="utf-8")
    (tmp_path / "tests" / "test_pay.py").write_text(
        "def test_pay():\n    assert pay(3) == 9\n", encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "--quiet", "-m", "first")
    (tmp_path / "tests" / "test_pay.py").write_text("def test_pay():\n    pass\n", encoding="utf-8")
    run("git", "add", "-A")
    run("git", "commit", "--quiet", "-m", "make it green")

    report = {"root": str(tmp_path), "work_order": [{"path": "pay.py"}]}
    attach_conformance(SimpleNamespace(conformance="HEAD~1...HEAD", ask=None), report)

    record = report["scope_conformance"]
    assert record["clean"] is False
    assert record["oracle_weakened"][0]["kind"] == "assertion deleted"

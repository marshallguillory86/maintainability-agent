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


RENAME = """diff --git a/tests/test_old.py b/tests/test_new.py
similarity index 90%
rename from tests/test_old.py
rename to tests/test_new.py
index 1111111..2222222 100644
--- a/tests/test_old.py
+++ b/tests/test_new.py
@@ -2 +2 @@
-    assert pay(3) == 9
+    assert pay(3) == 10
"""

LOOKALIKE = """diff --git a/tests/test_pay.py b/tests/test_pay.py
index 1111111..2222222 100644
--- a/tests/test_pay.py
+++ b/tests/test_pay.py
@@ -3,2 +3,2 @@
--- a/not/a/header.txt
-    assert pay(3) == 9
+++ b/not/a/header.txt
+    assert pay(3) == 10
"""


def test_a_renamed_test_that_changes_a_value_is_not_a_deletion() -> None:
    """Grok, 2026-09-27: removed lines were keyed by the old name, added by the new."""
    from maintainability_audit._oracle import oracle_weakening
    from maintainability_audit.git_tools import _added_from_diff, _removed_from_diff

    added, removed = _added_from_diff(RENAME), _removed_from_diff(RENAME)

    assert set(removed) == set(added) == {"tests/test_new.py"}
    assert oracle_weakening(added, removed) == []


def test_a_content_line_that_looks_like_a_header_is_content() -> None:
    """Inside a hunk, `--- a/x` is a removed line `-- a/x`, not a new file."""
    from maintainability_audit.git_tools import _added_from_diff, _removed_from_diff

    removed, added = _removed_from_diff(LOOKALIKE), _added_from_diff(LOOKALIKE)

    assert set(removed) == set(added) == {"tests/test_pay.py"}
    assert [t for _n, t in removed["tests/test_pay.py"]] == ["-- a/not/a/header.txt", "    assert pay(3) == 9"]
    assert [t for _n, t in added["tests/test_pay.py"]] == ["++ b/not/a/header.txt", "    assert pay(3) == 10"]

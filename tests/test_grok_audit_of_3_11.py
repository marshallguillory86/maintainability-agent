"""Grok's audit of v3.11.0, 2026-09-28: each verified finding, failing first.

1. Git quotes a path with a space or a quote (`--- "a/my file.py"`); the
   diff reader dropped the file, so `clean` never saw it. (High)
2. `skipif`, `skipIf` and `pytest.skip()` were not skips, and any added
   call — `print()` — excused a deleted assertion.
3. A whole test deleted read as "assertion deleted"; it is reported as
   what it is.
4. `--ask`: a glob that matches nothing is recorded, and a malformed ask
   is a usage error rather than a traceback.
5. A symlinked `coverage/` directory was followed; a coverage file that
   fails to parse ended the search instead of trying the next.
6. The report save could create the repository's config, history or
   baseline file.
"""

from __future__ import annotations

import os
import stat
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit._oracle import oracle_weakening
from maintainability_audit.git_tools import _added_from_diff, _removed_from_diff

QUOTED = '''diff --git "a/tests/my test.py" "b/tests/my test.py"
index 1111111..2222222 100644
--- "a/tests/my test.py"
+++ "b/tests/my test.py"
@@ -2 +2 @@
-    assert pay(3) == 9
+    assert True
'''

OCTAL = '''diff --git "a/tests/caf\\303\\251.py" "b/tests/caf\\303\\251.py"
--- "a/tests/caf\\303\\251.py"
+++ "b/tests/caf\\303\\251.py"
@@ -1 +1 @@
-    assert x == 1
+    pass
'''


def test_a_quoted_path_is_read() -> None:
    added, removed = _added_from_diff(QUOTED), _removed_from_diff(QUOTED)

    assert set(added) == set(removed) == {"tests/my test.py"}
    assert oracle_weakening(added, removed), "the weakened quoted test went unseen"


def test_an_octal_escaped_path_is_decoded() -> None:
    assert set(_removed_from_diff(OCTAL)) == {"tests/café.py"}


@pytest.mark.parametrize("line", [
    '@pytest.mark.skipif(sys.platform == "linux", reason="later")',
    '@unittest.skipIf(True, "later")',
    '    pytest.skip("later")',
    "  it.skip('pays', () => {",
    "  xit('pays', () => {",
    "  test.skip('pays', () => {",
])
def test_every_ordinary_skip_is_a_skip(line) -> None:
    assert oracle_weakening({"tests/test_pay.py": [(1, line)]}, {}), line


def test_an_unrelated_call_does_not_excuse_a_deleted_assertion() -> None:
    added = {"tests/test_pay.py": [(2, "    print(pay(3))")]}
    removed = {"tests/test_pay.py": [(2, "    assert pay(3) == 9")]}

    assert oracle_weakening(added, removed)


def test_a_helper_call_still_excuses_it() -> None:
    """Covers existing behaviour: a helper call always excused a deleted assertion;
    this guards that the narrower rule keeps it."""
    added = {"tests/test_pay.py": [(2, "    check_pay(3, 9)")]}
    removed = {"tests/test_pay.py": [(2, "    assert pay(3) == 9")]}

    assert oracle_weakening(added, removed) == []


def test_a_whole_test_deleted_is_named_as_such() -> None:
    removed = {"tests/test_pay.py": [(1, "def test_pay():"), (2, "    assert pay(3) == 9")]}

    found = oracle_weakening({}, removed)

    assert [f["kind"] for f in found] == ["test deleted"]


def test_an_ask_glob_that_matches_nothing_is_recorded() -> None:
    from maintainability_audit._conformance import scope_conformance

    record = scope_conformance({"work_order": []}, {"src/pay.py"}, "main...HEAD",
                               ask={"src/pay.py", "lib/*.py"})

    assert record["ask_unmatched"] == ["lib/*.py"]


def test_a_malformed_ask_is_a_usage_error(tmp_path) -> None:
    from maintainability_audit._gates import attach_conformance

    empty = tmp_path / "ask.txt"
    empty.write_text("# nothing\n", encoding="utf-8")
    report = {"root": str(tmp_path), "work_order": []}

    with pytest.raises(SystemExit) as stopped:
        attach_conformance(SimpleNamespace(conformance="HEAD", ask=str(empty)), report)

    assert stopped.value.code == 2


def _suite_writing(root: Path, body: str) -> dict:
    from maintainability_audit._test_execution import repository_key
    from maintainability_audit._user_config import write_user_answers

    script = root / "run-suite.sh"
    script.write_text("#!/bin/sh\n" + body + "exit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    write_user_answers({"test_execution": {"requested": True,
                                           "commands": {repository_key(root): ["./run-suite.sh"]}}})
    return {"test_execution": {"requested": True}, "expected_commands": {"test": ["./run-suite.sh"]}}


def test_a_symlinked_coverage_directory_is_not_followed(tmp_path) -> None:
    from maintainability_audit._test_execution import run_test_suite

    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    root = tmp_path / "repo"
    root.mkdir()
    os.symlink(elsewhere, root / "coverage", target_is_directory=True)
    config = _suite_writing(root, "printf 'SF:a\\nLF:10\\nLH:10\\nend_of_record\\n' > coverage/lcov.info\n")

    assert run_test_suite(root, config)["coverage_percent"] is None


def test_a_broken_artifact_falls_through_to_the_next(tmp_path) -> None:
    from maintainability_audit._test_execution import run_test_suite

    config = _suite_writing(
        tmp_path,
        "printf 'not xml' > coverage.xml\nmkdir -p coverage\n"
        "printf 'SF:a\\nLF:10\\nLH:5\\nend_of_record\\n' > coverage/lcov.info\n")

    assert run_test_suite(tmp_path, config)["coverage_percent"] == 50.0


@pytest.mark.parametrize("reserved", ["maintainability-agent.json", ".maintainability/history.jsonl",
                                      ".maintainability/baseline.json"])
def test_the_report_cannot_take_an_artifacts_place(tmp_path, reserved) -> None:
    from test_mcp_baseline_payload import _repo

    from maintainability_audit._mcp_audit import InvalidAuditArgument, audit_repository

    root = _repo(tmp_path)
    target = root / reserved
    if target.exists() and reserved != "maintainability-agent.json":
        target.unlink()  # absent: a save must not create it either

    with pytest.raises(InvalidAuditArgument, match="reserved"):
        audit_repository(str(root), roots=(root.parent.resolve(),), record_history=False,
                         format="markdown", output_path=str(target))

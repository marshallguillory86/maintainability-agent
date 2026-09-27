"""Conformance reads a diff against an ask it did not write (Decision 13).

The case that motivated it: the frozen tests were wrong before the agent
saw them, the agent rewrote production code until they passed, and the
test file was byte for byte the one frozen. Nothing weakened a test and
the record was one the agent could not write — and the diff was still
wrong, because nobody had asked for that code. What caught it was reading
the diff against the original ask.

`--conformance` already did that when the ask was this tool's own work
order. `--ask FILE` supplies the ask for work this tool did not order:
paths and globs, one per line, from the operator's path — never
discovered in the audited tree, which would be the writable oracle again.
Still shape: a file inside the ask is not thereby the right change.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit._conformance import read_ask, scope_conformance
from maintainability_audit._operator_reads import PathNotAllowed

REPORT = {"work_order": [{"path": "src/unrelated.py"}]}


def test_production_code_nobody_asked_for_is_out_of_scope() -> None:
    """Every frozen test passed and the diff touched code outside the ask."""
    changed = {"src/pay.py", "src/ledger.py"}

    record = scope_conformance(REPORT, changed, "main...HEAD", {}, {}, ask={"src/pay.py"})

    assert record["ask_source"] == "operator"
    assert record["in_scope"] == ["src/pay.py"]
    assert record["out_of_scope"] == ["src/ledger.py"]
    assert record["out_of_scope_production"] == 1 and record["out_of_scope_tests"] == 0
    assert record["conformant"] is False and record["clean"] is False


def test_the_ask_replaces_the_work_order_as_what_was_named() -> None:
    record = scope_conformance(REPORT, {"src/unrelated.py"}, "main...HEAD", ask={"src/pay.py"})

    assert record["named_paths"] == ["src/pay.py"]
    assert record["out_of_scope"] == ["src/unrelated.py"]


def test_a_glob_in_the_ask_matches_and_a_paired_test_stays_in_scope() -> None:
    changed = {"src/pay/core.py", "tests/test_core.py"}

    record = scope_conformance(REPORT, changed, "main...HEAD", ask={"src/pay/*.py"})

    assert record["in_scope"] == ["src/pay/core.py"]
    assert record["paired_tests"] == ["tests/test_core.py"]
    assert record["conformant"] is True


def test_tests_outside_the_ask_are_counted_apart() -> None:
    changed = {"src/pay.py", "tests/test_ledger.py"}

    record = scope_conformance(REPORT, changed, "main...HEAD", ask={"src/pay.py"})

    assert record["out_of_scope_tests"] == 1 and record["out_of_scope_production"] == 0


def test_without_an_ask_the_work_order_is_the_ask() -> None:
    record = scope_conformance(REPORT, {"src/unrelated.py"}, "main...HEAD")

    assert record["ask_source"] == "work order"
    assert record["conformant"] is True


def test_the_ask_file_is_read_from_the_operators_path(tmp_path: Path) -> None:
    ask = tmp_path / "ask.txt"
    ask.write_text("# the task\nsrc/pay.py\n\n  src/pay/*.py  \n", encoding="utf-8")

    assert read_ask(str(ask)) == {"src/pay.py", "src/pay/*.py"}


def test_an_empty_ask_is_refused_not_read_as_asking_for_nothing(tmp_path: Path) -> None:
    ask = tmp_path / "ask.txt"
    ask.write_text("# nothing yet\n", encoding="utf-8")

    with pytest.raises(ValueError, match="names no path"):
        read_ask(str(ask))


def test_an_ask_that_is_not_a_file_is_refused(tmp_path: Path) -> None:
    """Through the operator-file door, like `--config` and `--baseline`.

    A directory or FIFO named as the ask is refused rather than read or
    waited on. The operator names this path themselves, so it has the
    same trust as `--config`; what it may never be is discovered in the
    audited tree.
    """
    (tmp_path / "ask").mkdir()

    with pytest.raises((PathNotAllowed, ValueError, OSError)):
        read_ask(str(tmp_path / "ask"))


def test_the_cli_takes_an_ask_and_refuses_it_without_conformance() -> None:
    from maintainability_audit._gates import audit_exit_code
    from maintainability_audit.cli import _parse

    _parser, args = _parse(["--ask", "ask.txt"])
    assert args.ask == "ask.txt"

    refused = SimpleNamespace(fail_on_new=False, fail_on_gate=False, fail_on_out_of_scope=False,
                              fail_on_regression=False, baseline=None, conformance=None, ask="ask.txt")
    assert audit_exit_code(refused, {"hard_gate_failures": []}) == 2

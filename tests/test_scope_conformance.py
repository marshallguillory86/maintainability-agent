"""The bounded work order stops being an instruction and becomes checkable.

*Fix exactly these findings and refactor nothing else* is the product's
central claim, and until this check it was enforced socially: the prompt
said it, and nothing compared the diff that came back. An agent that
rewrote half the tree while closing one finding produced a diff this tool
could not distinguish from an obedient one.

What is worth testing here is not the set arithmetic. It is the three
judgments that decide whether the check is usable at all:

- **A fix and its own test are one bounded change.** A check that flagged
  every correct remediation would be switched off in a week, so a test that
  pairs to a named path is in scope by the convention `_test_pairing`
  already uses.
- **A test that pairs to nothing named is still reported**, because "while
  I was here I rewrote the suite" is the drift being watched for.
- **It never scores.** Whether a diff was obedient is a fact about an
  agent's behaviour, not evidence about the code's condition.
"""

from __future__ import annotations

import copy

from maintainability_audit._conformance import scope_conformance

REPORT = {
    "work_order": [
        {"path": "src/pkg/widget.py", "finding_class": "oversized-function"},
        {"path": "src/pkg/gadget.py", "finding_class": "near-duplicate"},
    ]
}


def _record(changed: set[str], report: dict | None = None) -> dict:
    return scope_conformance(report or REPORT, changed, "main...HEAD")


def test_a_diff_inside_the_work_order_is_conformant() -> None:
    record = _record({"src/pkg/widget.py"})

    assert record["conformant"] is True
    assert record["in_scope"] == ["src/pkg/widget.py"]
    assert record["out_of_scope"] == []


def test_a_fix_and_its_own_test_are_one_bounded_change() -> None:
    """The case that decides whether anyone leaves this check switched on.

    A correct remediation nearly always touches a file the work order does
    not name — the test proving the fix. Reporting that as drift would make
    every good remediation look disobedient.
    """
    record = _record({"src/pkg/widget.py", "tests/test_widget.py"})

    assert record["conformant"] is True, "a fix plus its own test must not read as drift"
    assert record["paired_tests"] == ["tests/test_widget.py"]
    assert record["out_of_scope"] == []


def test_a_test_that_pairs_to_nothing_named_is_reported() -> None:
    """The other half: the pairing rule must not become a blanket exemption."""
    record = _record({"src/pkg/widget.py", "tests/test_unrelated_thing.py"})

    assert record["conformant"] is False
    assert record["out_of_scope"] == ["tests/test_unrelated_thing.py"]
    assert record["paired_tests"] == []


def test_an_unrelated_refactor_is_reported() -> None:
    """The failure the whole check exists for."""
    record = _record({"src/pkg/widget.py", "src/pkg/untouched_by_any_finding.py"})

    assert record["conformant"] is False
    assert record["out_of_scope"] == ["src/pkg/untouched_by_any_finding.py"]


def test_addressing_one_item_of_several_is_not_a_violation() -> None:
    """A bounded change may take one finding at a time."""
    record = _record({"src/pkg/widget.py"})

    assert record["conformant"] is True
    assert record["unaddressed"] == ["src/pkg/gadget.py"]


def test_an_empty_work_order_names_nothing_and_flags_everything() -> None:
    """A clean repository hands over no work, so any diff is outside it.

    Reported rather than smoothed over: the honest answer to "did this diff
    stay inside its work order" when there was no work order is that there
    was nothing to stay inside, and a caller should see that rather than a
    reassuring pass.
    """
    record = _record({"src/pkg/widget.py"}, {"work_order": []})

    assert record["work_order_items"] == 0
    assert record["conformant"] is False
    assert record["out_of_scope"] == ["src/pkg/widget.py"]


def test_the_record_never_reaches_a_score() -> None:
    """ADR 007's line: this is behaviour, not code condition.

    The record is attached to the report; it must not carry a dimension, an
    aspect, a grade or a pressure, because a check on an agent's obedience
    that could move a score would let the agent's behaviour change the
    measurement of the code.
    """
    record = _record({"src/pkg/widget.py", "src/other.py"})

    forbidden = {"score", "grade", "estimate", "dimension", "aspect", "pressure",
                 "categories", "maintainability_estimate", "verified_grade"}
    assert not forbidden.intersection(record), (
        f"the conformance record carries scoring keys: "
        f"{sorted(forbidden.intersection(record))}"
    )


def test_the_report_is_not_mutated_by_the_check() -> None:
    before = copy.deepcopy(REPORT)

    scope_conformance(REPORT, {"src/pkg/widget.py", "src/elsewhere.py"}, "main...HEAD")

    assert before == REPORT, "the conformance check mutated the report it read"


def test_the_record_states_that_it_compared_paths_only() -> None:
    """A file in scope means the work order named it, nothing more.

    Without this said out loud, a green conformance record reads as "the
    change was correct", which it cannot establish — the check never opens
    the diff.
    """
    record = _record({"src/pkg/widget.py"})

    assert "Paths only" in record["note"]

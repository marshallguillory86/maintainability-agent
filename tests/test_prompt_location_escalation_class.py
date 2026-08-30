"""Claim 5: the prompt locates every class and withholds the escalated.

Two populations, one claim: the counted work-order classes
(`_items_from_counted`) and the prompt focus categories
(`prompt_focus_sections`). Every counted class must carry a production
location (path plus start_line, or the first entry of a `locations`
list), so a duplicate-only report still yields duplicate-block items with
a place to go -- the #2 escape where the whole class fell out of the
prompt. And a design-review candidate is announced as withheld, so it
must not also be listed under "verify" in any focus category -- the #11
double-listing.

Unnamed focus category: **risk findings**. The escalation test drives a
risk that is also a design_review_candidate and asserts it is absent from
the rendered focus sections; hotspots and large files are the categories
usually named, and risks were the one that leaked. If a new focus
category listed escalated members, the derived escalation assertion
below would catch it.
"""

from __future__ import annotations

from maintainability_audit._identity import risk_identities
from maintainability_audit._work_order import _items_from_counted
from maintainability_audit.prompts import prompt_focus_sections


def _report(**over):
    base = {
        "duplicate_blocks": [], "near_duplicates": [], "dead_code": [],
        "risk_findings": [], "function_hotspots": [], "largest_files": [],
        "hard_gate_failures": [], "design_review_candidates": [],
    }
    base.update(over)
    return base


COUNTED = {
    "duplicate-block": dict(duplicate_blocks=[{"locations": ["src/a.py:40", "src/b.py:9"], "count": 2}]),
    "near-duplicate": dict(near_duplicates=[{"path": "src/d.py", "name": "f", "start_line": 30, "lines": 8}]),
    "dead-code": dict(dead_code=[{"path": "src/c.py", "name": "_u", "start_line": 12}]),
}


def test_every_counted_class_locates_its_items() -> None:
    """Each counted class emits work-order items with a real path and line."""
    for label, payload in COUNTED.items():
        items = _items_from_counted(_report(**payload))
        mine = [i for i in items if i["finding_class"] == label]
        assert mine, f"{label} produced no work-order items (dropped from the prompt)"
        for item in mine:
            assert item["path"], f"{label} item has no path: {item}"
            assert item["line"] is not None, f"{label} item has no line: {item}"


def test_a_duplicate_only_report_still_emits_duplicate_items() -> None:
    items = _items_from_counted(_report(**COUNTED["duplicate-block"]))
    dupes = [i for i in items if i["finding_class"] == "duplicate-block"]
    assert dupes and dupes[0]["path"] == "src/a.py" and dupes[0]["line"] == 40


def test_an_escalated_risk_is_not_listed_under_verify() -> None:
    """A design-review candidate risk is withheld, not listed in focus."""
    risks = [{"path": "src/r.py", "name": "eval_use", "line": 5, "text": "avoid eval"}]
    report = _report(risk_findings=risks)
    fingerprint = risk_identities(report)[("src/r.py", "eval_use", 5)]
    report["design_review_candidates"] = [{"fingerprint": fingerprint, "returns": 2}]

    focus = "\n".join(prompt_focus_sections(report))

    assert "src/r.py:5" not in focus, (
        "an escalated risk was listed under a focus category after being "
        "announced as withheld"
    )


def test_a_non_escalated_risk_is_still_listed() -> None:
    """The over-correction guard: an ordinary risk stays in focus."""
    report = _report(risk_findings=[{"path": "src/r.py", "name": "eval_use", "line": 5, "text": "avoid eval"}])
    focus = "\n".join(prompt_focus_sections(report))
    assert "src/r.py:5" in focus

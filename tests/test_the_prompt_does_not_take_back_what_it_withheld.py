"""Nothing the prompt withholds appears elsewhere in it as work (D207).

One prompt says two things. `_withheld_paragraph` prints *"Not in scope
for this change: N finding(s) need a design decision before code moves
… Do not attempt them here."* `prompt_escalation_note` prints that the
escalated findings are *deliberately excluded*. Then
`prompt_focus_sections` listed those same targets under "to inspect
first", "to verify" and "to inspect".

`withheld_reason` is the one rule, and it has two clauses — a Major
Project, and a finding fixed before that came back. The focus lists
honoured only the second, and only on three of their seven categories:
hotspots, large files and risk findings. Duplicate blocks,
near-duplicates, dead code and competing libraries were filtered by
nothing at all, and no category filtered on the Major Project clause.

This is D180's "one run authorising and forbidding the same change" on a
different axis, and the audit of `e88b429` had already fixed it once —
**for risk findings alone**, written from the instance rather than from
the claim, which is the shape the falsifier standard above the register
exists to stop. So the population here is not a list of categories typed
by a test author: it is **every item the report's own work order marks
withheld**, read back through `withheld_reason`, and the assertion is
that none of their locations survives anywhere in the rendered focus
text.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._prompt_sections import prompt_focus_sections
from maintainability_audit._work_order import (
    Band,
    escalated_fingerprints,
    withheld_reason,
)

#: A report carrying one finding of every class the focus sections
#: render, each with a work-order item that is withheld. Built here
#: rather than from a fixture tree because the point is coverage of the
#: *classes*, and a real repository produces whichever ones it happens to
#: have.
CLASSES: tuple[tuple[str, str, dict[str, Any]], ...] = (
    ("duplicate-block", "duplicate_blocks",
     {"count": 3, "locations": ["dup.py:10", "other.py:20"]}),
    ("near-duplicate", "near_duplicates",
     {"path": "near.py", "start_line": 5, "name": "copy", "similarity": 0.95,
      "duplicate_of": {"path": "orig.py", "start_line": 1, "name": "orig"},
      "cross_file": True}),
    ("dead-code", "dead_code",
     {"path": "dead.py", "start_line": 7, "name": "unused", "lines": 12}),
    ("competing-libraries", "divergent_idioms",
     {"concern": "http", "count": 2,
      "packages": [{"package": "requests", "files": 9, "example": "a.py"},
                   {"package": "httpx", "files": 1, "example": "idiom.py"}]}),
    ("risk-pattern", "risk_findings",
     {"path": "risk.py", "line": 3, "name": "TODO", "text": "fix later"}),
)


def _report() -> dict[str, Any]:
    """Every class present, and every one of them withheld."""
    report: dict[str, Any] = {
        "hard_gate_failures": [],
        "function_hotspots": [
            {"path": "hot.py", "name": "big", "start_line": 4, "lines": 90,
             "status": "fail", "complexity": 20},
        ],
        "largest_files": [{"path": "huge.py", "lines": 900, "status": "fail"}],
        "work_order": [],
        "design_review_candidates": [],
    }
    for _, key, finding in CLASSES:
        report[key] = [finding]
    # Each one a Major Project, which is the clause no category honoured.
    report["work_order"] = [
        {"finding_class": name, "title": f"{name} item", "band": Band.MAJOR_PROJECT.value,
         "path": path, "line": line, "target": "decide", "severity": 1.0, "weight": 1.0}
        for name, path, line in (
            ("duplicate-block", "dup.py", 10),
            ("near-duplicate", "near.py", 5),
            ("dead-code", "dead.py", 7),
            ("competing-libraries", "idiom.py", None),
            ("risk-pattern", "risk.py", 3),
        )
    ]
    # Risk patterns are the one class here the report gives a stable
    # identity to, and `_items_from_counted` stamps their items with it.
    # Omitting it made this fixture claim a shape production never
    # produces — an identified finding whose work-order item is keyed by
    # location — and a first attempt at the fix was written to satisfy
    # that shape, which then suppressed real findings elsewhere.
    for item in report["work_order"]:
        if item["finding_class"] == "risk-pattern":
            item["fingerprint"] = _identity_of(report, item)
    return report


def _identity_of(report: dict[str, Any], item: dict[str, Any]) -> str | None:
    """The fingerprint this class's findings carry, or None if it has none.

    Read from the same identity functions the focus sections use, so a
    test cannot escalate something by a key the renderer would never
    produce — which is how the first version of this file asserted a
    property the data model cannot express.
    """
    from maintainability_audit._identity import risk_identities

    if item["finding_class"] != "risk-pattern":
        return None
    finding = (report.get("risk_findings") or [None])[0]
    if finding is None:
        return None
    return risk_identities(report).get(
        (finding["path"], finding["name"], finding["line"])
    )


def _withheld(report: dict[str, Any]) -> list[dict[str, Any]]:
    """The population, read through the rule the prompt itself applies."""
    blocked = escalated_fingerprints(report)
    return [item for item in report["work_order"]
            if withheld_reason(item, blocked) is not None]
def test_no_withheld_target_is_listed_as_work() -> None:
    """The claim, over every withheld item rather than one class of them."""
    report = _report()
    # Clause two: a fixture that withheld nothing would pass this
    # while saying nothing, which is how the first fix shipped wrong
    # for two of seven categories.
    assert len(_withheld(report)) == len(CLASSES), "fixture withholds fewer classes than it carries"
    text = "\n".join(prompt_focus_sections(report))

    offenders = [
        item["path"] for item in _withheld(report)
        if item["path"] in text
    ]

    assert not offenders, (
        "the prompt withheld these and then listed them as work anyway: "
        f"{sorted(set(offenders))}\n\n{text}"
    )

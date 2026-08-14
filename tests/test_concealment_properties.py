"""Concealment resistance: what withholding evidence can and cannot buy.

Split out of ``test_scoring_calibration`` when that file crossed the
500-line ceiling this project enforces on everyone else. These are the
properties three consecutive audits attacked — the interval containing
its own score, the grade never improving when evidence disappears — and
they read better collected than scattered among the calibration tests.
"""
from __future__ import annotations

from test_scoring_calibration import _evidence_summary, _history, score_report

from maintainability_audit.scoring import _BANDS

# Best grade to worst, read from the scale's own bands rather than
# restated here. A list of letters copied into a test is one more thing
# that can quietly stop matching the rubric it claims to rank, which is
# the class of defect this file exists to catch.
_GRADE_RANK = {grade: rank for rank, (_floor, grade) in enumerate(reversed(_BANDS), start=1)}


def _rank(grade: str | None) -> int:
    """Where a `verified_grade` sits, with withheld below every letter.

    `None` is not a good grade and not a bad one — it is the absence of
    a verified judgment. Ranking it lowest encodes both halves of the
    property: losing a letter by hiding evidence is not an improvement,
    and gaining one where there was none is.
    """
    return 0 if grade is None else _GRADE_RANK[grade]


def _improved(before: str | None, after: str | None) -> bool:
    """Whether `after` is a better verified grade than `before`."""
    return _rank(after) > _rank(before)


# ---------------------------------------------------------------------------
# The interval and the grade have to hold under concealment
# ---------------------------------------------------------------------------

def test_the_interval_always_contains_the_score() -> None:
    """``low <= overall <= high``, including for untested repositories.

    An audit produced a repo scoring 4.4 with a range of [4.5, 4.5]:
    the untested testability cap was applied to the point estimate and
    not to the endpoints, so the "uncertainty interval" excluded the
    number it claimed to bound. Both endpoints now run the same
    pipeline, and the untested boundary is checked explicitly because
    that is the exact case the collapse test missed.
    """
    untested = _evidence_summary(test_file_count=0, declarations_scanned=1000)
    cases = {
        "clean+history": {"summary": _evidence_summary(), "history": _history()},
        "clean shallow": {"summary": _evidence_summary()},
        "untested+history": {"summary": untested, "history": _history()},
        "untested shallow": {"summary": untested},
        "worst+history": {
            "summary": _evidence_summary(file_failures=500, risk_findings=500),
            "history": _history(qualifying_hotspots=50, code_coupling_pairs=50, single_author_files=10),
        },
    }
    for label, report in cases.items():
        result = score_report(report)
        low, high = result["maintainability_range"]
        assert low <= result["maintainability_estimate"] <= high, f"{label}: {result['maintainability_estimate']} outside [{low}, {high}]"


def test_hiding_evidence_can_never_raise_the_grade() -> None:
    """The grade bands the evidence floor, which closes the exploit the
    interval only disclosed.

    With the worst measurable history visible this repo graded C; with
    the same history withheld the point estimate rose and it graded B.
    Printing the interval told a careful human and left every machine
    consumer reading the flattered field. Concealment can only widen the
    interval downward, so grading the floor makes it unprofitable at
    every boundary rather than only at A.
    """
    worst = _history(qualifying_hotspots=20, code_coupling_pairs=20, single_author_files=10)

    visible = score_report({"summary": _evidence_summary(), "history": worst})
    hidden = score_report({"summary": _evidence_summary()})

    # The point estimate is still flattered by concealment — which is
    # precisely why the grade is not read from it.
    assert hidden["maintainability_estimate"] > visible["maintainability_estimate"]

    # Stage 8: there is no compatibility grade to compare. Withholding
    # verification is the stronger property and is asserted directly.
    assert hidden["verified_grade"] is None
    assert hidden["maintainability_range"][0] <= visible["maintainability_range"][0]


def test_withholding_any_single_input_cannot_raise_the_floor_or_the_grade() -> None:
    """The concealment property, swept over every field rather than one.

    The previous version of this test hid the whole history object and
    called the property proven. An audit pointed out — correctly — that
    its name claimed far more than it checked, then demonstrated the
    gap: deleting ``test_file_count`` escaped the untested testability
    cap, because the cap was a penalty that only fired on reports
    carrying the evidence, and the *floor* rose. Sweeping every key here
    found three more fields with the identical shape
    (``file_failures``, ``files_scanned``, ``risk_findings``), where an
    absent count read as "zero findings" instead of "not measured".

    The sweep is over ``summary`` itself, so a field added later is
    covered the day it is added rather than the day someone remembers
    to extend a list.

    The grade half of the name went unchecked for as long as the name
    existed. Only the floor was compared; the grade appeared solely in
    the failure string, reading a ``grade`` key ADR 001 stage 8 removed
    — so the one run that would have printed it would have raised
    ``KeyError`` instead. A message that only executes on failure is a
    message nothing ever ran.
    """
    summary = _evidence_summary(
        test_file_count=0, dead_code_count=40, near_duplicate_count=40, idiom_concern_count=5,
        has_readme=False, has_changelog=False, has_docs_dir=False,
        file_failures=60, function_failures=200, duplicate_blocks=300, risk_findings=80,
    )
    history = _history(qualifying_hotspots=20, code_coupling_pairs=20, single_author_files=10)
    baseline = score_report({"summary": dict(summary), "history": history})

    # The premise, pinned. If the fixture ever stopped earning a
    # verified grade, every comparison below would be None against None
    # and the grade half of this test would prove nothing while still
    # passing.
    assert baseline["verified_grade"] is not None, (
        "the baseline must earn a verified grade or concealing evidence "
        "cannot be shown to leave it alone"
    )

    concealments = {key: {"summary": {k: v for k, v in summary.items() if k != key}, "history": history}
                    for key in summary}
    concealments["<the whole history object>"] = {"summary": dict(summary)}

    gains = []
    for label, report in concealments.items():
        hidden = score_report(report)
        if (hidden["maintainability_range"][0] > baseline["maintainability_range"][0]
                or _improved(baseline["verified_grade"], hidden["verified_grade"])):
            gains.append(
                f"hiding {label}: "
                f"floor {baseline['maintainability_range'][0]} -> {hidden['maintainability_range'][0]}, "
                f"verified_grade {baseline['verified_grade']} -> {hidden['verified_grade']}"
            )

    assert not gains, "withholding evidence improved the graded fields:\n" + "\n".join(gains)

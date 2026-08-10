"""Scoring: how bad is this repo, in what way, and what should be fixed first.

Rewritten in 0.5.0 after the previous model was measured against real
code and found to be scoring repo *size*, not maintainability. Under it
Django, pytest, black, tornado, click, httpx, attrs, lodash, svelte,
axios and fastapi all scored 0.0 / F, while a 53-file toy repo scored
4.6 / A. Findings were counted in absolute terms — 20 oversized files
cost the same in a 50-file project as in a 3,000-file one — so every
real codebase saturated the floor and the scale carried no information.

Three things changed.

**Rates, not counts.** Every pressure is a finding count divided by the
population it was drawn from, so a repo is judged by the share of its
code that is in trouble.

**Calibrated against real code.** Each dimension is divided by the median
that mature, heavily-maintained open-source repositories actually exhibit
on it, so a score speaks in multiples of real-world normal. This matters
more than it sounds: measured raw, duplication runs 15x file-size
pressure and 93x declaration pressure, so summing raw numbers would score
duplication and nothing else. The curve is then fitted so the corpus
median scores 4.0 — a well-run real codebase earns a B, and every grade
above it has to be paid for. See ``_calibration`` for the constants.

**A+ is gated, not averaged.** A mean lets a repo hide one bad dimension
behind four good ones. The top grades additionally require every
dimension to be clean, so A+ means "nothing is wrong anywhere", which is
rare and expensive by design.

Scores exist to aim the remediation prompt. ``dimension_pressures`` is
ordered worst-first for exactly that reason: the generated prompt should
name the specific thing dragging the score, not a letter.
"""
from __future__ import annotations

from typing import Any

from ._aspects import aspect_scores, evidence_aspect_scores, is_untested
from ._calibration import CATEGORIES, GRADE_GATES
from ._formula import (
    CATEGORY_ASPECTS,
    CATEGORY_WEIGHTS,
    UNSCORED,
    clamp_score,
    overall_bounds,
    overall_from_aspects,
)
from ._pressures import (
    _rate,
    dimension_pressures,
    normalize,
    normalize_production,
    production_pressures,
)

__all__ = [
    "CATEGORIES",
    "aspect_scores",
    "clamp_score",
    "dimension_pressures",
    "evidence_aspect_scores",
    "grade_from_score",
    "is_untested",
    "normalize",
    "normalize_production",
    "production_pressures",
    "score_report",
]

_BANDS = [(4.8, "A+"), (4.5, "A"), (4.0, "B"), (3.0, "C"), (2.0, "D"), (0.0, "F")]


def _gate_readings(summary: dict[str, Any], pressures: dict[str, float]) -> dict[str, float]:
    files = summary.get("files_scanned", 0)
    decls = summary.get("declarations_scanned", 0)
    return {
        "file_fail_rate": _rate(summary.get("file_failures", 0), files),
        "decl_fail_rate": _rate(summary.get("function_failures", 0), decls),
        "file_warn_rate": _rate(summary.get("file_warnings", 0), files),
        "decl_warn_rate": _rate(summary.get("function_warnings", 0), decls),
        "duplication": pressures["duplication"],
        "risk": pressures["risk"],
        "gates": float(summary.get("hard_gate_failures", 0)),
    }


def grade_from_score(score: float) -> str:
    """Band a score, ignoring gates. Kept for callers that only have a number."""
    for floor, letter in _BANDS:
        if score >= floor:
            return letter
    return "F"


_GATED_ORDER = ["A+", "A"]


def _gate_failures(grade: str, readings: dict[str, float]) -> list[str]:
    return [
        f"{name} {readings.get(name, 0.0):.3f} exceeds the {grade} ceiling of {ceiling:g}"
        for name, ceiling in GRADE_GATES[grade].items()
        if readings.get(name, 0.0) > ceiling
    ]


def grade_for(score: float, readings: dict[str, float]) -> tuple[str, list[str]]:
    """Band a score, then withhold the top grades unless every gate passes.

    Demotion cascades. A repo denied A+ must still satisfy A's ceilings to
    be given an A — stepping down exactly one grade would let a hard gate
    failure land on A, which is the kind of quiet generosity this rewrite
    exists to remove.

    Returns the grade and the reasons it was capped, which the remediation
    prompt surfaces so "why am I not an A" has an answer naming a specific
    measurement.
    """
    banded = grade_from_score(score)
    if banded not in GRADE_GATES:
        return banded, []
    blockers = _gate_failures(banded, readings)
    if not blockers:
        return banded, []
    for candidate in _GATED_ORDER[_GATED_ORDER.index(banded) + 1 :]:
        if not _gate_failures(candidate, readings):
            return candidate, blockers
    return "B", blockers


def _evidence_rules(
    grade: str, blockers: list[str], aspects: dict[str, float | None], untested: bool | None, history_present: bool
) -> tuple[str, list[str]]:
    """The two rules that keep A-grades honest about evidence.

    No test evidence demotes, stated even when the rubric already landed
    below A on its own — "why is my grade capped" deserves the answer
    regardless of which arithmetic delivered the cap. And an unknown is
    not clean: a shallow clone hides coupling, hotspots and ownership,
    so unmeasured aspects withhold the top grades rather than letting
    "nothing wrong in what could be seen" pass for "nothing is wrong
    anywhere". (CI note: actions/checkout defaults to depth 1; use
    fetch-depth: 0 for the full grade.)

    "Couldn't look" blocks; "looked and there was nothing to measure"
    does not — knowledge_concentration is None on a young repo whose log
    is fully readable but where no file has three commits yet, and that
    None carries no penalty.
    """
    if untested:
        blockers = [*blockers, "no test evidence found: A-grades require it"]
        if grade in GRADE_GATES:
            grade = "B"
    missing = sorted(name for name, value in aspects.items() if value is None)
    if history_present:
        missing = [name for name in missing if name != "knowledge_concentration"]
    if missing:
        # Stated whatever the grade, not only when it is being demoted
        # from an A. Grading on the evidence floor can push a repo well
        # below A on missing evidence alone, and a demotion nobody
        # explains is the failure mode this whole blocker list exists to
        # prevent.
        blockers = [*blockers, f"unmeasured aspects ({', '.join(missing)}): A-grades require full evidence"]
        if grade in GRADE_GATES:
            grade = "B"
    return grade, blockers


def _grade_on_the_floor(
    report: dict[str, Any],
    summary: dict[str, Any],
    pressures: dict[str, float],
    aspects: dict[str, float | None],
    untested: bool | None,
    interval: tuple[float, float, float],
) -> tuple[str, list[str]]:
    """Band the grade from the evidence floor, and say so when it bites.

    The point estimate prices unknowns at the corpus anchor, so a repo
    whose hidden evidence is worse than typical is flattered by hiding
    it — an audit demonstrated 3.9/C with the history visible against
    4.5/B with the same history withheld. Printing the interval made
    that visible to a careful reader while every machine consumer (CI
    gate, badge, ranking, API) kept reading the flattered field.
    Grading the floor makes concealment monotonically unprofitable:
    hiding an aspect can only widen the interval downward, so it can
    never raise the grade. Supply the evidence and the floor rises to
    meet the point estimate.
    """
    overall, low, high = interval
    grade, blockers = grade_for(low, _gate_readings(summary, pressures))
    if low < overall:
        blockers = [
            *blockers,
            f"graded on the evidence floor {low} (point estimate {overall}, ceiling {high}): "
            "unmeasured aspects price at 0 for the grade",
        ]
    return _evidence_rules(grade, blockers, aspects, untested, report.get("history") is not None)


def score_report(report: dict[str, Any]) -> dict[str, Any]:
    """Aspects -> categories -> overall, by the rubric in ``_formula``.

    Every aspect the tool can measure gets a score; every aspect it
    cannot gets None in the report, prices at the corpus anchor (4.0)
    in the numeric rollup, and blocks the A-grades; every aspect of
    maintainability it cannot measure *at all* is named in
    ``rubric.unscored`` with the reason — absence is a statement here,
    never an omission. The calibration constant is fitted so the corpus
    median still rolls up to 4.0 through this exact pipeline.

    The untested cap lands on the categories BEFORE rounding, and the
    overall is computed from the categories exactly as displayed — two
    audits caught two versions of the same lie, an overall that was not
    the mean of the numbers printed beside it.
    """
    summary = report["summary"]
    pressures = dimension_pressures(summary)
    normalized = normalize(pressures)
    aspects = aspect_scores(report, normalized)
    untested = is_untested(summary)
    overall, rounded_categories = overall_from_aspects(aspects, untested=untested)
    low, high = overall_bounds(aspects, untested=untested)

    # The grade is banded from the *floor*, not the point estimate. The
    # point estimate prices unknowns at the corpus anchor, so a repo
    # whose hidden evidence is worse than typical is flattered by hiding
    # it — an audit demonstrated 3.9/C with the history visible against
    # 4.5/B with the same history withheld. Printing the interval made
    # that visible to a careful reader and left every machine consumer
    # (CI gate, badge, ranking) reading the flattered field. Grading the
    # floor makes concealment monotonically unprofitable: hiding an
    # aspect can only widen the interval downward, so it can never raise
    # the grade. Supply the evidence and the floor rises to meet the
    # point estimate.
    grade, blockers = _grade_on_the_floor(report, summary, pressures, aspects, untested, (overall, low, high))
    worst = sorted(normalized.items(), key=lambda item: -item[1])
    return {
        "standard": "ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based",
        "overall": overall,
        "grade": grade,
        # The exact numbers the overall was computed from — the identity
        # "overall == weighted mean of these" is checkable on the report.
        "categories": rounded_categories,
        # The interval the overall lives in once unmeasured aspects are
        # priced at their extremes. Collapses to the overall itself when
        # everything was measured. This is the honest companion to
        # anchor imputation: no single imputed value can stop hiding
        # worse-than-anchor evidence from flattering the point estimate,
        # so the report prints the width of what is not known instead of
        # pretending the point is precise.
        "overall_range": [low, high],
        # The full aspect layer: every score the rubric read, None where
        # the evidence was unavailable rather than clean.
        "aspects": {
            name: (clamp_score(value) if value is not None else None)
            for name, value in aspects.items()
        },
        # The judgment layer, in the open: which aspects feed which
        # category at what weight, and what is not scored at all.
        "rubric": {
            "category_aspects": CATEGORY_ASPECTS,
            "category_weights": CATEGORY_WEIGHTS,
            "unscored": UNSCORED,
        },
        # Multiples of the mature-OSS median: 1.0 is typical real code.
        "dimensions": {name: round(value, 2) for name, value in normalized.items()},
        # Worst-first, so the remediation prompt can lead with the
        # dimension actually costing the most rather than a letter.
        "worst_dimension": worst[0][0] if worst and worst[0][1] > 1.0 else None,
        "grade_blockers": blockers,
        "reference": {
            "unit": "multiple of the median mature-OSS repo (1.0 = typical real code)",
            "note": "Calibrated so a repo at the OSS median on every dimension scores 4.0.",
        },
    }



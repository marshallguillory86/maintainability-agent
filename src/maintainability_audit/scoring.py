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

from ._calibration import (
    CALIBRATION_C,
    CATEGORIES,
    DIMENSION_REFERENCES,
    DIMENSION_WEIGHTS,
    GRADE_GATES,
    WARN_WEIGHT,
)

__all__ = ["CATEGORIES", "score_report", "grade_from_score", "clamp_score"]

_BANDS = [(4.8, "A+"), (4.5, "A"), (4.0, "B"), (3.0, "C"), (2.0, "D"), (0.0, "F")]


def clamp_score(value: float) -> float:
    return round(max(0.0, min(5.0, value)), 1)


def _rate(count: float, population: float) -> float:
    return count / population if population > 0 else 0.0


def dimension_pressures(summary: dict[str, Any]) -> dict[str, float]:
    """The five independently-sourced pressures, as rates.

    Unlike the previous model's five categories — which were five linear
    re-weightings of the same handful of counts — each of these is drawn
    from a different measurement, so they can disagree with each other.
    """
    files = summary.get("files_scanned", 0)
    decls = summary.get("declarations_scanned", 0)
    return {
        "file_size": _rate(summary.get("file_failures", 0), files)
        + WARN_WEIGHT * _rate(summary.get("file_warnings", 0), files),
        "declarations": _rate(summary.get("function_failures", 0), decls)
        + WARN_WEIGHT * _rate(summary.get("function_warnings", 0), decls),
        "duplication": _rate(summary.get("duplicate_blocks", 0), files),
        "risk": _rate(summary.get("risk_findings", 0), files),
        # Gates are discrete policy breaches, not a population sample, so
        # they are scaled to sit on the same footing as a rate.
        "gates": 0.05 * summary.get("hard_gate_failures", 0),
    }


def normalize_production(summary: dict[str, Any]) -> dict[str, float]:
    """Production-only pressures, in the same normalized units."""
    raw = production_pressures(summary)
    return {name: value / DIMENSION_REFERENCES[name] for name, value in raw.items()}


def production_pressures(summary: dict[str, Any]) -> dict[str, float]:
    """The same pressures, counting production code only.

    ``analyzability`` and ``testability`` ask how understandable and how
    testable the *production* code is. Charging them for a long test body
    inverts the incentive — extracting duplicated test setup into a
    fixture would lower the score for improving the code. Falls back to
    the combined counts when a summary predates the split.
    """
    files = summary.get("production_files_scanned", summary.get("files_scanned", 0))
    decls = summary.get("production_declarations_scanned", summary.get("declarations_scanned", 0))
    return {
        "file_size": _rate(summary.get("production_file_failures", summary.get("file_failures", 0)), files)
        + WARN_WEIGHT * _rate(summary.get("production_file_warnings", summary.get("file_warnings", 0)), files),
        "declarations": _rate(
            summary.get("production_function_failures", summary.get("function_failures", 0)), decls
        )
        + WARN_WEIGHT
        * _rate(summary.get("production_function_warnings", summary.get("function_warnings", 0)), decls),
        "gates": 0.05 * summary.get("production_hard_gate_failures", summary.get("hard_gate_failures", 0)),
    }


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


def score_report(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    pressures = dimension_pressures(summary)
    normalized = normalize(pressures)
    overall = _curve(_weighted_mean(normalized))
    readings = _gate_readings(summary, pressures)
    grade, blockers = grade_for(overall, readings)
    worst = sorted(normalized.items(), key=lambda item: -item[1])
    return {
        "standard": "ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based",
        "overall": overall,
        "grade": grade,
        "categories": _iso_categories(normalized, normalize_production(summary)),
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


def normalize(pressures: dict[str, float]) -> dict[str, float]:
    """Express each pressure as a multiple of what real code carries.

    1.0 means "typical of the mature OSS corpus". 2.0 means twice the
    trouble a well-run real codebase shows on that dimension. This is
    the unit the report should speak in, because "duplication 3.1x" is
    actionable in a way that "duplication 0.6346" is not.
    """
    return {name: value / DIMENSION_REFERENCES[name] for name, value in pressures.items()}


def _weighted_mean(normalized: dict[str, float]) -> float:
    total = sum(DIMENSION_WEIGHTS[name] * value for name, value in normalized.items())
    return total / sum(DIMENSION_WEIGHTS[name] for name in normalized)


def _curve(normalized_pressure: float) -> float:
    return clamp_score(5 * CALIBRATION_C / (normalized_pressure + CALIBRATION_C))


def _iso_categories(pressures: dict[str, float], prod: dict[str, float]) -> dict[str, float]:
    """ISO/IEC 25010 view of the same pressures.

    Retained because the category model is what the docs and existing
    baselines speak. Each category is now dominated by a *different*
    measurement rather than being one number re-weighted five times, so
    two categories can genuinely disagree — but they are still views onto
    five inputs, not five independent assessments, and the report says so.

    ``analyzability`` and ``testability`` read the production-only
    pressures: they describe the code under test, not the tests.
    """
    file_size = pressures["file_size"]
    dup, risk, gates = pressures["duplication"], pressures["risk"], pressures["gates"]
    return {
        "modularity": _curve(file_size + dup),
        "reusability": _curve(dup * 2 + file_size * 0.3),
        "analyzability": _curve(prod["declarations"] + risk),
        "modifiability": _curve(gates + dup + risk + file_size * 0.4),
        "testability": _curve(prod["declarations"] * 0.8 + prod["gates"]),
    }

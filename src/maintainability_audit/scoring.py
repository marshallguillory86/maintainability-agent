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

from pathlib import PurePosixPath
from typing import Any

from ._calibration import (
    CALIBRATION_C,
    CATEGORIES,
    DIMENSION_REFERENCES,
    DIMENSION_WEIGHTS,
    GRADE_GATES,
    WARN_WEIGHT,
)
from ._formula import (
    CALIBRATED_ASPECTS,
    CATEGORY_ASPECTS,
    CATEGORY_WEIGHTS,
    UNSCORED,
    overall_from_aspects,
)
from .declarations import DECLARATION_SUFFIXES

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
    return {name: _relative(value, DIMENSION_REFERENCES[name]) for name, value in raw.items()}


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
    """Aspects -> categories -> overall, by the rubric in ``_formula``.

    Every aspect the tool can measure gets a score; every aspect it
    cannot gets None and its weight renormalizes away; every aspect of
    maintainability it cannot measure *at all* is named in
    ``rubric.unscored`` with the reason — absence is a statement here,
    never an omission. The calibration constant is fitted so the corpus
    median still rolls up to 4.0 through this exact pipeline.
    """
    summary = report["summary"]
    pressures = dimension_pressures(summary)
    normalized = normalize(pressures)
    aspects = aspect_scores(report, normalized)
    overall_raw, categories = overall_from_aspects(aspects)
    overall = clamp_score(overall_raw if overall_raw is not None else _curve(_weighted_mean(normalized)))
    readings = _gate_readings(summary, pressures)
    grade, blockers = grade_for(overall, readings)
    # Production code with not one test file cannot take an A-grade,
    # whatever its structural pressures. The top grades are published as
    # meaning "tested"; withholding them here is what makes that sentence
    # true rather than aspirational. Demotion lands on B — the same
    # landing spot as a failed grade gate — and names its reason.
    # .get, not [] — reports written before 0.4.0 carry no
    # test_file_count, and an absent count is "unknown", not "zero".
    untested = summary.get("test_file_count") == 0 and summary.get("production_declarations_scanned", 0) > 0
    if untested:
        # Stated even when the rubric already landed below A on its own:
        # "why is my grade capped" deserves this answer regardless of
        # which arithmetic delivered the cap.
        blockers = [*blockers, "no test files found: A-grades require test evidence"]
        if grade in GRADE_GATES:
            grade = "B"
        if categories.get("testability") is not None:
            categories["testability"] = min(categories["testability"], UNTESTED_TESTABILITY_CAP)
    worst = sorted(normalized.items(), key=lambda item: -item[1])
    return {
        "standard": "ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based",
        "overall": overall,
        "grade": grade,
        "categories": {
            name: (clamp_score(value) if value is not None else None)
            for name, value in categories.items()
        },
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


def normalize(pressures: dict[str, float]) -> dict[str, float]:
    """Express each pressure as a multiple of what real code carries.

    1.0 means "typical of the mature OSS corpus". 2.0 means twice the
    trouble a well-run real codebase shows on that dimension. This is
    the unit the report should speak in, because "duplication 3.1x" is
    actionable in a way that "duplication 0.6346" is not.
    """
    return {name: _relative(value, DIMENSION_REFERENCES[name]) for name, value in pressures.items()}


def _relative(value: float, reference: float) -> float:
    """Express a pressure as a multiple of its reference.

    A reference of zero means the corpus showed none of this at all, so
    there is nothing to be a multiple *of*. Report 0.0 rather than
    dividing — the dimension simply carries no signal for this scale.
    """
    if reference <= 0:
        return 0.0
    return value / reference


def _weighted_mean(normalized: dict[str, float]) -> float:
    total = sum(DIMENSION_WEIGHTS[name] * value for name, value in normalized.items())
    return total / sum(DIMENSION_WEIGHTS[name] for name in normalized)


def _curve(normalized_pressure: float) -> float:
    return clamp_score(5 * CALIBRATION_C / (normalized_pressure + CALIBRATION_C))


# A codebase with no tests at all cannot score better than this on
# testability, whatever its structure looks like. See aspect_scores.
UNTESTED_TESTABILITY_CAP = 2.0


def _banded(value: float, bands: list[tuple[float, float]], floor: float) -> float:
    """Score a rate against ascending (ceiling, score) bands.

    The bands are the standard's judgment calls, written where anyone
    can read or dispute them, informed by the corpus and cohort
    measurements where those exist, and applied identically to every
    repository — which is what makes them a standard rather than an
    opinion.
    """
    for ceiling, score in bands:
        if value <= ceiling:
            return score
    return floor


def _history_rate_aspect(history: dict[str, Any] | None, count_of: str) -> float | None:
    """Hotspot or coupling count as a share of files that changed.

    A rate, not a count — a count would score repository size, which is
    the bug the 0.5.0 rewrite existed to remove. No history means None:
    a shallow CI clone must not grade as either clean or dirty.
    """
    if history is None:
        return None
    changed = history.get("files_changed", 0)
    if changed == 0:
        return 5.0  # had history to read; nothing changed in the window
    if count_of == "hotspots":
        count = sum(
            1 for item in history["hotspots"] if item["commits"] >= 5 and item["complexity"] >= 50
        )
    else:
        # Code-to-code pairs only. README co-changing with CHANGELOG, or
        # config.py with the docs that describe it, is discipline — the
        # wrong-boundary signal this aspect scores lives between source
        # files. The report still lists every pair; only the score
        # filters. (Hotspots need no filter: a doc file has cognitive
        # complexity 0 and never qualifies.)
        count = sum(
            1
            for item in history["change_coupling"]
            if all(PurePosixPath(path).suffix in DECLARATION_SUFFIXES for path in item["files"])
        )
    return _banded(count / changed, [(0.0, 5.0), (0.02, 4.5), (0.05, 4.0), (0.10, 3.0), (0.20, 2.0)], 1.0)


def _test_presence_aspect(summary: dict[str, Any]) -> float | None:
    """Share of *declarations* that live in test files.

    Declarations, not files: a file denominator counts every README and
    changelog against the test ratio, so documenting a repo would lower
    its testability. Zero test files is a score of 0.0; an absent count
    (pre-0.4.0 reports) is None — zero and unknown are different claims.
    """
    test_count = summary.get("test_file_count")
    if test_count is None:
        return None
    if test_count == 0:
        return 0.0
    total = summary.get("declarations_scanned", 0)
    if total == 0:
        return None
    share = (total - summary.get("production_declarations_scanned", 0)) / total
    # Tests exist, so the floor is above "none" even if they hold no
    # parsed declarations (table-driven suites, fixtures-as-data).
    return max(1.5, _banded(share, [(0.05, 1.5), (0.10, 2.5), (0.20, 3.5), (0.30, 4.5)], 5.0))


def _finding_rate_aspect(
    summary: dict[str, Any], count_key: str, bands: list[tuple[float, float]], floor: float
) -> float | None:
    """A finding count as a share of production declarations."""
    count = summary.get(count_key)
    production = summary.get("production_declarations_scanned", 0)
    if count is None or production == 0:
        return None
    return _banded(count / production, bands, floor)


def _ownership_aspect(history: dict[str, Any] | None) -> float | None:
    """Share of settled files (3+ commits) that one person owns alone."""
    if history is None or history.get("multi_commit_files", 0) == 0:
        return None
    share = history["single_author_files"] / history["multi_commit_files"]
    return _banded(share, [(0.2, 5.0), (0.4, 4.0), (0.6, 3.0), (0.8, 2.0)], 1.0)


def _documentation_aspect(summary: dict[str, Any]) -> float | None:
    """Artifact presence: README, changelog, docs directory.

    A proxy for whether anyone can orient, not for whether the words are
    accurate — accuracy is in UNSCORED and stays there.
    """
    readme = summary.get("has_readme")
    if readme is None:
        return None
    extras = int(bool(summary.get("has_changelog"))) + int(bool(summary.get("has_docs_dir")))
    if not readme:
        return 1.5 if extras else 0.5
    return [3.0, 4.0, 5.0][extras]


def aspect_scores(report: dict[str, Any], normalized: dict[str, float]) -> dict[str, float | None]:
    """Every aspect the rubric reads, scored 0-5 or None for unknown.

    Calibrated aspects push their corpus-normalized pressure through the
    score curve, so they inherit the anchor: the corpus median is worth
    the same everywhere. Rubric aspects score evidence the corpus cannot
    price, against the banded thresholds above. None always means "could
    not measure", never "measured nothing wrong" — old reports and
    baselines that predate a count simply do not get an opinion on it.
    """
    summary = report["summary"]
    history = report.get("history")
    scores: dict[str, float | None] = {
        name: _curve(normalized[dimension]) for name, dimension in CALIBRATED_ASPECTS.items()
    }
    # declaration_size reads the *production* pressure. Its only rubric
    # consumers are analyzability and testability, which describe the
    # code under test — an oversized test function must not drag either
    # (pinned by test_analyzability_not_penalized_by_test_function_size).
    scores["declaration_size"] = _curve(normalize_production(summary)["declarations"])
    scores["test_presence"] = _test_presence_aspect(summary)
    scores["dead_code"] = _finding_rate_aspect(
        summary, "dead_code_count", [(0.0, 5.0), (0.001, 4.5), (0.005, 3.5), (0.015, 2.5)], 1.5
    )
    scores["near_duplication"] = _finding_rate_aspect(
        summary,
        "near_duplicate_count",
        [(0.0, 5.0), (0.005, 4.5), (0.01, 4.0), (0.02, 3.0), (0.05, 2.0)],
        1.0,
    )
    concerns = summary.get("idiom_concern_count")
    scores["idiom_consistency"] = (
        None if concerns is None else _banded(concerns, [(0, 5.0), (1, 3.5), (2, 2.5)], 1.5)
    )
    scores["churn_hotspots"] = _history_rate_aspect(history, "hotspots")
    scores["change_coupling"] = _history_rate_aspect(history, "coupling")
    scores["knowledge_concentration"] = _ownership_aspect(history)
    scores["documentation"] = _documentation_aspect(summary)
    return scores

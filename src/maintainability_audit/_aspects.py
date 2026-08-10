"""Every aspect score, from the evidence a report carries.

The layer between raw pressures and the rollup: each function here
turns one kind of measurement into a 0-5 score, and ``aspect_scores``
assembles the thirteen the rubric weights. ``None`` means the evidence
was unavailable, which is a distinct statement from a low score and is
carried as such all the way to the report.

Bands are the standard's judgment calls, stated where they can be
disputed and applied identically to every repository. Both the live
scorer and the corpus derivation call into this module, so the anchor
cannot be fitted through a different set of aspects than a real report
gets scored by.
"""
from __future__ import annotations

from typing import Any

from ._calibration import CALIBRATION_C
from ._formula import CALIBRATED_ASPECTS, curve
from ._pressures import (
    normalize_production,
    production_declarations_measured,
    unmeasured_dimensions,
)


def _curve(normalized_pressure: float) -> float:
    return curve(normalized_pressure, CALIBRATION_C)


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
    # Full counts computed by history_section before its display lists
    # are truncated. Reading len() of a capped list here made the rate
    # fall as repositories grew — the forbidden size-bias class — so an
    # old report that carries only the capped lists reads as unknown
    # rather than as a bogus rate. (code_coupling_pairs counts
    # code-to-code pairs only: README co-changing with CHANGELOG is
    # discipline, not a wrong boundary.)
    key = "qualifying_hotspots" if count_of == "hotspots" else "code_coupling_pairs"
    count = history.get(key)
    if count is None:
        return None
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
    # Test files with zero declarations in them are indistinguishable
    # from empty files, and an audit demonstrated the previous 1.5 floor
    # here priced exactly that: one empty test-shaped artifact bought an
    # A. No test declarations scores the same as no tests.
    if share == 0:
        return 0.0
    return _banded(share, [(0.05, 1.5), (0.10, 2.5), (0.20, 3.5), (0.30, 4.5)], 5.0)


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


def evidence_aspect_scores(summary: dict[str, Any]) -> dict[str, float | None]:
    """The five rubric aspects a summary alone can answer.

    Public and separate from :func:`aspect_scores` because the
    calibration derivation (``_derive``) must price the corpus through
    the *identical* code path users' repositories get — a re-statement
    of these bands in the derivation would drift, and the anchor would
    quietly stop describing the shipped score.
    """
    concerns = summary.get("idiom_concern_count")
    return {
        "test_presence": _test_presence_aspect(summary),
        "dead_code": _finding_rate_aspect(
            summary, "dead_code_count", [(0.0, 5.0), (0.001, 4.5), (0.005, 3.5), (0.015, 2.5)], 1.5
        ),
        "near_duplication": _finding_rate_aspect(
            summary,
            "near_duplicate_count",
            [(0.0, 5.0), (0.005, 4.5), (0.01, 4.0), (0.02, 3.0), (0.05, 2.0)],
            1.0,
        ),
        "idiom_consistency": (
            None if concerns is None else _banded(concerns, [(0, 5.0), (1, 3.5), (2, 2.5)], 1.5)
        ),
        "documentation": _documentation_aspect(summary),
    }


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
    unmeasured = unmeasured_dimensions(summary)
    scores: dict[str, float | None] = {
        name: (None if dimension in unmeasured else _curve(normalized[dimension]))
        for name, dimension in CALIBRATED_ASPECTS.items()
    }
    # declaration_size reads the *production* pressure. Its only rubric
    # consumers are analyzability and testability, which describe the
    # code under test — an oversized test function must not drag either
    # (pinned by test_analyzability_not_penalized_by_test_function_size).
    scores["declaration_size"] = (
        _curve(normalize_production(summary)["declarations"])
        if production_declarations_measured(summary)
        else None
    )
    scores.update(evidence_aspect_scores(summary))
    scores["churn_hotspots"] = _history_rate_aspect(history, "hotspots")
    scores["change_coupling"] = _history_rate_aspect(history, "coupling")
    scores["knowledge_concentration"] = _ownership_aspect(history)
    return scores


def is_untested(summary: dict[str, Any]) -> bool | None:
    """Production code with no test evidence at all — or no evidence either way.

    Three-valued, and the third value is the point. ``True`` is "there
    are no tests", ``False`` is "there are", and ``None`` is "this
    report does not say". Integer evidence, not the aspect's float: no
    test files, or test files holding zero declarations (an empty
    test-shaped artifact), both count as untested.

    Returning a plain ``False`` for the unknown case is what an audit
    exploited. The testability cap is a penalty that fired only on
    reports carrying the evidence, so deleting ``test_file_count``
    escaped it and *raised the evidence floor* — concealment paying
    again, one level below the interval that was supposed to have
    closed it. Unknown is now carried as unknown and priced by the same
    dial as every other unknown: typical for the point estimate,
    worst-case for the floor the grade is banded from.
    """
    test_count = summary.get("test_file_count")
    production = summary.get("production_declarations_scanned")
    if test_count is None or production is None:
        return None
    if production <= 0:
        return False
    return test_count == 0 or summary.get("declarations_scanned", 0) - production == 0

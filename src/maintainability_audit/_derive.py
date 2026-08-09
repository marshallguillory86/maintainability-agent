"""Turning corpus measurements into the calibration constants.

Kept as pure functions, separate from both the constants themselves and
from the tool that fetches the corpus, for one reason: it makes the
calibration *auditable offline*. ``tools/calibration/measure.py`` does the
network work once and writes ``measurements.json``; everything from there
to the numbers in ``_calibration`` is deterministic arithmetic that a test
can re-run with no clone, no network, and no trust required.

Without this split the constants would be numbers someone once computed on
their own machine — exactly the kind of unfalsifiable claim this scoring
rewrite exists to stop making.
"""
from __future__ import annotations

from statistics import median
from typing import Any

from ._formula import CALIBRATED_ASPECTS, overall_from_aspects

DIMENSIONS = ("file_size", "declarations", "duplication", "risk", "gates")

# Enough repos that one unusual codebase cannot move a median on its own.
MIN_CORPUS_SIZE = 8

# References that are a fixed unit rather than something the corpus
# measures, and the values themselves.
#
# Hard gates are discrete policy breaches a repository opts into, not a
# rate drawn from a population, so there is no meaningful median to
# divide by — and once gating became opt-in the corpus median went to
# zero, which would have made the dimension silently ignore real
# failures. 0.05 is one gate failure, so one breach reads as 1.0x.
#
# **This module is the authority, deliberately.** Reading the value back
# out of ``_calibration`` instead would make
# ``test_dimension_references_match_the_measured_corpus`` compare the
# constant against itself, and a hand-edited ``gates`` would pass the one
# test written to catch hand-edited constants.
FIXED_REFERENCES: dict[str, float] = {"gates": 0.05}


def derive_references(measurements: list[dict[str, Any]]) -> dict[str, float]:
    """Median raw pressure per dimension across the corpus.

    The median rather than the mean: lodash carries 6.8x the corpus
    duplication and would drag a mean noticeably, and a reference is
    supposed to describe typical code, not average code.
    """
    if len(measurements) < MIN_CORPUS_SIZE:
        raise ValueError(f"corpus has {len(measurements)} repos; at least {MIN_CORPUS_SIZE} required")
    return {
        dimension: (
            FIXED_REFERENCES[dimension]
            if dimension in FIXED_REFERENCES
            else round(median(entry["dimensions"][dimension] for entry in measurements), 4)
        )
        for dimension in DIMENSIONS
    }


def normalized_pressures(
    measurements: list[dict[str, Any]],
    references: dict[str, float],
    weights: dict[str, float],
) -> list[float]:
    """Each repo's weighted mean pressure, in units of the reference."""
    total_weight = sum(weights[dimension] for dimension in DIMENSIONS)
    values = []
    for entry in measurements:
        weighted = sum(
            weights[dimension] * entry["dimensions"][dimension] / references[dimension]
            for dimension in DIMENSIONS
            # A dimension the corpus never exhibits has no reference to
            # divide by and contributes nothing.
            if references[dimension] > 0
        )
        values.append(weighted / total_weight)
    return values


def _corpus_overall(entry: dict[str, Any], references: dict[str, float], c: float) -> float:
    """One repo's rubric rollup, from every aspect the corpus can supply.

    Structural aspects come from the stored dimension pressures; the
    summary-derived rubric aspects (test presence, dead code,
    near-duplication, idioms, documentation) come from the stored
    ``evidence`` block, priced by ``scoring.evidence_aspect_scores`` —
    the *same function* a live report goes through, so the anchor cannot
    drift from the shipped score. History aspects stay None: the corpus
    is pinned via shallow fetches, so its history is genuinely
    unmeasurable, and they price at the corpus anchor here exactly as
    they do for any shallow clone. Entries measured before evidence was
    recorded fall back to structural-only.
    """
    from .scoring import evidence_aspect_scores, production_pressures  # local: avoids import cycle at module load

    scores: dict[str, float | None] = {
        aspect: 5 * c / (entry["dimensions"][dimension] / references[dimension] + c)
        for aspect, dimension in CALIBRATED_ASPECTS.items()
        if references[dimension] > 0
    }
    evidence = entry.get("evidence")
    if evidence is not None:
        summary = {
            **evidence,
            "files_scanned": entry["files"],
            "declarations_scanned": entry["declarations"],
        }
        scores.update(evidence_aspect_scores(summary))
        if references["declarations"] > 0:
            production = production_pressures(summary)["declarations"] / references["declarations"]
            scores["declaration_size"] = 5 * c / (production + c)
    # Mirror the live path to the digit: categories are rounded to one
    # decimal before the overall, because that is what score_report
    # ships. An audit found six of forty corpus repos differing between
    # the rounded and unrounded paths while the docs said "same
    # pipeline" — the anchor must go through the same rounding or the
    # word "same" is decoration.
    _, categories = overall_from_aspects(scores)
    rounded = {name: round(max(0.0, min(5.0, value)), 1) for name, value in categories.items()}
    return sum(rounded.values()) / len(rounded)


def derive_curve_constant(
    measurements: list[dict[str, Any]],
    references: dict[str, float],
    weights: dict[str, float],
    target_score: float = 4.0,
) -> float:
    """Fit ``c`` so the corpus median *rolls up* to ``target_score``.

    The overall is no longer ``curve(weighted mean pressure)`` — it is
    the rubric rollup: each structural pressure curved into an aspect
    score, aspects averaged into categories, categories into the
    overall. ``c`` appears inside every per-aspect curve, so there is no
    closed form any more; the median rollup is monotonic in ``c``, and a
    bisection recovers it to 4 decimal places.

    ``weights`` stays in the signature for the callers and tests that
    pass it, but the rollup weights now live in ``_formula`` — the
    dimension weights only steer the fallback score and worst-dimension
    readout in ``scoring``.

    The median repo still does not sit at 1.0x on every dimension: no
    single repo is median at everything, so fitting to the observed
    rollup is what keeps "a well-run real codebase earns a B" literally
    true rather than approximately intended.
    """
    del weights  # rollup weights come from _formula; see docstring
    if not 0 < target_score < 5:
        raise ValueError("target_score must be between 0 and 5 exclusive")

    def median_overall(c: float) -> float:
        return median(_corpus_overall(entry, references, c) for entry in measurements)

    low, high = 1e-3, 1e3
    for _ in range(200):
        mid = (low + high) / 2
        if median_overall(mid) < target_score:
            low = mid
        else:
            high = mid
    fitted = (low + high) / 2
    # The rounded pipeline is a step function, so the bisection can land
    # on a tread adjacent to the target (median 3.99). Scan the
    # neighborhood for the plateau where the median hits the target
    # exactly and return its midpoint; keep the bisection value when no
    # such plateau exists.
    plateau = [
        round(fitted + offset * 0.001, 4)
        for offset in range(-80, 81)
        if median_overall(fitted + offset * 0.001) == target_score
    ]
    if plateau:
        return round((plateau[0] + plateau[-1]) / 2, 4)
    return round(fitted, 4)

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


def derive_curve_constant(
    measurements: list[dict[str, Any]],
    references: dict[str, float],
    weights: dict[str, float],
    target_score: float = 4.0,
) -> float:
    """Fit ``c`` in ``score = 5c/(n+c)`` so the corpus median hits ``target_score``.

    Solving ``5c/(n+c) = t`` for ``c`` gives ``c = n*t/(5-t)``; at the
    default target of 4.0 that is ``4n``.

    Note the median repo does not sit at n = 1.0 even though every
    reference is a median: no single repo is simultaneously median on all
    five dimensions, so the median of the means is not the mean of the
    medians. Fitting to the observed value is what keeps the documented
    claim — "a well-run real codebase earns a B" — literally true.
    """
    if not 0 < target_score < 5:
        raise ValueError("target_score must be between 0 and 5 exclusive")
    observed = median(normalized_pressures(measurements, references, weights))
    return round(observed * target_score / (5 - target_score), 4)

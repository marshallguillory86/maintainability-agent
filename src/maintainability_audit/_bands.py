"""The band matrix: measurements to pressure — ADR 008.

A threshold turns cyclomatic complexity 14 and complexity 45 into the same
fact, one failure each. The difference between extracting a guard clause and
redesigning a module is exactly the information the reader wanted, so a
measurement is mapped through **ordered ranges** to a pressure between 0 and 1
instead of being compared to a single line.

Hard gates keep their binary character. Bands drive the *score*; gates drive
the *exit code*. A policy line is meant to be crossed or not.

**Boundaries are anchored on thresholds that already exist**, not invented
here. `warn_complexity` (10) and `max_complexity` (15) are the project's
calibrated judgments, with the cognitive pair fitted against 21,300 corpus
declarations where 15 sits near the 94th percentile and 25 near the 97th.
Deriving fresh boundaries from one repository's distribution would replace a
corpus-backed judgment with an n=1 one — which is the mistake this module is
positioned to make and must not.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# Pressure a measurement contributes, by band. Zero is "nothing to say here";
# one is "as bad as this scale expresses". The intermediate values are evenly
# spaced on purpose: an uneven curve would be a second, undocumented judgment
# layered on the boundaries, and one arguable thing per decision is enough.
CLEAN, MILD, ELEVATED, HIGH, SEVERE = 0.0, 0.25, 0.5, 0.75, 1.0

BAND_NAMES: tuple[str, ...] = ("clean", "mild", "elevated", "high", "severe")


@dataclass(frozen=True)
class Band:
    """One range, its label, and the pressure it contributes."""

    name: str
    upper: float | None  # inclusive; None means "and above"
    pressure: float


@dataclass(frozen=True)
class Concept:
    """A measurable property, and how its values become pressure.

    ``warn`` and ``fail`` name the config keys the boundaries derive from,
    so a project that raises its complexity threshold moves its bands with
    it rather than having two disagreeing notions of "too complex".
    """

    name: str
    unit: str
    warn_key: str
    fail_key: str
    # Higher is worse for most concepts; maintainability index and coverage
    # run the other way, and getting this backwards would score a healthy
    # repository as broken.
    higher_is_worse: bool = True


CONCEPTS: dict[str, Concept] = {
    "cyclomatic_complexity": Concept(
        "cyclomatic_complexity", "branches", "warn_complexity", "max_complexity",
    ),
    "cognitive_complexity": Concept(
        "cognitive_complexity", "nesting-weighted",
        "warn_cognitive_complexity", "max_cognitive_complexity",
    ),
    "declaration_lines": Concept(
        "declaration_lines", "lines", "warn_function_lines", "max_function_lines",
    ),
    "file_lines": Concept("file_lines", "lines", "warn_file_lines", "max_file_lines"),
    "documentation_coverage": Concept(
        "documentation_coverage", "percent", "warn_doc_coverage", "min_doc_coverage",
        higher_is_worse=False,
    ),
    "duplication": Concept(
        "duplication", "percent of lines", "warn_duplication_percent",
        "max_duplication_percent",
    ),
    "maintainability_index": Concept(
        "maintainability_index", "index", "warn_maintainability_index",
        "min_maintainability_index", higher_is_worse=False,
    ),
}

# Boundaries for concepts the config does not threshold. Stated here rather
# than silently defaulted, because a band nobody chose is still a judgment.
# Documentation coverage: interrogate's own default gate is 80%, widely used
# and as defensible a starting point as any; the maintainability index bands
# follow radon's published A–C ranks.
FALLBACK_THRESHOLDS: dict[str, float] = {
    # jscpd's own default gate is 5% duplicated lines, and 10% is the
    # figure most teams that set one settle on. Both are conventions
    # rather than measurements, which is why they are here and named
    # rather than buried in the band function.
    "warn_duplication_percent": 5.0,
    "max_duplication_percent": 10.0,
    "warn_doc_coverage": 80.0,
    "min_doc_coverage": 50.0,
    "warn_maintainability_index": 20.0,
    "min_maintainability_index": 10.0,
}


def thresholds_for(concept: Concept, thresholds: dict[str, Any]) -> tuple[float, float]:
    """The (warn, fail) pair this concept bands around."""
    warn = thresholds.get(concept.warn_key, FALLBACK_THRESHOLDS.get(concept.warn_key))
    fail = thresholds.get(concept.fail_key, FALLBACK_THRESHOLDS.get(concept.fail_key))
    if warn is None or fail is None:
        raise KeyError(
            f"{concept.name} bands need {concept.warn_key} and {concept.fail_key}; "
            "add them to thresholds or to FALLBACK_THRESHOLDS rather than guessing"
        )
    return float(warn), float(fail)


def bands_for(concept: Concept, thresholds: dict[str, Any]) -> tuple[Band, ...]:
    """Five ordered bands around this concept's warn and fail points.

    The two calibrated points anchor the middle of the scale; the outer
    bands are placed relative to them rather than at absolute values, so a
    project with different thresholds gets a consistently shaped curve
    instead of one squashed against an end.
    """
    warn, fail = thresholds_for(concept, thresholds)
    pressures = (CLEAN, MILD, ELEVATED, HIGH, SEVERE)
    if concept.higher_is_worse:
        # `upper` is an inclusive ceiling: at or below it, you are in this
        # band. Ascending, so the last band is everything above.
        span = max(fail - warn, 1.0)
        edges: tuple[float | None, ...] = (warn * 0.6, warn, fail, fail + span, None)
    else:
        # `upper` is an inclusive *floor*: at or above it, you are in this
        # band. Descending, so the last band is everything below.
        #
        # Getting this backwards scored a maintainability index of 95 as
        # severe and 5 as clean — the direction is stated in the field name
        # and was still inverted in the first implementation, which is why
        # both directions have named tests.
        span = max(warn - fail, 1.0)
        edges = (warn, (warn + fail) / 2, fail, fail - span, None)
    return tuple(
        Band(name, edge, pressure)
        for name, edge, pressure in zip(BAND_NAMES, edges, pressures, strict=True)
    )


def band_of(concept: Concept, value: float, thresholds: dict[str, Any]) -> Band:
    """Which band a single measurement falls in."""
    bands = bands_for(concept, thresholds)
    for band in bands:
        if band.upper is None:
            break
        inside = value <= band.upper if concept.higher_is_worse else value >= band.upper
        if inside:
            return band
    return bands[-1]


def pressure_of(concept: Concept, value: float, thresholds: dict[str, Any]) -> float:
    return band_of(concept, value, thresholds).pressure


def population_pressure(
    concept: Concept, values: list[float], thresholds: dict[str, Any]
) -> float | None:
    """Mean pressure across every measured unit.

    A mean rather than a worst-case: one pathological function in a
    thousand should not read the same as a thousand pathological ones, and
    the outlier is reported as a finding regardless. ``None`` for an empty
    population — a rate over nothing is not zero, it is unmeasured.
    """
    if not values:
        return None
    return sum(pressure_of(concept, value, thresholds) for value in values) / len(values)


def unit_pressure(readings: dict[str, float], thresholds: dict[str, Any]) -> float | None:
    """One unit's pressure: the worst band among its measured concepts.

    Mirrors ``function_status``, which fails a declaration on lines OR
    complexity OR cognitive complexity — the worst concept governs.
    Averaging a unit against itself would let two mild readings dilute
    one severe one, which is the 16-versus-45 collapse moved down a
    level. ``None`` when nothing recognisable was measured: no readings
    is unmeasured, never clean.
    """
    known = [
        pressure_of(CONCEPTS[name], value, thresholds)
        for name, value in readings.items()
        if name in CONCEPTS
    ]
    return max(known) if known else None

"""How a second evidence source reaches the score — ADR 006 §1 and §4.

Split from ``scoring`` when that file crossed the 500-line gate this
tool enforces on everyone else. The seam is the question being answered:
``scoring`` turns one tree's evidence into a number; everything here
decides what happens when a *second* source has also spoken — which
reading supplies the point (analyzer-primary, per dimension), what the
fallback tier would have said (the interval must contain it), and what
independent tools disagreeing about one concept costs (width, never a
shift of the estimate).
"""
from __future__ import annotations

from ._aspects import aspect_scores
from ._corroborate import agreement, combine, single_source_concepts
from ._formula import (
    SINGLE_SOURCE_HALF_WIDTH,
    SPREAD_HALF_WIDTH,
    clamp_score,
    overall_from_aspects,
)
from ._pressures import (
    ExternalPressures,
    dimension_pressures,
    normalize,
    normalize_production,
)
from .evidence import NormalizedEvidence


def analyzer_scored(external: ExternalPressures | None) -> list[str]:
    """Dimensions an analyzer measured, and so contributed to the estimate.

    Empty when `--analyzers` did not run, and empty when it ran and
    measured nothing the rubric scores. Those are different facts, but
    both mean the number came from the built-in tier.
    """
    if external is None:
        return []
    return sorted({
        name for population in (external.all_code, external.production)
        for name, value in population.items() if value is not None
    })


def widen_for_disagreement(
    evidence: NormalizedEvidence,
    external: ExternalPressures | None,
    aspects: dict[str, float | None],
    untested: bool | None,
    not_applicable: frozenset[str] | None,
    bounds: tuple[float, float],
) -> tuple[float, float]:
    """Stretch the interval to contain what the *other* source would score.

    The estimate now comes from the analyzers wherever they measured, so
    the alternative rollup is the built-in one: the interval reaches from
    the primary reading to what the fallback tier would have said, and a
    reader can see how far apart the two sources are without either being
    folded into the other.

    A no-op when nothing external was measured, which keeps every
    existing report byte-identical unless `--analyzers` ran.
    """
    low, high = bounds
    if not external or not external.measured_anything():
        return low, high

    alternative, _ = overall_from_aspects(
        aspect_scores(
            evidence,
            normalize(dimension_pressures(evidence.summary)),
            normalize_production(evidence.summary),
        ),
        untested=untested,
        not_applicable=not_applicable,
    )
    return min(low, alternative), max(high, alternative)


def widen_for_spread(
    external: ExternalPressures | None,
    bounds: tuple[float, float],
) -> tuple[float, float]:
    """Per-concept tool disagreement, priced into the interval.

    Two readings that were reduced to one pressure have already lost
    their distance from each other, so this reads the raw measurements
    the pressures came from. Mean relative spread across corroborated
    concepts widens both bounds; a concept only one tool measured widens
    them by a stated minimum, because a lone convention has *unknown*
    spread — pricing it as zero would make one tool indistinguishable
    from two tools that independently agreed.

    Symmetric, so the estimate stays inside its own interval, and a
    no-op when the run carried no measurements at all.
    """
    low, high = bounds
    measurements = list(getattr(external, "measurements", ()) or ())
    if not measurements:
        return low, high
    combined = combine(measurements)
    spreads = agreement(combined)
    half = SPREAD_HALF_WIDTH * (sum(spreads.values()) / len(spreads) if spreads else 0.0)
    if single_source_concepts(combined):
        half += SINGLE_SOURCE_HALF_WIDTH
    if half <= 0.0:
        return low, high
    return round(clamp_score(low - half), 1), round(clamp_score(high + half), 1)


def primary_pressures(
    built_in: dict[str, float | None],
    external: ExternalPressures | None,
    population: str,
    already_normalized: bool = False,
) -> dict[str, float | None]:
    """One population's pressures, analyzer-first and built-in where silent.

    Per dimension rather than wholesale: coverage is partial by nature —
    lizard reads complexity everywhere and documentation nowhere — so a
    repository legitimately gets an analyzer number for some dimensions
    and a built-in number for the rest. A `None` from the analyzers means
    *nobody measured this*, which keeps the built-in reading; substituting
    the `None` itself would score a silent dimension as clean, which is
    the defect that produced a 5.0/A+ over one function.

    `already_normalized` because the two populations arrive in different
    units: `dimension_pressures` returns raw pressures that the caller
    normalizes afterwards, while `normalize_production` has normalized
    already, so a raw analyzer reading has to be converted before it can
    sit beside its neighbours.
    """
    merged = dict(built_in)
    if external is None:
        return merged
    for dimension, value in getattr(external, population).items():
        if value is None or dimension not in merged:
            continue
        merged[dimension] = normalize({dimension: value})[dimension] if already_normalized else value
    return merged

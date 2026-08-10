"""The rubric: every aspect, its weight, and the rollup — in one place.

``scoring.py`` computes aspect scores from a report; ``_derive.py``
re-anchors the calibration constant against the corpus. Both must agree
on what the rollup *is*, so the rollup lives here and neither restates
it. The tables below are the entire judgment layer of the score — every
weight is a decision someone can disagree with, which is exactly why
they are data in one module rather than arithmetic scattered through
functions.

Two kinds of aspect:

- **calibrated** — the five structural pressures, each normalized
  against the reference corpus and pushed through the score curve.
  These inherit the corpus anchor: 1.0x the median maps to the same
  score everywhere.
- **rubric** — evidence the corpus reference cannot price (test
  presence, dead code, churn, coupling, ownership, documentation),
  scored against banded thresholds stated in ``scoring.py``. Bands and
  weights are judgments, which is what every standard is made of — their
  legitimacy is that they are explicit, deterministic, and applied
  identically to every repository. An outcome study (docs/standard.md,
  "Tuning the standard against outcomes") would tune them, not license
  them.

An aspect that cannot be measured for a given report — no git history,
an old baseline without the newer counts — scores ``None`` in the
report, blocks the A-grades, and **prices at the corpus anchor
(4.0) in the numeric rollup**. Renormalizing unknowns away was tried
first and audited into retirement: it let a shallow clone of a clean
repository outscore the same repository with its worst-band history
visible by 0.8 points, because hiding evidence deleted its weight.
Unknown must price as *typical*, never as zero, perfect, or absent.
"""

from __future__ import annotations

# What an unmeasured aspect contributes to the numeric rollup: the
# corpus anchor, i.e. "assume typical of real code until measured".
UNKNOWN_ASPECT_SCORE = 4.0

# Ceiling on testability for a repository with no test evidence at all.
# Lives here, with the rest of the rubric, because it is part of the
# rollup: an audit found the point score applying it and the uncertainty
# interval not, producing a "range" that excluded the score it bounded.
UNTESTED_TESTABILITY_CAP = 2.0

# Aspect -> the dimension pressure it curves (calibrated aspects only).
CALIBRATED_ASPECTS: dict[str, str] = {
    "file_size": "file_size",
    "declaration_size": "declarations",
    "duplication": "duplication",
    "risk_patterns": "risk",
    "policy_gates": "gates",
}

# Every rubric-scored aspect. Order is the report's presentation order.
RUBRIC_ASPECTS: tuple[str, ...] = (
    "test_presence",
    "dead_code",
    "near_duplication",
    "idiom_consistency",
    "churn_hotspots",
    "change_coupling",
    "knowledge_concentration",
    "documentation",
)

# Aspects each ISO/IEC 25010 category reads, with weights. Weights are
# renormalized over the aspects that actually produced a score.
CATEGORY_ASPECTS: dict[str, dict[str, float]] = {
    "modularity": {
        "file_size": 0.35,
        "duplication": 0.25,
        "change_coupling": 0.25,
        "churn_hotspots": 0.15,
    },
    "reusability": {
        "duplication": 0.30,
        "near_duplication": 0.30,
        "idiom_consistency": 0.25,
        "file_size": 0.15,
    },
    "analyzability": {
        "declaration_size": 0.30,
        "documentation": 0.20,
        "dead_code": 0.15,
        "risk_patterns": 0.15,
        "churn_hotspots": 0.10,
        # Code only one person has ever touched is code only one person
        # can read quickly. An audit found this aspect scored, printed,
        # and weighted nowhere — thirteen advertised, twelve effective.
        "knowledge_concentration": 0.10,
    },
    "modifiability": {
        "change_coupling": 0.25,
        "duplication": 0.20,
        "churn_hotspots": 0.15,
        "risk_patterns": 0.15,
        "knowledge_concentration": 0.10,
        "policy_gates": 0.10,
        "file_size": 0.05,
    },
    "testability": {
        "test_presence": 0.50,
        "declaration_size": 0.30,
        "policy_gates": 0.20,
    },
}

# ISO gives the five sub-characteristics no ordering; equal weight is
# the least-arguable default and is stated rather than implied.
CATEGORY_WEIGHTS: dict[str, float] = dict.fromkeys(CATEGORY_ASPECTS, 0.2)

# Measured aspects of maintainability this tool cannot score, and why.
# Listed in the rubric so their absence is a statement, not an omission.
UNSCORED: dict[str, str] = {
    "test_effectiveness": "requires running the suite (mutation/coverage); this audit never executes code",
    "naming_quality": "no static proxy survives contact; a wrong-name detector needs semantics",
    "comment_accuracy": "comments are deliberately unparsed; staleness needs meaning, not structure",
    "indirection_depth": "call-graph construction is not implemented for the supported languages",
    "architectural_coherence": "no measurement distinguishes a wrong boundary from an unusual one statically",
}


def rollup(
    scores: dict[str, float | None], weights: dict[str, float], unknown_price: float = UNKNOWN_ASPECT_SCORE
) -> float:
    """Weighted mean, with unmeasured aspects priced at ``unknown_price``.

    The default anchor gives the point estimate. Callers pass 0.0 and
    5.0 to obtain the bounds of the uncertainty interval — the honest
    companion to any imputation, because no single imputed value can
    stop concealment from flattering a repo whose true evidence is
    worse than the imputed one. The interval makes concealment visible
    instead of pretending a constant makes it impossible.
    """
    return sum(
        (unknown_price if scores.get(name) is None else scores[name]) * weight
        for name, weight in weights.items()
    ) / sum(weights.values())


def clamp_score(value: float) -> float:
    """The one rounding in the system: 0-5, one decimal, as displayed."""
    return round(max(0.0, min(5.0, value)), 1)


def curve(normalized_pressure: float, constant: float) -> float:
    """A pressure in corpus-median units, as a 0-5 aspect score.

    Parameterized by the constant so the calibration fit and the live
    report share one curve. They previously shared a formula but not a
    rounding — the live path clamped each aspect to a decimal and the
    derivation kept full precision, which is the same "same pipeline"
    claim failing one step further down than the last audit found it.
    """
    return clamp_score(5 * constant / (normalized_pressure + constant))


def cap_testability(untested: bool | None, unknown_price: float) -> bool:
    """Whether the untested ceiling applies at this unknown price.

    Unknown test evidence is an unknown like any other, so it is priced
    by the same dial: typical (no cap) for the point estimate, worst
    case (cap) for the floor. An audit found the cap firing only when
    the evidence was present, which meant deleting ``test_file_count``
    escaped the penalty and *raised* the floor the grade is banded
    from — concealment paying one level below the interval that was
    supposed to have closed it.
    """
    if untested is None:
        return unknown_price <= 0.0
    return untested


def overall_from_aspects(
    aspect_scores: dict[str, float | None],
    *,
    untested: bool | None = False,
    unknown_price: float = UNKNOWN_ASPECT_SCORE,
) -> tuple[float, dict[str, float]]:
    """The whole rollup: aspects -> displayed categories -> overall.

    Every caller goes through here — the live report, the uncertainty
    interval, and the corpus derivation that fits the calibration
    constant. That is the point. Three audits in a row found a score
    path that differed from a neighbouring one in exactly one step
    (rounding, then the untested cap, then the cap again in the
    interval), and each time the published sentence "the same pipeline"
    was decoration. There is now one pipeline and no second copy of it.

    ``untested`` applies the testability ceiling *before* rounding, so
    the displayed categories are the numbers the overall is the mean
    of. ``unknown_price`` is the anchor for the point estimate and 0.0 /
    5.0 for the interval endpoints.
    """
    categories = {
        name: rollup(aspect_scores, weights, unknown_price)
        for name, weights in CATEGORY_ASPECTS.items()
    }
    if cap_testability(untested, unknown_price):
        categories["testability"] = min(categories["testability"], UNTESTED_TESTABILITY_CAP)
    displayed = {name: clamp_score(value) for name, value in categories.items()}
    return overall_from_displayed(displayed), displayed


def overall_from_displayed(displayed_categories: dict[str, float]) -> float:
    """Weighted mean of the categories exactly as printed.

    Computed from the *rounded* values, deliberately: an audit produced
    categories displaying 3.5/4.2/5.0/4.5/2.0 with a reported overall of
    3.9 against a displayed mean of 3.8, because the overall came from
    hidden unrounded values. The published sentence is "the overall is
    the weighted mean of the reported categories", so it is computed
    from the reported numbers and a reader can check the arithmetic on
    the report itself.
    """
    total = sum(CATEGORY_WEIGHTS[name] for name in displayed_categories)
    return clamp_score(
        sum(value * CATEGORY_WEIGHTS[name] for name, value in displayed_categories.items()) / total
    )


def overall_bounds(
    aspect_scores: dict[str, float | None], *, untested: bool | None = False
) -> tuple[float, float]:
    """The overall's floor and ceiling over every unmeasured aspect.

    Equal to the overall itself when everything was measured, because
    the endpoints run the identical pipeline with the unknown price
    swapped — so ``low <= overall <= high`` holds by construction
    rather than by inspection. An audit caught the previous version
    computing the endpoints from uncapped aspects: an untested repo
    reported 4.4 with a "range" of [4.5, 4.5], an interval that
    excluded its own score.

    The width is the price of the missing evidence, printed rather than
    hidden: a shallow clone's report says "somewhere in [x, y]" instead
    of lending its point estimate false precision.
    """
    low, _ = overall_from_aspects(aspect_scores, untested=untested, unknown_price=0.0)
    high, _ = overall_from_aspects(aspect_scores, untested=untested, unknown_price=5.0)
    return low, high

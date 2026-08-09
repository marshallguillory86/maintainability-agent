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
        "dead_code": 0.20,
        "risk_patterns": 0.15,
        "churn_hotspots": 0.15,
    },
    "modifiability": {
        "change_coupling": 0.25,
        "duplication": 0.20,
        "churn_hotspots": 0.20,
        "risk_patterns": 0.15,
        "file_size": 0.10,
        "policy_gates": 0.10,
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


def overall_from_aspects(aspect_scores: dict[str, float | None]) -> tuple[float, dict[str, float]]:
    """Category scores and the overall point estimate, anchor-imputing
    unknowns.

    The point estimate answers "typical until measured". It does NOT
    make concealment neutral: a repo whose hidden evidence is worse
    than the anchor still gains by hiding it, which is why
    :func:`overall_bounds` exists and the report prints the interval
    whenever anything is unknown. The A-grade block for missing
    evidence lives in scoring, on top of these numbers.
    """
    categories = {
        name: rollup(aspect_scores, weights) for name, weights in CATEGORY_ASPECTS.items()
    }
    overall = rollup(categories, {name: CATEGORY_WEIGHTS[name] for name in categories})
    return overall, categories


def overall_bounds(aspect_scores: dict[str, float | None]) -> tuple[float, float]:
    """The overall's floor and ceiling over every unmeasured aspect.

    Equal when everything is measured. The width is the price of the
    missing evidence, printed rather than hidden: a shallow clone's
    report says "somewhere in [x, y]" instead of lending its point
    estimate false precision.
    """
    bounds = []
    for price in (0.0, 5.0):
        categories = {
            name: rollup(aspect_scores, weights, price) for name, weights in CATEGORY_ASPECTS.items()
        }
        bounds.append(rollup(categories, {name: CATEGORY_WEIGHTS[name] for name in categories}, price))
    return bounds[0], bounds[1]

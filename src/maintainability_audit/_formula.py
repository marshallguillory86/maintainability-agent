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
  scored against banded thresholds stated in ``scoring.py``. These are
  heuristics and the docs say so; their honesty is in being visible,
  not in being validated.

An aspect that cannot be measured for a given report — no git history,
an old baseline without the newer counts — scores ``None`` and its
weight renormalizes away. "Unknown" must never price as either zero or
perfect.
"""
from __future__ import annotations

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


def rollup(scores: dict[str, float | None], weights: dict[str, float]) -> float | None:
    """Weighted mean over the aspects that produced a score.

    None when *nothing* under the weights was measurable — a category
    built entirely on missing evidence has no opinion, and pretending
    otherwise is how "unknown" quietly becomes "fine".
    """
    known = {name: weight for name, weight in weights.items() if scores.get(name) is not None}
    total = sum(known.values())
    if total == 0:
        return None
    return sum(scores[name] * weight for name, weight in known.items()) / total


def overall_from_aspects(aspect_scores: dict[str, float | None]) -> tuple[float | None, dict[str, float | None]]:
    """Category scores and the overall, renormalizing at both levels."""
    categories = {
        name: rollup(aspect_scores, weights) for name, weights in CATEGORY_ASPECTS.items()
    }
    overall = rollup(
        {name: value for name, value in categories.items()},
        {name: CATEGORY_WEIGHTS[name] for name in categories},
    )
    return overall, categories

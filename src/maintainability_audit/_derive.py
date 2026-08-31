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

from ._aspects import evidence_aspect_scores, is_untested
from ._formula import CALIBRATED_ASPECTS, curve, overall_from_aspects
from ._pressures import production_pressures
from .evidence import REPORT_SCHEMA_VERSION, SCHEMA_VERSION_KEY, normalize_report_evidence

# The stored column holding the analyzers' production reading. Named
# once because both the refusal and the mix key on it.
ANALYZER_COLUMN = "analyzer_production_dimensions"

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
    require_analyzer_column(measurements)
    return {
        dimension: (
            FIXED_REFERENCES[dimension]
            if dimension in FIXED_REFERENCES
            else round(median(_reference_reading(entry, dimension) for entry in measurements), 4)
        )
        for dimension in DIMENSIONS
    }


def _reference_reading(entry: dict[str, Any], dimension: str) -> float:
    """The value a dimension's reference median is taken over.

    `declarations` is the one dimension with two sources, and the
    reference is the denominator the fit divides by — so it has to be the
    median of the *same* readings the numerator uses. A built-in median
    under an analyzer numerator is a ratio between two different
    measurements, which is how four wrong ratios were published from this
    comparison already.
    """
    if dimension == "declarations":
        value = primary_declarations(entry)
        if value is not None:
            return value
    return entry["dimensions"][dimension]


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


def primary_declarations(entry: dict[str, Any]) -> float | None:
    """One corpus row's declaration pressure, under the shipped mix.

    The same rule `scoring._primary_pressures` applies to a live report:
    the analyzers' production reading where they supplied one, the
    built-in reading where they did not. Fitting the curve against a
    source the product no longer consults is how a constant comes to
    describe a pipeline nobody runs.

    `null` and a `null` value both mean unmeasured — the pool failed, or
    it measured too narrow a concept set to compose the dimension — and
    both fall back. A row with no analyzer key at all is a different
    thing: it predates `--with-analyzers`, and answering for it would
    quietly re-derive the old constant, so it raises.
    """
    analyzer = analyzer_declarations(entry)
    if analyzer is not None:
        return analyzer
    production = entry.get("production_dimensions") or {}
    if production.get("declarations") is not None:
        return float(production["declarations"])
    return entry["dimensions"].get("declarations")


def analyzer_declarations(entry: dict[str, Any]) -> float | None:
    """The analyzers' declaration pressure for one row, or None.

    None covers both "the pool did not contribute" and "it measured too
    narrow a concept set". A row with no analyzer key at all predates
    `--with-analyzers` and raises, because fitting it would silently
    re-derive the built-in constant under the analyzer-primary label.
    """
    if ANALYZER_COLUMN not in entry:
        raise ValueError(
            f"corpus row {entry.get('repo', '?')!r} has no `{ANALYZER_COLUMN}`: it was "
            "measured by the pre-analyzer pipeline. Re-run "
            "tools/calibration/measure.py --with-analyzers. The constant cannot be "
            "derived from a file that never saw the analyzer readings."
        )
    reading = entry[ANALYZER_COLUMN] or {}
    value = reading.get("declarations")
    return None if value is None else float(value)


def require_analyzer_column(measurements: list[dict[str, Any]]) -> None:
    """Refuse a corpus measured before the analyzers were recorded.

    The stored file is the input to a constant every score depends on,
    and one produced by the old pipeline looks exactly like a current one
    until the numbers come out unchanged.
    """
    missing = [
        entry.get("repo", "?") for entry in measurements
        if ANALYZER_COLUMN not in entry
    ]
    if missing:
        raise ValueError(
            f"{len(missing)} corpus rows have no `{ANALYZER_COLUMN}` and were measured "
            f"by the pre-analyzer pipeline (first: {', '.join(missing[:3])}). "
            "Re-run tools/calibration/measure.py --with-analyzers; the constant "
            "cannot be derived from a file that never saw the analyzer readings."
        )
    return None


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

    The rollup itself is ``_formula.overall_from_aspects`` — not a
    re-implementation of it. Two successive audits found this path
    differing from the live one by a single step (first the category
    rounding, then the untested testability cap: corpus member ``tabby``
    derived 3.9 and scored 3.8 live). "Same pipeline" is only true if
    there is one pipeline, so the derivation now calls the shipped
    function and ``test_derivation_matches_live_score_report`` checks
    the two against each other repo by repo.
    """
    scores: dict[str, float | None] = {
        aspect: curve(entry["dimensions"][dimension] / references[dimension], c)
        for aspect, dimension in CALIBRATED_ASPECTS.items()
        if references[dimension] > 0
    }
    untested: bool | None = False
    recorded = entry.get("evidence")
    if recorded is not None:
        # Through the shipped normalizer, exactly as a live report goes:
        # the derivation must not have a private way of reading evidence.
        summary = normalize_report_evidence({
            SCHEMA_VERSION_KEY: REPORT_SCHEMA_VERSION,
            "summary": {
                **recorded,
                "files_scanned": entry["files"],
                "declarations_scanned": entry["declarations"],
            },
        }).summary
        scores.update(evidence_aspect_scores(summary))
        untested = is_untested(summary)
        # The shipped mix, not the built-in reading: the analyzers
        # supply this dimension wherever they measured the full concept
        # set, so a fit that always used `production_pressures` here
        # would calibrate a pipeline the product stopped running.
        # The analyzers' reading where they supplied one; otherwise the
        # *production* pressure measured from this summary, which is what
        # `score_evidence` reads. Falling back to the stored all-code
        # dimension instead put the derivation 0.1 above the live score on
        # a third of the corpus.
        production = analyzer_declarations(entry)
        if production is None:
            production = production_pressures(summary)["declarations"]
        if references["declarations"] > 0 and production is not None:
            scores["declaration_size"] = curve(production / references["declarations"], c)
    # test_effectiveness is NotApplicable across the corpus (none of it opted
    # into running a suite), excluded exactly as `score_evidence` excludes it
    # so the derivation still matches the live score repo by repo (Class 5).
    overall, _ = overall_from_aspects(
        scores, untested=untested, not_applicable=frozenset({"test_effectiveness"}))
    return overall


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
    require_analyzer_column(measurements)
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

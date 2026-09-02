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

from math import inf
from typing import Any

from ._aspects import (
    aspect_scores,
    evidence_aspect_scores,
    is_untested,
    not_applicable_aspects,
)
from ._calibration import CATEGORIES, GRADE_GATES
from ._formula import (
    CATEGORY_ASPECTS,
    CATEGORY_WEIGHTS,
    UNSCORED,
    clamp_score,
    overall_bounds,
    overall_from_aspects,
)
from ._pressures import (
    ExternalPressures,
    dimension_pressures,
    measured,
    normalize,
    normalize_production,
    production_pressures,
)
from ._second_source import (
    analyzer_scored,
    primary_pressures,
    widen_for_disagreement,
    widen_for_spread,
)
from ._verification import INSUFFICIENT, verification
from .evidence import (
    NormalizedEvidence,
    SummaryEvidence,
    normalize_report_evidence,
)

__all__ = [
    "CATEGORIES",
    "aspect_scores",
    "clamp_score",
    "dimension_pressures",
    "evidence_aspect_scores",
    "grade_from_score",
    "is_untested",
    "normalize",
    "normalize_production",
    "production_pressures",
    "score_report",
]

_BANDS = [(4.8, "A+"), (4.5, "A"), (4.0, "B"), (3.0, "C"), (2.0, "D"), (0.0, "F")]


def _gate_readings(summary: SummaryEvidence, pressures: dict[str, float | None]) -> dict[str, float]:
    """Readings the A-grade ceilings are checked against.

    An unmeasured reading reports ``inf`` rather than zero, so it fails
    every ceiling. "Could not look" must never clear a gate that "looked
    and found none" would have had to earn.
    """
    files = measured(summary.files_scanned)
    decls = measured(summary.declarations_scanned)
    gates = measured(summary.hard_gate_failures)
    return {
        "file_fail_rate": _gate_rate(measured(summary.file_failures), files),
        "decl_fail_rate": _gate_rate(measured(summary.function_failures), decls),
        "file_warn_rate": _gate_rate(measured(summary.file_warnings), files),
        "decl_warn_rate": _gate_rate(measured(summary.function_warnings), decls),
        "duplication": _unknown_fails(pressures["duplication"]),
        "risk": _unknown_fails(pressures["risk"]),
        "gates": inf if gates is None else float(gates),
    }


def _unknown_fails(value: float | None) -> float:
    return inf if value is None else value


def _gate_rate(count: float | None, population: float | None) -> float:
    if count is None or population is None:
        return inf
    return count / population if population > 0 else 0.0


def grade_from_score(score: float) -> str:
    """Band a score, ignoring gates. Kept for callers that only have a number."""
    for floor, letter in _BANDS:
        if score >= floor:
            return letter
    return "F"


_GATED_ORDER = ["A+", "A"]


def _gate_failures(grade: str, readings: dict[str, float]) -> list[str]:
    # Direct lookup, not `readings.get(name, 0.0)`. `_gate_readings`
    # builds the readings with exactly the keys every grade's gates name,
    # and reports an unmeasured one as `inf` so it fails every ceiling. A
    # `.get` default of 0.0 would have done the opposite -- turned a
    # missing reading into a perfect one and cleared the gate -- which is
    # the "absence read as excellence" ADR 001 forbids, and which
    # architecture.md already states was removed. A future gate key with
    # no reading should raise here, not silently pass.
    return [
        f"{name} {readings[name]:.3f} exceeds the {grade} ceiling of {ceiling:g}"
        for name, ceiling in GRADE_GATES[grade].items()
        if readings[name] > ceiling
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


def _evidence_rules(
    grade: str,
    blockers: list[str],
    aspects: dict[str, float | None],
    untested: bool | None,
    not_applicable: frozenset[str],
) -> tuple[str, list[str]]:
    """The two rules that keep A-grades honest about evidence.

    No test evidence demotes, stated even when the rubric already landed
    below A on its own — "why is my grade capped" deserves the answer
    regardless of which arithmetic delivered the cap. And an unknown is
    not clean: a shallow clone hides coupling, hotspots and ownership,
    so unmeasured aspects withhold the top grades rather than letting
    "nothing wrong in what could be seen" pass for "nothing is wrong
    anywhere". (CI note: actions/checkout defaults to depth 1; use
    fetch-depth: 0 for the full grade.)

    "Couldn't look" blocks; "looked and there was nothing to measure"
    does not — an aspect is None either because it is Unknown (missing
    evidence, which must block) or NotApplicable (a resolved absence of
    population, which must not). ``not_applicable`` is the authority on
    which: knowledge_concentration on a young repo whose log is readable
    but no file has three commits, and test_effectiveness whenever the
    operator did not opt the suite in, are both None-but-not-missing.
    """
    if untested:
        blockers = [*blockers, "no test evidence found: A-grades require it"]
        if grade in GRADE_GATES:
            grade = "B"
    missing = sorted(
        name for name, value in aspects.items()
        if value is None and name not in not_applicable
    )
    if missing:
        # Stated whatever the grade, not only when it is being demoted
        # from an A. Grading on the evidence floor can push a repo well
        # below A on missing evidence alone, and a demotion nobody
        # explains is the failure mode this whole blocker list exists to
        # prevent.
        blockers = [*blockers, f"unmeasured aspects ({', '.join(missing)}): A-grades require full evidence"]
        if grade in GRADE_GATES:
            grade = "B"
    return grade, blockers


def _grade_on_the_floor(
    evidence: NormalizedEvidence,
    pressures: dict[str, float | None],
    aspects: dict[str, float | None],
    untested: bool | None,
    interval: tuple[float, float, float],
    not_applicable: frozenset[str],
) -> tuple[str, list[str]]:
    """Band the grade from the evidence floor, and say so when it bites.

    The point estimate prices unknowns at the corpus anchor, so a repo
    whose hidden evidence is worse than typical is flattered by hiding
    it — an audit demonstrated 3.9/C with the history visible against
    4.5/B with the same history withheld. Printing the interval made
    that visible to a careful reader while every machine consumer (CI
    gate, badge, ranking, API) kept reading the flattered field.
    Grading the floor makes concealment monotonically unprofitable:
    hiding an aspect can only widen the interval downward, so it can
    never raise the grade. Supply the evidence and the floor rises to
    meet the point estimate.
    """
    overall, low, high = interval
    grade, blockers = grade_for(low, _gate_readings(evidence.summary, pressures))
    if low < overall:
        blockers = [
            *blockers,
            f"graded on the evidence floor {low} (point estimate {overall}, ceiling {high}): "
            "unmeasured aspects price at 0 for the grade",
        ]
    return _evidence_rules(
        grade,
        blockers,
        aspects,
        untested,
        not_applicable,
    )


def score_report(
    report: dict[str, Any], external: ExternalPressures | None = None
) -> dict[str, Any]:
    """Aspects -> categories -> overall, by the rubric in ``_formula``.

    Every aspect the tool can measure gets a score; every aspect it
    cannot gets None in the report, prices at the corpus anchor (4.0)
    in the numeric rollup, and blocks the A-grades; every aspect of
    maintainability it cannot measure *at all* is named in
    ``rubric.unscored`` with the reason — absence is a statement here,
    never an omission. The calibration constant is fitted so the corpus
    median still rolls up to 4.0 through this exact pipeline.

    The untested cap lands on the categories BEFORE rounding, and the
    overall is computed from the categories exactly as displayed — two
    audits caught two versions of the same lie, an overall that was not
    the mean of the numbers printed beside it.
    """
    unpaired = bool((report.get("tdd_structure") or {}).get("unpaired_fail_band"))
    coverage = (report.get("test_suite") or {}).get("coverage_percent")
    return score_evidence(
        normalize_report_evidence(report), external,
        unpaired_hotspot=unpaired, test_coverage=coverage,
    )


def _seat_coverage_aspect(
    aspects: dict[str, float | None],
    not_applicable: frozenset[str],
    test_coverage: float | None,
) -> frozenset[str]:
    """Seat the opt-in coverage aspect (Class 5) and resolve its state.

    A line-coverage percent becomes a 0-5 score, ``coverage / 20``.
    Without a coverage artifact ``test_effectiveness`` stays NotApplicable
    — excluded from testability so the category renormalizes to exactly
    its pre-Class-5 value — rather than an unknown priced at the anchor.
    """
    aspects["test_effectiveness"] = (
        None if test_coverage is None else clamp_score(test_coverage / 20)
    )
    if test_coverage is None:
        return not_applicable
    return not_applicable - {"test_effectiveness"}


def score_evidence(
    evidence: NormalizedEvidence,
    external: ExternalPressures | None = None,
    *,
    unpaired_hotspot: bool = False,
    test_coverage: float | None = None,
) -> dict[str, Any]:
    """Score an already-normalized model — the seam validation ends at.

    ``score_report`` is validation plus this. Splitting them lets the
    stage 6 property suite vary evidence states directly and score them
    through the *production* pipeline, rather than round-tripping
    hand-built dictionaries and hoping they reconstruct the states it
    means to test. There is still exactly one scorer; this is where it
    begins.
    """
    summary = evidence.summary
    # The analyzers are the primary evidence (ADR 006 §1). Where they
    # measured a dimension, their reading is the one the estimate uses;
    # where they said nothing, the built-in detector's reading stands,
    # because a dimension nobody measured is unmeasured and not clean.
    pressures = primary_pressures(dimension_pressures(summary), external, "all_code")
    production = primary_pressures(
        normalize_production(summary), external, "production", already_normalized=True
    )
    normalized = normalize(pressures)
    aspects = aspect_scores(evidence, normalized, production)
    not_applicable = _seat_coverage_aspect(
        aspects, not_applicable_aspects(evidence), test_coverage
    )
    untested = is_untested(summary)
    overall, rounded_categories = overall_from_aspects(
        aspects,
        untested=untested,
        unpaired_hotspot=unpaired_hotspot,
        not_applicable=not_applicable,
    )
    low, high = overall_bounds(
        aspects,
        untested=untested,
        unpaired_hotspot=unpaired_hotspot,
        not_applicable=not_applicable,
    )
    # Disagreement between the two sources is real uncertainty about the
    # code and is never averaged away (ADR 006 §4) — a mean would lend
    # the estimate a precision neither source earned. Now that the
    # analyzers supply the point, the *built-in* rollup is the
    # alternative the interval has to reach.
    low, high = widen_for_disagreement(
        evidence, external, aspects, untested, not_applicable, (low, high)
    )
    # And within the analyzer tier itself: independent tools disagreeing
    # on one concept is uncertainty about the code, priced into the
    # interval and never averaged into the estimate (ADR 006 §4).
    low, high = widen_for_spread(external, (low, high))

    # Banded from the *floor*, not the point estimate, so concealment is
    # monotonically unprofitable — see `_grade_on_the_floor`.
    grade, blockers = _grade_on_the_floor(
        evidence, pressures, aspects, untested, (overall, low, high), not_applicable
    )
    if unpaired_hotspot:
        blockers = [
            *blockers,
            "unpaired fail-band production unit: testability capped at 4.0",
        ]
    measurable = {name: value for name, value in normalized.items() if value is not None}
    worst = sorted(measurable.items(), key=lambda item: -item[1])
    document = _score_document(
        aspects, rounded_categories, overall, (low, high), grade, blockers, normalized, worst,
        verification(evidence, grade),
    )
    document["analyzer_scored_dimensions"] = analyzer_scored(external)
    return document










def _reference_block() -> dict[str, object]:
    """What a reported multiple is a multiple *of*.

    The unit and the anchor were always here. The two corpus fields were
    not, and their absence was the gap: the rubric is uniform across
    repositories (P2) and the corpus is not uniform across languages. It
    is 40 repositories of Python, TypeScript and JavaScript, while this
    project parses seven languages, so Java, C, C++, C# and Fortran are
    scored against medians measured on none of their code.

    Disclosed rather than corrected. Per-language references would remove
    the awkwardness by trading a stated limit for a silent breach of the
    one-rubric promise, and two repositories must stay comparable
    regardless of what they are written in.
    """
    return {
        "unit": "multiple of the median mature-OSS repo (1.0 = typical real code)",
        "note": "Calibrated so a repo at the OSS median on every dimension scores 4.0.",
        "corpus_languages": ["Python", "TypeScript", "JavaScript"],
        "corpus_note": (
            "Reference medians are drawn from 40 mature repositories in "
            "Python, TypeScript and JavaScript. Other languages are scored "
            "against that anchor; see docs/standard.md#the-reference-corpus."
        ),
    }


def _score_document(
    aspects: dict[str, float | None],
    rounded_categories: dict[str, float],
    overall: float,
    interval: tuple[float, float],
    grade: str,
    blockers: list[str],
    normalized: dict[str, float | None],
    worst: list[tuple[str, float]],
    verified: dict[str, Any],
) -> dict[str, Any]:
    """The score block exactly as it ships, assembled in one place."""
    low, high = interval
    # A run the scale cannot speak to carries no number at all. Not a
    # zero, not a dash, not a pessimistic floor -- ADR 001 §1 already
    # rejected reporting unknown quality as bad quality, and ADR 005
    # extends that to quality measured over the wrong kind of population.
    # The aspects and every finding stay: they are observations, and only
    # the rolled-up judgment is withheld.
    withheld = verified["evidence_status"]["status"] == INSUFFICIENT
    return {
        "standard": "ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based",
        "maintainability_estimate": None if withheld else overall,
        # Evidence sufficiency, separate from quality (ADR 001 stage 5).
        # `grade` keeps its existing evidence-floor meaning for the
        # compatibility period; `verified_grade` is null unless the
        # profile's required evidence is complete. Consumers migrate in
        # stage 7, not here.
        **verified,
        # The exact numbers the overall was computed from — the identity
        # "overall == weighted mean of these" is checkable on the report.
        "categories": rounded_categories,
        # The interval the overall lives in once unmeasured aspects are
        # priced at their extremes. Collapses to the overall itself when
        # everything was measured. This is the honest companion to
        # anchor imputation: no single imputed value can stop hiding
        # worse-than-anchor evidence from flattering the point estimate,
        # so the report prints the width of what is not known instead of
        # pretending the point is precise.
        "maintainability_range": None if withheld else [low, high],
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
        "dimensions": {
            name: (None if value is None else round(value, 2)) for name, value in normalized.items()
        },
        # Worst-first, so the remediation prompt can lead with the
        # dimension actually costing the most rather than a letter.
        "worst_dimension": worst[0][0] if worst and worst[0][1] > 1.0 else None,
        # Only ever explains a grade that was issued. When verification is
        # withheld there is no grade to cap, and the reasons live in
        # evidence_status.reasons instead — mixing the two is what let an
        # evidence gap read as a quality demotion.
        "verified_grade_blockers": blockers if verified.get("verified_grade") else [],
        "reference": _reference_block(),
    }

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

from ._calibration import CALIBRATION_C
from ._formula import ASPECT_POPULATIONS, CALIBRATED_ASPECTS, curve, population_floor
from ._pressures import measured, normalize_production
from .evidence import HistoryEvidence, NormalizedEvidence, NotApplicable, SummaryEvidence


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


def _history_rate_aspect(history: HistoryEvidence, count_of: str) -> float | None:
    """Hotspot or coupling count as a share of files that changed.

    A rate, not a count — a count would score repository size, which is
    the bug the 0.5.0 rewrite existed to remove. Unmeasured history
    means None: a shallow CI clone must not grade as either clean or
    dirty.
    """
    changed = measured(history.files_changed)
    if changed is None:
        return None
    if changed == 0:
        # Unknown, not perfect. This returned 5.0 — "had history to
        # read; nothing changed in the window" — and an audit showed
        # what that grades: a repository whose only commit predates the
        # twelve-month window scores A+ on every history aspect, while
        # its working tree is filthy. The photograph could see the mess
        # and the window could not.
        #
        # A rate needs a denominator. Zero files changed is no
        # denominator, which is the same state as a shallow clone —
        # nothing was observed — and D37 closed exactly this collapse
        # one layer down, where a *failed* log produced the same zeros.
        # A successful log over an empty window produces them honestly
        # and they mean no less and no more: unknown.
        return None
    # Full counts computed by history_section before its display lists
    # are truncated. Reading len() of a capped list here made the rate
    # fall as repositories grew — the forbidden size-bias class — so an
    # old report that carries only the capped lists reads as unknown
    # rather than as a bogus rate. (code_coupling_pairs counts
    # code-to-code pairs only: README co-changing with CHANGELOG is
    # discipline, not a wrong boundary.)
    source = history.qualifying_hotspots if count_of == "hotspots" else history.code_coupling_pairs
    count = measured(source)
    if count is None:
        return None
    return _banded(count / changed, [(0.0, 5.0), (0.02, 4.5), (0.05, 4.0), (0.10, 3.0), (0.20, 2.0)], 1.0)


def _test_presence_aspect(summary: SummaryEvidence) -> float | None:
    """Share of *declarations* that live in test files.

    Declarations, not files: a file denominator counts every README and
    changelog against the test ratio, so documenting a repo would lower
    its testability. Zero test files is a score of 0.0; an unmeasured
    count is None — zero and unknown are different claims, and an audit
    proved the difference was worth a whole grade.
    """
    test_count = measured(summary.test_file_count)
    if test_count is None:
        return None
    if test_count == 0:
        return 0.0
    total = measured(summary.declarations_scanned)
    production = measured(summary.production_declarations_scanned)
    if total is None or production is None or total == 0:
        return None
    share = (total - production) / total
    # Test files with zero declarations in them are indistinguishable
    # from empty files, and an audit demonstrated the previous 1.5 floor
    # here priced exactly that: one empty test-shaped artifact bought an
    # A. No test declarations scores the same as no tests.
    if share == 0:
        return 0.0
    return _banded(share, [(0.05, 1.5), (0.10, 2.5), (0.20, 3.5), (0.30, 4.5)], 5.0)


def _finding_rate_aspect(
    count_state: object, production_state: object, bands: list[tuple[float, float]], floor: float
) -> float | None:
    """A finding count as a share of production declarations."""
    count = measured(count_state)
    production = measured(production_state)
    if count is None or production is None or production == 0:
        return None
    return _banded(count / production, bands, floor)


def _ownership_aspect(history: HistoryEvidence) -> float | None:
    """Share of settled files (3+ commits) that one person owns alone.

    ``None`` covers both "could not look" and "looked, and no file has
    three commits yet". The typed state distinguishes Unknown from
    NotApplicable; :func:`not_applicable_aspects` carries the latter to
    the rollup so it is excluded rather than priced as uncertainty.
    """
    settled = measured(history.multi_commit_files)
    owners = measured(history.single_author_files)
    if not settled or owners is None:
        return None
    return _banded(owners / settled, [(0.2, 5.0), (0.4, 4.0), (0.6, 3.0), (0.8, 2.0)], 1.0)


def _documentation_aspect(summary: SummaryEvidence) -> float | None:
    """Artifact presence: README, changelog, docs directory.

    A proxy for whether anyone can orient, not for whether the words are
    accurate — accuracy is in UNSCORED and stays there.

    All three flags must be known. ``bool(measured(state))`` read an
    Unknown as *absent*, so a report that did not say whether it had a
    changelog scored as one that said it had none — the bug class this
    architecture exists to remove, surviving in the last aspect nobody
    had swept. Found by the stage 6 property suite, not by an audit.
    """
    flags = [measured(summary.has_readme), measured(summary.has_changelog),
             measured(summary.has_docs_dir)]
    if any(flag is None for flag in flags):
        return None
    readme, changelog, docs = flags
    extras = int(bool(changelog)) + int(bool(docs))
    if not readme:
        return 1.5 if extras else 0.5
    return [3.0, 4.0, 5.0][extras]


def evidence_aspect_scores(summary: SummaryEvidence) -> dict[str, float | None]:
    """The five rubric aspects a summary alone can answer.

    Public and separate from :func:`aspect_scores` because the
    calibration derivation (``_derive``) must price the corpus through
    the *identical* code path users' repositories get — a re-statement
    of these bands in the derivation would drift, and the anchor would
    quietly stop describing the shipped score.
    """
    production = summary.production_declarations_scanned
    concerns = measured(summary.idiom_concern_count)
    return {
        "test_presence": _test_presence_aspect(summary),
        "dead_code": _finding_rate_aspect(
            summary.dead_code_count, production,
            [(0.0, 5.0), (0.001, 4.5), (0.005, 3.5), (0.015, 2.5)], 1.5,
        ),
        "near_duplication": _finding_rate_aspect(
            summary.near_duplicate_count, production,
            [(0.0, 5.0), (0.005, 4.5), (0.01, 4.0), (0.02, 3.0), (0.05, 2.0)], 1.0,
        ),
        "idiom_consistency": (
            None if concerns is None else _banded(concerns, [(0, 5.0), (1, 3.5), (2, 2.5)], 1.5)
        ),
        "documentation": _documentation_aspect(summary),
    }


def aspect_scores(
    evidence: NormalizedEvidence,
    normalized: dict[str, float | None],
    production_override: dict[str, float | None] | None = None,
) -> dict[str, float | None]:
    """Every aspect the rubric reads, scored 0-5 or None for unknown.

    Calibrated aspects push their corpus-normalized pressure through the
    score curve, so they inherit the anchor: the corpus median is worth
    the same everywhere. Rubric aspects score evidence the corpus cannot
    price, against the banded thresholds above. None always means "could
    not measure", never "measured nothing wrong" — and since ADR 001
    stage 4 that is carried by the type rather than by a companion list
    of which keys had to be present.
    """
    summary = evidence.summary
    # Same shape as the rollup: bind the value, then test it. Testing
    # `normalized[dimension]` and then indexing again reads as one
    # operation and is two, which is how a None reaches `_curve`.
    def curved(dimension: str) -> float | None:
        pressure = normalized[dimension]
        return None if pressure is None else _curve(pressure)

    scores: dict[str, float | None] = {
        name: curved(dimension) for name, dimension in CALIBRATED_ASPECTS.items()
    }
    # declaration_size reads the *production* pressure. Its only rubric
    # consumers are analyzability and testability, which describe the
    # code under test — an oversized test function must not drag either
    # (pinned by test_analyzability_not_penalized_by_test_function_size).
    # `declaration_size` is the only route the declarations dimension
    # takes into the score, and it reads the *production* pressure rather
    # than the one in `normalized` — so substituting there alone changes
    # nothing. A second source has to arrive here or it cannot move the
    # number at all, which is what a first attempt at the interval
    # widening discovered by moving it not at all.
    production = (production_override or normalize_production(summary))["declarations"]
    scores["declaration_size"] = None if production is None else _curve(production)
    scores.update(evidence_aspect_scores(summary))
    scores["churn_hotspots"] = _history_rate_aspect(evidence.history, "hotspots")
    scores["change_coupling"] = _history_rate_aspect(evidence.history, "coupling")
    scores["knowledge_concentration"] = _ownership_aspect(evidence.history)
    return _withhold_undersupported(scores, summary)


def undersupported_aspects(summary: SummaryEvidence) -> dict[str, tuple[int, int]]:
    """Aspects whose population is too small for their rate to mean anything.

    Maps aspect -> (observed, floor). A rate over a denominator of one is
    arithmetic, not evidence: a repository with one production function
    once scored ``dead_code 5.0``, which said only that one declaration
    was not dead.

    An unmeasured population is *not* undersupported — that is an Unknown
    with its own reason, and conflating the two would tell a reader to
    grow a repository whose size nobody established.
    """
    thin: dict[str, tuple[int, int]] = {}
    for aspect, population in ASPECT_POPULATIONS.items():
        floor = population_floor(population)
        observed = measured(getattr(summary, population))
        if floor is None or observed is None:
            continue
        if observed < floor:
            thin[aspect] = (int(observed), floor)
    return thin


def _withhold_undersupported(
    scores: dict[str, float | None], summary: SummaryEvidence
) -> dict[str, float | None]:
    """Blank aspects the population cannot support.

    ``None`` here means the same thing it always has — could not measure
    — so the rollup, the interval and the grade gate need no new concept:
    an unsupported aspect widens the range and blocks a verified grade
    exactly as an unmeasured one does.
    """
    for aspect in undersupported_aspects(summary):
        if aspect in scores:
            scores[aspect] = None
    return scores


def not_applicable_aspects(evidence: NormalizedEvidence) -> frozenset[str]:
    """Aspects with a resolved absence of population, not missing data.

    Aspect scores use ``None`` for values that cannot be computed, but
    the rollup must still distinguish why. Unknown evidence keeps its
    weight and widens the range; NotApplicable evidence has no member
    to score and is removed from the category denominator. Derive this
    from the typed state at the scoring boundary rather than carrying a
    second applicability flag that can disagree with it.
    """
    if isinstance(evidence.history.single_author_files, NotApplicable):
        return frozenset({"knowledge_concentration"})
    return frozenset()


def is_untested(summary: SummaryEvidence) -> bool | None:
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
    closed it.
    """
    test_count = measured(summary.test_file_count)
    production = measured(summary.production_declarations_scanned)
    total = measured(summary.declarations_scanned)
    if test_count is None or production is None or total is None:
        return None
    if production <= 0:
        return False
    return test_count == 0 or total - production == 0

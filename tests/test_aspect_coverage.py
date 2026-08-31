"""Every advertised aspect has to actually do something.

Split from `test_scoring_calibration.py` when that file crossed the
500-line gate this project enforces on everyone else. The seam is real:
everything left there is about the *scale* — the corpus, the constant,
the rollup that lands a median repository on 4.0. Everything here is
about the *rubric* — that each aspect carries weight somewhere, that
moving one moves the score, and that the overall is the mean of the
numbers printed beside it rather than a differently-derived figure that
happens to look plausible.

Two audits found the second kind of defect. An aspect listed in the
rubric and weighted nowhere is a promise the report does not keep, and
an overall that is not the mean of its own printed categories is a lie
a careful reader will eventually check.
"""

from __future__ import annotations

from _scoring_fixtures import (
    _evidence_summary,
    _history,
    score_report,
    summary,
)

# Every advertised aspect has to actually do something
# ---------------------------------------------------------------------------

def test_every_scored_aspect_carries_weight_in_some_category() -> None:
    """The rubric advertises thirteen scored aspects; an audit found one
    of them decorative.

    ``knowledge_concentration`` was measured, printed under "Aspect
    Scores", and referenced in the docs, while appearing in no
    category's weights: moving it from 5.0 to 1.0 changed nothing at
    all. This is the structural block on that class of defect — any
    aspect added to the scored list without a weight fails here.
    """
    from maintainability_audit._formula import (
        CALIBRATED_ASPECTS,
        CATEGORY_ASPECTS,
        RUBRIC_ASPECTS,
    )

    advertised = set(CALIBRATED_ASPECTS) | set(RUBRIC_ASPECTS)
    weighted = {aspect for weights in CATEGORY_ASPECTS.values() for aspect in weights}

    assert advertised == weighted, (
        f"scored but weighted nowhere: {sorted(advertised - weighted)}; "
        f"weighted but never scored: {sorted(weighted - advertised)}"
    )


def test_knowledge_concentration_changes_the_score() -> None:
    """The behavioural half of the same finding: a bus factor of one has
    to cost something."""
    shared = _history(multi_commit_files=10, single_author_files=0)
    siloed = _history(multi_commit_files=10, single_author_files=10)

    spread = score_report({"summary": _evidence_summary(), "history": shared})
    concentrated = score_report({"summary": _evidence_summary(), "history": siloed})

    assert concentrated["aspects"]["knowledge_concentration"] < spread["aspects"]["knowledge_concentration"]
    assert concentrated["maintainability_estimate"] < spread["maintainability_estimate"]


def test_the_overall_is_the_weighted_mean_of_the_printed_categories() -> None:
    """P4, checked directly instead of by proxy.

    The architecture table used to map this promise to the corpus-median
    test, which asserts only that the median is 4.0 — it never checks
    the arithmetic identity on any individual report. An audit called
    that out: naming a test is not the same as the test checking the
    thing. This asserts the published sentence on every report it can
    reach, including untested and partially-unknown ones, where the
    testability cap and anchor imputation act.
    """
    from maintainability_audit._formula import CATEGORY_WEIGHTS

    reports = [
        {"summary": summary(500, 1000)},
        {"summary": summary(500, 1000, file_failures=250, risk_findings=400)},
        {"summary": _evidence_summary(), "history": _history()},
        {"summary": _evidence_summary(test_file_count=0), "history": _history()},
        {"summary": _evidence_summary()},
        {"summary": _evidence_summary(), "history": _history(single_author_files=10)},
    ]
    for report in reports:
        score = score_report(report)
        categories = score["categories"]
        total = sum(CATEGORY_WEIGHTS[name] for name in categories)
        expected = round(
            sum(value * CATEGORY_WEIGHTS[name] for name, value in categories.items()) / total, 1
        )
        assert score["maintainability_estimate"] == expected, (
            f"{score['maintainability_estimate']} is not the weighted mean of {categories}"
        )


def test_the_ownership_aspect_does_not_claim_to_be_bus_factor() -> None:
    """ADR 007 §4 asks for the shared term. The shared term would be wrong.

    Bus factor is a count of people: how many would have to leave before
    the project stalls. `knowledge_concentration` is the share of settled
    files that exactly one person has touched — related, cheaper, and a
    different quantity. A repository where one author owns 80% of files
    can still have a bus factor of four.

    Adopting the name would claim a measurement this tool does not make,
    which is the defect the whole project exists to prevent. The
    vocabulary is reconciled in `standard.md` by stating the relationship
    instead, and ADR 007 §4 records the deviation.

    This test exists so nobody closes that ADR item by renaming the key.
    """
    from maintainability_audit._formula import CATEGORY_ASPECTS

    emitted = {name for aspects in CATEGORY_ASPECTS.values() for name in aspects}

    assert "knowledge_concentration" in emitted
    assert "bus_factor" not in emitted, (
        "renaming the ownership proxy to `bus_factor` claims a count of "
        "people the tool never computes; see standard.md for the mapping"
    )


def test_the_docs_state_the_current_advertised_aspect_count() -> None:
    """Recurrence guard for the aspect-count drift.

    ``architecture.md``'s data-flow node and ``standard.md``'s Layer-1 line
    each state a *live* aspect count, and both went stale the day Class 5
    added the fourteenth aspect while the aspect table beside them already
    listed it. Anchored to those two exact sentences, so a future aspect
    fails here until the prose is updated — the historical past-tense
    counts elsewhere ("thirteen advertised, twelve effective") are left
    untouched because they describe a fixed moment, not the current set.
    """
    from pathlib import Path

    from maintainability_audit._formula import CALIBRATED_ASPECTS, RUBRIC_ASPECTS

    count = len(CALIBRATED_ASPECTS) + len(RUBRIC_ASPECTS)
    words = {12: "Twelve", 13: "Thirteen", 14: "Fourteen", 15: "Fifteen", 16: "Sixteen"}
    docs = Path(__file__).resolve().parents[1] / "docs"
    architecture = (docs / "architecture.md").read_text(encoding="utf-8")
    standard = (docs / "standard.md").read_text(encoding="utf-8")

    assert f"aspect_scores — {count} aspects" in architecture, (
        f"docs/architecture.md data-flow node must state {count} aspects"
    )
    assert f"{words[count]} measured aspects" in standard, (
        f"docs/standard.md Layer 1 must state {words[count].lower()} measured aspects"
    )

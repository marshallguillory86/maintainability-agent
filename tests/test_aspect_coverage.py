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

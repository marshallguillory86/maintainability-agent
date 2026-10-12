"""An analyzer's findings that the grade does not use are said to be unused.

Found from a field report on a C# repository: jscpd ran and reported 439
duplicate blocks in its `.cs` files, the report listed them, and the
duplication grade came from the built-in detector's 196 — by design, since
only `declarations` takes its score from the analyzer tier
(`_criteria_scope.ANALYZER_DIMENSIONS`). Nothing on the page said so, and a
reader concluded the analyzer's output had been ignored.

When an analyzer that ran reports findings for a concept whose dimension is
scored from the built-in detectors only, the coverage section names the
tool, the count, the dimension, and that the count does not move the grade.
"""

from __future__ import annotations

from maintainability_audit._coverage_notes import coverage_notes
from maintainability_audit._criteria_scope import ANALYZER_DIMENSIONS, reported_not_scored


def _coverage(*ran: dict) -> dict:
    return {"by_outcome": {"ran": list(ran)}, "concepts_unexamined": []}


JSCPD = {"tool": "jscpd", "tier": "analyzer", "concepts": ["duplication"], "findings": 439, "measurements": 1}


def test_an_analyzer_reporting_on_a_built_in_scored_dimension_is_listed() -> None:
    assert "duplication" not in ANALYZER_DIMENSIONS  # the premise the note exists for

    assert reported_not_scored(_coverage(JSCPD)) == [
        {"tool": "jscpd", "concept": "duplication", "dimension": "duplication", "findings": 439}]


def test_an_analyzer_that_drives_its_dimension_or_found_nothing_is_not_listed() -> None:
    lizard = {"tool": "lizard", "tier": "analyzer", "concepts": ["cyclomatic_complexity", "declaration_lines"],
              "findings": 0, "measurements": 9699}
    quiet = dict(JSCPD, findings=0)
    built_in = {"tool": "duplicate-blocks", "tier": "built-in", "concepts": ["duplication"], "findings": 196}

    assert reported_not_scored(_coverage(lizard, quiet, built_in)) == []


def test_the_coverage_section_says_the_count_does_not_move_the_grade() -> None:
    coverage = _coverage(JSCPD)
    coverage["reported_not_scored"] = reported_not_scored(coverage)

    text = "\n".join(coverage_notes(coverage))

    assert "jscpd" in text and "439" in text
    assert "does not move the grade" in text

"""D68: the declarations dimension says which tier measured it.

`_declaration_pressure` returns `None` -- falling the dimension back to
the built-in detectors -- whenever the analyzers between them did not
supply all three of `DECLARATION_CRITERIA`. That fallback is correct: the
built-in path fails a declaration on cyclomatic complexity **or** lines
**or** cognitive complexity, and a rate built from a narrower set is not
comparable to it.

What was wrong is that it happened in silence. P8 requires the report to
state what measured each value, and a reader saw a declarations rate with
nothing attributing it. Nor is it a corner: lizard reports cyclomatic
complexity and declaration lines and no cognitive complexity at all, so a
JavaScript repository with lizard installed takes this branch on every
run -- while `decisions.md` credited the analyzer pool for the work.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import (
    DECLARATION_CRITERIA,
    analyzer_pressures,
    declaration_concepts_missing,
    declined_dimensions,
)
from maintainability_audit.config import DEFAULT_CONFIG


def _reading(concept: str, value: float, unit: str = "app.js:tangled") -> Measurement:
    return Measurement(
        tool="lizard", unit=unit, concept=concept, value=value, path="app.js",
    )


LIZARD_CONCEPTS = ("cyclomatic_complexity", "declaration_lines")


def test_lizard_alone_cannot_drive_the_declarations_dimension() -> None:
    """The premise. If this ever fails, the rest of the file is moot."""
    covered = set(LIZARD_CONCEPTS)
    missing = declaration_concepts_missing(covered)
    assert missing == ("cognitive_complexity",), (
        "lizard's concept set changed; the JavaScript declaration source "
        f"may no longer be the built-in scanner: {missing}"
    )
    assert {concept for concept, _w, _f in DECLARATION_CRITERIA} - covered, (
        "the criteria no longer exceed what lizard emits"
    )


def test_a_partial_concept_set_falls_back_rather_than_estimating() -> None:
    """Two criteria out of three is not a comparable rate."""
    readings = [_reading(concept, 12.0) for concept in LIZARD_CONCEPTS]
    pressures = analyzer_pressures(readings, DEFAULT_CONFIG["thresholds"])
    assert pressures["declarations"] is None, (
        "a declarations rate was computed from a concept set that cannot "
        "see a long-but-simple function, and it drives the estimate"
    )


def test_the_fallback_is_attributed_rather_than_inferred() -> None:
    """P8: the report says who measured it and what was missing."""
    readings = [_reading(concept, 12.0) for concept in LIZARD_CONCEPTS]
    declined = declined_dimensions(readings)
    assert len(declined) == 1, declined
    entry: dict[str, Any] = declined[0]
    assert entry["dimension"] == "declarations"
    assert entry["missing_concepts"] == ["cognitive_complexity"]
    assert "built-in" in entry["measured_by"]
    assert "cognitive_complexity" in entry["reason"]


def test_a_complete_concept_set_declines_nothing() -> None:
    """The disclosure must not fire when the analyzers did supply it."""
    readings = [
        _reading(concept, 12.0)
        for concept, _warn, _fail in DECLARATION_CRITERIA
    ]
    assert declined_dimensions(readings) == (), (
        "a dimension the analyzers fully covered was reported as declined"
    )
    pressures = analyzer_pressures(readings, DEFAULT_CONFIG["thresholds"])
    assert pressures["declarations"] is not None, (
        "the analyzer tier stopped driving a dimension it fully measured"
    )


def test_the_declined_dimension_reaches_the_reader() -> None:
    """A disclosure only in JSON is not a disclosure to a person."""
    from maintainability_audit._scan_view import analyzer_coverage_markdown

    rendered = "\n".join(analyzer_coverage_markdown({
        "selection": {"concerns": ["complexity"], "depth": "baseline",
                      "license_policy": "permissive"},
        "sources": {"built_in": 8, "analyzers": 1},
        "tools_attempted": 1,
        "tools_contributed": 1,
        "by_outcome": {},
        "concepts_single_source": [],
        "concepts_unexamined": [],
        "dimensions_declined": list(declined_dimensions(
            [_reading(concept, 12.0) for concept in LIZARD_CONCEPTS])),
    }))
    assert "declarations" in rendered and "built-in" in rendered, rendered
    assert "cognitive_complexity" in rendered, (
        "the reader is told the dimension fell back but not what was "
        f"missing, so they cannot act on it: {rendered}"
    )

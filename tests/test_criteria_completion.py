"""Completing an analyzer's criterion set from the built-in tier.

The `declarations` dimension may be analyzer-driven only when every
declaration was eligible to fail on all three criteria — cyclomatic
complexity, declaration lines, cognitive complexity. No single tier
supplies all three: `lizard` reads sixteen languages and reports
cognitive complexity for none of them, `complexipy` reports cognitive
complexity for Python alone, and PMD reports it as threshold violations
rather than a reading per declaration, which cannot make a rate.

Measured consequence, before this: of the 112 corpus repositories, zero
satisfied the criterion set without `complexipy`. The analyzer tier could
drive this dimension for Python and nothing else, by construction.

The union of the two tiers per declaration is complete, and the join is
`(path, start_line)` — exact on this package, where all 1,008 `lizard`
declarations match a built-in declaration at the same start line.

**The path spellings in these tests are deliberately inconsistent.** This
merge shipped once with the whole suite green and the join matching
nothing, because three vocabularies meet here — `./src/x.py` from lizard,
an absolute path from complexipy, `src/x.py` from the scanner — and every
test built both sides of the join from the same string. A test that
agrees with itself about paths cannot fail the way production did.
"""
from __future__ import annotations

import pytest

from maintainability_audit._criteria_scope import canonical_path
from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import (
    ExternalPressures,
    analyzer_pressures,
    analyzer_production_pressures,
    declined_dimensions,
)
from maintainability_audit._second_source import analyzer_scored

ROOT = "/repo/"


@pytest.fixture
def limits() -> dict:
    return {
        "warn_complexity": 8, "max_complexity": 15,
        "warn_function_lines": 40, "max_function_lines": 60,
        "warn_cognitive_complexity": 10, "max_cognitive_complexity": 20,
    }


def _lizard_go(count: int) -> list[Measurement]:
    """Go declarations as lizard reports them: `./` prefix, no cognitive."""
    out: list[Measurement] = []
    for i in range(count):
        unit = f"./server.go:fn{i}"
        out += [
            Measurement("cyclomatic_complexity", unit, 5, "lizard", "./server.go", 100 + i),
            Measurement("declaration_lines", unit, 20, "lizard", "./server.go", 100 + i),
        ]
    return out


def _built_in_go(count: int, cognitive: float = 4.0) -> dict:
    """The scanner's reading of the same declarations: repo-relative path."""
    return {
        ("server.go", 100 + i): {
            "cyclomatic_complexity": 5.0,
            "declaration_lines": 20.0,
            "cognitive_complexity": cognitive,
        }
        for i in range(count)
    }


def test_a_language_with_no_cognitive_source_is_completed(limits: dict) -> None:
    """Go is the case the merge exists for.

    No tool in the pool reports cognitive complexity for Go, so before
    this the whole dimension fell back to the built-in tier and lizard's
    cyclomatic and length readings — the two it measures well, from an
    independent implementation — were discarded.
    """
    go = _lizard_go(10)

    assert analyzer_pressures(go, limits)["declarations"] is None
    completed = analyzer_pressures(go, limits, _built_in_go(10), ROOT)
    assert completed["declarations"] == pytest.approx(0.25)


def test_the_join_survives_three_path_spellings(limits: dict) -> None:
    """The defect that let this ship inert, as a test.

    lizard writes `./server.go`, the scanner writes `server.go`, and
    complexipy writes the absolute path. Keyed on any of them as given,
    the join matches nothing — which is exactly what happened, with 2,535
    tests passing and the feature dead, because every test built both
    sides of the join from one string.
    """
    assert canonical_path(ROOT, "./server.go") == "server.go"
    assert canonical_path(ROOT, "/repo/server.go") == "server.go"
    assert canonical_path(ROOT, "server.go") == "server.go"

    absolute = [
        Measurement("cyclomatic_complexity", "u", 5, "lizard", "/repo/server.go", 100),
        Measurement("declaration_lines", "u", 20, "lizard", "/repo/server.go", 100),
    ]
    assert analyzer_pressures(
        absolute, limits, _built_in_go(1), ROOT)["declarations"] is not None


def test_a_declaration_the_scanner_never_saw_is_not_invented(limits: dict) -> None:
    """No built-in partner means no completion, and no completion means
    the criterion set is still short — so the dimension falls back rather
    than scoring the declaration on two criteria of three.
    """
    go = _lizard_go(3)
    elsewhere = {("other.go", 999): {"cognitive_complexity": 4.0}}

    assert analyzer_pressures(go, limits, elsewhere, ROOT)["declarations"] is None


def test_completion_does_not_overwrite_what_an_analyzer_measured(
    limits: dict,
) -> None:
    """Only the missing concepts come from the scanner.

    ADR 006 makes the analyzer primary for what it measures. A completion
    that replaced lizard's cyclomatic reading with the built-in one would
    quietly undo that, and the number would still look plausible.
    """
    unit = "./server.go:fn0"
    go = [
        Measurement("cyclomatic_complexity", unit, 30, "lizard", "./server.go", 100),
        Measurement("declaration_lines", unit, 20, "lizard", "./server.go", 100),
    ]
    # The scanner disagrees sharply on complexity and supplies cognitive.
    built_in = {("server.go", 100): {
        "cyclomatic_complexity": 1.0,
        "declaration_lines": 20.0,
        "cognitive_complexity": 4.0,
    }}

    pressure = analyzer_pressures(go, limits, built_in, ROOT)["declarations"]

    # lizard's 30 is far over `max_complexity` 15, so the unit must band
    # severe. Had the scanner's 1.0 won, this would be clean.
    assert pressure is not None
    assert pressure > 0.5, (
        f"pressure {pressure} suggests the built-in reading replaced "
        "lizard's rather than completing it"
    )


def test_the_note_states_the_composition_rather_than_crediting_one_tier(
    limits: dict,
) -> None:
    """P8, and the self-contradiction that reached a rendered report.

    With the merge in place the report said "Analyzer readings for
    declarations" and "declarations measured by built-in detectors" in
    the same document, because the disclosure was computed before the
    completion. The note now runs the same computation as the score.
    """
    go = _lizard_go(4)

    without = declined_dimensions(go)
    assert without[0]["measured_by"] == "built-in detectors"

    with_completion = declined_dimensions(go, False, _built_in_go(4), ROOT)
    entry = with_completion[0]
    assert entry["measured_by"] == "analyzers, completed by built-in detectors"
    assert entry["languages"] == ["Go"]
    assert entry["missing_concepts"] == ["cognitive_complexity"]
    assert "built-in scanner supplied" in entry["reason"]


def test_a_completed_go_pressure_names_its_builtin_fill_when_published(
    limits: dict,
) -> None:
    """The score's source label must not credit lizard for scanner evidence.

    The two sides deliberately use different spellings: lizard's ``./``
    path and the scanner's repository-relative path.  Building both from
    one path string is the inert-merge hole #198 already had.  Go is a
    non-Python population where lizard supplies cyclomatic complexity and
    lines while the built-in scanner supplies cognitive complexity.
    """
    go = _lizard_go(3)
    completed = _built_in_go(3)
    published = ExternalPressures(
        all_code=analyzer_pressures(go, limits, completed, ROOT),
        production=analyzer_production_pressures(go, limits, completed, ROOT),
        measurements=tuple(go),
    )

    assert analyzer_scored(published) == [
        "declarations (completed by built-in detectors)"
    ], "a mixed-tier pressure is published as an analyzer-only reading"


def test_a_still_incomplete_language_is_still_reported_as_a_fallback(
    limits: dict,
) -> None:
    """Completion that does not complete must not read as if it did."""
    go = _lizard_go(3)
    partial = {("server.go", 100 + i): {"declaration_lines": 20.0} for i in range(3)}

    entry = declined_dimensions(go, False, partial, ROOT)[0]

    assert entry["measured_by"] == "built-in detectors"
    assert analyzer_pressures(go, limits, partial, ROOT)["declarations"] is None

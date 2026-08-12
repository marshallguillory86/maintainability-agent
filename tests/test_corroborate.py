"""Combining readings from several tools — ADR 006.

Tools that claim the same metric disagree: lizard and radon put
`change_coupling` at cyclomatic complexity 13, mccabe at 8, because radon and
lizard count boolean operators and comprehensions and mccabe's path graph does
not. A single-tool number is therefore a measurement of that tool's
convention. The answer is arithmetic — weighted mean, keep the spread — not
arbitration.

The failure this module nearly shipped with: it could not corroborate
anything. 1465 measurements from three tools produced **zero** corroborated
readings, because each tool spelled the unit differently — absolute versus
relative paths, `Class::method` versus `method`. Identity has to be reconciled
before values can be, and a corroboration layer that never corroborates is
worse than none because the reports look multi-sourced.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._adapters import Measurement
from maintainability_audit._corroborate import (
    agreement,
    canonical_unit,
    combine,
    single_source_concepts,
    weight_for,
)


def _m(tool: str, value: float, unit: str = "a.py::f", concept: str = "complexity") -> Measurement:
    return Measurement(concept=concept, unit=unit, value=value, tool=tool, path="a.py")


def test_two_tools_on_one_unit_become_one_reading_with_a_spread() -> None:
    """The mccabe-versus-radon case, which is the reason this exists."""
    combined = combine([_m("radon", 13), _m("mccabe", 8)])

    assert len(combined) == 1
    only = combined[0]
    assert only.value == pytest.approx(10.5)
    assert (only.low, only.high) == (8, 13)
    assert only.tools == ("mccabe", "radon")
    assert only.corroborated


def test_disagreement_is_kept_rather_than_arbitrated() -> None:
    """Picking a tool would be picking a convention and hiding the choice."""
    wide = combine([_m("a", 2), _m("b", 20)])[0]
    tight = combine([_m("a", 10, unit="b.py::g"), _m("b", 11, unit="b.py::g")])[0]

    assert wide.spread > tight.spread
    assert agreement([wide])["complexity"] > agreement([tight])["complexity"]


def test_paths_and_member_names_are_reconciled_before_values() -> None:
    """The defect that made corroboration structurally impossible.

    complexipy reports absolute paths and `Class::method`; lizard reports
    relative paths and a bare member name. Without reconciling identity,
    no two tools ever group together.
    """
    root = Path("/repo")

    assert canonical_unit("/repo/a.py::Klass::run", root) == "a.py::run"
    assert canonical_unit("a.py::run", root) == "a.py::run"

    merged = combine(
        [_m("complexipy", 7, unit="/repo/a.py::Klass::run"),
         _m("lizard", 5, unit="a.py::run")],
        root,
    )
    assert len(merged) == 1 and merged[0].corroborated


def test_a_name_one_tool_cannot_disambiguate_is_not_pooled() -> None:
    """lizard emits bare member names.

    Three classes' `version_argv` in one file are indistinguishable in its
    output. Pooling them and calling it corroboration would manufacture
    agreement between readings that are not about the same code, so they
    stay single-source — the honest limit of what these tools can jointly
    establish.
    """
    root = Path("/repo")
    combined = combine(
        [
            _m("lizard", 3, unit="a.py::run"),
            _m("lizard", 9, unit="a.py::run"),
            _m("complexipy", 4, unit="/repo/a.py::A::run"),
            _m("complexipy", 8, unit="/repo/a.py::B::run"),
        ],
        root,
    )

    assert all(not item.corroborated for item in combined), (
        "an ambiguous name must not become false agreement"
    )


def test_one_tool_reporting_a_unit_twice_makes_it_ambiguous_not_pooled() -> None:
    """Averaging a tool's duplicate readings would invent a unit.

    A tool naming the same unit twice is describing two different things
    it cannot tell apart. Averaging them produces a number about neither,
    and then pairing that with another tool's reading would call it
    agreement. Splitting is the only honest option, so no reading here is
    corroborated.
    """
    combined = combine([_m("a", 10), _m("a", 20), _m("b", 0)])

    assert all(not item.corroborated for item in combined)
    assert {item.value for item in combined} == {10, 20, 0}, (
        "each reading survives as itself rather than becoming an average"
    )


def test_weights_default_to_equal_and_are_declared_not_inferred() -> None:
    """An unequal weight is a judgment; one nobody wrote down is worse than none."""
    assert weight_for("complexity", "lizard") == weight_for("complexity", "radon") == 1.0


def test_a_single_source_concept_is_reported_as_such() -> None:
    """A lone reading carries a convention nobody checked."""
    combined = combine([_m("lizard", 5), _m("radon", 3, concept="metrics", unit="a.py")])

    assert single_source_concepts(combined) == {"complexity", "metrics"}


def test_combination_is_stable_across_runs() -> None:
    """Unstable ordering makes every report diff noise."""
    measurements = [_m("b", 2, unit="z.py::f"), _m("a", 1, unit="a.py::f"),
                    _m("c", 3, unit="a.py::f", concept="metrics")]

    first = [(c.concept, c.unit) for c in combine(measurements)]
    second = [(c.concept, c.unit) for c in combine(list(reversed(measurements)))]

    assert first == second == sorted(first)


def test_agreement_ignores_uncorroborated_readings() -> None:
    """A concept only one tool measured has no spread to report.

    Counting it as zero spread would read as perfect agreement, which is
    the absence-as-value defect wearing a statistics hat.
    """
    lonely = combine([_m("lizard", 5)])

    assert agreement(lonely) == {}


def test_a_concept_is_one_measurement_not_a_family() -> None:
    """The error this cost two rounds to see.

    `complexity` first covered both lizard's cyclomatic count and
    complexipy's cognitive score, so 812 unit pairs looked corroborated
    while disagreeing by 107% — averaging a branch count with a
    nesting-weighted score produces a number about neither. `metrics`
    repeated it one level down, pooling a per-function line count with a
    per-file maintainability index.

    The signal that exposed both was the disagreement figure itself:
    genuine corroboration between careful tools does not sit at 100%.
    A concept must therefore name one measurement at one granularity.
    """
    from maintainability_audit._adapters import ADAPTERS, adapter_for

    families = {"complexity", "metrics", "structure"}
    for slug in ADAPTERS:
        adapter = adapter_for(slug)
        if adapter.emits == "verdict":
            # Verdict emitters carry findings, which are grouped by the
            # user-facing concern rather than by a measured concept.
            continue
        overlap = families & set(adapter.concepts)
        assert not overlap, (
            f"{slug} emits {sorted(overlap)}, which name families rather than "
            "measurements; two different metrics under one name produce false "
            "corroboration"
        )


def test_every_measured_concept_belongs_to_a_user_facing_concern() -> None:
    """A concept nothing maps to is unreachable.

    Users select concerns; tools emit concepts. A concept absent from
    the map can never be requested, so its tool would silently never run.
    """
    from maintainability_audit._adapters import ADAPTERS, adapter_for
    from maintainability_audit._catalog import CONCERNS, concepts_for

    reachable = {concept for concern in CONCERNS for concept in concepts_for(concern)}
    for slug in ADAPTERS:
        adapter = adapter_for(slug)
        if adapter.emits == "verdict":
            continue
        unreachable = set(adapter.concepts) - reachable
        assert not unreachable, (
            f"{slug} measures {sorted(unreachable)}, which no concern selects"
        )

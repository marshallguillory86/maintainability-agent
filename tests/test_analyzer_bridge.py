"""The analyzer bridge: two sources, one rubric — ADR 008.

Split from `test_bands.py` when that file crossed the 500-line gate this
tool enforces on everyone else. The seam is real: `test_bands` is about
the band matrix — thresholds in, pressure out — while everything here is
about whether an external analyzer's numbers and the built-in
detector's numbers are the *same measurement*, which is a different
question with a much worse track record.

Four ratios were published from that comparison before it could be
trusted: 4.0x from a sample of one, 0.3x from mixing a Python-only
concept with a multi-language one, 0.19x from two different formulas
wearing one name, and 0.77x from counting complexity while the other
side counted lines, complexity and cognitive complexity. Every one
described the bridge rather than the code. These tests exist so the
fifth number means something.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from _analyzer_fixtures import (
    _metric,
    _summary_from_metrics,
    thresholds,
)

__all__ = ["thresholds"]


def test_analyzer_pressures_are_a_drop_in_for_the_built_in_ones(thresholds: dict) -> None:
    """Same formula, not merely the same key names.

    The first version returned a mean band pressure while the built-in
    path returns a weighted rate of threshold breaches. Two formulas
    under one name, compared across forty repositories, and the
    difference read as tool disagreement — when on a file where all three
    could be checked, the built-in detector, lizard and eslint reported
    cyclomatic complexity 11, 11 and 11.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import (
        ANALYZER_DIMENSIONS,
        analyzer_pressures,
        dimension_pressures,
    )

    # Four declarations: one above max_complexity, one between warn and
    # max, two clean. The built-in path is handed the same counts.
    values = [thresholds["max_complexity"] + 5, thresholds["warn_complexity"] + 1, 1, 1]
    # All three criteria, because a dimension is not composed from a
    # partial concept set. The extra two are clean, so the breach counts
    # are the ones the built-in path is handed below.
    measurements = [
        Measurement(concept=concept, unit=f"a.py::f{i}", value=float(value),
                    tool="lizard", path="a.py")
        for i, v in enumerate(values)
        for concept, value in (
            ("cyclomatic_complexity", v),
            ("declaration_lines", 1),
            ("cognitive_complexity", 0),
        )
    ]
    functions = [
        _metric(v, name=f"f{i}") for i, v in enumerate(values)
    ]

    from_analyzers = analyzer_pressures(measurements, thresholds)["declarations"]
    from_builtin = dimension_pressures(_summary_from_metrics(functions, thresholds))["declarations"]

    assert from_analyzers == pytest.approx(from_builtin), (
        "identical breach counts over an identical population must give an "
        "identical pressure, or the two sources are not comparable"
    )
    assert set(ANALYZER_DIMENSIONS) <= set(dimension_pressures(_summary_from_metrics(functions, thresholds)))


def test_a_dimension_no_analyzer_measured_is_unmeasured_not_zero(thresholds: dict) -> None:
    """The defect this whole project exists to remove, one layer out."""
    from maintainability_audit._pressures import analyzer_pressures

    assert all(v is None for v in analyzer_pressures([], thresholds).values())


def test_the_rubric_owns_the_threshold_not_the_tool(thresholds: dict) -> None:
    """ADR 008's seam: a tool contributes numbers, the rubric decides meaning.

    The same measurements under a stricter rubric must produce more
    pressure. If they do not, a threshold is coming from somewhere other
    than the configuration.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_pressures

    # The complete criteria set; only complexity varies, so the two
    # threshold settings below differ in exactly one thing.
    measurements = [
        Measurement(concept=concept, unit=f"a.py::f{i}", value=float(value),
                    tool="lizard", path="a.py")
        for i, v in enumerate([3, 8, 12, 17])
        for concept, value in (
            ("cyclomatic_complexity", v),
            ("declaration_lines", 1),
            ("cognitive_complexity", 0),
        )
    ]
    lenient = analyzer_pressures(measurements, {**thresholds, "warn_complexity": 30,
                                                "max_complexity": 50})["declarations"]
    strict = analyzer_pressures(measurements, {**thresholds, "warn_complexity": 2,
                                               "max_complexity": 4})["declarations"]

    assert lenient == 0.0
    assert strict > lenient


def test_both_paths_agree_on_every_failure_criterion(thresholds: dict) -> None:
    """The instrument test, written before the instrument.

    `function_status` fails a declaration on **lines OR complexity OR
    cognitive complexity**. A bridge that counts only complexity breaches
    is measuring something narrower and must not be compared against it —
    but that is exactly what I did, three times, quoting ratios of 4x,
    0.3x and 0.19x. Every one was an artifact of my own bridge rather
    than a fact about the tools.

    This sweeps each criterion in isolation: one declaration breaching
    only that criterion, everything else clean. Both paths must count the
    same breach, or any ratio between them means nothing.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_pressures, dimension_pressures
    from maintainability_audit.declarations import function_status

    clean = {"lines": 1, "complexity": 1, "cognitive": 0}
    breaches = {
        "lines": {**clean, "lines": thresholds["max_function_lines"] + 1},
        "complexity": {**clean, "complexity": thresholds["max_complexity"] + 1},
        "cognitive": {**clean, "cognitive": thresholds["max_cognitive_complexity"] + 1},
    }

    for criterion, breaching in breaches.items():
        assert function_status(
            breaching["lines"], breaching["complexity"], thresholds, breaching["cognitive"]
        ) == "fail", f"fixture for {criterion} does not actually breach"

        # The built-in path, handed the same four declarations. Under
        # the band matrix the comparable construction is the summary the
        # production code builds from these values, not a hand-made
        # count — that is the two-formulas regression in miniature.
        functions = [
            _metric(decl["complexity"], lines=decl["lines"],
                    cognitive=decl["cognitive"], name=f"f{i}")
            for i, decl in enumerate([breaching, clean, clean, clean])
        ]
        expected = dimension_pressures(
            _summary_from_metrics(functions, thresholds))["declarations"]

        # The analyzer path, given the same four declarations as measurements.
        measurements = [
            Measurement(concept=concept, unit=f"a.py::f{i}", value=float(value),
                        tool="lizard", path="a.py")
            for i, decl in enumerate([breaching, clean, clean, clean])
            for concept, value in (
                ("cyclomatic_complexity", decl["complexity"]),
                ("declaration_lines", decl["lines"]),
                ("cognitive_complexity", decl["cognitive"]),
            )
        ]
        actual = analyzer_pressures(measurements, thresholds)["declarations"]

        assert actual == pytest.approx(expected), (
            f"{criterion}: built-in counts this as a failure and the analyzer path "
            f"does not ({expected} vs {actual}). Any ratio between two paths that "
            "disagree about what a failure is measures the disagreement, not the code."
        )


def test_every_criterion_the_bridge_reads_is_a_concept_an_adapter_emits() -> None:
    """A green test over a pipeline that never runs.

    The equivalence test above constructs `declaration_lines`
    measurements directly, so it passed while lizard emitted `nloc` and
    the lines criterion silently never fired in production. A test that
    fabricates the name its subject expects proves the subject consistent
    with itself and nothing more.

    This checks the two vocabularies actually meet.
    """
    from maintainability_audit._pressures import DECLARATION_CRITERIA
    from maintainability_audit._tool_adapters import ADAPTERS, adapter_for

    emitted = {c for slug in ADAPTERS for c in adapter_for(slug).concepts}
    needed = {concept for concept, _warn, _fail in DECLARATION_CRITERIA}
    missing = needed - emitted

    assert not missing, (
        f"{sorted(missing)} are read by the scoring bridge and emitted by no adapter, "
        "so those criteria can never fire however green the unit tests are"
    )


def test_a_declaration_breaching_two_limits_counts_once(thresholds: dict) -> None:
    """`function_status` grades a declaration, not its individual limits.

    A function that is both too long and too complex is one failure.
    Counting per criterion would inflate the worst code by a factor of
    however many limits it happens to break, and the two paths would
    diverge exactly where a codebase is in most trouble.

    This was asserted in a comment until it was asserted here, which is
    the same gap as claiming enforcement from a test's name.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_pressures
    from maintainability_audit.declarations import function_status

    long_and_complex = {
        "cyclomatic_complexity": thresholds["max_complexity"] + 1,
        "declaration_lines": thresholds["max_function_lines"] + 1,
        "cognitive_complexity": thresholds["max_cognitive_complexity"] + 1,
    }
    assert function_status(
        long_and_complex["declaration_lines"],
        long_and_complex["cyclomatic_complexity"],
        thresholds,
        long_and_complex["cognitive_complexity"],
    ) == "fail"

    def _pressure(units: list[dict[str, float]]) -> float:
        return analyzer_pressures(
            [
                Measurement(concept=concept, unit=f"a.py::f{i}", value=float(value),
                            tool="lizard", path="a.py")
                for i, unit in enumerate(units)
                for concept, value in unit.items()
            ],
            thresholds,
        )["declarations"]

    clean = {"cyclomatic_complexity": 1.0, "declaration_lines": 1.0, "cognitive_complexity": 0.0}
    breaks_three = _pressure([long_and_complex, clean, clean, clean])
    breaks_one = _pressure([{**clean, "cyclomatic_complexity": thresholds["max_complexity"] + 1},
                            clean, clean, clean])

    assert breaks_three == pytest.approx(breaks_one), (
        "one declaration is one failure however many limits it breaks"
    )


def test_a_warning_is_weighted_below_a_failure(thresholds: dict) -> None:
    """Both paths discount warnings identically, or the rates diverge.

    The equivalence test above only exercises failures, so a bridge that
    ignored warnings entirely would still have passed it.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_pressures, dimension_pressures

    warning = {
        "cyclomatic_complexity": (thresholds["warn_complexity"] + thresholds["max_complexity"]) / 2,
        "declaration_lines": 1.0,
        "cognitive_complexity": 0.0,
    }
    clean = {"cyclomatic_complexity": 1.0, "declaration_lines": 1.0, "cognitive_complexity": 0.0}
    measurements = [
        Measurement(concept=concept, unit=f"a.py::f{i}", value=float(value),
                    tool="lizard", path="a.py")
        for i, unit in enumerate([warning, clean, clean, clean])
        for concept, value in unit.items()
    ]

    functions = [
        _metric(int(unit["cyclomatic_complexity"]), lines=int(unit["declaration_lines"]),
                cognitive=int(unit["cognitive_complexity"]), name=f"f{i}")
        for i, unit in enumerate([warning, clean, clean, clean])
    ]

    from_analyzers = analyzer_pressures(measurements, thresholds)["declarations"]
    from_builtin = dimension_pressures(_summary_from_metrics(functions, thresholds))["declarations"]

    assert from_analyzers == pytest.approx(from_builtin)
    assert 0 < from_analyzers < 1 / 4, "a warning weighs less than a failure would"


def test_analyzer_production_pressure_excludes_test_declarations(thresholds: dict) -> None:
    """Both tiers must score the same population, or neither number means anything.

    The built-in path splits production from test code before it counts
    anything: growing a test suite should not change how maintainable the
    production code is. The analyzer path did not, so every declaration in
    `tests/` landed in the denominator and diluted the rate.

    The size of that is not theoretical. On flask, 2206 declarations reach
    the analyzers and only 712 are production; the pressure moves 0.0049 →
    0.0138, close to threefold. Left alone, the bridge would have rewarded
    repositories for having large test suites — and would have done it
    invisibly, inside a number presented as the same measurement the
    built-in detector makes.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import (
        analyzer_pressures,
        analyzer_production_pressures,
    )

    def unit(path: str, name: str, complexity: float) -> list[Measurement]:
        """One declaration, measured on all three criteria.

        A partial set makes the whole dimension unmeasured, so every
        fixture here names each criterion even where only complexity
        carries the point being tested.
        """
        return [
            Measurement(concept=concept, unit=f"{path}::{name}", value=float(value),
                        tool="lizard", path=path)
            for concept, value in (
                ("cyclomatic_complexity", complexity),
                ("declaration_lines", 1),
                ("cognitive_complexity", 0),
            )
        ]

    def breaching(path: str, name: str) -> list[Measurement]:
        return unit(path, name, thresholds["max_complexity"] + 5)

    def clean(path: str, name: str) -> list[Measurement]:
        return unit(path, name, 1.0)

    production = [*breaching("src/a.py", "f"), *clean("src/a.py", "g")]
    # Same two declarations again, in files the built-in path calls tests.
    tests = [*clean("tests/test_a.py", "t1"), *clean("src/a_test.py", "t2"),
             *clean("spec/thing.js", "t3")]

    everything = production + tests
    assert analyzer_production_pressures(everything, thresholds)["declarations"] == (
        analyzer_production_pressures(production, thresholds)["declarations"]
    ), "test declarations must not enter the production population"
    # And the all-code reading keeps them, because it stands in for
    # `dimension_pressures`, which counts every declaration scanned.
    assert analyzer_pressures(everything, thresholds)["declarations"] < (
        analyzer_pressures(production, thresholds)["declarations"]
    ), "the all-code reading must keep the population dimension_pressures uses"


def test_a_repository_of_only_tests_has_no_production_pressure(
    thresholds: dict,
) -> None:
    """Excluded, not counted as clean.

    Once test declarations are filtered out, a tree with nothing else has
    an empty population — and an empty population is unmeasured. Returning
    0.0 there would be the absence-as-value defect wearing the filter as a
    disguise.
    """
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_production_pressures

    only_tests = [
        Measurement(concept="cyclomatic_complexity", unit="tests/test_a.py::t",
                    value=99.0, tool="lizard", path="tests/test_a.py"),
    ]

    assert analyzer_production_pressures(only_tests, thresholds)["declarations"] is None


@pytest.mark.parametrize(
    ("suffix", "body"),
    [
        (".go", "package main\nfunc Real() int { return 1 }\nfunction decoy() {}\n"),
        (".c", "int real(void) { return 1; }\nfunction decoy() {}\n"),
    ],
)
def test_analyzer_declarations_do_not_enable_func_patterns_for_unparsed_languages(
    tmp_path: Path,
    thresholds: dict,
    suffix: str,
    body: str,
) -> None:
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import analyzer_production_pressures
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = tmp_path / suffix.lstrip(".")
    root.mkdir()
    path = root / f"main{suffix}"
    path.write_text(body, encoding="utf-8")
    config = load_config(None)
    config["paths"]["include_extensions"] = [
        *config["paths"]["include_extensions"], suffix,
    ]
    report = build_report(root, config)
    measurements = [
        Measurement(concept=concept, unit=f"main{suffix}::Real", value=float(value),
                    tool="lizard", path=f"main{suffix}")
        for concept, value in (
            ("cyclomatic_complexity", 1),
            ("declaration_lines", 1),
            ("cognitive_complexity", 0),
        )
    ]

    assert report["summary"]["declarations_scanned"] == 0, (
        "FUNC_PATTERNS must not manufacture a built-in population for this language"
    )
    assert analyzer_production_pressures(measurements, thresholds)["declarations"] is not None

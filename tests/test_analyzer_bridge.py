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

from maintainability_audit.config import DEFAULT_CONFIG


@pytest.fixture
def thresholds() -> dict:
    return dict(DEFAULT_CONFIG["thresholds"])


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
    from maintainability_audit.evidence import Measured, SummaryEvidence

    # Four declarations: one above max_complexity, one between warn and
    # max, two clean. The built-in path is handed the same counts.
    values = [thresholds["max_complexity"] + 5, thresholds["warn_complexity"] + 1, 1, 1]
    measurements = [
        Measurement(concept="cyclomatic_complexity", unit=f"a.py::f{i}", value=float(v),
                    tool="lizard", path="a.py")
        for i, v in enumerate(values)
    ]
    fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "t"))
    fields.update(
        declarations_scanned=Measured(4, "t"),
        function_failures=Measured(1, "t"),
        function_warnings=Measured(1, "t"),
    )

    from_analyzers = analyzer_pressures(measurements, thresholds)["declarations"]
    from_builtin = dimension_pressures(SummaryEvidence(**fields))["declarations"]

    assert from_analyzers == pytest.approx(from_builtin), (
        "identical breach counts over an identical population must give an "
        "identical pressure, or the two sources are not comparable"
    )
    assert set(ANALYZER_DIMENSIONS) <= set(dimension_pressures(SummaryEvidence(**fields)))


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

    measurements = [
        Measurement(concept="cyclomatic_complexity", unit=f"a.py::f{i}", value=float(v),
                    tool="lizard", path="a.py")
        for i, v in enumerate([3, 8, 12, 20])
    ]
    lenient = analyzer_pressures(measurements, {**thresholds, "warn_complexity": 30,
                                                "max_complexity": 50})["declarations"]
    strict = analyzer_pressures(measurements, {**thresholds, "warn_complexity": 2,
                                               "max_complexity": 4})["declarations"]

    assert lenient == 0.0
    assert strict > lenient


def test_a_disagreeing_second_source_widens_the_interval() -> None:
    """ADR 006 §4: disagreement is uncertainty, not something to average away.

    The point estimate stays on the built-in path, which is what the
    scale is calibrated against; a second reading stretches the interval
    to contain what it would have scored.
    """
    import subprocess
    import tempfile

    from maintainability_audit._pressures import ExternalPressures
    from maintainability_audit.config import load_config
    from maintainability_audit.evidence import normalize_report_evidence
    from maintainability_audit.report import build_report
    from maintainability_audit.scoring import score_evidence

    root = Path(tempfile.mkdtemp()) / "r"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(40):
        (root / f"m{i}.py").write_text(
            "\n".join(f"def f{i}_{j}():\n    return {j}\n" for j in range(4)), encoding="utf-8")
    evidence = normalize_report_evidence(build_report(root, load_config(None)))

    agreed = score_evidence(evidence)
    disagreed = score_evidence(evidence, ExternalPressures(
        all_code={"declarations": 0.3}, production={"declarations": 0.3}))

    assert agreed["maintainability_range"][0] == agreed["maintainability_range"][1]
    assert disagreed["maintainability_range"][0] < agreed["maintainability_range"][0]
    assert disagreed["maintainability_estimate"] == agreed["maintainability_estimate"], (
        "a second source widens the interval; it does not move the estimate"
    )


def test_a_second_source_must_reach_the_pressure_the_score_reads() -> None:
    """The defect the first attempt at this had.

    `declaration_size` is the only route the declarations dimension takes
    into the score, and it reads the *production* pressure rather than
    the general one — so substituting into `dimension_pressures` alone
    changed nothing, and the interval stayed collapsed however far the
    two sources were pushed apart. This asserts the substitution lands
    where the score actually looks.
    """
    from maintainability_audit._aspects import aspect_scores
    from maintainability_audit._pressures import dimension_pressures, normalize
    from maintainability_audit.evidence import (
        HistoryEvidence,
        Measured,
        NormalizedEvidence,
        SummaryEvidence,
        Unknown,
    )

    fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "t"))
    fields.update(
        declarations_scanned=Measured(200, "t"),
        production_declarations_scanned=Measured(200, "t"),
        files_scanned=Measured(50, "t"),
        production_files_scanned=Measured(50, "t"),
    )
    history = HistoryEvidence(**dict.fromkeys(
        HistoryEvidence.__dataclass_fields__, Unknown("no history", "t")))
    evidence = NormalizedEvidence(
        schema_version=3, summary=SummaryEvidence(**fields), history=history)
    normalized = normalize(dimension_pressures(evidence.summary))

    baseline = aspect_scores(evidence, normalized)["declaration_size"]
    overridden = aspect_scores(evidence, normalized, {"declarations": 3.0})["declaration_size"]

    assert overridden != baseline, "a production override that changes nothing is not an override"


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
    from maintainability_audit.evidence import Measured, SummaryEvidence

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

        # The built-in path, told there is one failure among four.
        fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "t"))
        fields.update(declarations_scanned=Measured(4, "t"), function_failures=Measured(1, "t"))
        expected = dimension_pressures(SummaryEvidence(**fields))["declarations"]

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
    from maintainability_audit.evidence import Measured, SummaryEvidence

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

    fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "t"))
    fields.update(declarations_scanned=Measured(4, "t"), function_warnings=Measured(1, "t"))

    from_analyzers = analyzer_pressures(measurements, thresholds)["declarations"]
    from_builtin = dimension_pressures(SummaryEvidence(**fields))["declarations"]

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

    def breaching(path: str, name: str) -> Measurement:
        return Measurement(concept="cyclomatic_complexity", unit=f"{path}::{name}",
                           value=float(thresholds["max_complexity"] + 5),
                           tool="lizard", path=path)

    def clean(path: str, name: str) -> Measurement:
        return Measurement(concept="cyclomatic_complexity", unit=f"{path}::{name}",
                           value=1.0, tool="lizard", path=path)

    production = [breaching("src/a.py", "f"), clean("src/a.py", "g")]
    # Same two declarations again, in files the built-in path calls tests.
    tests = [clean("tests/test_a.py", "t1"), clean("src/a_test.py", "t2"),
             clean("spec/thing.js", "t3")]

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


def test_each_population_is_substituted_from_its_own_reading(tmp_path: Path) -> None:
    """The production slot must not be filled from the all-code number.

    It was, for as long as the bridge could not tell test code from
    production code — one dict went into both slots, so production
    aspects were charged for the state of the test suite. Pairing the two
    readings in `ExternalPressures` makes the mix-up unrepresentable; this
    checks the substitution honours the pairing rather than reading one
    field twice.
    """
    import subprocess

    from maintainability_audit._pressures import ExternalPressures
    from maintainability_audit.config import load_config
    from maintainability_audit.evidence import normalize_report_evidence
    from maintainability_audit.report import build_report
    from maintainability_audit.scoring import score_evidence

    root = tmp_path / "r"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(40):
        (root / f"m{i}.py").write_text(
            "\n".join(f"def f{i}_{j}():\n    return {j}\n" for j in range(4)), encoding="utf-8")
    evidence = normalize_report_evidence(build_report(root, load_config(None)))

    # Identical all-code readings; the production reading is the only
    # thing that differs. A clean production reading must not be
    # overridden by the pessimistic all-code one.
    clean = score_evidence(evidence, ExternalPressures(
        all_code={"declarations": 0.4}, production={"declarations": 0.0}))
    dire = score_evidence(evidence, ExternalPressures(
        all_code={"declarations": 0.4}, production={"declarations": 0.4}))

    assert clean["maintainability_range"][0] > dire["maintainability_range"][0], (
        "the production slot is being filled from the all-code reading"
    )

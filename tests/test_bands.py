"""Bands map measurements to pressure — ADR 008.

A threshold makes cyclomatic complexity 14 and 45 the same fact. The
difference between extracting a guard clause and redesigning a module is
exactly what the reader wanted, so measurements run through ordered ranges
instead of a single line.

Both directions are tested by name because the first implementation inverted
one of them: a maintainability index of 95 scored as severe and 5 as clean.
The field is called `higher_is_worse` and the code still got it backwards,
which is the argument for testing the property rather than trusting the name.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._bands import (
    BAND_NAMES,
    CONCEPTS,
    band_of,
    bands_for,
    population_pressure,
    pressure_of,
    thresholds_for,
)
from maintainability_audit.config import load_config


@pytest.fixture
def thresholds() -> dict:
    return load_config(None)["thresholds"]


@pytest.mark.parametrize("name", sorted(CONCEPTS))
def test_every_concept_has_resolvable_thresholds(name: str, thresholds: dict) -> None:
    """A concept whose bands cannot be built is a silent hole.

    Swept over the registry so a concept added without thresholds fails
    here rather than at the first repository that measures it.
    """
    warn, fail = thresholds_for(CONCEPTS[name], thresholds)

    assert warn != fail, f"{name} has coincident warn and fail points; its bands collapse"


@pytest.mark.parametrize("name", sorted(CONCEPTS))
def test_bands_are_ordered_and_complete(name: str, thresholds: dict) -> None:
    bands = bands_for(CONCEPTS[name], thresholds)

    assert [b.name for b in bands] == list(BAND_NAMES)
    assert [b.pressure for b in bands] == sorted(b.pressure for b in bands)
    assert bands[0].pressure == 0.0 and bands[-1].pressure == 1.0
    assert bands[-1].upper is None, "the worst band must be open-ended or values fall through"


@pytest.mark.parametrize("name", sorted(CONCEPTS))
def test_pressure_moves_the_right_way(name: str, thresholds: dict) -> None:
    """The property that was inverted, swept over every concept.

    For a higher-is-worse concept, a larger value can never be less
    pressure. For higher-is-better, the reverse. Named for the class so a
    concept added with the wrong flag fails immediately.
    """
    concept = CONCEPTS[name]
    warn, fail = thresholds_for(concept, thresholds)
    ladder = sorted({fail * 4, fail, warn, warn / 2, 0.0})
    pressures = [pressure_of(concept, value, thresholds) for value in ladder]

    if concept.higher_is_worse:
        assert pressures == sorted(pressures), f"{name}: bigger values must not score better"
    else:
        assert pressures == sorted(pressures, reverse=True), (
            f"{name}: bigger values must not score worse"
        )


def test_the_inverted_case_that_was_wrong(thresholds: dict) -> None:
    """Maintainability index, pinned with real values.

    95 is excellent and 5 is dire. The first implementation had these
    exactly backwards, so they are asserted with the actual numbers
    rather than only as a monotonicity property.
    """
    index = CONCEPTS["maintainability_index"]

    assert band_of(index, 95, thresholds).name == "clean"
    assert band_of(index, 5, thresholds).pressure > 0.5


def test_two_values_a_threshold_would_merge_land_in_different_bands(
    thresholds: dict,
) -> None:
    """The whole reason bands exist."""
    complexity = CONCEPTS["cyclomatic_complexity"]

    just_over = band_of(complexity, 14, thresholds)
    far_over = band_of(complexity, 45, thresholds)

    assert just_over.name != far_over.name
    assert far_over.pressure > just_over.pressure


def test_bands_follow_the_projects_thresholds(thresholds: dict) -> None:
    """A project that raises its limit moves its bands with it.

    Otherwise the tool holds two disagreeing notions of "too complex" —
    one in the gate and one in the score.
    """
    complexity = CONCEPTS["cyclomatic_complexity"]
    relaxed = {**thresholds, "warn_complexity": 30, "max_complexity": 50}
    strict = {**thresholds, "warn_complexity": 4, "max_complexity": 6}

    # The same measurement, three policies. Relaxing must lower pressure
    # and tightening must raise it -- not necessarily to the extremes,
    # since the outer bands sit relative to the two anchors.
    under_default = band_of(complexity, 20, thresholds).pressure
    assert band_of(complexity, 20, relaxed).pressure < under_default
    assert band_of(complexity, 20, strict).pressure > under_default


def test_an_empty_population_is_unmeasured_not_clean(thresholds: dict) -> None:
    """A rate over nothing is not zero.

    This is the defect the whole project exists to remove, and a
    population helper is precisely where it would reappear.
    """
    assert population_pressure(CONCEPTS["cyclomatic_complexity"], [], thresholds) is None


def test_population_pressure_is_a_mean_not_a_worst_case(thresholds: dict) -> None:
    """One bad function among a thousand is not a bad codebase.

    The outlier is reported as a finding regardless; the score should not
    also let it dominate.
    """
    complexity = CONCEPTS["cyclomatic_complexity"]
    mostly_fine = [1.0] * 99 + [80.0]

    pressure = population_pressure(complexity, mostly_fine, thresholds)

    assert pressure is not None
    assert pressure < 0.05, "a single outlier must not swamp the population"
    assert pressure > 0, "and must not vanish either"


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
    disagreed = score_evidence(evidence, {"declarations": 0.3})

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

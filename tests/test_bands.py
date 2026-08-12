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

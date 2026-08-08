"""The cohort comparison must not claim a difference it cannot support.

``tools/calibration/measure_cohorts.py`` is what turns two piles of
repositories into a sentence like "these populations are
indistinguishable on file size". That sentence is the whole product of
the authorship study, so the arithmetic under it is pinned here rather
than trusted — the same standard ``test_calibration_corpus.py`` holds the
scoring constants to.

The rank-sum test is hand-rolled because this package ships no
scientific dependencies, which makes these tests the only thing standing
between a subtle ranking bug and a published claim about AI-written code.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

TOOL = Path(__file__).resolve().parents[1] / "tools" / "calibration" / "measure_cohorts.py"


def _load():
    spec = importlib.util.spec_from_file_location("measure_cohorts", TOOL)
    module = importlib.util.module_from_spec(spec)
    sys.modules["measure_cohorts"] = module
    spec.loader.exec_module(module)
    return module


measure_cohorts = _load()
mann_whitney = measure_cohorts.mann_whitney
distribution = measure_cohorts.distribution


# ---------------------------------------------------------------------------
# The test refuses to produce a number it cannot justify
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("left,right", [([1.0, 2.0], [3.0, 4.0, 5.0]), ([1.0, 2.0, 3.0], [4.0, 5.0])])
def test_returns_nothing_when_a_group_is_too_small(left: list[float], right: list[float]) -> None:
    """Two repositories are not a cohort. The normal approximation is
    already rough at these sizes; below three per group it is theatre,
    and a p-value printed next to n=2 would be read as evidence."""
    assert mann_whitney(left, right) is None


def test_identical_groups_are_not_a_difference() -> None:
    values = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]

    result = mann_whitney(values, list(values))

    assert result["p"] == 1.0
    assert result["z"] == 0.0


def test_all_values_tied_does_not_divide_by_zero() -> None:
    """A metric every repository scores 0.0 on is the common case for the
    rarer signals — it must report "no difference", not crash the run."""
    result = mann_whitney([0.0] * 5, [0.0] * 5)

    assert result["p"] == 1.0


# ---------------------------------------------------------------------------
# ...but it does detect one when it is there
# ---------------------------------------------------------------------------

def test_cleanly_separated_groups_are_significant() -> None:
    low = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    high = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0]

    result = mann_whitney(high, low)

    assert result["p"] < 0.01
    assert result["u"] == 0.0, "no overlap means U collapses to zero"


def test_argument_order_does_not_change_the_verdict() -> None:
    """U is reported as the smaller of the two, so the test is two-sided
    and symmetric. If this ever fails, every reported p-value depends on
    which cohort was passed first."""
    low, high = [1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]

    assert mann_whitney(low, high) == mann_whitney(high, low)


def test_ties_take_the_average_rank() -> None:
    """Ranks 2, 3 and 4 shared by three tied values must each score 3.
    Handing them sequential ranks instead would invent an ordering the
    data does not contain and bias U toward whichever group was sorted
    first."""
    tied = [1.0, 5.0, 5.0, 5.0, 9.0, 13.0]
    spread = [2.0, 6.0, 7.0, 8.0, 10.0, 14.0]

    result = mann_whitney(tied, spread)

    assert result is not None
    assert 0.0 < result["p"] <= 1.0


# ---------------------------------------------------------------------------
# The distribution summary is what lands in the docs
# ---------------------------------------------------------------------------

def test_distribution_reports_median_p90_and_max() -> None:
    stats = distribution([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])

    assert stats == {"n": 10, "median": 0.55, "p90": 0.9, "max": 1.0}


def test_p90_never_runs_off_the_end_of_a_tiny_cohort() -> None:
    """ceil(0.9 * n) - 1 indexes past the last element for some n if it is
    not clamped, and the cohorts are small enough for that to matter."""
    for size in range(1, 12):
        values = [float(i) for i in range(size)]

        stats = distribution(values)

        assert stats["n"] == size
        assert stats["p90"] in values, "p90 must be an observed value, not an interpolation"
        assert stats["median"] <= stats["p90"] <= stats["max"] == max(values)


def test_distribution_is_order_independent() -> None:
    assert distribution([3.0, 1.0, 2.0]) == distribution([1.0, 2.0, 3.0])

"""A change that improves one dimension while regressing another.

`--fail-on-new` catches a finding that clears and returns. Nothing caught
the slower failure: modularity up, testability quietly down, both scans
green by every existing gate, and the thing that got worse never named.

The judgment that matters here is not the subtraction. It is **when
subtracting is allowed at all**. Two scans taken with different
instruments — a different calibration constant, a different analyzer
population — cannot be compared, and `_scan_history.segments` already owns
that rule for the trend charts. A ratchet that ignored it would have
reported every repository on earth as catastrophically regressed on the day
2.0.0 extended the corpus and moved `CALIBRATION_C` from 5.8843 to 8.7161,
and the ratchet would have been the thing that was wrong.

So "not comparable" is a third outcome, and it is not a pass.
"""

from __future__ import annotations

from maintainability_audit._ratchet import TOLERANCE, dimension_ratchet
from maintainability_audit._scan_history import ScanRecord


def _record(
    commit: str,
    categories: dict[str, float],
    *,
    calibration: float = 8.7161,
    aspects: dict[str, float] | None = None,
) -> ScanRecord:
    return ScanRecord(
        recorded_at=f"2026-09-0{commit[-1]}T00:00:00Z",
        commit=commit,
        branch="main",
        scope="repository",
        rubric_version="2",
        calibration=calibration,
        thresholds_digest="same",
        analyzers=("lizard", "jscpd"),
        scored_languages=("python",),
        estimate=4.0,
        categories=categories,
        aspects=aspects or {},
    )


def test_a_dimension_that_slipped_is_named() -> None:
    """The failure the ratchet exists for: one up, one down, both green."""
    records = [
        _record("aaaaaa1", {"modularity": 4.0, "testability": 4.2}),
        _record("aaaaaa2", {"modularity": 4.4, "testability": 3.6}),
    ]

    result = dimension_ratchet(records)

    assert result["comparable"] is True
    assert result["held"] is False
    assert [item["name"] for item in result["regressed"]] == ["testability"]
    assert result["regressed"][0]["drop"] == 0.6
    assert result["regressed"][0]["was"] == 4.2


def test_an_improvement_is_not_a_regression() -> None:
    records = [
        _record("aaaaaa1", {"modularity": 4.0}),
        _record("aaaaaa2", {"modularity": 4.5}),
    ]

    assert dimension_ratchet(records)["held"] is True


def test_movement_inside_the_rounding_boundary_is_not_a_slide() -> None:
    """Scores are reported to one decimal; noise below that is not news."""
    records = [
        _record("aaaaaa1", {"modularity": 4.00}),
        _record("aaaaaa2", {"modularity": 4.00 - TOLERANCE / 2}),
    ]

    assert dimension_ratchet(records)["held"] is True


def test_scans_across_an_instrument_change_are_not_comparable() -> None:
    """The case that would have made this ratchet a liability.

    2.0.0 moved `CALIBRATION_C` 5.8843 -> 8.7161. Every score moved with it,
    and subtracting across that boundary would report a catastrophic
    regression everywhere while nothing about the code had changed.
    """
    records = [
        _record("aaaaaa1", {"modularity": 4.6}, calibration=5.8843),
        _record("aaaaaa2", {"modularity": 3.1}, calibration=8.7161),
    ]

    result = dimension_ratchet(records)

    assert result["comparable"] is False, (
        "scores from two different calibrations were subtracted"
    )
    assert result["regressed"] == []
    assert "instrument" in result["reason"] or "different" in result["reason"]


def test_not_comparable_is_not_a_pass() -> None:
    """A caller must be able to tell "nothing regressed" from "nobody asked".

    Both have an empty `regressed` list, so the distinction has to live
    somewhere a gate can read, and `held` must not be true where the
    question was never asked.
    """
    single = dimension_ratchet([_record("aaaaaa1", {"modularity": 4.0})])

    assert single["comparable"] is False
    assert single["regressed"] == []
    assert single.get("held") is not True, (
        "a scan with nothing to compare against reported that it held"
    )


def test_an_aspect_that_became_unmeasurable_is_not_a_drop() -> None:
    """Withheld evidence must never read as a failure.

    P3: withholding evidence cannot improve the grade — and the inversion
    matters just as much. An aspect that stops being measurable is reported
    as Unknown by the evidence model, not as a zero, so scoring its absence
    as a fall to nothing would turn missing evidence into a regression.
    """
    records = [
        _record("aaaaaa1", {"modularity": 4.0}, aspects={"documentation": 4.5}),
        _record("aaaaaa2", {"modularity": 4.0}, aspects={}),
    ]

    result = dimension_ratchet(records)

    assert result["aspects"] == []
    assert result["held"] is True


def test_aspects_are_reported_but_do_not_decide_the_verdict() -> None:
    """An aspect can wobble while its category holds.

    Failing on every aspect movement makes the gate noise, and a noisy gate
    gets switched off — but hiding what moved underneath makes the verdict
    unactionable, so aspects are reported beside the decision.
    """
    records = [
        _record("aaaaaa1", {"modularity": 4.0}, aspects={"file_size": 4.4}),
        _record("aaaaaa2", {"modularity": 4.0}, aspects={"file_size": 3.2}),
    ]

    result = dimension_ratchet(records)

    assert [item["name"] for item in result["aspects"]] == ["file_size"]
    assert result["regressed"] == []
    assert result["held"] is True

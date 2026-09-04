"""Comparing run seven of a transformation with run six.

The last remediation-integrity item, and the only one that is a report
rather than a gate. What is worth testing is not that a join joins. It is
the four places where this could quietly overclaim:

- it compares **movement across an interval**, never the *effect* of the
  transformation, because the tool never saw the work and cannot attribute
  the interval to it;
- it **refuses across an instrument change** and says how many runs it
  refused, reusing the segment rule the ratchet already answers to;
- a **withheld estimate is not a zero**, so a run with no number produces
  no movement rather than a fabricated one;
- and it **never says "better"**, because two runs of one codemod land on
  different code.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._history_view import run_comparison_markdown
from maintainability_audit._run_comparison import compare_runs
from maintainability_audit._scan_history import ScanRecord


def _record(
    estimate: float | None,
    *,
    transformation: str = "",
    calibration: float = 5.88,
    analyzers: tuple[str, ...] = ("lizard",),
    at: str = "2026-09-01T00:00:00Z",
    commit: str = "a" * 40,
) -> ScanRecord:
    return ScanRecord(
        recorded_at=at,
        commit=commit,
        branch="main",
        scope="full",
        rubric_version="2.5.0",
        calibration=calibration,
        thresholds_digest="d" * 16,
        analyzers=analyzers,
        scored_languages=("python",),
        estimate=estimate,
        populations={"files_scanned": 100, "declarations_scanned": 900},
        transformation=transformation,
    )


def _series(*records: ScanRecord) -> list[ScanRecord]:
    return list(records)


def test_a_run_reports_the_movement_since_the_scan_before_it() -> None:
    history = _series(
        _record(3.8),
        _record(4.1, transformation="react-18"),
    )

    comparison = compare_runs(history, "react-18")

    assert len(comparison["runs"]) == 1
    assert comparison["runs"][0]["moved"] == 0.3


def test_the_newest_run_is_compared_with_the_previous_run_of_the_same_name() -> None:
    """Run seven against run six, which is the question the item names."""
    history = _series(
        _record(3.5),
        _record(3.6, transformation="codemod"),   # moved +0.1
        _record(3.6),
        _record(4.0, transformation="codemod"),   # moved +0.4
    )

    trend = compare_runs(history, "codemod")["trend"]

    assert trend["comparable"] is True
    assert trend["latest_moved"] == 0.4
    assert trend["previous_moved"] == 0.1
    assert "further than" in trend["summary"]


def test_a_smaller_movement_says_less_rather_than_worse() -> None:
    history = _series(
        _record(3.0),
        _record(3.9, transformation="codemod"),
        _record(3.9),
        _record(4.0, transformation="codemod"),
    )

    summary = compare_runs(history, "codemod")["trend"]["summary"]

    assert "less than" in summary
    for forbidden in ("better", "worse", "improved", "degraded"):
        assert forbidden not in summary, (
            f"the trend said {forbidden!r}; two runs of one transformation "
            "land on different code, so the movement is what was measured "
            "and a judgment about the work is not"
        )


def test_a_movement_inside_the_tolerance_is_neither_further_nor_less() -> None:
    history = _series(
        _record(3.0),
        _record(3.30, transformation="codemod"),
        _record(3.30),
        _record(3.62, transformation="codemod"),
    )

    trend = compare_runs(history, "codemod")["trend"]

    assert "within tolerance of" in trend["summary"], trend["summary"]


def test_runs_before_an_instrument_change_are_refused_and_counted() -> None:
    """The ratchet's rule, and the reason it exists.

    A series that quietly spanned the 2.0 corpus extension would have
    reported every transformation on earth as catastrophic, and it would
    have been the comparison that was wrong. Refusing silently is the other
    failure: a reader who cannot see the refusal concludes there was no
    history.
    """
    history = _series(
        _record(3.0, calibration=2.26),
        _record(4.4, transformation="codemod", calibration=2.26),
        _record(3.0, calibration=5.88),
        _record(3.1, transformation="codemod", calibration=5.88),
    )

    comparison = compare_runs(history, "codemod")

    assert len(comparison["runs"]) == 1, "a run from the old instrument was joined"
    assert comparison["excluded_earlier_runs"] == 1
    assert "calibration" in comparison["exclusion_reason"]
    assert comparison["trend"]["comparable"] is False


def test_an_analyzer_change_breaks_the_series_too() -> None:
    """Coverage is an instrument, exactly as calibration is."""
    history = _series(
        _record(3.0, analyzers=("lizard",)),
        _record(4.0, transformation="codemod", analyzers=("lizard",)),
        _record(3.0, analyzers=("lizard", "jscpd")),
        _record(4.0, transformation="codemod", analyzers=("lizard", "jscpd")),
    )

    comparison = compare_runs(history, "codemod")

    assert comparison["excluded_earlier_runs"] == 1


def test_a_withheld_estimate_produces_no_movement_rather_than_a_zero() -> None:
    """P7 withholds a number because the evidence did not support one.

    Subtracting from a withheld estimate would manufacture the number the
    scoring model deliberately refused to publish.
    """
    history = _series(
        _record(None),
        _record(4.0, transformation="codemod"),
        _record(4.0),
        _record(None, transformation="codemod"),
    )

    runs = compare_runs(history, "codemod")["runs"]

    assert [run["moved"] for run in runs] == [None, None]
    assert compare_runs(history, "codemod")["trend"]["comparable"] is False


def test_an_unnamed_series_reports_nothing_rather_than_inventing_one() -> None:
    history = _series(_record(3.0), _record(4.0))

    comparison = compare_runs(history, "never-ran")

    assert comparison["runs"] == []
    assert comparison["trend"]["comparable"] is False
    assert "never-ran" in comparison["trend"]["reason"]


def test_one_run_is_not_a_comparison() -> None:
    history = _series(_record(3.0), _record(4.0, transformation="first-time"))

    trend = compare_runs(history, "first-time")["trend"]

    assert trend["comparable"] is False
    assert "fewer than two" in trend["reason"]


def test_two_scans_of_one_commit_are_two_runs(tmp_path: Any) -> None:
    """Records are compared by identity, not equality.

    Two scans of an unchanged tree produce records that differ only in
    their timestamp, and an equality-based join would have collapsed them
    into one run — silently losing exactly the repeat this feature exists
    to count.
    """
    history = _series(
        _record(3.0, at="2026-09-01T00:00:00Z"),
        _record(4.0, transformation="codemod", at="2026-09-01T01:00:00Z"),
        _record(3.0, at="2026-09-02T00:00:00Z"),
        _record(4.0, transformation="codemod", at="2026-09-02T01:00:00Z"),
    )

    assert len(compare_runs(history, "codemod")["runs"]) == 2


# ---------------------------------------------------------------------------
# What the reader is told
# ---------------------------------------------------------------------------

def test_the_section_states_that_it_measured_an_interval_not_an_effect() -> None:
    """The disclaimer is the feature.

    Without it the table reads as "the transformation did this", which is a
    claim about work the tool never saw. Anything else that happened in the
    same interval is inside the number.
    """
    history = _series(
        _record(3.5),
        _record(3.6, transformation="codemod"),
        _record(3.6),
        _record(4.0, transformation="codemod"),
    )

    text = "\n".join(run_comparison_markdown(compare_runs(history, "codemod")))

    assert "not the effect of the transformation" in text.replace("\n", " ")
    assert "codemod" in text


def test_an_unnamed_run_renders_no_section_at_all() -> None:
    assert run_comparison_markdown(None) == []
    assert run_comparison_markdown({}) == []


def test_the_section_names_the_runs_it_refused_to_join() -> None:
    history = _series(
        _record(3.0, calibration=2.26),
        _record(4.4, transformation="codemod", calibration=2.26),
        _record(3.0, calibration=5.88),
        _record(3.1, transformation="codemod", calibration=5.88),
    )

    text = "\n".join(run_comparison_markdown(compare_runs(history, "codemod")))

    assert "1 earlier run(s) under this name are excluded" in text


# ---------------------------------------------------------------------------
# The record itself
# ---------------------------------------------------------------------------

def test_the_label_does_not_split_the_history_into_segments() -> None:
    """Two transformations on one instrument are still one series.

    Segmenting on the label would break a comparison for the sole reason
    that a run said its own name, and would make the ratchet refuse the
    moment anybody used this flag.
    """
    from maintainability_audit._scan_history import comparability_key

    plain = _record(3.0)
    named = _record(3.0, transformation="react-18")

    assert comparability_key(plain) == comparability_key(named)


def test_an_older_line_loads_with_no_transformation(tmp_path: Any) -> None:
    """Schema 3 lines predate the field and belong to no series.

    That is the truth about them rather than a gap: nothing recorded what
    they followed.
    """
    import json

    from maintainability_audit._scan_history import read_history

    payload = json.loads(_record(3.0).as_line())
    payload.pop("transformation")
    payload["history_schema_version"] = 3
    path = tmp_path / "history.jsonl"
    path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    loaded = read_history(path)

    assert len(loaded) == 1
    assert loaded[0].transformation == ""


def test_the_label_round_trips_through_the_written_line(tmp_path: Any) -> None:
    import json

    from maintainability_audit._scan_history import read_history

    path = tmp_path / "history.jsonl"
    path.write_text(_record(3.0, transformation="react-18").as_line() + "\n",
                    encoding="utf-8")

    assert read_history(path)[0].transformation == "react-18"
    assert json.loads(path.read_text())["history_schema_version"] == 4


def test_the_label_is_read_off_the_report_like_every_other_run_fact() -> None:
    """A surface opts in by setting one field, not by a new argument.

    `record_of` already takes `mode` and `git_commit` this way, so the CLI
    and the MCP door cannot drift into recording different things.
    """
    from maintainability_audit._scan_history import record_of

    record = record_of(
        {"transformation": "react-18", "summary": {}, "score": {}},
        version="2.5.0", calibration=5.88, config={"thresholds": {}},
        fingerprints=(),
    )

    assert record.transformation == "react-18"

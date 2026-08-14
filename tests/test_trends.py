"""Trends are measurements of the past — ADR 009 §3, task 5.3.

Four arithmetic statements over a **checked** segment:

- **debt velocity** — findings introduced against findings cleared. A
  repository clearing more than it adds is improving regardless of its
  absolute score, which a snapshot cannot say.
- **trajectory** — direction and rate, withheld when the intervals
  overlap, because a move inside the uncertainty is not a move.
- **growth versus quality** — is the finding *rate* rising, or just the
  codebase? This is the distinction a snapshot structurally cannot make
  and the one people most often get wrong about their own code.
- **stability** — findings that never clear across the whole segment.

Two rules constrain every one of them.

**Nothing is computed across a segment boundary.** The comparability
gate exists because this repository's own tooling changed several times
in one day and the same repositories scored differently at 09:00 and
17:00. A velocity spanning that would count my bug fixes as someone's
debt. The gate is upstream, and these functions take a `Segment` rather
than a list of records so there is no signature that *can* be handed an
unchecked series.

**Extrapolation is forbidden.** "Complexity rose 18% over six months" is
a fact. "Will keep rising" is a prediction, and remains forbidden under
the product's own claim rules until an outcome study earns it. There is
deliberately no function here that takes a horizon, and a test asserts
the vocabulary stays in the past tense.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._scan_history import ScanRecord, Segment, segments
from maintainability_audit._trends import (
    Direction,
    debt_velocity,
    growth_versus_quality,
    stability,
    trajectory,
    trend_report,
)


def _scan(n: int, *, estimate: float | None = 4.0, low: float | None = None,
          high: float | None = None, findings: tuple[str, ...] = (),
          declarations: int = 400, **overrides: object) -> ScanRecord:
    base: dict[str, object] = {
        "recorded_at": f"2026-0{n + 1}-01T00:00:00Z",
        "commit": str(n) * 40,
        "branch": "main",
        "scope": "full",
        "rubric_version": "0.7.0",
        "calibration": 2.6279,
        "thresholds_digest": "t-abc",
        "analyzers": ("lizard", "ruff"),
        "scored_languages": ("Python",),
        "estimate": estimate,
        "range_low": estimate if low is None else low,
        "range_high": estimate if high is None else high,
        "populations": {"files_scanned": 100, "declarations_scanned": declarations},
        "fingerprints": findings,
    }
    base.update(overrides)
    return ScanRecord(**base)  # type: ignore[arg-type]


def _segment(*records: ScanRecord) -> Segment:
    return Segment(records=list(records))


# --------------------------------------------------------------------
# Debt velocity
# --------------------------------------------------------------------


def test_velocity_counts_findings_introduced_against_findings_cleared() -> None:
    """The statement a snapshot cannot make.

    A repository at 3.8 clearing more than it adds is in a different
    position from one at 3.8 adding more than it clears, and the score
    is identical for both.
    """
    result = debt_velocity(_segment(
        _scan(0, findings=("a", "b", "c")),
        _scan(1, findings=("b", "c", "d", "e")),
    ))

    assert result.introduced == 2, "d and e are new"
    assert result.cleared == 1, "a is gone"
    assert result.net == 1
    assert result.improving is False


def test_a_repository_clearing_more_than_it_adds_is_improving() -> None:
    result = debt_velocity(_segment(
        _scan(0, findings=("a", "b", "c", "d")),
        _scan(1, findings=("d", "e")),
    ))

    assert (result.introduced, result.cleared, result.net) == (1, 3, -2)
    assert result.improving is True


def test_velocity_sums_across_every_step_not_just_the_endpoints() -> None:
    """A finding added and cleared between scans is real work.

    Comparing only first to last would report zero for a segment where
    somebody added forty findings and cleared forty others — which is
    not a quiet period and should not read as one.
    """
    result = debt_velocity(_segment(
        _scan(0, findings=("a",)),
        _scan(1, findings=("a", "b", "c")),
        _scan(2, findings=("a",)),
    ))

    assert (result.introduced, result.cleared) == (2, 2)
    assert result.net == 0


# --------------------------------------------------------------------
# Trajectory, and the refusal to read noise as movement
# --------------------------------------------------------------------


def test_a_move_inside_the_interval_is_not_a_direction() -> None:
    """The honesty check, using evidence the report already carries.

    `maintainability_range` states how far the estimate could move on
    evidence that was not gathered. Two scans whose ranges overlap have
    not been shown to differ, and calling that a decline would be
    reporting the tool's own uncertainty as the code's decay.

    No new threshold: the interval is already computed and already
    published beside every score.
    """
    result = trajectory(_segment(
        _scan(0, estimate=4.2, low=3.9, high=4.4),
        _scan(1, estimate=4.0, low=3.8, high=4.3),
    ))

    assert result.direction is Direction.INDISTINGUISHABLE
    assert "overlap" in result.reason.lower()


def test_a_move_beyond_the_interval_is_a_direction() -> None:
    result = trajectory(_segment(
        _scan(0, estimate=4.4, low=4.3, high=4.5),
        _scan(1, estimate=3.6, low=3.5, high=3.7),
    ))

    assert result.direction is Direction.DECLINING
    assert result.change == pytest.approx(-0.8)


def test_a_withheld_score_does_not_become_a_trend_of_zero() -> None:
    """The founding defect, in the time dimension.

    A scan below the population floor has no estimate. Treating that as
    0.0 would manufacture a catastrophic decline out of an absence, and
    treating it as unchanged would manufacture stability.
    """
    result = trajectory(_segment(
        _scan(0, estimate=4.2, low=4.1, high=4.3),
        _scan(1, estimate=None, low=None, high=None),
    ))

    assert result.direction is Direction.UNKNOWN
    assert result.change is None
    assert "no estimate" in result.reason.lower()


def test_one_scan_carries_no_trajectory() -> None:
    """One point is not a direction."""
    result = trajectory(_segment(_scan(0)))

    assert result.direction is Direction.UNKNOWN
    assert "at least two" in result.reason.lower()


# --------------------------------------------------------------------
# Growth versus quality
# --------------------------------------------------------------------


def test_a_codebase_that_only_got_bigger_is_not_getting_worse() -> None:
    """The distinction people get wrong about their own code.

    Findings doubled and so did the code. The rate is flat, and a report
    that led with "findings doubled" would be technically true and
    actively misleading.
    """
    result = growth_versus_quality(_segment(
        _scan(0, findings=tuple(f"f{n}" for n in range(10)), declarations=200),
        _scan(1, findings=tuple(f"f{n}" for n in range(20)), declarations=400),
    ))

    assert result.population_change == pytest.approx(1.0), "the code doubled"
    assert result.rate_change == pytest.approx(0.0, abs=1e-9), "the rate did not move"
    assert result.verdict == "grew without getting worse"


def test_a_codebase_getting_worse_without_growing_is_named_as_such() -> None:
    result = growth_versus_quality(_segment(
        _scan(0, findings=("a", "b"), declarations=400),
        _scan(1, findings=tuple(f"f{n}" for n in range(8)), declarations=400),
    ))

    assert result.population_change == pytest.approx(0.0)
    assert result.rate_change > 0
    assert result.verdict == "got worse without growing"


def test_growth_is_unknown_when_the_population_was_not_recorded() -> None:
    """No denominator, no rate. Never a zero."""
    result = growth_versus_quality(_segment(
        _scan(0, findings=("a",), populations={}),
        _scan(1, findings=("a", "b"), populations={}),
    ))

    assert result.rate_change is None
    assert result.verdict == "unknown"


# --------------------------------------------------------------------
# Stability, and the ban on forecasting
# --------------------------------------------------------------------


def test_stability_names_what_never_cleared() -> None:
    """Present in every scan of the segment: nobody has touched it.

    A finding surviving the whole window is a different problem from one
    that appeared yesterday, and the work order should treat them
    differently.
    """
    result = stability(_segment(
        _scan(0, findings=("old", "a")),
        _scan(1, findings=("old", "b")),
        _scan(2, findings=("old", "c")),
    ))

    assert result.persistent == ("old",)
    assert result.scans == 3


def test_no_function_here_accepts_a_horizon() -> None:
    """Extrapolation is forbidden, and the API cannot express it.

    "Complexity rose 18% over six months" is a fact; "will keep rising"
    is a prediction the product may not make until an outcome study
    earns it. A parameter naming a future period is how that line gets
    crossed by accident, so no signature has one.
    """
    import inspect

    from maintainability_audit import _trends

    banned = {"horizon", "forecast", "predict", "project", "extrapolate", "eta", "until"}
    for name, function in inspect.getmembers(_trends, inspect.isfunction):
        parameters = set(inspect.signature(function).parameters)
        assert not parameters & banned, f"{name} accepts a forecasting parameter"


def test_the_report_states_the_window_it_measured() -> None:
    """A trend without its window is not checkable.

    "Declining" over two scans an hour apart and over two scans a year
    apart are different claims, and a reader cannot tell which they are
    reading without the dates.
    """
    report = trend_report(_segment(
        _scan(0, estimate=4.4, low=4.3, high=4.5, findings=("a",)),
        _scan(1, estimate=3.6, low=3.5, high=3.7, findings=("a", "b")),
    ))

    assert report["scans"] == 2
    assert report["from"] == "2026-01-01T00:00:00Z"
    assert report["to"] == "2026-02-01T00:00:00Z"
    assert report["trajectory"]["direction"] == Direction.DECLINING.value


def test_a_segmented_history_reports_per_segment_and_never_across() -> None:
    """The gate and the arithmetic, working together.

    Three scans, an analyzer change, two more. Each side gets its own
    trend and the break is named. A single trend across all five would
    measure the tooling change.
    """
    history = [
        _scan(0, estimate=4.4, low=4.3, high=4.5),
        _scan(1, estimate=4.3, low=4.2, high=4.4),
        _scan(2, estimate=4.2, low=4.1, high=4.3),
        _scan(3, estimate=3.2, low=3.1, high=3.3, analyzers=("lizard",)),
        _scan(4, estimate=3.1, low=3.0, high=3.2, analyzers=("lizard",)),
    ]

    reports = [trend_report(s) for s in segments(history)]

    assert len(reports) == 2
    assert [r["scans"] for r in reports] == [3, 2]
    assert reports[1]["break_reason"], "the second segment names what changed"
    assert all(r["trajectory"]["change"] is None or abs(r["trajectory"]["change"]) < 0.5
               for r in reports), "no report spans the 1.0 drop at the boundary"


def test_the_trend_reaches_the_rendered_report(tmp_path: Path) -> None:
    """A trend nobody sees is a data structure.

    The first wiring of this silently did nothing: two string
    replacements found no match, wrote the file unchanged, and every
    test still passed — because they all asserted the *arithmetic* and
    none asserted the output. The computation was correct and invisible,
    which is the same shape as a green test over a broken pipeline.
    """
    from maintainability_audit.renderers import render_markdown

    rendered = render_markdown({
        "root": ".", "summary": {"files_scanned": 1, "file_warnings": 0,
                                 "file_failures": 0, "function_warnings": 0,
                                 "function_failures": 0, "duplicate_blocks": 0,
                                 "risk_findings": 0, "hard_gate_failures": 0},
        "score": {"standard": "s", "aspects": {}, "categories": {},
                  "maintainability_estimate": 4.0, "maintainability_range": [4.0, 4.0],
                  "evidence_status": {"status": "complete", "profile": "default-v1",
                                      "reasons": []},
                  "verified_grade": "B", "verified_grade_blockers": [],
                  "dimensions": {}, "worst_dimension": None, "rubric": {},
                  "reference": {}},
        "hard_gate_failures": [], "largest_files": [], "function_hotspots": [],
        "missing_files": [], "risk_findings": [], "duplicate_blocks": [],
        "near_duplicates": [], "dead_code": [], "idiom_concerns": [],
        "external_findings": [], "history": None, "git_branch": "main",
        "scan_history": [{
            "scans": 3, "from": "2026-01-01T00:00:00Z", "to": "2026-03-01T00:00:00Z",
            "break_reason": "", "trajectory": {"direction": "declining", "change": -0.4,
                                               "reason": "moved"},
            "velocity": {"introduced": 9, "cleared": 2, "net": 7, "improving": False},
            "growth": {"population_change": 0.0, "rate_change": 0.1,
                       "verdict": "got worse without growing"},
            "persistent_findings": 4,
        }],
    })

    assert "## Trend" in rendered
    assert "declining" in rendered
    assert "9 introduced, 2 cleared" in rendered
    assert "got worse without growing" in rendered
    assert "does not forecast" in rendered, "the ban on prediction is stated to the reader"


def test_a_break_is_named_in_the_rendered_report() -> None:
    """Two series with the reason, never one line through both."""
    from maintainability_audit._history_view import scan_history_markdown

    rendered = "\n".join(scan_history_markdown([
        {"scans": 3, "from": "a", "to": "b", "break_reason": "",
         "trajectory": {"direction": "flat", "change": 0.0, "reason": "r"},
         "velocity": {"introduced": 0, "cleared": 0, "net": 0, "improving": False},
         "growth": {"population_change": 0.0, "rate_change": 0.0, "verdict": "v"},
         "persistent_findings": 0},
        {"scans": 2, "from": "c", "to": "d",
         "break_reason": "analyzers changed, so scans before this point were "
                         "produced by a different instrument",
         "trajectory": {"direction": "flat", "change": 0.0, "reason": "r"},
         "velocity": {"introduced": 0, "cleared": 0, "net": 0, "improving": False},
         "growth": {"population_change": 0.0, "rate_change": 0.0, "verdict": "v"},
         "persistent_findings": 0},
    ]))

    assert "2 separate series" in rendered
    assert "different instrument" in rendered
    assert "Series 1" in rendered and "Series 2" in rendered


def test_a_quiet_period_is_not_described_as_getting_worse() -> None:
    """Nothing introduced and nothing cleared is neither direction.

    The rendered line read "0 introduced, 0 cleared (adding faster than
    clearing)" — a claim the two numbers printed beside it contradict.
    `improving` was `net < 0`, so a net of zero fell through to the
    pessimistic branch. Found by reading the real output of a backfill,
    not by a unit test.
    """
    from maintainability_audit._history_view import scan_history_markdown

    quiet = debt_velocity(_segment(_scan(0, findings=("a",)), _scan(1, findings=("a",))))

    assert quiet.net == 0
    assert quiet.improving is False
    assert quiet.worsening is False, "a net of zero is not a decline"

    rendered = "\n".join(scan_history_markdown([trend_report(_segment(
        _scan(0, findings=("a",)), _scan(1, findings=("a",))))]))

    assert "adding faster than clearing" not in rendered
    assert "unchanged" in rendered.lower()

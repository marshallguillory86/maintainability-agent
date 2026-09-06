"""Did run seven of this transformation land better than run six?

The last of the remediation-integrity items, and the only one that is a
**report rather than a gate**. Where an agent performs one class of work
repeatedly in one repository — a framework upgrade, a migration, a codemod
run again and again as it is refined — nobody measures whether the seventh
run produced better code than the sixth. The generator cannot answer it: its output is not
reproducible and it keeps no memory across runs. This tool has pinned
references, structured finding identity and scan history, so the
comparison is a join, not new machinery.

One repository, deliberately. Joining several repositories' histories on a
shared label — how one codemod fared across a fleet — is a roadmap item and
is **not built**; what it needs is in `docs/roadmap.md`, and it is not this
join. This docstring is where the opposite reading came from twice: it used
to say "a codemod applied across services", which reads as a fleet.

**What names a run.** Nothing in a tree says "this scan followed the React
18 upgrade", so the operator says it: `--transformation react-18`. The
label rides on the scan record and groups runs into a series.

**What it measures, stated precisely because the temptation is to
overstate it.** For each labeled run, the movement between the *previous
scan in history* and that run. That is the movement across an interval,
and the transformation is what the operator says happened during that
interval. This module does not and cannot verify that claim: anything else
that happened in the same interval is inside the number. So the report
speaks of a run's *movement*, never of its *effect*, and never says one
run was "better" — it says one moved further than another, which is what
was actually measured.

**It refuses across an instrument change**, reusing `segments` exactly as
`_ratchet` does. Two scans taken under different calibration cannot be
subtracted, and a series that quietly spanned the 2.0 corpus extension
would have reported every transformation on earth as catastrophic. When
the newest labeled run sits in a different segment from its predecessors,
the earlier runs are named as excluded rather than dropped in silence:
a reader who cannot see the refusal will assume there was no history.

Nothing here reaches scoring, and nothing here fails a build.
"""
from __future__ import annotations

from typing import Any

from ._scan_history import ScanRecord, segments

#: The same rounding boundary `_ratchet` uses, and for the same reason:
#: estimates are published to one decimal, so a smaller difference is the
#: rounding and not a movement.
TOLERANCE = 0.05


def _movement(previous: ScanRecord | None, current: ScanRecord) -> float | None:
    """How far the estimate moved across the interval ending at `current`.

    `None` where either end is missing an estimate. A withheld estimate is
    not a zero — P7 withholds it precisely because the evidence did not
    support a number, and subtracting from it would manufacture one.
    """
    if previous is None or previous.estimate is None or current.estimate is None:
        return None
    return round(current.estimate - previous.estimate, 3)


def _run_entry(
    record: ScanRecord, previous: ScanRecord | None
) -> dict[str, Any]:
    return {
        "recorded_at": record.recorded_at,
        "commit": record.commit,
        "scope": record.scope,
        "estimate": record.estimate,
        "evidence_status": record.evidence_status,
        # Named so a reader can tell a movement in the code from a movement
        # in what was measured: a run that doubled the tree is a different
        # event from one that changed the same tree's condition.
        "populations": dict(record.populations),
        "moved": _movement(previous, record),
        # A reconstructed scan carries today's tooling against an old
        # commit, which is not the scan that would have happened then.
        "backfilled": record.backfilled,
    }


def _direction(difference: float) -> str:
    """How to say it. Never "better" — see `_trend`."""
    if abs(difference) < TOLERANCE:
        return "within tolerance of"
    return "further than" if difference > 0 else "less than"


def _trend(runs: list[dict[str, Any]]) -> dict[str, Any]:
    """How the newest run's movement compares with the one before it.

    Deliberately not called "better". Two runs of one codemod land on
    different code, so a larger movement can come from the tree it was
    applied to as easily as from the run. "Moved further" is what the
    numbers support; "better" is a judgment about work this tool never saw.
    """
    movements = [run for run in runs if run["moved"] is not None]
    if len(movements) < 2:
        return {
            "comparable": False,
            "reason": (
                "fewer than two runs in this series carry a movement, so "
                "there is nothing to compare them on"
            ),
        }
    latest, prior = movements[-1]["moved"], movements[-2]["moved"]
    difference = round(latest - prior, 3)
    direction = _direction(difference)
    return {
        "comparable": True,
        "latest_moved": latest,
        "previous_moved": prior,
        "difference": difference,
        "summary": (
            f"the newest run moved {latest:+.2f}, {direction} the "
            f"{prior:+.2f} of the run before it"
        ),
    }


def _segment_holding(records: list[ScanRecord], wanted: ScanRecord) -> Any:
    """The instrument-segment containing one record.

    Membership is by **identity**, not equality: two scans of an unchanged
    tree differ only in their timestamp, and an equality test would find
    the wrong one — silently attributing a run to the wrong instrument.
    """
    return next(
        segment for segment in segments(records)
        if any(item is wanted for item in segment.records)
    )


def _entries_within(segment: Any, labelled: list[ScanRecord]) -> list[dict[str, Any]]:
    """The labelled runs inside this segment, each with its predecessor.

    A run's predecessor is the scan immediately before it *in the
    segment*, whatever that scan was labelled — the movement being
    measured is across the interval, not between two runs of the same
    name.
    """
    order = {id(record): index for index, record in enumerate(segment.records)}
    return [
        _run_entry(
            record,
            segment.records[order[id(record)] - 1] if order[id(record)] else None,
        )
        for record in labelled if id(record) in order
    ]


def compare_runs(records: list[ScanRecord], label: str) -> dict[str, Any]:
    """Every recorded run of one transformation, and how the last two differ.

    The current scan is already in `records` when this is called — history
    is appended before the post-audit records are attached — so the newest
    labeled run is this one.
    """
    labelled = [record for record in records if record.transformation == label]
    if not labelled:
        return {
            "label": label,
            "runs": [],
            "excluded_earlier_runs": 0,
            "trend": {
                "comparable": False,
                "reason": f"no scan has been recorded under the name {label!r}",
            },
        }

    current = _segment_holding(records, labelled[-1])
    runs = _entries_within(current, labelled)
    excluded = len(labelled) - len(runs)

    comparison = {
        "label": label,
        "runs": runs,
        "excluded_earlier_runs": excluded,
        "trend": _trend(runs),
    }
    if excluded:
        comparison["exclusion_reason"] = (
            current.break_reason
            or "those runs were produced by a different instrument"
        )
    return comparison

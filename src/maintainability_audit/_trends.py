"""Trends are measurements of the past — ADR 009 §3.

Arithmetic over a **checked** segment. Every function here takes a
`Segment` rather than a list of records, so there is no signature that
can be handed an unchecked series: the comparability gate is upstream
and cannot be skipped by a caller who forgot it exists.

That matters because this repository's own tooling changed several times
in one day, and the same repositories scored differently at 09:00 and
17:00. A velocity spanning that boundary would count bug fixes in the
instrument as debt in someone's code.

**Extrapolation is forbidden and the API cannot express it.**
"Complexity rose 18% over six months" is a fact. "Will keep rising" is a
prediction the product may not make until an outcome study earns it, and
a parameter naming a future period is how that line gets crossed by
accident. No function here takes a horizon, and a test enforces it.

The other constraint is subtler: **a move inside the interval is not a
move.** Every score ships with `maintainability_range`, the span the
estimate could occupy on evidence that was not gathered. Two scans whose
ranges overlap have not been shown to differ, and reporting that as a
decline would present the tool's own uncertainty as the code's decay.
No new threshold is introduced for this — the interval is already
computed and already published beside every score.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from ._scan_history import ScanRecord, Segment


class Direction(StrEnum):
    """What a segment shows about the score, including "cannot say"."""

    IMPROVING = "improving"
    DECLINING = "declining"
    FLAT = "flat"
    # Moved, but by less than the evidence can resolve.
    INDISTINGUISHABLE = "indistinguishable"
    # Cannot be computed at all: too few scans, or a withheld estimate.
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Velocity:
    """Findings introduced against findings cleared, over a segment."""

    introduced: int
    cleared: int

    @property
    def net(self) -> int:
        return self.introduced - self.cleared

    @property
    def improving(self) -> bool:
        """Clearing more than adding, whatever the absolute score.

        A repository at 3.8 clearing more than it adds is in a different
        position from one at 3.8 adding more than it clears, and the
        snapshot is identical for both.
        """
        return self.net < 0

    @property
    def worsening(self) -> bool:
        """Adding more than clearing.

        Deliberately not `not improving`. A net of zero is neither, and
        collapsing the three states into two produced a rendered line
        reading "0 introduced, 0 cleared (adding faster than clearing)"
        — a claim contradicted by the two numbers printed beside it.
        """
        return self.net > 0


@dataclass(frozen=True)
class Trajectory:
    """Direction of the score, and why it is what it is."""

    direction: Direction
    change: float | None
    reason: str


@dataclass(frozen=True)
class Growth:
    """Whether the codebase got bigger, got worse, or both."""

    population_change: float | None
    rate_change: float | None
    verdict: str


@dataclass(frozen=True)
class Stability:
    """Findings present in every scan of the segment."""

    persistent: tuple[str, ...]
    scans: int


def debt_velocity(segment: Segment) -> Velocity:
    """Findings introduced and cleared, summed across every step.

    Every step, not first against last: a segment where somebody added
    forty findings and cleared forty others is not a quiet period, and
    comparing only the endpoints would report it as one.
    """
    introduced = cleared = 0
    for earlier, later in zip(segment.records, segment.records[1:], strict=False):
        before, after = set(earlier.fingerprints), set(later.fingerprints)
        introduced += len(after - before)
        cleared += len(before - after)
    return Velocity(introduced=introduced, cleared=cleared)


def trajectory(segment: Segment) -> Trajectory:
    """Direction of the estimate across the segment, or why there is none.

    Withheld in three cases, each meaning something different: fewer
    than two scans, an absent estimate, and a move the intervals cannot
    resolve. Collapsing any of them into "flat" would report an absence
    as a finding, which is the defect this project exists to remove.
    """
    if len(segment.records) < 2:
        return Trajectory(Direction.UNKNOWN, None,
                          "a direction needs at least two comparable scans")
    first, last = segment.records[0], segment.records[-1]
    if first.estimate is None or last.estimate is None:
        return Trajectory(
            Direction.UNKNOWN, None,
            "a scan in this segment carries no estimate, and an absent score "
            "is not a score of zero")

    change = round(last.estimate - first.estimate, 3)
    if _intervals_overlap(first, last):
        return Trajectory(
            Direction.INDISTINGUISHABLE, change,
            "the intervals of the first and last scans overlap, so the move is "
            "smaller than the evidence can resolve")
    if change == 0:
        return Trajectory(Direction.FLAT, 0.0, "the estimate did not move")
    direction = Direction.IMPROVING if change > 0 else Direction.DECLINING
    return Trajectory(direction, change,
                      f"the estimate moved {change:+.2f} beyond either interval")


def _intervals_overlap(first: ScanRecord, last: ScanRecord) -> bool:
    """Whether two scans have been shown to differ at all.

    Falls back to the point estimates when a record predates the stored
    interval, in which case any change is a change — the honest
    behaviour for a record that cannot express uncertainty.
    """
    low_a = first.range_low if first.range_low is not None else first.estimate
    high_a = first.range_high if first.range_high is not None else first.estimate
    low_b = last.range_low if last.range_low is not None else last.estimate
    high_b = last.range_high if last.range_high is not None else last.estimate
    if None in (low_a, high_a, low_b, high_b):
        return False
    return low_a <= high_b and low_b <= high_a  # type: ignore[operator]


def _rate(record: ScanRecord) -> float | None:
    """Findings per declaration, or None when the population is unrecorded."""
    population = record.populations.get("declarations_scanned")
    if not population:
        return None
    return len(record.fingerprints) / population


def growth_versus_quality(segment: Segment) -> Growth:
    """Did the codebase get bigger, get worse, or both.

    The distinction a snapshot structurally cannot make, and the one
    people most often get wrong about their own code: findings doubling
    while the code doubles is a flat rate, and a report leading with
    "findings doubled" would be true and actively misleading.
    """
    if len(segment.records) < 2:
        return Growth(None, None, "unknown")
    first, last = segment.records[0], segment.records[-1]
    before, after = _rate(first), _rate(last)
    start = first.populations.get("declarations_scanned")
    end = last.populations.get("declarations_scanned")
    if before is None or after is None or not start:
        return Growth(None, None, "unknown")

    population_change = round((end or 0) / start - 1, 4)
    rate_change = round(after - before, 6)
    grew = population_change > 0.05
    worse = rate_change > 0
    if grew and worse:
        verdict = "grew and got worse"
    elif grew:
        verdict = "grew without getting worse"
    elif worse:
        verdict = "got worse without growing"
    else:
        verdict = "neither grew nor got worse"
    return Growth(population_change, rate_change, verdict)


def stability(segment: Segment) -> Stability:
    """Findings present in every scan of the segment.

    A finding that survived the whole window is a different problem from
    one that appeared yesterday: nobody has touched it, or every attempt
    failed. The work order should treat them differently, and cannot if
    the report does not distinguish them.
    """
    if not segment.records:
        return Stability((), 0)
    surviving = set(segment.records[0].fingerprints)
    for record in segment.records[1:]:
        surviving &= set(record.fingerprints)
    return Stability(tuple(sorted(surviving)), len(segment.records))


def trend_report(segment: Segment) -> dict[str, Any]:
    """One segment's trends, with the window they describe.

    The window is not decoration. "Declining" over two scans an hour
    apart and over two scans a year apart are different claims, and a
    reader cannot tell which they are reading without the dates.
    """
    moved = trajectory(segment)
    velocity = debt_velocity(segment)
    growth = growth_versus_quality(segment)
    persistent = stability(segment)
    return {
        "scans": len(segment.records),
        "from": segment.records[0].recorded_at if segment.records else None,
        "to": segment.records[-1].recorded_at if segment.records else None,
        "break_reason": segment.break_reason,
        "trajectory": {
            "direction": moved.direction.value,
            "change": moved.change,
            "reason": moved.reason,
        },
        "velocity": {
            "introduced": velocity.introduced,
            "cleared": velocity.cleared,
            "net": velocity.net,
            "improving": velocity.improving,
            "worsening": velocity.worsening,
        },
        "growth": {
            "population_change": growth.population_change,
            "rate_change": growth.rate_change,
            "verdict": growth.verdict,
        },
        "persistent_findings": len(persistent.persistent),
    }

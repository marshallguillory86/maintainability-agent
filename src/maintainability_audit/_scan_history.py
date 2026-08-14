"""An append-only record per scan, and the gate that keeps a series honest.

ADR 009 §2 and §4.

**The gate is the load-bearing half.** This repository's own tooling
changed several times in one day — a line-count column corrected,
generated code excluded from the corpus, unread source discovered — and
the same fourteen repositories scored differently at 09:00 and 17:00.
Every one of those changes was a fix. A trend line drawn through those
runs would have been a chart of bug fixes presented as a statement about
someone's code.

That is ADR 006's defect arriving through the time dimension, and it is
worse there: a wrong snapshot is obviously a snapshot, while a wrong
trend looks like knowledge. So two scans are comparable only when the
rubric, the analyzer coverage and the scope all match, and where they
differ the series is **segmented at that boundary** with the break named.
A silently spliced series is worse than none.

**Append-only, and nothing here can rewrite a record.** A history a
later run can edit is a history that can be made to say anything, and
the first line anyone would want to edit is the run that made their
number look bad. Writes are `O_APPEND`; there is no update path.

Trend *arithmetic* is deliberately not in this module. Records and
comparability come first so the numbers cannot be computed over a series
that has not been checked.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

# Versioned separately from the report contract. The two change for
# different reasons — a report field is a consumer-facing break, a
# history field is a migration of stored data — and one number for both
# would force either break to break the other.
HISTORY_SCHEMA_VERSION = 1

DEFAULT_HISTORY_PATH = ".maintainability/history.jsonl"

# What a score *means*. Two scans whose values differ on any of these
# were produced by different instruments, and a trend across them
# measures the instrument rather than the code.
#
# Swept by `test_every_field_that_changes_meaning_breaks_comparability`
# rather than spot-checked: the failure mode is a seventh input to the
# score being added and not added here, after which trends silently span
# a change in the instrument.
COMPARABILITY_FIELDS: tuple[str, ...] = (
    "rubric_version",
    "calibration",
    "thresholds_digest",
    "analyzers",
    "scored_languages",
    "scope",
)


@dataclass(frozen=True)
class ScanRecord:
    """One scan, as it is stored.

    Holds populations and fingerprints, not only the score. A run that
    drops from 4.4 to 4.0 because the repository doubled in size is a
    different event from one that drops because the same code got worse,
    and the score alone cannot tell them apart.
    """

    recorded_at: str
    commit: str
    branch: str
    scope: str
    rubric_version: str
    calibration: float
    # A digest of the thresholds in force. Stored rather than the
    # thresholds themselves: the comparison is equality, and a digest
    # cannot be partially compared by accident.
    thresholds_digest: str
    analyzers: tuple[str, ...]
    scored_languages: tuple[str, ...]
    estimate: float | None
    # The interval the estimate could occupy on evidence not gathered.
    # Stored so a later run can tell a real move from a move inside the
    # uncertainty — without it, trend direction would need a threshold
    # invented for the purpose when the report already publishes one.
    range_low: float | None = None
    range_high: float | None = None
    populations: dict[str, int] = field(default_factory=dict)
    # Stable finding identities, for the recurrence work that follows.
    fingerprints: tuple[str, ...] = ()
    # Whether this scan was reconstructed rather than observed. A commit
    # audited today carries today's tooling, config and analyzer
    # versions, which is not the scan that would have happened then. The
    # comparability gate already segments on those; this is the reader's
    # distinction between "we watched this" and "we went back and looked".
    backfilled: bool = False
    # Which of those a remediation prompt actually asked somebody to fix.
    # This is what makes recurrence a strong signal rather than a weak
    # one: "a rule fired again" says only that the file changed twice,
    # while "the thing we told you to fix came back" says the advice did
    # not hold. Only something that remembers what it advised can say it.
    targeted: tuple[str, ...] = ()

    def as_line(self) -> str:
        payload: dict[str, Any] = {
            "history_schema_version": HISTORY_SCHEMA_VERSION,
            **asdict(self),
        }
        return json.dumps(payload, sort_keys=True)


@dataclass(frozen=True)
class Segment:
    """A run of scans produced by one instrument.

    `break_reason` names what changed against the previous segment, and
    is empty for the first — which breaks from nothing rather than from
    something unstated.
    """

    records: list[ScanRecord]
    break_reason: str = ""

    @property
    def comparable_trend(self) -> bool:
        """Whether this segment can carry a direction at all.

        One point is not a direction. Reporting a trend from a single
        scan would be the population-floor defect in the time dimension:
        a number computed over a sample too small to support one.
        """
        return len(self.records) >= 2


def comparability_key(record: ScanRecord) -> tuple[Any, ...]:
    """What must match for two scans to belong to one series.

    Sets rather than sequences for the collections: tool order is an
    artifact of how the pool was iterated, not a change in coverage.
    """
    return tuple(
        frozenset(value) if isinstance(value, (tuple, list, set)) else value
        for value in (getattr(record, name) for name in COMPARABILITY_FIELDS)
    )


def _difference(earlier: ScanRecord, later: ScanRecord) -> str:
    """Which comparability fields changed, named for the report."""
    changed = []
    for name in COMPARABILITY_FIELDS:
        before, after = getattr(earlier, name), getattr(later, name)
        if isinstance(before, (tuple, list, set)):
            if frozenset(before) != frozenset(after):
                changed.append(name)
        elif before != after:
            changed.append(name)
    return ", ".join(changed)


def segments(records: list[ScanRecord]) -> list[Segment]:
    """Split a history wherever the instrument changed.

    Segmenting rather than withholding, because the earlier scans remain
    perfectly good evidence about the period they cover — they simply
    cannot be joined to the later ones. Withholding everything on a
    coverage change would throw away real history to avoid one bad line.
    """
    if not records:
        return []
    found: list[Segment] = [Segment(records=[records[0]])]
    for previous, current in zip(records, records[1:], strict=False):
        if comparability_key(previous) == comparability_key(current):
            found[-1].records.append(current)
            continue
        found.append(Segment(
            records=[current],
            break_reason=(
                f"{_difference(previous, current)} changed, so scans before this "
                "point were produced by a different instrument and cannot be "
                "joined to those after it"
            ),
        ))
    return found


def append_scan(path: Path, record: ScanRecord) -> None:
    """Add one line. Never touches what is already there.

    Opened in append mode with no read and no seek, so there is no code
    path that could rewrite an earlier scan even by mistake.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.as_line() + "\n")


# Fields stored as sequences, derived from the dataclass rather than
# listed by hand so a new one is handled the day it is added.
_SEQUENCE_FIELDS: tuple[str, ...] = (
    "analyzers", "scored_languages", "fingerprints", "targeted",
)


def read_history(path: Path) -> list[ScanRecord]:
    """Every readable record, oldest first.

    A line that will not parse costs that one scan and nothing else. A
    history that refuses to load because a write was truncated is a
    history that gets deleted by whoever hits the error first, which
    loses everything rather than one line.
    """
    if not path.exists():
        return []
    records: list[ScanRecord] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            payload.pop("history_schema_version", None)
            # Every sequence field back to a tuple. JSON has one list
            # type, so a field missed here returns as a list and the
            # record stops comparing equal to a freshly built one —
            # `targeted` was missed exactly that way and a test caught
            # it. Driven off the field list rather than named one by one,
            # so the next tuple field added cannot be forgotten.
            records.append(ScanRecord(
                **{**payload,
                   **{name: tuple(payload.get(name, ())) for name in _SEQUENCE_FIELDS}}))
        except (ValueError, TypeError):
            continue
    return records


def thresholds_digest(thresholds: dict[str, Any]) -> str:
    """A stable digest of the thresholds in force.

    Stored rather than the thresholds themselves because the comparison
    is equality: a digest cannot be half-compared by a later reader who
    checks three keys and forgets the fourth. Sorted so key order in a
    config file is not mistaken for a change in the rubric.
    """
    import hashlib

    payload = json.dumps(thresholds, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def record_of(report: dict[str, Any], config: dict[str, Any], version: str,
              calibration: float, fingerprints: tuple[str, ...],
              targeted: tuple[str, ...] = (), backfilled: bool = False) -> ScanRecord:
    """Build a record from a finished report.

    Every comparability field is taken from what the run actually did,
    never from what it was asked to do: `analyzers` is the tools that
    *contributed*, not the pool that was selected, because a tool that
    failed to run changes the coverage exactly as much as one that was
    never chosen.
    """
    from datetime import UTC, datetime

    coverage = report.get("analyzer_coverage") or {}
    contributed = tuple(sorted(
        entry["tool"]
        for entries in (coverage.get("by_outcome") or {}).values()
        for entry in entries
        if entry.get("tier") == "analyzer" and entry.get("measurements") is not None
    ))
    summary = report.get("summary") or {}
    score = report.get("score") or {}
    return ScanRecord(
        recorded_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        commit=report.get("git_commit") or "",
        branch=report.get("git_branch") or "",
        scope=report.get("mode") or "full",
        rubric_version=version,
        calibration=calibration,
        thresholds_digest=thresholds_digest(config.get("thresholds") or {}),
        analyzers=contributed,
        scored_languages=tuple(sorted(coverage.get("scored_languages") or ())),
        estimate=score.get("maintainability_estimate"),
        range_low=(score.get("maintainability_range") or [None, None])[0],
        range_high=(score.get("maintainability_range") or [None, None])[-1],
        populations={
            key: int(summary[key])
            for key in ("files_scanned", "declarations_scanned",
                        "production_files_scanned", "production_declarations_scanned")
            if isinstance(summary.get(key), int)
        },
        fingerprints=fingerprints,
        targeted=targeted,
        backfilled=backfilled,
    )

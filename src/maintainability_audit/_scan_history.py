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

from .config import PathNotAllowed

# Versioned separately from the report contract. The two change for
# different reasons — a report field is a consumer-facing break, a
# history field is a migration of stored data — and one number for both
# would force either break to break the other.
# 2 since ADR 011: a record now stores what the charts draw —
# categories, aspects, the pillar conditions and the practice level as
# two separate series (ADR 007 forbids averaging them), and the
# evidence status. Schema-1 lines still load; the new fields default
# to empty, and a chart treats empty as a gap, never as a zero.
# 3 since ADR 009 identity: a record also stores structured identity
# records (kind, path, name, ordinal, body digest, label) beside the
# label tuple, so recurrence can match findings across renames and
# reorders while charts keep their strings. Schema-1/2 lines still
# load with empty identities, and recurrence between two such records
# stays label equality.
# Schema 4 adds `transformation`, the operator's name for the class of work
# a scan followed. Older lines load with it empty and are simply not part of
# any series, which is the truth about them: nothing recorded what they
# followed. A schema-4 line read by an older build fails that one line's
# parse and costs that scan, which is the tolerance `read_history` was
# built with rather than a new risk.
HISTORY_SCHEMA_VERSION = 4

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
    # Stable finding identity labels, for charts and the targeted join.
    fingerprints: tuple[str, ...] = ()
    # Schema 3 (ADR 009): the same findings as structured records —
    # dicts shaped like `_finding_match.Identity` — so recurrence can
    # match through renames and same-name reorders. Empty on older
    # lines, which keeps their comparisons label-only.
    identities: tuple[dict[str, Any], ...] = ()
    # Whether this scan was reconstructed rather than observed. A commit
    # audited today carries today's tooling, config and analyzer
    # versions, which is not the scan that would have happened then. The
    # comparability gate already segments on those; this is the reader's
    # distinction between "we watched this" and "we went back and looked".
    backfilled: bool = False
    # Schema 2 (ADR 011): what the report *published* for this scan,
    # copied and never recomputed — a record that recomputes is a second
    # scorer. `pillars` maps pillar name to its condition score;
    # `practice_level` is the separate maturity series. Empty/None on
    # records written by schema 1.
    categories: dict[str, float] = field(default_factory=dict)
    aspects: dict[str, float | None] = field(default_factory=dict)
    pillars: dict[str, float | None] = field(default_factory=dict)
    practice_level: int | None = None
    evidence_status: str = ""
    # Which of those a remediation prompt actually asked somebody to fix.
    # This is what makes recurrence a strong signal rather than a weak
    # one: "a rule fired again" says only that the file changed twice,
    # while "the thing we told you to fix came back" says the advice did
    # not hold. Only something that remembers what it advised can say it.
    targeted: tuple[str, ...] = ()
    # Schema 4: the operator's name for the class of work this scan
    # followed -- `--transformation react-18`. Nothing in a tree says which
    # transformation produced it, so this is a claim the operator makes and
    # this tool records without verifying. Deliberately absent from
    # `COMPARABILITY_FIELDS`: two runs of different transformations on one
    # instrument are still comparable measurements of code condition, and
    # segmenting on a label would break a series for saying its own name.
    transformation: str = ""

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


def append_scan(path: Path, record: ScanRecord, root: Path | None = None) -> None:
    """Add one line, without ever opening the existing inode for writing.

    Append mode was the obvious implementation and the wrong one. An
    audit hardlinked this file to a target outside the repository and
    watched a scan record land on it: `repository_path` had bounded the
    *name*, and `open("a")` then wrote to whatever inode the name
    pointed at (D34). `O_NOFOLLOW` is no help against a hardlink.

    So the file is rewritten through a staged replacement instead. That
    costs a read of a history measured in kilobytes and buys the only
    property that actually holds: no existing inode is opened, so a
    hardlink keeps its contents and stops being this name.

    ``root`` is optional so the many existing callers that pass a path
    already bounded by `repository_path` keep working; when it is
    absent the file's own directory bounds the write, which still
    refuses symlinks and still stages.
    """
    from ._safe_write import write_bounded

    _refuse_clobbering_non_history(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_bounded(
        Path(root) if root is not None else path.parent,
        path, record.as_line() + "\n", append=True,
    )


def _refuse_clobbering_non_history(target: Path) -> None:
    """A scan record may extend a history, and nothing else.

    The history path comes from the repository's own config, and being
    inside the granted root was the only check. An audit set
    ``paths.history`` to ``README.md`` and watched an audit append a JSON
    line onto source -- in a tool whose contract is five artifacts and
    "never source". `write_bounded` refuses a symlink or an irregular
    file but not a plain one, because appending to a plain file is
    exactly what a history *is*; the file's contents are what tell a
    history apart from someone's work. This is the history twin of
    `_refuse_clobbering_non_baseline`.

    An absent or empty file is fine, and so is one whose every line is a
    scan record this tool wrote. A single foreign line is someone else's
    file.
    """
    if not target.exists() or target.is_symlink():
        # Absence is fine; a symlink is `write_bounded`'s to refuse, with
        # the message that fits that case.
        return
    if target.stat().st_nlink > 1:
        # A hardlink is the *other* redirect, and `write_bounded` already
        # answers it: its staged replacement severs the link, so the
        # outside inode keeps its contents and this name becomes a fresh
        # history. Content-checking it here would refuse the very write
        # that defence is designed to perform safely (the D34 hardlink
        # case). This guard is only for a plain file sitting where the
        # history should go -- the `paths.history: README.md` attack.
        return
    try:
        lines = [ln for ln in target.read_text(encoding="utf-8").splitlines() if ln.strip()]
    except (OSError, ValueError) as unreadable:
        raise PathNotAllowed(
            f"{target} exists and cannot be read as a scan history "
            f"({unreadable}); refusing to write over it."
        ) from unreadable
    # At least one line must be a scan record. `read_history` already
    # tolerates a single corrupt line -- a truncated write costs one scan,
    # never the series -- so requiring *every* line to parse would freeze a
    # slightly-damaged history against all further appends. The distinction
    # this needs is coarser and exact for it: a file with zero records is
    # not this tool's history, it is someone's source (`README.md`).
    if not any(_is_scan_record(line) for line in lines):
        raise PathNotAllowed(
            f"{target} exists and is not a scan history; refusing to "
            "write over it. Choose a path that is absent or holds a "
            "history this tool wrote."
        )


def _is_scan_record(line: str) -> bool:
    try:
        record = json.loads(line)
    except ValueError:
        return False
    return isinstance(record, dict) and "recorded_at" in record


# Fields stored as sequences, derived from the dataclass rather than
# listed by hand so a new one is handled the day it is added.
_SEQUENCE_FIELDS: tuple[str, ...] = (
    "analyzers", "scored_languages", "fingerprints", "targeted", "identities",
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

    from ._finding_match import identities_from_report

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
        # Read off the report like `mode` and `git_commit`, so a surface
        # opts in by setting one field rather than by threading a new
        # argument through every caller of this function.
        transformation=str(report.get("transformation") or ""),
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
        identities=tuple(
            asdict(identity)
            for identity in sorted(identities_from_report(report),
                                   key=lambda i: i.fingerprint)
        ),
        # Published values, straight off the score document. `or {}`
        # rather than KeyError: a withheld score has no categories, and
        # a record of that scan is still a record.
        categories=dict(score.get("categories") or {}),
        aspects=dict(score.get("aspects") or {}),
        pillars={
            entry["pillar"]: entry.get("condition")
            for entry in (report.get("pillars") or [])
            if isinstance(entry, dict) and entry.get("pillar")
        },
        practice_level=(report.get("practice") or {}).get("level"),
        evidence_status=str((score.get("evidence_status") or {}).get("status") or ""),
        targeted=targeted,
        backfilled=backfilled,
    )

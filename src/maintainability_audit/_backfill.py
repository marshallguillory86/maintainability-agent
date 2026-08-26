"""Scanning the past into history, and deciding what to keep — ADR 009 §5.

A first run need not be blind. Past commits can be materialized in a git
worktree and scanned, producing a real series on day one rather than in
three months — which matters because recurrence, velocity and trajectory
all need several scans before they say anything. Without backfill the
sharpest feature in the tool is inert until enough time has passed for
somebody to have stopped using it.

**Expensive, therefore explicit.** A separate command with a range or a
sampling interval, never implicit in a normal run. A worktree and a full
audit per commit is minutes of work, and a tool that silently does that
during a routine scan is a tool people disable.

**Backfilled records say so.** A commit scanned today with today's tools
is not the scan that would have happened then: the config, the analyzer
versions and the rubric are all current. The comparability gate already
segments on those, but the distinction between *watched* and *went back
and looked* belongs to the reader.

**Compaction is a policy and never a side effect.** A history that trims
itself during a routine scan can drop the return that would have
escalated a finding, and nobody would know which run did it. Reading
never writes.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from ._scan_history import ScanRecord, read_history
from .git_tools import GIT_TIMEOUT_SECONDS, git_env, validate_revspec


def _git(root: Path, *args: str) -> str:
    """Run git in `root`, raising on any failure.

    `-C` alone does not bind the repository: `GIT_DIR` and its siblings
    outrank it, so an inherited value would silently redirect these
    commands — and the worktree ones below write. The environment is
    scrubbed and the child is bounded, both D37.
    """
    try:
        result = subprocess.run(  # noqa: S603 - argv list, never a shell
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, check=False,
            timeout=GIT_TIMEOUT_SECONDS, env=git_env())
    except subprocess.TimeoutExpired as expired:
        raise ValueError(
            f"{' '.join(args)} timed out after {GIT_TIMEOUT_SECONDS}s") from expired
    if result.returncode != 0:
        raise ValueError(
            f"{' '.join(args)} failed: {result.stderr.strip()[:200] or 'unknown error'}")
    return result.stdout


def commits_in_range(root: Path, revspec: str) -> list[str]:
    """Every commit in `revspec`, oldest first.

    Oldest first because history is written forward. Recording
    newest-first would make every consecutive pair look like a reversal,
    and velocity would report each cleared finding as introduced.

    A bad revspec raises rather than returning nothing. An empty plan
    and a typo look identical from the outside, and "backfilled 0
    commits" would leave someone believing their history was complete.
    """
    try:
        # Validated before git sees it: `--output=<path>` would be read as
        # an option and create that file (D37). The MCP door checked this
        # and the CLI's --backfill did not.
        output = _git(root, "rev-list", "--reverse", validate_revspec(revspec), "--")
    except ValueError as error:
        raise ValueError(f"{revspec!r} is not a valid commit range: {error}") from error
    return output.split()


def plan_backfill(
    root: Path, revspec: str, interval: int = 1, history: Path | None = None
) -> list[str]:
    """Which commits to scan, in order, skipping any already recorded.

    Sampling exists because a thousand-commit range is hours of work
    nobody asked for, and the shape of the series is what a trend reads —
    every tenth commit gives that shape at a tenth of the cost.

    Skipping recorded commits makes backfill resumable. Without it, a
    second run after an interruption would double every record and make
    velocity count each finding twice.
    """
    if interval < 1:
        raise ValueError("interval must be at least 1")
    commits = commits_in_range(root, revspec)
    sampled = commits[::interval] if interval > 1 else commits
    if history is None:
        return sampled
    seen = {record.commit for record in read_history(history)}
    return [commit for commit in sampled if commit not in seen]


def compact(records: list[ScanRecord], keep: int) -> list[ScanRecord]:
    """Thin a history to `keep` records, preserving the window's ends.

    The oldest record is kept deliberately. A trend states the window it
    measured, so dropping the first scan shrinks that window and makes
    the same history quietly assert something narrower than before —
    a change to the claim that nobody decided to make.

    Never called by a scan. Compaction is something an operator does on
    purpose, because a history that trims itself can drop the return
    that would have escalated a finding.
    """
    if keep < 2:
        raise ValueError("keeping fewer than two records leaves no trend to read")
    if len(records) <= keep:
        return records
    # Both ends, and an even sample of the middle: the shape survives
    # while the count comes down.
    middle = records[1:-1]
    step = max(1, len(middle) // (keep - 2)) if keep > 2 else len(middle) + 1
    return [records[0], *middle[::step][: keep - 2], records[-1]]


def backfill(root: Path, revspec: str, config: dict, version: str,
             calibration: float, history: Path, interval: int = 1,
             announce: bool = True) -> int:
    """Scan each commit in a worktree and record it. Returns the count.

    A **worktree**, never a checkout in place. Rewinding somebody's
    working tree to scan it would be a destructive act performed by a
    read-only-sounding command, and would lose uncommitted work. The
    worktree is removed afterwards even when a scan raises, because a
    stale one blocks the next attempt with a confusing git error.
    """
    import tempfile

    from ._identity import finding_fingerprints
    from ._scan_history import append_scan, record_of
    from .report import build_report

    commits = plan_backfill(root, revspec, interval=interval, history=history)
    if not commits:
        if announce:
            print(f"nothing to backfill: every commit in {revspec} is already recorded")
        return 0

    recorded = 0
    with tempfile.TemporaryDirectory(prefix="maintainability-backfill-") as scratch:
        tree = Path(scratch) / "tree"
        for index, commit in enumerate(commits, start=1):
            _git(root, "worktree", "add", "--detach", "--quiet", str(tree), commit)
            try:
                report = build_report(tree, config)
                append_scan(history, record_of(
                    report, config, version, calibration,
                    tuple(sorted(finding_fingerprints(report))),
                    backfilled=True))
                recorded += 1
                if announce:
                    estimate = (report.get("score") or {}).get("maintainability_estimate")
                    print(f"  [{index}/{len(commits)}] {commit[:8]} est={estimate}")
            finally:
                # Always, even on failure: a stale worktree blocks the
                # next attempt with an error about the path existing.
                _git(root, "worktree", "remove", "--force", str(tree))
    return recorded

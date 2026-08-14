"""Scanning the past into history, and deciding what to keep — 5.5, 5.6.

A first run need not be blind. Past commits can be materialized in a git
worktree and scanned, producing a real series on day one rather than in
three months. Recurrence, velocity and trajectory all need several scans
before they say anything, so without backfill the sharpest feature in
the tool is inert until enough time has passed for somebody to have
stopped using it.

**It is expensive, so it is explicit.** A separate command with a range
or an interval, never implicit in a normal run. Cloning a worktree and
running a full audit per commit is minutes of work, and a tool that
silently does that during a routine scan is a tool people disable.

**Backfilled records are marked.** A scan of a commit as it exists today
is not the same evidence as a scan taken at the time: the tooling is
today's, the config is today's, and the analyzer versions are today's.
The comparability gate already segments on those, but a reader deserves
to know which records were reconstructed rather than observed.

**Compaction is a policy, never a side effect.** A history that silently
drops records is one that can quietly lose the return that would have
escalated a finding. Dropping is explicit, states what went, and keeps
the oldest record of a segment so the window a trend describes does not
shrink without saying so.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from maintainability_audit._backfill import (
    commits_in_range,
    compact,
    plan_backfill,
)
from maintainability_audit._scan_history import ScanRecord, append_scan, read_history


def _repo_with_commits(root: Path, count: int) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    for n in range(count):
        (root / f"f{n}.py").write_text(f"def f{n}():\n    return {n}\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-qm", f"c{n}"], check=True)
    return root


_ORDER = iter(range(1, 100))


def _record(commit: str, **overrides: object) -> ScanRecord:
    # Timestamps come from a counter, not from the commit. An earlier
    # version derived the day from the SHA's first two characters, which
    # worked on synthetic `00…` commits and raised on real hex ones —
    # a fixture that only accepts the data the test invents.
    base: dict[str, object] = {
        "recorded_at": f"2026-08-{next(_ORDER):02d}T00:00:00Z",
        "commit": commit, "branch": "main", "scope": "full",
        "rubric_version": "0.7.0", "calibration": 2.6279, "thresholds_digest": "t",
        "analyzers": ("lizard",), "scored_languages": ("Python",), "estimate": 4.0,
    }
    base.update(overrides)
    return ScanRecord(**base)  # type: ignore[arg-type]


# --------------------------------------------------------------------
# 5.5 — planning the walk
# --------------------------------------------------------------------


def test_a_range_resolves_to_its_commits_oldest_first(tmp_path: Path) -> None:
    """History is written forward, so the walk runs forward.

    Recording newest-first would make every consecutive pair look like a
    reversal, and velocity would report every cleared finding as
    introduced.
    """
    root = _repo_with_commits(tmp_path / "walk", 4)

    found = commits_in_range(root, "HEAD~3..HEAD")

    assert len(found) == 3
    ordered = subprocess.run(
        ["git", "-C", str(root), "rev-list", "--reverse", "HEAD~3..HEAD"],
        capture_output=True, text=True, check=True).stdout.split()
    assert found == ordered


def test_an_interval_samples_rather_than_scanning_everything(tmp_path: Path) -> None:
    """A thousand-commit range is hours of work nobody asked for.

    Sampling every Nth commit gives the shape of the series at a
    fraction of the cost, and the shape is what a trend reads.
    """
    root = _repo_with_commits(tmp_path / "sampled", 10)

    every_third = plan_backfill(root, "HEAD~9..HEAD", interval=3)

    assert len(every_third) == 3
    assert every_third == plan_backfill(root, "HEAD~9..HEAD", interval=3), (
        "planning is deterministic; two runs must choose the same commits"
    )


def test_commits_already_recorded_are_not_scanned_again(tmp_path: Path) -> None:
    """Backfill is resumable, and re-running must not duplicate a series.

    A second invocation after an interrupted first would otherwise
    double every record and make velocity count each finding twice.
    """
    root = _repo_with_commits(tmp_path / "resume", 4)
    history = root / ".maintainability" / "history.jsonl"
    already = commits_in_range(root, "HEAD~3..HEAD")[0]
    append_scan(history, _record(already))

    remaining = plan_backfill(root, "HEAD~3..HEAD", history=history)

    assert already not in remaining
    assert len(remaining) == 2


def test_an_unknown_range_is_refused_rather_than_silently_empty(tmp_path: Path) -> None:
    """An empty plan and a bad revspec look identical from the outside.

    Returning nothing would report "backfilled 0 commits" for a typo,
    and the user would believe their history was already complete.
    """
    root = _repo_with_commits(tmp_path / "bad", 2)

    with pytest.raises(ValueError, match="not a valid"):
        commits_in_range(root, "nonexistent-branch..HEAD")


# --------------------------------------------------------------------
# 5.5 — what a backfilled record says about itself
# --------------------------------------------------------------------


def test_a_backfilled_record_says_it_was_reconstructed(tmp_path: Path) -> None:
    """Reconstructed evidence is not observed evidence.

    A commit scanned today with today's tools is not the scan that would
    have happened then. The gate already segments on tooling changes,
    but a reader is owed the distinction between "we watched this" and
    "we went back and looked".
    """
    history = tmp_path / "h.jsonl"
    append_scan(history, _record("a" * 40, backfilled=True))
    append_scan(history, _record("b" * 40))

    records = read_history(history)

    assert records[0].backfilled is True
    assert records[1].backfilled is False


# --------------------------------------------------------------------
# 5.6 — compaction is a policy, never a side effect
# --------------------------------------------------------------------


def test_compaction_keeps_the_oldest_record_of_the_window(tmp_path: Path) -> None:
    """Dropping the oldest silently shortens every trend that reads it.

    A trend states the window it measured. If compaction removes the
    first scan, the window shrinks and the same history starts making a
    narrower claim without anyone deciding to.
    """
    records = [_record(f"{n:02d}" + "0" * 38) for n in range(10)]

    kept = compact(records, keep=4)

    assert len(kept) == 4
    assert kept[0] == records[0], "the start of the window survives"
    assert kept[-1] == records[-1], "and so does the most recent scan"


def test_compaction_never_runs_by_itself(tmp_path: Path) -> None:
    """Reading a history must not change it.

    A history that trims itself during a routine scan can drop the
    return that would have escalated a finding, and nobody would know
    which run did it.
    """
    history = tmp_path / "quiet.jsonl"
    for n in range(6):
        append_scan(history, _record(f"{n:02d}" + "0" * 38))
    before = history.read_bytes()

    read_history(history)

    assert history.read_bytes() == before, "reading the history modified it"


def test_compaction_below_the_limit_changes_nothing(tmp_path: Path) -> None:
    """The check must not fire on the case it does not describe."""
    records = [_record(f"{n:02d}" + "0" * 38) for n in range(3)]

    assert compact(records, keep=10) == records


# --------------------------------------------------------------------
# The command that walks it
# --------------------------------------------------------------------


def test_backfill_produces_a_real_series_from_history(tmp_path: Path) -> None:
    """Day-one history, which is what makes the rest of Phase 5 usable.

    Recurrence, velocity and trajectory all need several scans before
    they say anything. Without this the sharpest feature in the tool is
    inert until enough time has passed for somebody to have stopped
    using it.
    """
    from maintainability_audit.cli import main

    root = tmp_path / "past"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "pkg").mkdir()
    for n in range(60):
        (root / "pkg" / f"mod{n}.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    for step in range(3):
        (root / "pkg" / "moving.py").write_text(
            "def f(x):\n" + "".join(f"    if x == {i}:\n        return {i}\n"
                                   for i in range(step * 20)) + "    return -1\n",
            encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t",
                        "-c", "user.name=t", "commit", "-qm", f"step{step}"], check=True)

    assert main(["--root", str(root), "--backfill", "HEAD~2..HEAD"]) == 0

    records = read_history(root / ".maintainability" / "history.jsonl")
    assert len(records) == 2, "one record per commit in the range"
    assert all(r.backfilled for r in records), "reconstructed, and it says so"
    assert len({r.commit for r in records}) == 2, "distinct commits"
    assert records[0].recorded_at <= records[1].recorded_at, "oldest first"


def test_backfill_leaves_the_working_tree_untouched(tmp_path: Path) -> None:
    """It checks commits out in a worktree, not in place.

    Rewinding somebody's checkout to scan it would be a destructive act
    performed by a read-only-sounding command, and would lose uncommitted
    work.
    """
    from maintainability_audit.cli import main

    root = tmp_path / "safe"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "a.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "one"], check=True)
    (root / "b.py").write_text("def g():\n    return 2\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "two"], check=True)

    (root / "uncommitted.py").write_text("# work in progress\n", encoding="utf-8")
    head = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip()

    main(["--root", str(root), "--backfill", "HEAD~1..HEAD"])

    assert (root / "uncommitted.py").exists(), "uncommitted work was destroyed"
    assert subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                          capture_output=True, text=True, check=True).stdout.strip() == head
    leftover = subprocess.run(["git", "-C", str(root), "worktree", "list"],
                              capture_output=True, text=True, check=True).stdout
    assert leftover.count("\n") == 1, f"a worktree was left behind:\n{leftover}"

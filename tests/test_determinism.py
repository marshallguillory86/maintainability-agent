"""P1: same tree, same config, same answer — and what counts as "same".

The promise nothing tested. Every other published promise had a test
keeping it; determinism had only the intention, which is the state every
other defect in this project started from.

Two things make it worth pinning now rather than assuming:

**History is an input.** A report carries `scan_history`,
`design_review_candidates` and the escalations derived from them, so two
runs over an identical tree with different histories legitimately
produce different reports. That is correct — a finding that came back
twice *is* different information — but it means "deterministic" has to
name what it is a function of, or the promise is either false or vague.

**The analysis performs no network access.** Acquiring a tool may, on
first run, and the acquired version is recorded. Analysis itself must
not, or a run is a function of somebody else's uptime.
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report


ANSI_ESCAPE = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    (root / "pkg").mkdir()
    for n in range(60):
        (root / "pkg" / f"mod{n}.py").write_text(
            f"def f{n}(x):\n    if x:\n        return {n}\n    return 0\n", encoding="utf-8")
    body = "".join(f"    if x == {i}:\n        return {i}\n" for i in range(40))
    (root / "pkg" / "hot.py").write_text(f"def tangled(x):\n{body}    return -1\n",
                                         encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-qm", "init"], check=True)
    return root


def _comparable(report: dict) -> str:
    """The report minus the fields that are *meant* to vary.

    The absolute root, worktree status, every analyzer ``seconds`` field,
    and terminal paint around version strings may vary. The uncolored
    version text and every other analyzer result must not.
    """

    def stable(value: object, field: str = "") -> object:
        if isinstance(value, dict):
            return {
                key: stable(item, key)
                for key, item in value.items()
                if key != "seconds"
            }
        if isinstance(value, list):
            return [stable(item) for item in value]
        if isinstance(value, tuple):
            return tuple(stable(item) for item in value)
        if field == "version" and isinstance(value, str):
            return ANSI_ESCAPE.sub("", value)
        return value

    stripped = {k: v for k, v in report.items() if k not in {"root", "git_status_short"}}
    return json.dumps(stable(stripped), sort_keys=True, default=str)


def test_two_runs_on_one_tree_agree(tmp_path: Path) -> None:
    """The promise, checked rather than assumed.

    Ordering is the usual way this breaks: a set iterated into a list, a
    dict built from a filesystem walk. Neither shows up in a single run.
    """
    root = _repo(tmp_path / "twice")
    config = load_config(None)

    first = build_report(root, config)
    second = build_report(root, config)

    assert _comparable(first) == _comparable(second)


def test_two_analyzer_runs_on_one_tree_agree(tmp_path: Path) -> None:
    """Pinned tool versions make analyzer output part of P1's input."""
    root = _repo(tmp_path / "twice-with-analyzers")
    config = load_config(None)

    first = build_report(root, config, run_analyzers=True)
    second = build_report(root, config, run_analyzers=True)

    assert _comparable(first) == _comparable(second)


def test_a_history_is_an_input_and_the_report_says_so(tmp_path: Path) -> None:
    """Determinism is over (tree, config, history) — not the tree alone.

    A finding that cleared and came back twice is genuinely different
    information from one seen for the first time, so the same tree
    *should* report differently against different histories. The promise
    must name history as an input, or it is false as written.
    """
    from maintainability_audit._scan_history import (
        ScanRecord,
        append_scan,
        read_history,
        segments,
    )
    from maintainability_audit._trends import trend_report

    root = _repo(tmp_path / "withhistory")
    history = root / ".maintainability" / "history.jsonl"

    def record(commit: str, findings: tuple[str, ...]) -> ScanRecord:
        return ScanRecord(
            recorded_at=f"2026-08-{len(commit):02d}T00:00:00Z", commit=commit * 40,
            branch="main", scope="full", rubric_version="0.7.0", calibration=2.6279,
            thresholds_digest="t", analyzers=(), scored_languages=("Python",),
            estimate=4.0, fingerprints=findings)

    without = [trend_report(s) for s in segments(read_history(history))]
    assert without == [], "no history, no trend"

    append_scan(history, record("a", ("x",)))
    append_scan(history, record("bb", ()))
    append_scan(history, record("ccc", ("x",)))
    with_history = [trend_report(s) for s in segments(read_history(history))]

    assert with_history, "the same tree now carries a trend it did not before"
    assert with_history[0]["velocity"]["introduced"] == 1


def test_the_analysis_opens_no_sockets(tmp_path: Path) -> None:
    """"No network access during analysis" is P1's stated falsifier.

    A run that reaches the network is a function of somebody else's
    uptime, and its result cannot be reproduced from checked-in inputs —
    which would take P6 down with it.
    """
    import socket

    root = _repo(tmp_path / "offline")
    config = load_config(None)
    original = socket.socket

    class Refused(socket.socket):  # type: ignore[misc]
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise AssertionError("the analysis opened a socket")

    socket.socket = Refused  # type: ignore[misc, assignment]
    try:
        report = build_report(root, config)
    finally:
        socket.socket = original  # type: ignore[misc]

    assert report["summary"]["files_scanned"] >= 60

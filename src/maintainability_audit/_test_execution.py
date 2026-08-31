"""Running the repository's own test suite — the one place this agent
executes the audited tree, behind a disclosed, default-off opt-in.

Decision 9 said the agent never executes the audited repository's code.
plan-81dc6870 Class 5 amends that to: never, *unless* the operator opted
in at setup for the suite and configured its command. The opt-in is
``test_execution.requested``; the command is ``expected_commands.test``.
Nothing here runs without both.

The suite is spawned through ``_runner`` like every other child, in the
repository root, with no coverage flag injected — if the command already
produces a coverage artifact it is read, otherwise effectiveness stays
unscored and says so. A failing suite is *data* (recorded), never a
maintainability gate.

Coverage is read only from an artifact *this run* produced. A
``coverage.xml`` the tree already carried — committed, or left by an
earlier run — is ignored, because its provenance is the repository rather
than the suite we just executed, and reading it would let a repository
set its own ``test_effectiveness``. A symlinked artifact is refused
outright, the same posture ``_safe_write`` takes on the write side.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._runner import Invocation, run
from ._xml import AnalyzerXmlRefused, parse_analyzer_xml


def suite_opted_in(config: dict[str, Any]) -> bool:
    """Both halves of the opt-in: the request, and a command to run."""
    requested = bool((config.get("test_execution") or {}).get("requested"))
    command = (config.get("expected_commands") or {}).get("test")
    return requested and bool(command)


def run_test_suite(root: Path, config: dict[str, Any]) -> dict[str, Any] | None:
    """Execute the configured test command, or ``None`` when not opted in.

    Returning ``None`` on the default path is the Decision-9 guarantee: no
    opt-in, no spawn, no difference from an audit that never had this code.
    """
    if not suite_opted_in(config):
        return None
    command = list(config["expected_commands"]["test"])
    timeout = int((config.get("analyzers") or {}).get("timeout_seconds", 120))
    # Snapshot the artifact's state *before* the run so a pre-existing
    # coverage.xml cannot be mistaken for this run's output.
    before = _coverage_fingerprint(root)
    result = run(
        "test-suite",
        Invocation(argv=tuple(command), findings_exit_codes=(0, 1)),
        cwd=root, timeout_seconds=timeout,
    )
    # A test suite executed iff it exited 0 (all passed) or 1 (some failed),
    # regardless of how quiet it was — unlike an analyzer, a suite that ran
    # and failed is a real result, not a tool that produced nothing. Any
    # other exit (or a timeout, `exit_code` None) is the command failing to
    # run at all, which is not effectiveness data.
    ran = result.exit_code in (0, 1)
    return {
        "command": command,
        "ran": ran,
        "exit_code": result.exit_code,
        "passed": result.exit_code == 0,
        "detail": result.detail or "",
        "coverage_percent": _coverage_from_this_run(root, before) if ran else None,
    }


def _coverage_fingerprint(root: Path) -> int | None:
    """The coverage artifact's modification time in ns, or ``None``.

    ``None`` covers three cases treated identically: no artifact, a
    symlinked artifact (refused — we do not follow a link the tree
    planted), and an unreadable one. The nanosecond mtime is the signal
    ``_coverage_from_this_run`` compares against to tell a fresh artifact
    from a pre-existing one.
    """
    report = root / "coverage.xml"
    if report.is_symlink() or not report.is_file():
        return None
    try:
        return report.stat().st_mtime_ns
    except OSError:
        return None


def _coverage_from_this_run(root: Path, before: int | None) -> float | None:
    """A coverage percentage from an artifact *this run* produced, else ``None``.

    The artifact must exist after the run and be newer than the snapshot
    taken before it: a ``coverage.xml`` the repository committed, or one a
    previous run left untouched, has the tree for its provenance rather
    than the suite we just executed, so scoring it would let a repository
    set its own ``test_effectiveness``. ``before is None`` means there was
    nothing (or nothing readable) beforehand, so any artifact now present
    is this run's. Parsed through the same entity-refusing guard the
    analyzer XML uses, because it is still output from the audited tree.
    """
    report = root / "coverage.xml"
    after = _coverage_fingerprint(root)
    if after is None:
        return None
    if before is not None and after <= before:
        return None
    try:
        element = parse_analyzer_xml(
            report.read_text(encoding="utf-8", errors="replace"), fallback="<coverage/>")
        rate = element.get("line-rate")
        return round(float(rate) * 100, 1) if rate is not None else None
    except (AnalyzerXmlRefused, ValueError, OSError):
        return None

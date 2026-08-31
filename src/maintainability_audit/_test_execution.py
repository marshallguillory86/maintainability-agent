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
        "coverage_percent": _coverage_from_artifacts(root) if ran else None,
    }


def _coverage_from_artifacts(root: Path) -> float | None:
    """A coverage percentage from an artifact the suite already produced,
    or ``None``. Read, never injected — the command decides whether to emit
    one. Parsed through the same entity-refusing guard the analyzer XML uses,
    because the artifact is still output from the audited tree (D46)."""
    report = root / "coverage.xml"
    if not report.is_file():
        return None
    try:
        element = parse_analyzer_xml(
            report.read_text(encoding="utf-8", errors="replace"), fallback="<coverage/>")
        rate = element.get("line-rate")
        return round(float(rate) * 100, 1) if rate is not None else None
    except (AnalyzerXmlRefused, ValueError, OSError):
        return None

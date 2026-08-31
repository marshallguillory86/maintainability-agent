"""Class 5 (plan-81dc6870): the suite runs only on an explicit opt-in.

Decision 9 said the agent never executes the audited tree's code. Class 5
amends that to: never, unless the operator opted in and configured a
command. This audits the runner in isolation, before it is wired into an
audit — the load-bearing case is that the default path spawns nothing.
"""

from __future__ import annotations

import stat
from pathlib import Path

from maintainability_audit._test_execution import run_test_suite, suite_opted_in


def _fake_suite(root: Path, exit_code: int, coverage_line_rate: str | None = None) -> list[str]:
    """A stand-in test command: writes a marker (so a spawn is observable),
    optionally a coverage.xml, then exits with `exit_code`."""
    cov = ""
    if coverage_line_rate is not None:
        cov = f"printf '%s' '<coverage line-rate=\"{coverage_line_rate}\"/>' > coverage.xml\n"
    script = root / "run-suite.sh"
    script.write_text(f"#!/bin/sh\ntouch RAN_MARKER\n{cov}exit {exit_code}\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return ["./run-suite.sh"]


def _opted_in(command: list[str]) -> dict:
    return {"test_execution": {"requested": True}, "expected_commands": {"test": command}}


def test_the_default_config_never_spawns_the_suite(tmp_path: Path) -> None:
    """The Decision-9 guarantee and the falsifier: no opt-in, no spawn."""
    _fake_suite(tmp_path, 0)
    assert not suite_opted_in({})
    assert run_test_suite(tmp_path, {}) is None
    assert run_test_suite(tmp_path, {"test_execution": {"requested": False}}) is None
    # requested but no command is still not opted in — nothing to run.
    assert run_test_suite(tmp_path, {"test_execution": {"requested": True}}) is None
    assert not (tmp_path / "RAN_MARKER").exists(), "a suite was spawned without opt-in"


def test_an_opted_in_passing_suite_runs_and_reads_coverage(tmp_path: Path) -> None:
    command = _fake_suite(tmp_path, 0, coverage_line_rate="0.87")
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result is not None
    assert (tmp_path / "RAN_MARKER").exists(), "the opted-in suite did not run"
    assert result["ran"] is True and result["passed"] is True
    assert result["coverage_percent"] == 87.0


def test_a_failing_suite_is_data_not_an_error(tmp_path: Path) -> None:
    """Exit 1 is a suite that ran and failed — recorded, never a gate."""
    command = _fake_suite(tmp_path, 1, coverage_line_rate="0.42")
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["ran"] is True, "a failing suite must still count as having run"
    assert result["passed"] is False
    assert result["coverage_percent"] == 42.0


def test_a_suite_that_cannot_run_is_not_counted_as_ran(tmp_path: Path) -> None:
    """Exit 3+ is the command failing to execute, not a test failure."""
    command = _fake_suite(tmp_path, 3)
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["ran"] is False
    assert result["coverage_percent"] is None


def test_no_coverage_artifact_leaves_coverage_unknown(tmp_path: Path) -> None:
    command = _fake_suite(tmp_path, 0)  # passes, writes no coverage.xml
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["ran"] is True
    assert result["coverage_percent"] is None, "coverage must not be invented"


def _git_repo(tmp_path: Path) -> Path:
    """A committed fixture repo, so setup treats it as first-run."""
    import subprocess

    root = tmp_path / "repo"
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "fixture"],
        check=True,
    )
    return root


def test_opting_the_suite_in_stages_a_second_ask_for_the_command(tmp_path: Path) -> None:
    """`run_tests=yes` records intent; the command is a staged follow-up.

    Without a command the audit has nothing to spawn, so — exactly as
    economics stages the labor rates — the resolver must come back and
    ask for the command rather than leaving the repository at
    `test_execution.requested: true` with no command forever. Driven
    through `_setup_resolver_for`, the seam a host reaches, not
    `setup_schema` directly.
    """
    from types import SimpleNamespace

    from maintainability_audit._mcp_grants import _RootLedger
    from maintainability_audit._mcp_setup import CONFIG_FILENAME, apply_answers
    from maintainability_audit.config import load_config
    from maintainability_audit.mcp_server import _setup_resolver_for

    class _Capabilities:
        elicitation = object()

    context = SimpleNamespace(client_capabilities=_Capabilities())
    root = _git_repo(tmp_path)
    resolver = _setup_resolver_for(_RootLedger((tmp_path.resolve(),)), object)

    assert resolver(str(root), context) is not None, "the first call elicited nothing"
    apply_answers(root, {
        "run_pool": "yes", "depth": "moderate", "license_policy": "permissive",
        "economics": "skip", "run_tests": "yes", "default_format": "chat",
        "record_scan_history": "yes",
    })

    second = resolver(str(root), context)
    assert second is not None, (
        "opting the suite in left setup complete with no command; the second stage never runs"
    )
    assert set(second.schema.model_fields) == {"test_command"}, (
        f"the second call did not ask for the test command: {sorted(second.schema.model_fields)}"
    )
    assert "command" in second.message.lower(), (
        f"the second stage does not say what it is asking for: {second.message}"
    )

    apply_answers(root, {"test_command": "pytest -q"})
    assert resolver(str(root), context) is None, "setup keeps eliciting after the command was supplied"
    config = load_config(str(root / CONFIG_FILENAME))
    assert config["expected_commands"]["test"] == ["pytest", "-q"], (
        "the opted-in command was not recorded for the runner to spawn"
    )
    assert config["test_execution"]["requested"] is True

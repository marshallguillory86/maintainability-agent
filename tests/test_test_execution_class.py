"""Class 5 (plan-81dc6870): the suite runs only on an explicit opt-in.

Decision 9 said the agent never executes the audited tree's code. Class 5
amends that to: never, unless the operator opted in and configured a
command. This audits the runner in isolation, before it is wired into an
audit — the load-bearing case is that the default path spawns nothing.
"""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

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


def test_a_committed_coverage_artifact_is_not_scored(tmp_path: Path) -> None:
    """The provenance falsifier: a coverage.xml the tree carried, and the
    suite did not touch, must not score `test_effectiveness` — otherwise a
    repository could set its own coverage by committing the file."""
    (tmp_path / "coverage.xml").write_text(
        '<coverage line-rate="0.99"/>', encoding="utf-8")
    command = _fake_suite(tmp_path, 0)  # passes, does NOT write coverage.xml
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["ran"] is True
    assert result["coverage_percent"] is None, (
        "a pre-existing coverage.xml this run did not produce was scored"
    )


def test_a_suite_that_refreshes_coverage_is_scored(tmp_path: Path) -> None:
    """The complement: when the suite overwrites even a pre-existing
    artifact, that is this run's output and is read normally."""
    (tmp_path / "coverage.xml").write_text(
        '<coverage line-rate="0.10"/>', encoding="utf-8")
    command = _fake_suite(tmp_path, 0, coverage_line_rate="0.88")
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["coverage_percent"] == 88.0, (
        "the suite's own fresh coverage.xml should be read"
    )


def test_a_symlinked_coverage_artifact_is_refused(tmp_path: Path) -> None:
    """Posture parity with `_safe_write`: a coverage.xml the tree points
    elsewhere by symlink is not followed."""
    real = tmp_path / "real_coverage.xml"
    real.write_text('<coverage line-rate="0.95"/>', encoding="utf-8")
    command = _fake_suite(tmp_path, 0)  # writes no coverage.xml of its own
    (tmp_path / "coverage.xml").symlink_to(real)
    result = run_test_suite(tmp_path, _opted_in(command))
    assert result["coverage_percent"] is None, "a symlinked coverage.xml was followed"


def test_opted_in_coverage_scores_test_effectiveness_and_moves_testability(tmp_path: Path) -> None:
    """The scored-coverage path, end to end through `score_report`.

    Without a suite run the aspect is NotApplicable (None); with a coverage
    reading it scores `coverage / 20` and is no longer excluded, so more
    coverage lifts testability. Guards the one genuinely new *scored* path
    Class 5 added, which extraction-only tests never exercise.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report
    from maintainability_audit.scoring import score_report

    root = _git_repo(tmp_path)
    # A test file, so the tree is not "untested" — otherwise testability is
    # capped at 2.0 and the coverage contribution cannot be observed.
    (root / "test_app.py").write_text(
        "from app import ok\n\n\ndef test_ok():\n    assert ok() == 1\n", encoding="utf-8")
    report = build_report(root, load_config(None))
    assert score_report(report)["aspects"]["test_effectiveness"] is None

    def scored(coverage: float) -> dict:
        report["test_suite"] = {
            "command": ["pytest"], "ran": True, "exit_code": 0,
            "passed": True, "detail": "", "coverage_percent": coverage,
        }
        return score_report(report)

    low, high = scored(10.0), scored(90.0)
    assert low["aspects"]["test_effectiveness"] == 0.5   # 10 / 20
    assert high["aspects"]["test_effectiveness"] == 4.5  # 90 / 20
    assert high["categories"]["testability"] > low["categories"]["testability"], (
        "coverage is scored but does not move the testability category"
    )


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


def test_the_cli_stage_two_records_the_test_command(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The CLI half of the Class 5 second stage (`maybe_prompt_test_command`).

    Mirrors the MCP staged ask: an opted-in config with no command prompts
    for one and shlex-splits it into `expected_commands.test`; a blank
    answer cancels the opt-in rather than looping forever. Previously
    untested, so a regression here was invisible.
    """
    from maintainability_audit import _first_run
    from maintainability_audit._mcp_setup import CONFIG_FILENAME

    root = _git_repo(tmp_path)
    monkeypatch.setattr(_first_run, "_stdin_is_a_tty", lambda: True)

    def run_stage(answer: str) -> dict:
        (root / CONFIG_FILENAME).write_text(
            json.dumps({"test_execution": {"requested": True}}), encoding="utf-8")
        monkeypatch.setattr("builtins.input", lambda *_: answer)
        _first_run.maybe_prompt_test_command(root, {"test_execution": {"requested": True}})
        return json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))

    recorded = run_stage("pytest -q")
    assert recorded["expected_commands"]["test"] == ["pytest", "-q"]

    cancelled = run_stage("   ")
    assert cancelled["test_execution"]["requested"] is False, "a blank answer did not cancel"
    assert "test" not in (cancelled.get("expected_commands") or {})

"""Consent to run the suite, with no command, must name a way out (D185).

`test_execution.requested` true with no `expected_commands.test` in the user
tier is a reachable state: setup recorded the answer without recording the
program. In that state no suite runs on any audit.

Neither surface said what to do about it. The report explained the refusal and
stopped there, and the MCP gate treats a present `test_execution` key as
asked-and-answered, so `run_tests_pending` is false and no discovery line is
offered. A person who opted in got silence on every door, which is how this
repository's own audit reported "it did not run" for weeks.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit import _mcp_gate, _test_execution


@pytest.fixture
def consented(monkeypatch):
    """User tier that opted in and carries no command."""
    monkeypatch.setattr(
        _test_execution, "user_config_answers",
        lambda: {"test_execution": {"requested": True}})
    return None


def test_the_report_detail_names_a_remedy(consented, tmp_path):
    """The operator is told how to fix it, not only why it happened."""
    result = _test_execution.run_test_suite(
        tmp_path,
        {"test_execution": {"requested": True},
         "expected_commands": {"test": ["pytest", "-q"]}})

    assert result is not None and result["ran"] is False
    detail = result["detail"].lower()
    assert "reconfigure" in detail or "expected_commands" in detail, (
        f"the refusal names no remedy: {result['detail']!r}")


def test_the_predicate_sees_consent_without_a_command(consented):
    """`run_tests_pending` cannot see this state; this is what does."""
    assert _test_execution.consented_without_command() is True


def test_a_recorded_command_is_not_reported_as_missing(monkeypatch):
    """The predicate is about the gap, not about opting in."""
    monkeypatch.setattr(
        _test_execution, "user_config_answers",
        lambda: {"test_execution": {"requested": True},
                 "expected_commands": {"test": ["pytest", "-q"]}})
    assert _test_execution.consented_without_command() is False


def test_the_mcp_gate_offers_reconfigure_for_the_gap(consented, monkeypatch, tmp_path):
    """The chat door surfaces it too, where `run_tests_pending` is false."""
    monkeypatch.setattr(_mcp_gate, "run_tests_pending", lambda root: False)

    result = _mcp_gate._choose_next(Path(tmp_path))

    prompt = (result.get("choice_needed") or {}).get("prompt", "").lower()
    assert "no test command is recorded" in prompt, (
        f"the gate says nothing about the gap: {prompt!r}")

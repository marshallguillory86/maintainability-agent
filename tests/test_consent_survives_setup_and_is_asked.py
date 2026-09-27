"""Per-repository consent survives setup, and each repository is asked for its own.

Decision 9 (amended 2026-08-31): the suite runs only the command the
person named, only because they opted in, and *only for this repository*.
D214 recorded consent per repository and an audit found it broken twice:

- **Any full setup erased it.** `_persist_answers` wrote the person's tier
  from the setup payload, whose `test_execution` holds only `requested`,
  so setting up one repository wiped every other repository's consent.
- **The remedy could not be reached.** The report said "reconfigure", but
  whether the command is asked was read from the repository's config,
  which already carried a command, so reconfigure never asked it.

And Decision 4 (2026-09-27): the person's answers carry to a new
repository, which is asked only what is its own — its test command. One
rule for both doors: `test_command_pending`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maintainability_audit import _first_run
from maintainability_audit._mcp_setup import (
    apply_answers,
    setup_pending,
    staged_questions,
)
from maintainability_audit._mcp_setup import test_command_pending as command_pending
from maintainability_audit._setup_persist import _apply_command
from maintainability_audit._test_execution import opted_in_command
from maintainability_audit._user_config import user_config_answers, write_user_answers

FULL = {"run_pool": "no", "depth": "moderate", "license_policy": "permissive",
        "economics": "skip", "run_tests": "yes", "default_format": "chat",
        "record_scan_history": "no"}


def _repo(tmp_path: Path, name: str) -> Path:
    root = tmp_path / name
    root.mkdir()
    return root


def test_setting_up_another_repository_keeps_this_ones_consent(tmp_path) -> None:
    first, second = _repo(tmp_path, "first"), _repo(tmp_path, "second")
    apply_answers(first, FULL)
    _apply_command(first, {"test_command": "pytest -q"})

    apply_answers(second, FULL)

    assert opted_in_command(first) == ["pytest", "-q"]


def test_a_repository_configured_before_consent_was_keyed_is_asked_its_command(tmp_path) -> None:
    """The migration path the report names has to actually ask."""
    root = _repo(tmp_path, "old")
    (root / "maintainability-agent.json").write_text(json.dumps({
        "version": 1, "test_execution": {"requested": True},
        "expected_commands": {"test": ["pytest", "-q"]},
    }), encoding="utf-8")
    write_user_answers({"test_execution": {"requested": True},
                        "expected_commands": {"test": ["pytest", "-q"]}})

    assert command_pending(root) is True
    assert [q["name"] for q in staged_questions(root)] == ["test_command"]


def test_a_new_repository_is_asked_only_its_own_test_command(tmp_path) -> None:
    """Decision 4: the person's answers carry; the test command does not."""
    first, new = _repo(tmp_path, "first"), _repo(tmp_path, "new")
    apply_answers(first, FULL)
    _apply_command(first, {"test_command": "pytest -q"})

    assert setup_pending(new) is True
    assert [q["name"] for q in staged_questions(new)] == ["test_command"]


def test_a_person_who_declined_the_suite_is_not_asked_for_a_command(tmp_path) -> None:
    first, new = _repo(tmp_path, "first"), _repo(tmp_path, "new")
    apply_answers(first, {**FULL, "run_tests": "no"})

    assert setup_pending(new) is False
    assert command_pending(new) is False


def test_answering_the_new_repositorys_command_records_it_for_that_repository(tmp_path) -> None:
    first, new = _repo(tmp_path, "first"), _repo(tmp_path, "new")
    apply_answers(first, FULL)
    _apply_command(first, {"test_command": "pytest -q"})

    apply_answers(new, {"test_command": "npm test"})

    assert opted_in_command(new) == ["npm", "test"]
    assert opted_in_command(first) == ["pytest", "-q"]
    assert setup_pending(new) is False


@pytest.fixture
def terminal(monkeypatch):
    monkeypatch.setattr(_first_run, "_stdin_is_a_tty", lambda: True)
    asked: list[str] = []
    return asked


def test_the_terminal_does_not_rerun_setup_when_the_persons_answers_exist(
        tmp_path, terminal, monkeypatch) -> None:
    """first-run.md: setup is asked when both tiers are absent, on every door."""
    first, new = _repo(tmp_path, "first"), _repo(tmp_path, "new")
    apply_answers(first, FULL)
    monkeypatch.setattr("builtins.input", lambda prompt="": terminal.append(prompt) or "")

    _first_run.maybe_prompt_first_run(new, None)

    assert terminal == []


def test_the_terminal_asks_and_records_this_repositorys_command(
        tmp_path, terminal, monkeypatch) -> None:
    first, new = _repo(tmp_path, "first"), _repo(tmp_path, "new")
    apply_answers(first, FULL)
    _apply_command(first, {"test_command": "pytest -q"})
    monkeypatch.setattr(_first_run, "_input_with_default",
                        lambda prompt, default: terminal.append(prompt) or "make test")

    _first_run.maybe_prompt_test_command(new, {"test_execution": {"requested": True}})

    assert len(terminal) == 1
    assert opted_in_command(new) == ["make", "test"]
    assert opted_in_command(first) == ["pytest", "-q"]
    assert user_config_answers() is not None

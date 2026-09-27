"""Consent to run a test command is given for one repository, not for every one.

Found auditing Scrollwork: the audit ran this project's own suite —
`pytest -n auto --cov=maintainability_audit …` — against a JavaScript
and Python tree it has nothing to do with, because the person's tier
held a single `expected_commands.test`. Consent given while setting up
one repository was consent for every repository audited afterwards, and
it ran a program chosen for somewhere else.

The person still decides what this host runs (D147); the decision is now
recorded against the repository it was made for. A repository with no
consent of its own runs nothing and says why, and a consent recorded
before this existed — unkeyed — is not guessed at.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from maintainability_audit import _setup_persist, _test_execution

OPTED_IN = {"test_execution": {"requested": True},
            "expected_commands": {"test": ["pytest", "-q"]}}


@pytest.fixture
def user_tier(monkeypatch) -> dict[str, Any]:
    """An in-memory person's tier, read and written by every consumer."""
    tier: dict[str, Any] = {"test_execution": {"requested": True}}

    def write(payload: dict[str, Any]) -> None:
        tier.clear()
        tier.update(payload)

    for module in (_test_execution, _setup_persist):
        monkeypatch.setattr(module, "user_config_answers", lambda: dict(tier))
    monkeypatch.setattr(_setup_persist, "write_user_answers", write)
    return tier


def _consent(root: Path, command: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _setup_persist._apply_command(root, {"test_command": command})


def test_consent_given_in_one_repository_runs_only_there(user_tier, tmp_path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    _consent(first, "pytest -q")
    second.mkdir()

    assert _test_execution.opted_in_command(first) == ["pytest", "-q"]
    assert _test_execution.opted_in_command(second) == []


def test_another_repository_is_told_the_consent_was_not_its_own(user_tier, tmp_path, monkeypatch) -> None:
    """The closing test the defect asked for: nothing is spawned."""
    first, second = tmp_path / "first", tmp_path / "second"
    _consent(first, "pytest -q")
    second.mkdir()
    spawned: list[Any] = []
    monkeypatch.setattr(_test_execution, "run", lambda *a, **k: spawned.append(a))

    result = _test_execution.run_test_suite(second, OPTED_IN)

    assert spawned == []
    assert result is not None and result["ran"] is False
    assert "another repository" in result["detail"]
    assert "reconfigure" in result["detail"].lower()


def test_an_unkeyed_consent_from_before_is_not_run_anywhere(user_tier, tmp_path) -> None:
    """Which repository it was given for is unknowable, so it is not guessed."""
    user_tier["expected_commands"] = {"test": ["pytest", "-q"]}

    result = _test_execution.run_test_suite(tmp_path, OPTED_IN)

    assert _test_execution.opted_in_command(tmp_path) == []
    assert result is not None and result["ran"] is False
    assert "per repository" in result["detail"]


def test_declining_in_one_repository_leaves_the_others_consent(user_tier, tmp_path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    _consent(first, "pytest -q")
    _consent(second, "")

    assert _test_execution.opted_in_command(first) == ["pytest", "-q"]
    assert _test_execution.opted_in_command(second) == []
    assert user_tier["test_execution"]["requested"] is True, (
        "a decline in one repository switched the person's opt-in off everywhere"
    )
    assert _test_execution.consented_without_command(second) is False, (
        "a decline is an answer; the gate must not ask again for it"
    )


def test_a_repository_never_asked_is_reported_as_missing_its_command(user_tier, tmp_path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    _consent(first, "pytest -q")
    second.mkdir()

    assert _test_execution.consented_without_command(second) is True
    assert _test_execution.consented_without_command(first) is False


def test_the_same_repository_by_another_spelling_is_the_same_repository(user_tier, tmp_path) -> None:
    root = tmp_path / "repo"
    _consent(root, "pytest -q")

    assert _test_execution.opted_in_command(root / "." / ".." / "repo") == ["pytest", "-q"]


def test_the_refusal_names_no_other_repository(user_tier, tmp_path) -> None:
    """A report is about one repository and may be shared.

    Naming the other repository's absolute path put an unrelated checkout —
    possibly one belonging to another organisation — into this report.
    """
    first, second = tmp_path / "first-private-client", tmp_path / "second"
    _consent(first, "pytest -q")
    second.mkdir()

    result = _test_execution.run_test_suite(second, OPTED_IN)

    assert "first-private-client" not in result["detail"]
    assert str(tmp_path) not in result["detail"]
    assert "another repository" in result["detail"]

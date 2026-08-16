"""D13: XDG user configuration and state precede repository first-run asks."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

from maintainability_audit._user_config import (
    load_user_config,
    mark_repo_seen,
    repo_first_run,
    user_config_path,
    user_state_path,
)
from maintainability_audit.cli import main
from maintainability_audit.config import load_config


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-qm", "fixture",
        ],
        check=True,
    )
    return root


def test_user_paths_honor_xdg_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    config_home = tmp_path / "config-home"
    state_home = tmp_path / "state-home"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_home))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_home))

    assert user_config_path() == config_home / "maintainability-agent" / "config.json"
    assert user_state_path() == state_home / "maintainability-agent" / "state.json"


def test_user_paths_fall_back_under_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = tmp_path / "home"
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    monkeypatch.delenv("XDG_STATE_HOME", raising=False)
    monkeypatch.setenv("HOME", str(home))

    assert user_config_path() == home / ".config" / "maintainability-agent" / "config.json"
    assert user_state_path() == home / ".local" / "state" / "maintainability-agent" / "state.json"


def test_user_and_repository_config_merge_in_precedence_order(tmp_path: Path) -> None:
    user = {
        "version": 1,
        "thresholds": {"max_file_lines": 700, "max_function_lines": 70},
        "analyzers": {"allow_tools": ["ruff"]},
        "instruction_pack": {"strictness": "user"},
    }
    repository = {
        "version": 1,
        "thresholds": {"max_file_lines": 300},
        "analyzers": {"deny_tools": ["ruff"]},
        "instruction_pack": {"strictness": "repository"},
    }
    _write_json(user_config_path(), user)
    repository_path = _write_json(tmp_path / "maintainability-agent.json", repository)

    loaded = load_config(str(repository_path))

    assert load_user_config() == user
    assert loaded["thresholds"]["max_file_lines"] == 300
    assert loaded["thresholds"]["max_function_lines"] == 70
    assert loaded["thresholds"]["warn_file_lines"] == 400
    assert loaded["analyzers"]["allow_tools"] == ["ruff"]
    assert loaded["analyzers"]["deny_tools"] == ["ruff"]
    assert loaded["instruction_pack"]["strictness"] == "repository"


@pytest.mark.parametrize(
    ("user", "repository", "expected"),
    (
        ({"version": 1}, None, True),
        ({"version": 1, "analyzers": {"run": False}}, None, False),
        (None, {"version": 1}, True),
        (
            {"version": 1, "analyzers": {"run": False}},
            {"version": 1, "analyzers": {"run": True}},
            True,
        ),
        (
            {"version": 1, "analyzers": {"run": True}},
            {"version": 1, "analyzers": {"run": False}},
            False,
        ),
    ),
)
def test_any_loaded_config_tier_defaults_the_pool_on_and_explicit_false_wins(
    tmp_path: Path,
    user: dict | None,
    repository: dict | None,
    expected: bool,
) -> None:
    if user is not None:
        _write_json(user_config_path(), user)
    repository_path = (
        _write_json(tmp_path / "maintainability-agent.json", repository)
        if repository is not None
        else None
    )

    loaded = load_config(str(repository_path) if repository_path else None)

    assert loaded["analyzers"]["run"] is expected


def test_no_loaded_config_keeps_programmatic_callers_on_builtins() -> None:
    assert load_user_config() is None
    assert load_config(None)["analyzers"]["run"] is False


def test_corrupt_user_config_reads_as_absent() -> None:
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{not-json", encoding="utf-8")

    assert load_user_config() is None
    assert load_config(None)["analyzers"]["run"] is False


def test_unreadable_user_config_reads_as_absent(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = _write_json(user_config_path(), {"version": 1})
    original = Path.read_text

    def unreadable(candidate: Path, *args, **kwargs):
        if candidate == path:
            raise PermissionError("fixture denies this file")
        return original(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", unreadable)

    assert load_user_config() is None
    assert load_config(None)["analyzers"]["run"] is False


def test_seen_state_round_trips_with_an_absolute_root_and_iso_date(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    another = tmp_path / "another"
    another.mkdir()

    assert repo_first_run(root) is True
    mark_repo_seen(root)

    assert repo_first_run(root) is False
    assert repo_first_run(another) is True
    state = json.loads(user_state_path().read_text(encoding="utf-8"))
    assert set(state) == {"seen"}
    assert set(state["seen"]) == {str(root.resolve())}
    date.fromisoformat(state["seen"][str(root.resolve())][:10])


def test_corrupt_seen_state_is_absent_and_can_be_replaced(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    root.mkdir()
    path = user_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not-json", encoding="utf-8")

    assert repo_first_run(root) is True
    mark_repo_seen(root)
    assert repo_first_run(root) is False


def test_successful_cli_audit_marks_the_repository_seen(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    output = tmp_path / "report.json"
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    assert repo_first_run(root) is True

    code = main([
        "--root", str(root), "--no-analyzers", "--format", "json",
        "--output", str(output),
    ])

    assert code == 0
    assert output.is_file()
    assert repo_first_run(root) is False

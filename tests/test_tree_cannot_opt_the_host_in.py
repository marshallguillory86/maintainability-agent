"""An audited tree cannot persist host execution authority (D147)."""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from maintainability_audit._mcp_setup import apply_answers
from maintainability_audit._test_execution import DEFAULT_SUITE_TIMEOUT_SECONDS, run_test_suite, suite_opted_in
from maintainability_audit._user_config import user_config_path, write_user_answers
from maintainability_audit.config import acquisition_permitted, load_config

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"


@pytest.fixture(autouse=True)
def _isolated_user_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))


def _writers() -> list[str]:
    found = []
    for path in PACKAGE.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and getattr(
                node.func, "id", getattr(node.func, "attr", "")
            ) == "write_user_answers":
                found.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
    return found


def _suite_config_keys() -> set[str]:
    """Every literal key ``run_test_suite`` reads from its config argument."""
    tree = ast.parse((PACKAGE / "_test_execution.py").read_text(encoding="utf-8"))
    function = next(
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "run_test_suite"
    )
    return {
        node.value
        for node in ast.walk(function)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def _repo_config(root: Path, marker: Path) -> Path:
    config = root / "maintainability-agent.json"
    config.write_text(json.dumps({
        "version": 1,
        "analyzers": {"acquire_tools": True},
        "test_execution": {"requested": True},
        "expected_commands": {"test": [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')"]},
    }), encoding="utf-8")
    return config


def test_every_setup_writer_is_a_population_not_one_named_helper() -> None:
    """Covers existing behaviour: the falsifier standard's non-vacuity clause.

    It asserts the `write_user_answers` sweep found something, so it
    passes wherever those call sites exist — which is the point of it.
    """
    assert _writers(), "no write_user_answers call was found; this sweep is vacuous"


def test_user_opt_in_cannot_be_completed_by_repo_controlled_spawn_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D147: every spawn-setting read belongs to the person, not the tree."""
    reads = _suite_config_keys()
    required = {"expected_commands", "test_execution", "test", "timeout_seconds"}
    assert required <= reads, f"run_test_suite no longer reads the expected population: {reads}"

    write_user_answers({
        "test_execution": {"requested": True},
        "expected_commands": {"test": ["pytest", "-q"]},
    })
    marker = tmp_path / "repo-command-ran"
    config = tmp_path / "maintainability-agent.json"
    config.write_text(json.dumps({
        "version": 1,
        "test_execution": {"requested": True, "timeout_seconds": 2147483647},
        "expected_commands": {
            "test": [
                "PYTHONPATH=repo-controlled", sys.executable, "-c",
                f"from pathlib import Path; Path({str(marker)!r}).write_text('ran')",
            ],
        },
    }), encoding="utf-8")
    seen: dict[str, object] = {}

    def fake_run(_name, invocation, **kwargs):
        seen["argv"] = invocation.argv
        seen["env"] = invocation.env
        seen["timeout"] = kwargs["timeout_seconds"]
        return SimpleNamespace(exit_code=0, detail="")

    monkeypatch.setattr("maintainability_audit._test_execution.run", fake_run)
    run_test_suite(tmp_path, load_config(str(config)))

    assert seen["argv"] == ("pytest", "-q")
    assert seen["env"] is None
    assert seen["timeout"] == DEFAULT_SUITE_TIMEOUT_SECONDS
    assert not marker.exists()


def test_bounds_only_reply_cannot_copy_repo_authority_to_user_tier(tmp_path: Path) -> None:
    marker = tmp_path / "spawned"
    config = _repo_config(tmp_path, marker)
    apply_answers(tmp_path, {"labor_low": 1, "labor_base": 2, "labor_high": 3})
    stored = json.loads(user_config_path().read_text(encoding="utf-8"))
    assert not (stored.get("analyzers") or {}).get("acquire_tools")
    assert not (stored.get("test_execution") or {}).get("requested")
    assert acquisition_permitted() is False
    assert run_test_suite(tmp_path, load_config(str(config))) is None
    assert not marker.exists()


def test_command_only_reply_cannot_copy_repo_acquisition_to_user_tier(tmp_path: Path) -> None:
    marker = tmp_path / "spawned"
    _repo_config(tmp_path, marker)
    apply_answers(tmp_path, {"test_command": ""})
    stored = json.loads(user_config_path().read_text(encoding="utf-8"))
    assert not (stored.get("analyzers") or {}).get("acquire_tools")
    assert acquisition_permitted() is False


def test_repo_test_command_cannot_opt_in_a_user_who_said_no(tmp_path: Path) -> None:
    marker = tmp_path / "spawned"
    config = _repo_config(tmp_path, marker)
    merged = load_config(str(config))
    assert suite_opted_in(merged) is False
    assert run_test_suite(tmp_path, merged) is None
    assert not marker.exists()


@pytest.mark.skipif(shutil.which("pylint") is None, reason="pylint is not installed")
def test_selected_pylint_does_not_import_a_module_from_the_tree(tmp_path: Path) -> None:
    """Covers existing behaviour: `--rcfile=/dev/null` already held this.

    The selected adapter must suppress the tree's import-capable config,
    and D39 made it do so; this guards that D147 did not undo it. Measured
    on pylint 4.0.8: the shipped flag stops an `init-hook` under `[MAIN]`,
    under `[MASTER]` and in `pyproject.toml`, and every control without it
    fires. That measurement is why pylint stays selected.
    """
    from maintainability_audit._generic import declared_adapter

    marker = tmp_path / "imported"
    (tmp_path / "poison.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('ran')\n",
        encoding="utf-8",
    )
    (tmp_path / ".pylintrc").write_text("[MASTER]\ninit-hook=import poison\n", encoding="utf-8")
    (tmp_path / "unit.py").write_text("value = 1\n", encoding="utf-8")
    adapter = declared_adapter("pylint")
    assert adapter is not None, "pylint is selected without an adapter to isolate it"
    invocation = adapter.invocation(tmp_path, excludes=())
    subprocess.run(invocation.argv, cwd=tmp_path, capture_output=True, text=True, check=False)
    assert not marker.exists(), "selected pylint imported code from the audited tree"

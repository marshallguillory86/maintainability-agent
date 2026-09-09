"""An audited tree cannot persist host execution authority (D147)."""
from __future__ import annotations

import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit._mcp_setup import apply_answers
from maintainability_audit._test_execution import run_test_suite, suite_opted_in
from maintainability_audit._user_config import user_config_path
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
            if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "write_user_answers":
                found.append(f"{path.relative_to(PACKAGE)}:{node.lineno}")
    return found


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
    assert _writers(), "no write_user_answers call was found; this sweep is vacuous"


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
    """The selected adapter must suppress the tree's import-capable config."""
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

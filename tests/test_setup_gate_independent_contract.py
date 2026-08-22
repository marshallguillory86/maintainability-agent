"""Independent D26/D27/D30 contract, derived without the existing gate tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit._mcp_setup import SetupRequired, setup_questions
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.mcp_server import _report_markdown, audit_repository

NO_AUDIT_KEYS = {
    "analyzers_run",
    "gate_passed",
    "remediation_prompt",
    "report",
    "report_html",
    "report_json",
    "report_markdown",
    "score",
}


@pytest.fixture(autouse=True)
def isolated_user_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))


def _repository(base: Path, config: dict[str, Any] | None = None) -> Path:
    root = base / "repository"
    root.mkdir()
    (root / "README.md").write_text("# gate fixture\n", encoding="utf-8")
    (root / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    if config is not None:
        (root / CONFIG_FILENAME).write_text(json.dumps(config) + "\n", encoding="utf-8")
    return root


def _configured(base: Path) -> Path:
    return _repository(
        base,
        {
            "version": 1,
            "analyzers": {"run": False},
            "history": {"record": False},
        },
    )


def _call(root: Path, *, action: str | None, config_path: str | None = None) -> dict[str, Any]:
    return audit_repository(
        str(root),
        config_path=config_path,
        action=action,
        run_analyzers=False,
        record_history=False,
        roots=(root.parent.resolve(),),
    )


def _assert_not_an_audit(result: dict[str, Any]) -> None:
    assert result["audit_ran"] is False
    assert NO_AUDIT_KEYS.isdisjoint(result), result


def test_setup_precondition_outranks_an_explicit_run(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    result = _call(root, action="run")

    _assert_not_an_audit(result)
    assert result["setup_needed"]["questions"]
    assert "choice_needed" not in result


def test_an_empty_config_file_is_not_an_answer(tmp_path: Path) -> None:
    root = _repository(tmp_path, {})

    result = _call(root, action=None)

    _assert_not_an_audit(result)
    assert "setup_needed" in result


@pytest.mark.parametrize("action", [None, "", "yes", "RUN", "unknown"])
def test_only_the_exact_run_action_can_audit(
    tmp_path: Path,
    action: str | None,
) -> None:
    root = _configured(tmp_path)

    result = _call(root, action=action)

    _assert_not_an_audit(result)
    assert result["choice_needed"]["options"] == ["run", "reconfigure"]
    assert "setup_needed" not in result


def test_reconfigure_reopens_the_complete_form_without_mutating_answers(
    tmp_path: Path,
) -> None:
    root = _configured(tmp_path)
    config_path = root / CONFIG_FILENAME
    before = config_path.read_bytes()
    expected = setup_questions(load_config(None))

    result = _call(root, action="reconfigure")

    _assert_not_an_audit(result)
    assert result["setup_needed"]["questions"] == expected
    assert "choice_needed" not in result
    assert config_path.read_bytes() == before


def test_a_configured_run_is_explicitly_an_audit(tmp_path: Path) -> None:
    root = _configured(tmp_path)

    result = _call(root, action="run")

    assert result["audit_ran"] is True
    assert "setup_needed" not in result
    assert "choice_needed" not in result
    assert "report_markdown" in result


def test_an_explicit_config_path_supplies_the_missing_answer(tmp_path: Path) -> None:
    root = _repository(tmp_path)
    supplied = root / "explicit.json"
    supplied.write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}) + "\n",
        encoding="utf-8",
    )

    result = _call(root, action=None, config_path=str(supplied))

    assert result["audit_ran"] is True
    assert "setup_needed" not in result
    assert "choice_needed" not in result


def test_report_resource_refuses_to_create_a_first_report(tmp_path: Path) -> None:
    root = _repository(tmp_path)

    with pytest.raises(SetupRequired, match="Call the audit_repository tool"):
        _report_markdown(str(root), (root.parent.resolve(),))

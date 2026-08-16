"""D1: a configured repository runs its analyzer pool without a flag."""

from __future__ import annotations

import copy
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import maintainability_audit.cli as cli_module
import maintainability_audit.mcp_server as mcp_module
from maintainability_audit._catalog import settings_from
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report as production_build_report

ROOT = Path(__file__).resolve().parents[1]


def _repo(tmp_path: Path, config: dict | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    if config is not None:
        (root / "maintainability-agent.json").write_text(
            json.dumps(config), encoding="utf-8",
        )
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


def _write_config(path: Path, payload: dict) -> Path:
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _report_without_analyzers(root: Path) -> dict:
    return production_build_report(root, load_config(None), run_analyzers=False)


def _cli_run_value(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *flags: str,
) -> bool:
    observed: list[bool] = []
    report = _report_without_analyzers(root)

    def capture(*args, **kwargs):
        observed.append(kwargs["run_analyzers"])
        return copy.deepcopy(report)

    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(cli_module, "build_report", capture)
    output = root.parent / "report.json"
    assert cli_module.main([
        "--root", str(root), "--format", "json", "--output", str(output), *flags,
    ]) == 0
    assert len(observed) == 1
    return observed[0]


def _mcp_run_value(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    override: bool | None,
    *,
    omit: bool = False,
) -> tuple[bool, bool]:
    observed: list[bool] = []
    report = _report_without_analyzers(root)

    def capture(*args, **kwargs):
        observed.append(kwargs["run_analyzers"])
        return copy.deepcopy(report)

    monkeypatch.setattr(mcp_module, "build_report", capture)
    kwargs = {"roots": (root.parent.resolve(),)}
    if not omit:
        kwargs["run_analyzers"] = override
    result = mcp_module.audit_repository(str(root), **kwargs)
    assert len(observed) == 1
    return observed[0], result["analyzers_run"]


def test_a_loaded_config_file_defaults_run_true_but_builtins_do_not(
    tmp_path: Path,
) -> None:
    builtins = load_config(None)
    implicit = load_config(str(_write_config(tmp_path / "implicit.json", {"version": 1})))
    disabled = load_config(str(_write_config(
        tmp_path / "disabled.json",
        {"version": 1, "analyzers": {"run": False}},
    )))

    assert builtins["analyzers"]["run"] is False
    assert implicit["analyzers"]["run"] is True
    assert disabled["analyzers"]["run"] is False
    assert settings_from(builtins)["acquire_tools"] is False
    assert settings_from(implicit)["acquire_tools"] is False


def test_a_configured_repository_runs_its_pool_without_a_flag(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path, {"version": 1})

    assert _cli_run_value(root, monkeypatch) is True


@pytest.mark.parametrize(
    ("config", "flags", "expected"),
    (
        ({"version": 1, "analyzers": {"run": False}}, ("--analyzers",), True),
        ({"version": 1}, ("--no-analyzers",), False),
        ({"version": 1, "analyzers": {"run": False}}, (), False),
    ),
)
def test_cli_flags_override_config_in_both_directions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: dict,
    flags: tuple[str, ...],
    expected: bool,
) -> None:
    root = _repo(tmp_path, config)

    assert _cli_run_value(root, monkeypatch, *flags) is expected


@pytest.mark.parametrize(
    ("config", "override", "omit", "expected"),
    (
        (None, None, True, False),
        ({"version": 1}, None, True, True),
        ({"version": 1}, None, False, True),
        ({"version": 1, "analyzers": {"run": False}}, None, True, False),
        ({"version": 1, "analyzers": {"run": False}}, True, False, True),
        ({"version": 1, "analyzers": {"run": True}}, False, False, False),
    ),
)
def test_mcp_run_analyzers_is_tristate_and_config_aware(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    config: dict | None,
    override: bool | None,
    omit: bool,
    expected: bool,
) -> None:
    root = _repo(tmp_path, config)

    observed, published = _mcp_run_value(
        root, monkeypatch, override, omit=omit,
    )

    assert observed is expected
    assert published is expected


def test_mcp_run_analyzers_defaults_to_config_decision() -> None:
    assert inspect.signature(mcp_module.audit_repository).parameters[
        "run_analyzers"
    ].default is None


def test_this_repository_opts_into_its_analyzer_pool() -> None:
    configured = json.loads(
        (ROOT / "maintainability-agent.json").read_text(encoding="utf-8"),
    )

    assert configured["analyzers"]["run"] is True
    assert settings_from(configured)["acquire_tools"] is False

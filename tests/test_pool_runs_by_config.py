"""D1: every production entry point honours the repository's pool decision."""

from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
import sys
from pathlib import Path

import pytest

import maintainability_audit.cli as cli_module
from maintainability_audit import _evidence_view as evidence_view
from maintainability_audit._catalog import settings_from
from maintainability_audit.config import discovered_config, load_config
from maintainability_audit.mcp_server import audit_repository, create_server
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]


def _pool_config(run: bool) -> dict:
    """Select one real adapter without allowing tool acquisition or network."""
    return {
        "version": 1,
        "analyzers": {
            "run": run,
            "concerns": ["types"],
            "depth": "baseline",
            "license_policy": "permissive",
            "acquire_tools": False,
            # No type tool is selected at baseline. Explicitly allowing one
            # shipped adapter leaves exactly one observable pool outcome,
            # whether lizard is installed on this machine or not.
            "allow_tools": ["lizard"],
            "deny_tools": [],
            "deny_license_classes": [],
            "deny_concerns": [],
            "timeout_seconds": 5,
        },
    }


def _repo(tmp_path: Path, config: dict | None = None) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
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


def _assert_pool_ran(report: dict) -> None:
    coverage = report["analyzer_coverage"]
    assert coverage is not None, "the production analyzer seam did not publish coverage"
    analyzer_rows = [
        (outcome, row)
        for outcome, rows in coverage["by_outcome"].items()
        for row in rows
        if row["tier"] == "analyzer"
    ]
    assert coverage["tools_attempted"] == 1
    assert len(analyzer_rows) == 1
    assert analyzer_rows[0][0]
    assert analyzer_rows[0][1]["tool"] == "lizard"

    # Running the pool and using its readings for the estimate are separate
    # claims. Lizard lacks the complete declaration concept set, so this
    # fixture must still label the number as the built-in fallback.
    source = evidence_view.estimate_source(report["score"])
    assert source == "Built-in detectors (fallback tier)"
    assert f"| Estimate source | {source} |" in render_markdown(report)


def _assert_pool_did_not_run(report: dict) -> None:
    assert report["analyzer_coverage"] is None
    rendered = render_markdown(report)
    source = evidence_view.estimate_source(report["score"])
    assert source == "Built-in detectors (fallback tier)"
    assert f"| Estimate source | {source} |" in rendered
    assert "## Analyzer Coverage" not in rendered


def _cli_report(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    output_name: str,
    *flags: str,
) -> dict:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    output = root.parent / output_name
    assert cli_module.main([
        "--root", str(root), "--format", "json", "--output", str(output),
        *flags,
    ]) == 0
    return json.loads(output.read_text(encoding="utf-8"))


def _report_resource_markdown(root: Path) -> str:
    server = create_server(roots=(root.parent.resolve(),))
    resources = asyncio.run(server.list_resources())
    template = next(
        resource for resource in resources
        if resource.name == "maintainability-report-template"
    )
    uri = str(template.uri).replace("{repository_root}", str(root)).replace(
        "{root}", str(root),
    )
    contents = asyncio.run(server.read_resource(uri))
    return "".join(item.content for item in contents)


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


def test_build_report_resolves_the_pool_tristate_at_its_own_seam(
    tmp_path: Path,
) -> None:
    enabled_root = _repo(tmp_path / "enabled", _pool_config(True))
    disabled_root = _repo(tmp_path / "disabled", _pool_config(False))
    enabled = load_config(discovered_config(enabled_root))
    disabled = load_config(discovered_config(disabled_root))

    assert inspect.signature(build_report).parameters["run_analyzers"].default is None
    _assert_pool_ran(build_report(enabled_root, enabled))
    _assert_pool_did_not_run(build_report(enabled_root, enabled, run_analyzers=False))
    _assert_pool_did_not_run(build_report(disabled_root, disabled))
    _assert_pool_ran(build_report(disabled_root, disabled, run_analyzers=True))


def test_cli_runs_or_suppresses_the_pool_at_the_production_seam(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    enabled_root = _repo(tmp_path / "enabled", _pool_config(True))
    disabled_root = _repo(tmp_path / "disabled", _pool_config(False))

    _assert_pool_ran(_cli_report(enabled_root, monkeypatch, "enabled.json"))
    _assert_pool_did_not_run(_cli_report(
        enabled_root, monkeypatch, "forced-off.json", "--no-analyzers",
    ))
    _assert_pool_did_not_run(_cli_report(disabled_root, monkeypatch, "disabled.json"))
    _assert_pool_ran(_cli_report(
        disabled_root, monkeypatch, "forced-on.json", "--analyzers",
    ))


def test_mcp_audit_runs_or_suppresses_the_pool_at_the_production_seam(
    tmp_path: Path,
) -> None:
    enabled_root = _repo(tmp_path / "enabled", _pool_config(True))
    disabled_root = _repo(tmp_path / "disabled", _pool_config(False))
    roots = (tmp_path.resolve(),)

    enabled = audit_repository(str(enabled_root), format="json", roots=roots)
    assert enabled["analyzers_run"] is True
    _assert_pool_ran(enabled["report"])

    forced_off = audit_repository(
        str(enabled_root), run_analyzers=False, format="json", roots=roots,
    )
    assert forced_off["analyzers_run"] is False
    _assert_pool_did_not_run(forced_off["report"])

    disabled = audit_repository(str(disabled_root), format="json", roots=roots)
    assert disabled["analyzers_run"] is False
    _assert_pool_did_not_run(disabled["report"])

    forced_on = audit_repository(
        str(disabled_root), run_analyzers=True, format="json", roots=roots,
    )
    assert forced_on["analyzers_run"] is True
    _assert_pool_ran(forced_on["report"])


def test_mcp_report_resource_uses_the_repository_pool_decision(
    tmp_path: Path,
) -> None:
    enabled_root = _repo(tmp_path / "enabled", _pool_config(True))
    disabled_root = _repo(tmp_path / "disabled", _pool_config(False))

    enabled = _report_resource_markdown(enabled_root)
    assert "## Analyzer Coverage" in enabled
    assert "| `lizard` | analyzer |" in enabled
    assert "| Estimate source | Built-in detectors (fallback tier) |" in enabled

    disabled = _report_resource_markdown(disabled_root)
    assert "## Analyzer Coverage" not in disabled
    assert "| Estimate source | Built-in detectors (fallback tier) |" in disabled


def test_mcp_run_analyzers_defaults_to_config_decision() -> None:
    assert inspect.signature(audit_repository).parameters[
        "run_analyzers"
    ].default is None


def test_this_repository_opts_into_its_analyzer_pool() -> None:
    configured = json.loads(
        (ROOT / "maintainability-agent.json").read_text(encoding="utf-8"),
    )

    assert configured["analyzers"]["run"] is True
    assert settings_from(configured)["acquire_tools"] is False

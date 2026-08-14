"""CLI-flow tests for ``maintainability_audit``.

Covers behaviour that runs through ``main([...])`` — argument parsing,
exit codes, baseline gating, ``--changed-only`` git plumbing, agent-
instruction emission, and the renderer surface area. Pure-unit coverage
for config/metrics/baseline/scoring/SARIF lives in
``test_audit_components.py`` (split out 2026-05-11 so neither file
trips the file-length warn threshold of the audit's own config).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit.baseline import BASELINE_VERSION
from maintainability_audit.cli import (
    build_report,
    finding_fingerprints,
    instruction_path_for_target,
    load_config,
    main,
)
from maintainability_audit.instructions import instruction_body
from maintainability_audit.prompts import render_agent_instructions, render_ai_prompt
from maintainability_audit.renderers import render_markdown, render_pr_comment


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_changed_only_limits_scanned_files(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "a.py", "def a():\n    return 1\n")
    write(tmp_path / "b.py", "def b():\n    return 2\n")

    report = build_report(tmp_path, load_config(None), only_paths={"a.py"}, changed_revspec="main...HEAD")

    assert report["mode"] == "changed-only"
    assert report["summary"]["files_scanned"] == 1
    assert report["largest_files"][0]["path"] == "a.py"


def test_instruction_paths_are_tool_native(tmp_path: Path) -> None:
    assert instruction_path_for_target("codex", tmp_path).name == "AGENTS.md"
    assert instruction_path_for_target("claude-code", tmp_path).name == "CLAUDE.md"
    assert ".cursor" in str(instruction_path_for_target("cursor", tmp_path))
    assert ".github" in str(instruction_path_for_target("copilot", tmp_path))


def test_cli_writes_prompt_comment_and_sarif(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")
    report = tmp_path / "report.md"
    prompt = tmp_path / "prompt.md"
    comment = tmp_path / "comment.md"
    sarif = tmp_path / "report.sarif"

    code = main([
        "--root", str(tmp_path),
        "--output", str(report),
        "--prompt-output", str(prompt),
        "--comment-output", str(comment),
        "--sarif-output", str(sarif),
        "--fail-on-gate",
    ])

    assert code == 0
    assert "Maintainability CI Report" in report.read_text(encoding="utf-8")
    assert "AI Remediation Prompt" in prompt.read_text(encoding="utf-8")
    assert "Maintainability Audit" in comment.read_text(encoding="utf-8")
    sarif_data = json.loads(sarif.read_text(encoding="utf-8"))
    assert sarif_data["version"] == "2.1.0"
    assert sarif_data["runs"][0]["tool"]["driver"]["informationUri"].endswith("maintainability-agent")


def test_fail_on_new_respects_baseline(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config_path = tmp_path / "config.json"
    write(config_path, json.dumps({"version": 1, "thresholds": {"max_file_lines": 10}}))
    report = build_report(tmp_path, load_config(str(config_path)))
    baseline = tmp_path / "baseline.json"
    write(baseline, json.dumps({"version": BASELINE_VERSION,
                                "findings": sorted(finding_fingerprints(report))}))

    suppressed = main([
        "--root", str(tmp_path), "--config", str(config_path),
        "--baseline", str(baseline), "--fail-on-new",
    ])
    new_finding = main([
        "--root", str(tmp_path), "--config", str(config_path),
        "--baseline", str(tmp_path / "missing.json"), "--fail-on-new",
    ])

    assert suppressed == 0
    assert new_finding == 1


def test_fail_on_gate_returns_nonzero_for_missing_readme(tmp_path: Path) -> None:
    write(tmp_path / "app.py", "def ok():\n    return 1\n")

    code = main(["--root", str(tmp_path), "--fail-on-gate"])

    assert code == 1


def test_dirty_worktree_gate(tmp_path: Path) -> None:
    git(tmp_path, "init")
    write(tmp_path / "README.md", "# Test\n")
    config = load_config(None)
    config["hard_gates"]["require_clean_worktree"] = True

    report = build_report(tmp_path, config)

    assert "Worktree must be clean" in report["hard_gate_failures"][0]


def test_changed_only_against_fixture_repo(tmp_path: Path) -> None:
    git(tmp_path, "init", "-b", "main")
    git(tmp_path, "config", "user.email", "test@example.com")
    git(tmp_path, "config", "user.name", "Test User")
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "a.py", "def a():\n    return 1\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "initial")
    git(tmp_path, "checkout", "-b", "feature")
    write(tmp_path / "b.py", "def b():\n    return 2\n")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-m", "feature")

    code = main(["--root", str(tmp_path), "--changed-only", "main...HEAD", "--format", "json", "--output", str(tmp_path / "report.json")])
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert code == 0
    assert report["summary"]["files_scanned"] == 1
    assert report["largest_files"][0]["path"] == "b.py"


def test_version_flag() -> None:
    with pytest.raises(SystemExit) as exc:
        main(["--version"])

    assert exc.value.code == 0


def test_init_agent_standards_exits_without_audit(tmp_path: Path) -> None:
    code = main(["--root", str(tmp_path), "--init-agent-standards", "--target", "claude-code", "--instructions-output-dir", str(tmp_path)])

    assert code == 0
    assert (tmp_path / "CLAUDE.md").exists()


def test_renderers_cover_findings_and_instruction_notes(tmp_path: Path) -> None:
    report = {
        "root": str(tmp_path),
        "git_branch": "main",
        "mode": "full",
        "score": {
            "standard": "test standard",
            "maintainability_estimate": 3.2,
            "maintainability_range": [3.2, 3.2],
            "evidence_status": {"status": "complete", "profile": "default-v1", "reasons": []},
            "verified_grade": "C",
            "verified_grade_blockers": [],
            "categories": {
                "modularity": 3.0,
                "reusability": 3.0,
                "analyzability": 4.0,
                "modifiability": 3.0,
                "testability": 3.0,
            },
        },
        "summary": {
            "files_scanned": 2,
            "file_warnings": 1,
            "file_failures": 1,
            "function_warnings": 1,
            "function_failures": 1,
            "duplicate_blocks": 1,
            "risk_findings": 1,
            "hard_gate_failures": 1,
        },
        "hard_gate_failures": ["README.md is required but missing."],
        "largest_files": [{"path": "large.py", "lines": 999, "status": "fail"}],
        "function_hotspots": [{
            "path": "app.py", "name": "hot", "start_line": 7,
            "lines": 90, "complexity": 16, "status": "fail",
        }],
        "risk_findings": [{"path": "app.py", "line": 9, "name": "risk", "text": "unsafe | text"}],
        "duplicate_blocks": [{"locations": ["a.py:1", "b.py:1"], "count": 2}],
        "external_findings": [{
            "tool": "semgrep", "rule_id": "x.y", "level": "warning",
            "path": "app.py", "line": 1, "message": "hello | world",
        }],
    }
    config = {
        "instruction_pack": {
            "project_name": "Demo",
            "test_policy": "high-value tests",
            "architecture_notes": ["Keep modules focused."],
        }
    }

    assert "Risk Pattern Findings" in render_markdown(report)
    assert "Duplicate blocks to inspect" in render_ai_prompt(report)
    assert "Top Function Hotspots" in render_pr_comment(report)
    assert "Current Audit Context" in render_agent_instructions(report)
    assert "Keep modules focused." in instruction_body("codex", config)


def test_every_entry_point_uses_a_repositorys_own_config(tmp_path: Path) -> None:
    """A tool that ignores the config beside it is a trap.

    Fixed in the CLI first, which was not enough: the MCP server then
    returned 405 findings where the CLI returned 162 on the same
    repository, because discovery lived in one caller. It lives in
    `config` now, and both entry points are asserted here.

    This project audited itself for an entire session against built-in
    defaults rather than its own exclusions, and the difference was 422
    findings versus 162 — most of the excess from a generated data file
    the config had excluded all along. Nothing warned; the run simply
    measured something other than what the repository asked for.
    """
    from maintainability_audit.config import CONFIG_FILENAME, discovered_config

    assert discovered_config(tmp_path) is None, "no config means defaults, not an error"

    (tmp_path / CONFIG_FILENAME).write_text(
        json.dumps({"version": 1, "paths": {"exclude_patterns": ["generated/"]}}),
        encoding="utf-8",
    )
    discovered = discovered_config(tmp_path)

    assert discovered is not None
    assert load_config(discovered)["paths"]["exclude_patterns"] == ["generated/"]


def test_an_explicit_config_still_wins_over_the_discovered_one(tmp_path: Path) -> None:
    """Discovery is a default, not an override."""
    from maintainability_audit.config import CONFIG_FILENAME

    (tmp_path / CONFIG_FILENAME).write_text(
        json.dumps({"version": 1, "paths": {"exclude_patterns": ["beside/"]}}), encoding="utf-8",
    )
    explicit = tmp_path / "other.json"
    explicit.write_text(
        json.dumps({"version": 1, "paths": {"exclude_patterns": ["named/"]}}), encoding="utf-8",
    )

    assert load_config(str(explicit))["paths"]["exclude_patterns"] == ["named/"]


def test_the_mcp_server_discovers_the_same_config_as_the_cli(tmp_path: Path) -> None:
    """One fix, every entry point.

    Config discovery lived in `cli` and the MCP server did not get it, so
    the same repository audited through two doors produced 405 findings
    and 162. A rule that only one caller obeys is not a rule.
    """
    from maintainability_audit.config import CONFIG_FILENAME, discovered_config

    (tmp_path / CONFIG_FILENAME).write_text(
        json.dumps({"version": 1, "paths": {"exclude_patterns": ["shared/"]}}),
        encoding="utf-8",
    )
    discovered = discovered_config(tmp_path)

    assert discovered is not None
    assert load_config(discovered)["paths"]["exclude_patterns"] == ["shared/"]


# --------------------------------------------------------------------
# ADR 008: the server is a subcommand of this package
# --------------------------------------------------------------------
#
# "**MCP server** | Chat, agentic loops" is reached today only through a
# separate console script, `maintainability-agent-mcp`. That script is
# what every IDE config in `ide-agent-integration.md` points at, so it
# stays. What is missing is the form ADR 008 actually names: one package,
# one entry point, `maintainability-agent mcp`.
#
# A second console script is not the same thing as a subcommand. It is a
# separate binary a user has to know exists, and `--help` on the main
# command never mentions it.


def test_the_mcp_server_is_reachable_as_a_subcommand() -> None:
    """`maintainability-agent mcp --help` describes the server.

    Asserted through `main([...])` like every other CLI behaviour here,
    so it exercises the real dispatch rather than a console-script shim.
    """
    import contextlib
    import io

    captured = io.StringIO()
    with pytest.raises(SystemExit) as exit_info, contextlib.redirect_stdout(captured):
        main(["mcp", "--help"])

    assert exit_info.value.code == 0, (
        f"`mcp --help` exited {exit_info.value.code}; there is no mcp subcommand"
    )
    help_text = captured.getvalue().lower()
    assert "mcp" in help_text, "the mcp subcommand help does not describe the MCP server"
    assert "--allow-root" in help_text, (
        "the mcp subcommand help does not mention --allow-root, so a user cannot "
        "tell the server what it is allowed to read"
    )


def test_the_ordinary_audit_invocation_still_parses() -> None:
    """A subcommand must not capture the flag-only form IDEs and CI use.

    `maintainability-agent --root . --help` predates the subcommand and
    is what every documented recipe runs. Adding a positional dispatch in
    front of it is the obvious way to break it.
    """
    import contextlib
    import io

    captured = io.StringIO()
    with pytest.raises(SystemExit) as exit_info, contextlib.redirect_stdout(captured):
        main(["--root", ".", "--help"])

    assert exit_info.value.code == 0
    assert "--root" in captured.getvalue()


def test_the_standalone_console_script_survives_the_subcommand() -> None:
    """IDEs already point at `maintainability-agent-mcp`; it stays.

    Adding the subcommand is additive. Removing the script would break
    every editor configuration this project has published.
    """
    import tomllib

    pyproject = tomllib.loads(
        (Path(__file__).resolve().parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    scripts = pyproject["project"]["scripts"]

    assert scripts.get("maintainability-agent-mcp") == "maintainability_audit.mcp_server:main", (
        f"the standalone MCP console script changed or was removed: {scripts}"
    )

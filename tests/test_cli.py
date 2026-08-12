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
    write(baseline, json.dumps({"version": 1, "findings": sorted(finding_fingerprints(report))}))

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

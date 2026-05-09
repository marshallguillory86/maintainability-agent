from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit.baseline import write_baseline
from maintainability_audit.cli import (
    DEFAULT_CONFIG,
    build_report,
    finding_fingerprints,
    instruction_path_for_target,
    load_baseline,
    load_config,
    main,
    read_sarif_inputs,
    report_to_sarif,
)
from maintainability_audit.metrics import duplicate_blocks, file_status, function_status, is_excluded, read_lines
from maintainability_audit.renderers import (
    instruction_body,
    render_agent_instructions,
    render_ai_prompt,
    render_markdown,
    render_pr_comment,
)
from maintainability_audit.sarif import sarif_level
from maintainability_audit.scoring import grade_from_score


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def test_config_deep_merge(tmp_path: Path) -> None:
    config_path = tmp_path / "maintainability.json"
    write(config_path, json.dumps({"version": 1, "thresholds": {"max_file_lines": 12}}))

    config = load_config(str(config_path))

    assert config["thresholds"]["max_file_lines"] == 12
    assert config["thresholds"]["warn_file_lines"] == DEFAULT_CONFIG["thresholds"]["warn_file_lines"]


def test_build_report_flags_large_file(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config = load_config(None)
    config["thresholds"]["max_file_lines"] = 10
    config["thresholds"]["warn_file_lines"] = 5

    report = build_report(tmp_path, config)

    assert report["summary"]["file_failures"] == 1
    assert any("files exceed max_file_lines" in gate for gate in report["hard_gate_failures"])


def test_changed_only_limits_scanned_files(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "a.py", "def a():\n    return 1\n")
    write(tmp_path / "b.py", "def b():\n    return 2\n")

    report = build_report(tmp_path, load_config(None), only_paths={"a.py"}, changed_revspec="main...HEAD")

    assert report["mode"] == "changed-only"
    assert report["summary"]["files_scanned"] == 1
    assert report["largest_files"][0]["path"] == "a.py"


def test_baseline_fingerprints_round_trip(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config = load_config(None)
    config["thresholds"]["max_file_lines"] = 10
    report = build_report(tmp_path, config)
    baseline = tmp_path / "baseline.json"
    write(baseline, json.dumps({"version": 1, "findings": sorted(finding_fingerprints(report))}))

    assert load_baseline(str(baseline)) == finding_fingerprints(report)


def test_baseline_helpers_cover_empty_missing_and_written_files(tmp_path: Path) -> None:
    report = {
        "root": str(tmp_path),
        "score": {"overall": 3.0},
        "largest_files": [{"path": "large.py", "status": "fail"}],
        "function_hotspots": [{"path": "app.py", "name": "hot", "start_line": 4, "status": "fail"}],
        "risk_findings": [{"path": "app.py", "line": 5, "name": "risk"}],
        "duplicate_blocks": [{"locations": ["a.py:1", "b.py:1"], "count": 2}],
    }
    baseline = tmp_path / "baseline.json"

    assert load_baseline(None) == set()
    assert load_baseline(str(tmp_path / "missing.json")) == set()

    write_baseline(str(baseline), report)
    loaded = json.loads(baseline.read_text(encoding="utf-8"))

    assert loaded["score"] == {"overall": 3.0}
    assert len(loaded["findings"]) == 4


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


def test_sarif_input_is_summarized(tmp_path: Path) -> None:
    sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "semgrep"}},
                "results": [
                    {
                        "ruleId": "rule.test",
                        "level": "warning",
                        "message": {"text": "Example finding"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "app.py"},
                                    "region": {"startLine": 3},
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }
    sarif_path = tmp_path / "input.sarif"
    write(sarif_path, json.dumps(sarif))

    findings = read_sarif_inputs([str(sarif_path)])

    assert findings == [
        {
            "tool": "semgrep",
            "rule_id": "rule.test",
            "level": "warning",
            "message": "Example finding",
            "path": "app.py",
            "line": 3,
        }
    ]


def test_report_to_sarif_contains_hotspot_results(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config = load_config(None)
    config["thresholds"]["max_file_lines"] = 10
    report = build_report(tmp_path, config)

    sarif = report_to_sarif(report)

    assert sarif["runs"][0]["tool"]["driver"]["name"] == "maintainability-agent"
    assert sarif["runs"][0]["results"]
    assert sarif["runs"][0]["tool"]["driver"]["rules"]


def test_sarif_contains_duplicate_risk_and_level_variants(tmp_path: Path) -> None:
    report = {
        "largest_files": [{"path": "large.py", "lines": 99, "status": "warn"}],
        "function_hotspots": [{"path": "app.py", "name": "hot", "start_line": 3, "lines": 90, "complexity": 20, "status": "fail"}],
        "duplicate_blocks": [{"locations": ["a.py:10", "b.py:20"], "count": 2}],
        "risk_findings": [{"path": "app.py", "line": 5, "name": "secret-word", "text": "password found"}],
    }

    sarif = report_to_sarif(report)
    rule_ids = {rule["id"] for rule in sarif["runs"][0]["tool"]["driver"]["rules"]}
    levels = {result["ruleId"]: result["level"] for result in sarif["runs"][0]["results"]}

    assert sarif_level("ok") == "note"
    assert sarif_level("warn") == "warning"
    assert sarif_level("fail") == "error"
    assert "maintainability.duplicate_block" in rule_ids
    assert "maintainability.risk.secret-word" in rule_ids
    assert levels["maintainability.function_hotspot"] == "error"


def test_report_contains_iso_score(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")

    report = build_report(tmp_path, load_config(None))

    assert report["score"]["overall"] == 5.0
    assert report["score"]["grade"] == "A+"
    assert set(report["score"]["categories"]) == {"modularity", "reusability", "analyzability", "modifiability", "testability"}


def test_scoring_grade_boundaries() -> None:
    assert grade_from_score(4.6) == "A"
    assert grade_from_score(4.1) == "B"
    assert grade_from_score(3.2) == "C"
    assert grade_from_score(2.5) == "D"
    assert grade_from_score(1.9) == "F"


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


def test_risk_pattern_matching(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "password = 'example'\n")
    config = load_config(None)
    config["risk_patterns"] = [{"name": "secret-word", "pattern": "password", "extensions": [".py"]}]

    report = build_report(tmp_path, config)

    assert report["summary"]["risk_findings"] == 1
    assert report["risk_findings"][0]["name"] == "secret-word"


def test_exclude_patterns_use_glob_and_normalized_separators() -> None:
    patterns = ["**/generated/*.py", "node_modules/"]

    assert is_excluded("src\\generated\\client.py", patterns)
    assert is_excluded("node_modules/pkg/index.js", patterns)
    assert is_excluded("src/vendor/file.py", ["vendor"])
    assert not is_excluded("src/app.py", patterns)


def test_file_function_status_warning_paths() -> None:
    thresholds = {
        "max_file_lines": 10,
        "warn_file_lines": 5,
        "max_function_lines": 10,
        "warn_function_lines": 5,
        "max_complexity": 10,
        "warn_complexity": 5,
    }

    assert file_status(7, thresholds) == "warn"
    assert function_status(7, 1, thresholds) == "warn"
    assert function_status(1, 7, thresholds) == "warn"


def test_read_lines_replaces_decode_errors(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_bytes(b"ok\n\xff\n")

    assert read_lines(path)[0] == "ok"


def test_duplicate_blocks_ignore_repeated_single_line_blocks(tmp_path: Path) -> None:
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    write(first, "x = 1\nx = 1\nx = 1\n")
    write(second, "x = 1\nx = 1\nx = 1\n")

    assert duplicate_blocks(tmp_path, [first, second], 3) == []


def test_sarif_input_handles_realistic_semgrep_shape(tmp_path: Path) -> None:
    sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "Semgrep OSS"}},
                "results": [
                    {
                        "ruleId": "python.lang.security.audit",
                        "level": "error",
                        "message": {"text": "Avoid dynamic execution"},
                        "locations": [
                            {
                                "physicalLocation": {
                                    "artifactLocation": {"uri": "src/app.py"},
                                    "region": {"startLine": 42, "endLine": 42},
                                }
                            }
                        ],
                    }
                ],
            }
        ],
    }
    sarif_path = tmp_path / "semgrep.sarif"
    write(sarif_path, json.dumps(sarif))

    findings = read_sarif_inputs([str(sarif_path)])

    assert findings[0]["tool"] == "Semgrep OSS"
    assert findings[0]["level"] == "error"
    assert findings[0]["path"] == "src/app.py"


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
            "overall": 3.2,
            "grade": "C",
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

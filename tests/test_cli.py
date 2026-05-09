from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

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
from maintainability_audit.metrics import is_excluded


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


def test_report_contains_iso_score(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")

    report = build_report(tmp_path, load_config(None))

    assert report["score"]["overall"] == 5.0
    assert report["score"]["grade"] == "A+"
    assert set(report["score"]["categories"]) == {"modularity", "reusability", "analyzability", "modifiability", "testability"}


def test_fail_on_new_respects_baseline(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config_path = tmp_path / "config.json"
    write(config_path, json.dumps({"version": 1, "thresholds": {"max_file_lines": 10}}))
    report = build_report(tmp_path, load_config(str(config_path)))
    baseline = tmp_path / "baseline.json"
    write(baseline, json.dumps({"version": 1, "findings": sorted(finding_fingerprints(report))}))

    suppressed = main(["--root", str(tmp_path), "--config", str(config_path), "--baseline", str(baseline), "--fail-on-new"])
    new_finding = main(["--root", str(tmp_path), "--config", str(config_path), "--baseline", str(tmp_path / "missing.json"), "--fail-on-new"])

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
    assert not is_excluded("src/app.py", patterns)


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

from __future__ import annotations

import json
from pathlib import Path

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


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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
    assert json.loads(sarif.read_text(encoding="utf-8"))["version"] == "2.1.0"


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

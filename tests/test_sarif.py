"""Unit tests for SARIF input ingestion + report-to-SARIF rendering.

Split out of ``test_audit_components.py`` (2026-05-11) so neither
test file warns past the audit's file-length threshold. SARIF is a
self-contained concern — input parsing + output rendering of a
separate file format — so it lives on its own.
"""
from __future__ import annotations

import json
from pathlib import Path

from maintainability_audit.cli import (
    build_report,
    load_config,
    read_sarif_inputs,
    report_to_sarif,
)
from maintainability_audit.sarif import sarif_level


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


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

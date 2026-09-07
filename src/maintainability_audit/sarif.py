from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ._hotspots import hotspot_measure, hotspot_name
from .config import PROJECT_URL, PathNotAllowed, read_operator_file

SARIF_RULES: dict[str, dict[str, str]] = {
    "maintainability.file_size": {
        "name": "Large file",
        "short": "File exceeds configured maintainability size threshold.",
        "full": "Large files are harder to review, test, and safely change. Split only when there is a clear responsibility boundary.",
    },
    "maintainability.function_hotspot": {
        "name": "Function hotspot",
        "short": "Function or class exceeds configured size or complexity thresholds.",
        "full": "Large or complex functions often hide multiple responsibilities and deserve refactoring or explicit justification.",
    },
    "maintainability.duplicate_block": {
        "name": "Duplicate block",
        "short": "Repeated code block was detected.",
        "full": "Duplicate policy or business logic can drift. Consolidate when it represents the same responsibility.",
    },
    "maintainability.risk_pattern": {
        "name": "Risk pattern",
        "short": "Configured risk pattern matched repository text.",
        "full": "Risk patterns are repo-defined signals that deserve human review before release.",
    },
}


def sarif_level(status: str) -> str:
    if status == "fail":
        return "error"
    if status == "warn":
        return "warning"
    return "note"


def sarif_rule_descriptors(rule_ids: set[str]) -> list[dict[str, Any]]:
    descriptors = []
    for rule_id in sorted(rule_ids):
        base_id = "maintainability.risk_pattern" if rule_id.startswith("maintainability.risk.") else rule_id
        rule = SARIF_RULES.get(base_id, SARIF_RULES["maintainability.risk_pattern"])
        descriptors.append(
            {
                "id": rule_id,
                "name": rule["name"],
                "shortDescription": {"text": rule["short"]},
                "fullDescription": {"text": rule["full"]},
                "helpUri": f"{PROJECT_URL}/blob/main/docs/standard.md",
            }
        )
    return descriptors


def sarif_result(rule_id: str, message: str, path: str, line: int = 1, level: str = "warning") -> dict[str, Any]:
    return {
        "ruleId": rule_id,
        "level": level,
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": path},
                    "region": {"startLine": max(1, line)},
                }
            }
        ],
    }


def report_to_sarif(report: dict[str, Any]) -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    rule_ids: set[str] = set()
    for item in report.get("largest_files", []):
        if item["status"] in {"warn", "fail"}:
            rule_id = "maintainability.file_size"
            rule_ids.add(rule_id)
            results.append(
                sarif_result(
                    rule_id,
                    f"{item['path']} has {item['lines']} lines ({item['status']}).",
                    item["path"],
                    level=sarif_level(item["status"]),
                )
            )
    for item in report.get("function_hotspots", []):
        rule_id = "maintainability.function_hotspot"
        rule_ids.add(rule_id)
        results.append(
            sarif_result(
                rule_id,
                f"{hotspot_name(item, quote='')} ({hotspot_measure(item)}).",
                item["path"],
                item["start_line"],
                sarif_level(item["status"]),
            )
        )
    for item in report.get("duplicate_blocks", []):
        rule_id = "maintainability.duplicate_block"
        rule_ids.add(rule_id)
        first_location = item["locations"][0]
        path, _, line = first_location.partition(":")
        results.append(sarif_result(rule_id, f"Duplicate block appears {item['count']} times.", path, int(line or "1"), "note"))
    for item in report.get("risk_findings", []):
        rule_id = f"maintainability.risk.{item['name']}"
        rule_ids.add(rule_id)
        results.append(sarif_result(rule_id, item["text"], item["path"], item["line"]))
    return {
        "version": "2.1.0",
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "runs": [
            {
                "tool": {
                    "driver": {
                        "name": "maintainability-agent",
                        "informationUri": PROJECT_URL,
                        "rules": sarif_rule_descriptors(rule_ids),
                    }
                },
                "results": results,
                # Evidence completeness rides at run level, deliberately.
                # It describes the *audit*, not any line of code, so
                # emitting it as a result would invent a source-code
                # finding for a shallow clone and put it in the Security
                # tab next to real defects. SARIF property bags exist for
                # exactly this (§3.14.3, §3.8).
                **_evidence_run_properties(report),
            }
        ],
    }


def _evidence_run_properties(report: dict[str, Any]) -> dict[str, Any]:
    """The run's evidence property bag, or nothing at all.

    A report with no score object is not a report whose grade was
    withheld — it is one that was never scored, which some callers
    legitimately produce. Emitting ``verifiedGrade: null`` there would
    assert withholding that never happened, so the whole bag is omitted
    instead.
    """
    score = report.get("score")
    if not score:
        return {}
    status = score.get("evidence_status") or {}
    return {"properties": {
        "evidenceProfile": status.get("profile"),
        "evidenceStatus": status.get("status"),
        "verifiedGrade": score.get("verified_grade"),
        "maintainabilityEstimate": score["maintainability_estimate"],
        "evidenceReasons": [
            {
                "measurement": item["measurement"],
                "reason": item["reason"],
                "provenance": item["provenance"],
            }
            for item in status.get("reasons") or []
        ],
    }}


def read_sarif_inputs(paths: list[str] | None) -> list[dict[str, Any]]:
    """Findings from every SARIF file the operator named.

    Read through `read_operator_file`, like `--config` and `--baseline`,
    because this is the same kind of argument: a path from the command
    line, deliberately allowed to point outside `--root`, whose content
    is ingested into the published report.

    It read the name directly until 2.11.2. A FIFO blocked the process
    forever, `/dev/zero` read until memory died, and a directory or a
    missing file escaped as an uncaught traceback. D104 measured exactly
    that on `--config`, built this primitive for it, and recorded the
    class as closed on the claim that `--config` and `--baseline` were
    the only two such arguments — a claim written into the primitive's
    own docstring, which is why the third one stayed invisible (D130).
    """
    findings: list[dict[str, Any]] = []
    for path in paths or []:
        # `OSError` covers the directory, the missing file and the
        # unreadable one; it is re-raised as the door's own refusal so a
        # caller sees a named error rather than a traceback, and so the
        # test can assert the contract rather than "something raised" —
        # `IsADirectoryError` is an `OSError` too, and a test that
        # accepted one would have passed against the defect.
        try:
            text = read_operator_file(Path(path))
        except PathNotAllowed:
            raise
        except OSError as unreadable:
            detail = unreadable.strerror or unreadable.__class__.__name__
            raise PathNotAllowed(f"{path} could not be read: {detail}") from None
        data = json.loads(text)
        for run in data.get("runs", []):
            tool = run.get("tool", {}).get("driver", {}).get("name", "sarif")
            for result in run.get("results", []):
                location = (result.get("locations") or [{}])[0]
                physical = location.get("physicalLocation", {})
                artifact = physical.get("artifactLocation", {})
                region = physical.get("region", {})
                findings.append(
                    {
                        "tool": tool,
                        "rule_id": result.get("ruleId", "unknown"),
                        "level": result.get("level", "warning"),
                        "message": result.get("message", {}).get("text", ""),
                        "path": artifact.get("uri", ""),
                        "line": region.get("startLine", 1),
                    }
                )
    return findings

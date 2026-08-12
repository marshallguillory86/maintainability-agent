from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def finding_fingerprints(report: dict[str, Any]) -> set[str]:
    fingerprints: set[str] = set()
    for item in report.get("largest_files", []):
        if item["status"] == "fail":
            fingerprints.add(f"file-lines:{item['path']}")
    for item in report.get("function_hotspots", []):
        if item["status"] == "fail":
            fingerprints.add(f"function:{item['path']}:{item['name']}:{item['start_line']}")
    for item in report.get("risk_findings", []):
        fingerprints.add(f"risk:{item['path']}:{item['line']}:{item['name']}")
    for item in report.get("duplicate_blocks", []):
        locations = ",".join(item["locations"][:5])
        fingerprints.add(f"duplicate:{locations}")
    return fingerprints


def load_baseline(path: str | None) -> set[str]:
    if not path:
        return set()
    baseline_path = Path(path)
    if not baseline_path.exists():
        return set()
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    return set(data.get("findings", []))


def write_baseline(path: str, report: dict[str, Any]) -> None:
    # No score snapshot. Nothing ever read it back — `load_baseline`
    # takes the fingerprint list alone — and writing one would freeze an
    # obsolete report contract into every new baseline for no consumer.
    # The file version stays 1: the format a reader depends on has not
    # changed, and older baselines carrying a score still load because
    # the loader ignores the field.
    data = {
        "version": 1,
        "root": report["root"],
        "findings": sorted(finding_fingerprints(report)),
    }
    Path(path).write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")

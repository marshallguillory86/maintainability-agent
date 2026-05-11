"""Unit tests for config, metrics/build_report, baseline, and scoring.

Split out of the integration-heavy ``test_cli.py`` (2026-05-11) so
neither file warns past the audit's file-length threshold. SARIF
input/output tests live in ``test_sarif.py``; CLI-flow tests
(``--changed-only``, ``--fail-on-gate``, ``--init-agent-standards``,
``--version``, renderer pipeline) stay in ``test_cli.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

from maintainability_audit.baseline import write_baseline
from maintainability_audit.cli import (
    DEFAULT_CONFIG,
    build_report,
    finding_fingerprints,
    load_baseline,
    load_config,
)
from maintainability_audit.metrics import (
    duplicate_blocks,
    file_status,
    function_status,
    is_excluded,
    read_lines,
)
from maintainability_audit.scoring import grade_from_score


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# config
# ---------------------------------------------------------------------------

def test_config_deep_merge(tmp_path: Path) -> None:
    config_path = tmp_path / "maintainability.json"
    write(config_path, json.dumps({"version": 1, "thresholds": {"max_file_lines": 12}}))

    config = load_config(str(config_path))

    assert config["thresholds"]["max_file_lines"] == 12
    assert config["thresholds"]["warn_file_lines"] == DEFAULT_CONFIG["thresholds"]["warn_file_lines"]


# ---------------------------------------------------------------------------
# metrics / build_report
# ---------------------------------------------------------------------------

def test_build_report_flags_large_file(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "large.py", "\n".join(f"line_{i} = {i}" for i in range(20)))
    config = load_config(None)
    config["thresholds"]["max_file_lines"] = 10
    config["thresholds"]["warn_file_lines"] = 5

    report = build_report(tmp_path, config)

    assert report["summary"]["file_failures"] == 1
    assert any("files exceed max_file_lines" in gate for gate in report["hard_gate_failures"])


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


# ---------------------------------------------------------------------------
# baseline
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

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

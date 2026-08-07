"""Unit tests for config loading, baseline fingerprints, and scoring.

Split out of the integration-heavy ``test_cli.py`` (2026-05-11) so
neither file warns past the audit's file-length threshold, and thinned
again (2026-08-06) when ``metrics.py`` was split: file-level scanning
moved to ``test_scanning.py`` and Python declaration detection to
``test_python_declarations.py``. SARIF input/output tests live in
``test_sarif.py``; CLI-flow tests (``--changed-only``, ``--fail-on-gate``,
``--init-agent-standards``, ``--version``, renderer pipeline) stay in
``test_cli.py``.
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


def _make_huge_function_source(name: str, body_lines: int = 200) -> str:
    body = "\n".join(f"    x_{i} = {i}" for i in range(body_lines))
    return f"def {name}():\n{body}\n"


def test_testability_does_not_drop_when_only_test_file_grows(tmp_path: Path) -> None:
    """Bug #2 regression: an oversized function in a test file must not
    penalize the project's testability score. The whole point of
    testability is that production code is amenable to testing — long
    test bodies are common and should not count against the metric."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")
    config = load_config(None)
    config["thresholds"]["max_function_lines"] = 50

    report_before = build_report(tmp_path, config)

    write(tmp_path / "tests" / "test_app.py", _make_huge_function_source("test_lots_of_setup", body_lines=200))
    report_after = build_report(tmp_path, config)

    assert report_after["score"]["categories"]["testability"] >= report_before["score"]["categories"]["testability"], (
        "testability dropped from "
        f"{report_before['score']['categories']['testability']} to "
        f"{report_after['score']['categories']['testability']} purely because a "
        "test file gained a long function"
    )


def test_analyzability_not_penalized_by_test_function_size(tmp_path: Path) -> None:
    """Bug #2 regression: analyzability should respond to production-code
    function pressure. A long test function should not be the difference
    between two scores."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")
    config = load_config(None)
    config["thresholds"]["max_function_lines"] = 50

    baseline = build_report(tmp_path, config)["score"]["categories"]["analyzability"]
    write(tmp_path / "tests" / "test_app.py", _make_huge_function_source("test_big", body_lines=200))
    with_test = build_report(tmp_path, config)["score"]["categories"]["analyzability"]

    assert with_test >= baseline


def test_report_summary_splits_test_vs_production_function_counts(tmp_path: Path) -> None:
    """The summary must expose test-vs-production splits so downstream
    renderers and scorers can treat them differently."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "src" / "service.py", _make_huge_function_source("prod_huge", body_lines=200))
    write(tmp_path / "tests" / "test_service.py", _make_huge_function_source("test_huge", body_lines=200))
    config = load_config(None)
    config["thresholds"]["max_function_lines"] = 50

    report = build_report(tmp_path, config)

    assert report["summary"]["function_failures"] == 2
    assert report["summary"]["production_function_failures"] == 1
    assert report["summary"]["test_function_failures"] == 1


def test_scoring_grade_boundaries() -> None:
    assert grade_from_score(4.6) == "A"
    assert grade_from_score(4.1) == "B"
    assert grade_from_score(3.2) == "C"
    assert grade_from_score(2.5) == "D"
    assert grade_from_score(1.9) == "F"

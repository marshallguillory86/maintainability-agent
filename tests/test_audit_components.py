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
import subprocess
from pathlib import Path

from maintainability_audit.baseline import BASELINE_VERSION, write_baseline
from maintainability_audit.cli import (
    DEFAULT_CONFIG,
    build_report,
    finding_fingerprints,
    load_baseline,
    load_config,
)
from maintainability_audit.scoring import grade_from_score


def commit_all(root: Path) -> None:
    """Put the fixture under git so its history is measurable.

    Without this the history aspects read None and every grade
    assertion is really testing the missing-evidence rule.
    """
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin", "HOME": str(root)}
    for command in (["git", "init", "--quiet"], ["git", "add", "-A"],
                    ["git", "commit", "--quiet", "-m", "start"]):
        subprocess.run(command, cwd=root, check=True, capture_output=True, env=env)


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
    write(baseline, json.dumps({"version": BASELINE_VERSION,
                                "findings": sorted(finding_fingerprints(report))}))

    assert load_baseline(str(baseline)) == finding_fingerprints(report)


def test_baseline_helpers_cover_empty_missing_and_written_files(tmp_path: Path) -> None:
    report = {
        "root": str(tmp_path),
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

    assert "score" not in loaded, (
        "stage 8 stopped writing the informational score snapshot: nothing read it back, "
        "and keeping it would freeze an obsolete contract into every new baseline"
    )
    assert len(loaded["findings"]) == 4


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def test_report_contains_iso_score(tmp_path: Path) -> None:
    """A clean, tested, *documented* toy repo with history earns the top
    grade.

    Every artifact here is load-bearing: drop the test file and the
    grade caps at B; drop the changelog and docs and the documentation
    aspect scores 3.0, which costs the A+; drop the git history and the
    unmeasured-evidence rule withholds the A-grades."""
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "CHANGELOG.md", "## 0.1.0\n- start\n")
    write(tmp_path / "docs" / "index.md", "# Docs\n")
    write(tmp_path / "app.py", "def ok():\n    return 1\n")
    write(tmp_path / "test_app.py", "from app import ok\n\ndef test_ok():\n    assert ok() == 1\n")
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t", "PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}
    for command in (["git", "init", "--quiet"], ["git", "add", "-A"],
                    ["git", "commit", "--quiet", "-m", "start"]):
        subprocess.run(command, cwd=tmp_path, check=True, capture_output=True, env=env)

    report = build_report(tmp_path, load_config(None))

    assert report["score"]["maintainability_estimate"] == 5.0
    assert report["score"]["verified_grade"] == "A+"
    assert set(report["score"]["categories"]) == {"modularity", "reusability", "analyzability", "modifiability", "testability"}
    assert report["score"]["aspects"]["test_presence"] == 5.0
    assert report["score"]["rubric"]["unscored"], "unmeasurable aspects must be named, not omitted"


def test_a_grades_require_test_evidence(tmp_path: Path) -> None:
    """An earlier version of this file asserted the opposite: a README
    plus one untested function was blessed as A+ with testability 5.0.
    A hostile audit built a 100-file, zero-test repository and collected
    exactly that grade. The published meaning of 5 is "localized,
    tested, and easy to reason about" — so with not one test file, the
    A-grades are withheld, testability is capped, and the blocker names
    the reason instead of leaving "why am I not an A" unanswerable.

    Committed to git so the missing tests are the *only* thing missing:
    grading on the evidence floor would otherwise demote this fixture
    for absent history and the assertion would stop testing its own
    name. The interval must also contain the score — an audit found the
    cap applied to the point estimate and not to the endpoints, so an
    untested repo reported 4.4 inside a range of [4.5, 4.5]."""
    write(tmp_path / "README.md", "# Test\n")
    for index in range(20):
        write(tmp_path / f"m{index}.py", f"def f{index}(x):\n    return x + {index}\n")
    commit_all(tmp_path)

    score = build_report(tmp_path, load_config(None))["score"]

    assert score["verified_grade"] == "B"
    assert score["categories"]["testability"] <= 2.0
    assert any("test evidence" in blocker for blocker in score["verified_grade_blockers"])
    low, high = score["maintainability_range"]
    assert low <= score["maintainability_estimate"] <= high


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

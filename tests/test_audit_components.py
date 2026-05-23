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
    detect_functions,
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


def _detect(tmp_path: Path, source: str, filename: str = "module.py") -> list:
    path = tmp_path / filename
    write(path, source)
    thresholds = DEFAULT_CONFIG["thresholds"]
    return detect_functions(tmp_path, path, read_lines(path), thresholds)


def test_detect_functions_python_uses_actual_end_lineno(tmp_path: Path) -> None:
    """Bug #1 regression: a short Enum followed by unrelated code must report
    its own body length, not the distance to end-of-file."""
    trailing = "\n".join(f"VAR_{i} = {i}" for i in range(300))
    source = "import enum\n\nclass Foo(enum.Enum):\n    A = 1\n    B = 2\n\n" + trailing + "\n"
    funcs = _detect(tmp_path, source)

    foo = next(metric for metric in funcs if metric.name == "Foo")
    assert foo.lines <= 4, f"expected ~4-line Enum body, got {foo.lines}"
    assert foo.status == "ok"


def test_detect_functions_python_single_return_function(tmp_path: Path) -> None:
    """Bug #1 regression: a single-return function followed by another
    definition must report the body length, not "next def - 1"."""
    source = (
        "def short_one():\n"
        "    return (\n"
        "        'SELECT 1'\n"
        "    )\n"
        "\n"
        "def other():\n"
        "    if True:\n"
        "        return 2\n"
        "    return 3\n"
    )
    funcs = _detect(tmp_path, source)

    short = next(metric for metric in funcs if metric.name == "short_one")
    assert short.lines == 4, f"expected 4-line body for short_one, got {short.lines}"


def test_detect_functions_python_empty_class_does_not_absorb_trailing(tmp_path: Path) -> None:
    """Bug #1 regression: a class with no methods must NOT swallow a long
    function defined after it."""
    long_body = "\n".join(f"    x_{i} = {i}" for i in range(100))
    source = "class Empty:\n    pass\n\ndef big():\n" + long_body + "\n"
    funcs = _detect(tmp_path, source)

    empty = next(metric for metric in funcs if metric.name == "Empty")
    big = next(metric for metric in funcs if metric.name == "big")
    assert empty.lines <= 2
    assert big.lines >= 100


def test_detect_functions_python_async_def_supported(tmp_path: Path) -> None:
    """`async def` must be measured the same way as `def` via AST."""
    source = "async def coro():\n    await something()\n    return 1\n\ndef tail():\n    return 0\n"
    funcs = _detect(tmp_path, source)

    coro = next(metric for metric in funcs if metric.name == "coro")
    assert coro.lines == 3


def test_detect_functions_python_falls_back_when_syntax_broken(tmp_path: Path) -> None:
    """If a .py file fails to parse, the auditor should fall back to the
    line-pattern scan instead of skipping the file entirely."""
    source = "def broken(:\n    return 1\n"  # SyntaxError on purpose
    funcs = _detect(tmp_path, source)

    assert any(metric.name == "broken" for metric in funcs)


def test_duplicate_blocks_skip_pure_identifier_list_overlap(tmp_path: Path) -> None:
    """Bug #3 regression: a shared list of column-name identifiers appearing
    in both an INSERT column list and a function keyword-argument
    signature must not be flagged as a duplicate block. The shared
    ordering IS the architectural contract — deduplicating obscures it."""
    sql = (
        "def insert_run():\n"
        "    return db.execute(INSERT_SQL, (\n"
        "        source_name,\n"
        "        fetch_endpoint,\n"
        "        parser_class,\n"
        "        collection_window,\n"
        "        poll_interval_seconds,\n"
        "    ))\n"
    )
    kwargs = (
        "def build_run(\n"
        "    source_name,\n"
        "    fetch_endpoint,\n"
        "    parser_class,\n"
        "    collection_window,\n"
        "    poll_interval_seconds,\n"
        "):\n"
        "    return locals()\n"
    )
    first = tmp_path / "ledger.py"
    second = tmp_path / "builder.py"
    write(first, sql)
    write(second, kwargs)

    assert duplicate_blocks(tmp_path, [first, second], 5) == []


def test_duplicate_blocks_still_flag_real_logic_repetition(tmp_path: Path) -> None:
    """Bug #3 fix must NOT silence genuine code duplication. A repeated
    block with actual operators/calls should still surface."""
    block = (
        "def handler(payload):\n"
        "    cleaned = payload.strip().lower()\n"
        "    if not cleaned:\n"
        "        raise ValueError('empty payload')\n"
        "    metrics.incr('handler.calls', tags={'kind': cleaned})\n"
        "    return router.dispatch(cleaned)\n"
    )
    first = tmp_path / "a.py"
    second = tmp_path / "b.py"
    write(first, block)
    write(second, block)

    dupes = duplicate_blocks(tmp_path, [first, second], 5)
    assert dupes, "real cross-file code duplication should still be detected"


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

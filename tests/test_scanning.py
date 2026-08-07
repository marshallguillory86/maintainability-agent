"""What the file-level scan sees: exclusions, sizes, risks, duplicates.

Covers ``metrics`` (which files count and how big they are) and
``duplication`` (which blocks repeat, which risk patterns match). Split
out of ``test_audit_components.py`` (2026-08-06) when ``metrics.py`` was
itself split, so the tests track the modules they exercise.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import build_report, load_config
from maintainability_audit.duplication import duplicate_blocks
from maintainability_audit.metrics import file_status, is_excluded, read_lines


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# ---------------------------------------------------------------------------
# file selection and sizing
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


def test_exclude_patterns_use_glob_and_normalized_separators() -> None:
    patterns = ["**/generated/*.py", "node_modules/"]

    assert is_excluded("src\\generated\\client.py", patterns)
    assert is_excluded("node_modules/pkg/index.js", patterns)
    assert is_excluded("src/vendor/file.py", ["vendor"])
    assert not is_excluded("src/app.py", patterns)


def test_file_status_warning_path() -> None:
    assert file_status(7, {"max_file_lines": 10, "warn_file_lines": 5}) == "warn"


def test_read_lines_replaces_decode_errors(tmp_path: Path) -> None:
    path = tmp_path / "bad.py"
    path.write_bytes(b"ok\n\xff\n")

    assert read_lines(path)[0] == "ok"


# ---------------------------------------------------------------------------
# risk patterns
# ---------------------------------------------------------------------------

def test_risk_pattern_matching(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "app.py", "password = 'example'\n")
    config = load_config(None)
    config["risk_patterns"] = [{"name": "secret-word", "pattern": "password", "extensions": [".py"]}]

    report = build_report(tmp_path, config)

    assert report["summary"]["risk_findings"] == 1
    assert report["risk_findings"][0]["name"] == "secret-word"


# ---------------------------------------------------------------------------
# duplicate blocks
# ---------------------------------------------------------------------------

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

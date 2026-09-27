"""Coverage is read from lcov as well as Cobertura XML.

Found auditing Scrollwork: its suite measures with V8 and writes lcov, not
`coverage.xml`, so even the right command would have left
`test_effectiveness` unscored. JavaScript's coverage tools — c8, nyc, jest,
vitest — write `coverage/lcov.info` by convention. The same provenance rule
applies to every format: only an artifact this run produced is scored, so a
committed file cannot set its own number.
"""

from __future__ import annotations

import stat
from pathlib import Path

from maintainability_audit._test_execution import repository_key, run_test_suite
from maintainability_audit._user_config import write_user_answers

LCOV = "SF:a.js\nLF:10\nLH:8\nend_of_record\nSF:b.js\nLF:10\nLH:2\nend_of_record\n"


def _suite(root: Path, writes: str | None) -> dict:
    script = root / "run-suite.sh"
    body = "#!/bin/sh\n"
    if writes:
        body += f"mkdir -p coverage\nprintf '%s' '{LCOV}' > {writes}\n"
    script.write_text(body + "exit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    write_user_answers({"test_execution": {
        "requested": True, "commands": {repository_key(root): ["./run-suite.sh"]}}})
    return {"test_execution": {"requested": True}, "expected_commands": {"test": ["./run-suite.sh"]}}


def test_an_lcov_report_this_run_wrote_is_scored(tmp_path: Path) -> None:
    config = _suite(tmp_path, "coverage/lcov.info")

    result = run_test_suite(tmp_path, config)

    assert result["ran"] is True
    assert result["coverage_percent"] == 50.0


def test_lcov_at_the_root_is_read_too(tmp_path: Path) -> None:
    config = _suite(tmp_path, "lcov.info")

    assert run_test_suite(tmp_path, config)["coverage_percent"] == 50.0


def test_a_committed_lcov_report_is_not_scored(tmp_path: Path) -> None:
    (tmp_path / "coverage").mkdir()
    (tmp_path / "coverage" / "lcov.info").write_text(LCOV, encoding="utf-8")
    config = _suite(tmp_path, None)

    assert run_test_suite(tmp_path, config)["coverage_percent"] is None


def test_an_lcov_report_with_no_lines_scores_nothing(tmp_path: Path) -> None:
    """LF:0 everywhere is no measurement, not 0% or 100%."""
    script = tmp_path / "run-suite.sh"
    script.write_text("#!/bin/sh\nmkdir -p coverage\nprintf 'SF:a.js\\nLF:0\\nLH:0\\nend_of_record\\n' "
                      "> coverage/lcov.info\nexit 0\n", encoding="utf-8")
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    write_user_answers({"test_execution": {
        "requested": True, "commands": {repository_key(tmp_path): ["./run-suite.sh"]}}})

    result = run_test_suite(tmp_path, {"test_execution": {"requested": True},
                                       "expected_commands": {"test": ["./run-suite.sh"]}})

    assert result["coverage_percent"] is None

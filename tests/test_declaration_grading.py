"""How a detected declaration is graded, and what isn't graded at all.

Companion to ``test_declaration_ranges.py`` (which pins where a
declaration *ends*); split so neither file warns past the audit's own
file-length threshold. Two false-positive sources are covered here:

- A class was measured against ``max_function_lines`` and against a
  complexity that ``ast.walk`` had already charged to its methods, so
  ordinary multi-method classes were reported as over-long, over-complex
  "functions".
- Schema migrations are append-only history. A 102-line, complexity-2
  ``upgrade()`` is what a correct migration looks like, and refactoring
  one rewrites the past.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import DEFAULT_CONFIG, build_report, load_config
from maintainability_audit.declarations import detect_functions
from maintainability_audit.metrics import is_excluded, read_lines
from maintainability_audit.prompts import render_ai_prompt
from maintainability_audit.renderers import render_markdown, render_pr_comment
from maintainability_audit.sarif import report_to_sarif

THRESHOLDS = DEFAULT_CONFIG["thresholds"]


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def detect(tmp_path: Path, source: str, filename: str) -> dict[str, object]:
    path = tmp_path / filename
    write(path, source)
    return {metric.name: metric for metric in detect_functions(tmp_path, path, read_lines(path), THRESHOLDS)}


# ---------------------------------------------------------------------------
# Python fallback bounding
# ---------------------------------------------------------------------------

def test_regex_fallback_is_indentation_bounded(tmp_path: Path) -> None:
    """Unparseable Python falls back to the pattern scan. That scan must
    bound each body by indentation, not by end-of-file."""
    trailing = "\n".join(f"VALUE_{index} = {index}" for index in range(200))
    found = detect(tmp_path, "def broken(:\n    return 1\n\n" + trailing + "\n", "broken.py")

    assert found["broken"].lines == 3


# ---------------------------------------------------------------------------
# Classes get their own budget
# ---------------------------------------------------------------------------

def test_python_class_is_graded_against_the_class_threshold(tmp_path: Path) -> None:
    """A twenty-method class runs well past `max_function_lines` without
    anything being wrong with it, and `ast.walk` charges it the sum of
    its methods' branches. Grade it on `max_class_lines`, length only."""
    methods = "\n\n".join(
        f"    def step_{index}(self, value):\n        if value:\n            return {index}\n        return 0"
        for index in range(20)
    )
    worker = detect(tmp_path, f"class Worker:\n{methods}\n", "worker.py")["Worker"]

    assert worker.kind == "class"
    assert worker.lines > THRESHOLDS["max_function_lines"]
    assert worker.complexity > THRESHOLDS["max_complexity"]
    assert worker.status == "ok"


def test_python_class_still_fails_when_it_outgrows_its_own_budget(tmp_path: Path) -> None:
    body = "\n".join(f"    ATTR_{index} = {index}" for index in range(THRESHOLDS["max_class_lines"] + 5))
    found = detect(tmp_path, f"class Huge:\n{body}\n", "huge.py")

    assert found["Huge"].status == "fail"


def test_python_methods_are_still_graded_as_functions(tmp_path: Path) -> None:
    body = "\n".join(f"        step_{index}()" for index in range(THRESHOLDS["max_function_lines"] + 5))
    found = detect(tmp_path, f"class Worker:\n    def run(self):\n{body}\n", "worker.py")

    assert found["Worker"].status == "ok"
    assert found["run"].kind == "function"
    assert found["run"].status == "fail"


# ---------------------------------------------------------------------------
# Migration history
# ---------------------------------------------------------------------------

def test_migrations_are_excluded_by_default() -> None:
    patterns = DEFAULT_CONFIG["paths"]["exclude_patterns"]

    assert is_excluded("api/migrations/versions/0001_initial_schema.py", patterns)
    assert is_excluded("migrations/0002_add_index.py", patterns)
    assert not is_excluded("api/models/migration_helpers.py", patterns)


def test_migration_file_does_not_trip_the_file_size_gate(tmp_path: Path) -> None:
    write(tmp_path / "README.md", "# Test\n")
    write(tmp_path / "api/migrations/versions/0001_initial.py", "\n".join(f"op.add_column({i})" for i in range(200)))
    config = load_config(None)
    config["thresholds"]["max_file_lines"] = 10

    report = build_report(tmp_path, config)

    assert report["summary"]["file_failures"] == 0


# ---------------------------------------------------------------------------
# A flagged class has to *read* as a class
# ---------------------------------------------------------------------------

CLASS_HOTSPOT = {
    "path": "app/worker.py",
    "name": "ScanWorker",
    "start_line": 12,
    "lines": 260,
    "complexity": 42,
    "status": "warn",
    "kind": "class",
}


def flagged_class_report() -> dict[str, object]:
    """A report whose only finding is the class hotspot above.

    ``only_paths=set()`` scans nothing, so no scanned file can smuggle a
    stray number into the assertions below.
    """
    report = build_report(Path(__file__).parent, load_config(None), only_paths=set())
    report["function_hotspots"] = [CLASS_HOTSPOT]
    return report


def test_class_hotspot_is_labelled_and_hides_its_double_counted_complexity() -> None:
    """The number is the sum of branches already charged to the class's
    own methods, and nothing is graded against it — so print neither it
    nor the word "function" beside a class."""
    rendered = render_markdown(flagged_class_report())

    assert "`ScanWorker` (class)" in rendered
    assert "| Declaration |" in rendered

    # The row, not the document. `"42" not in rendered` was the first
    # spelling, and it read every number anywhere in the report: it
    # started failing the day the history block learned to say how many
    # commits it had read, because this repository happened to have 142.
    # A whole-document substring search for a bare integer is not a
    # check that the class's complexity is hidden -- it is a check that
    # the digits never occur, which is a different and unmeetable claim.
    row = next(
        line for line in rendered.splitlines()
        if "`ScanWorker` (class)" in line
    )
    assert "42" not in row, (
        "the class's complexity is printed beside it; it is the sum of "
        f"branches already charged to its own methods: {row}"
    )


def test_function_hotspot_still_reports_its_complexity() -> None:
    report = flagged_class_report()
    report["function_hotspots"] = [{**CLASS_HOTSPOT, "name": "scan", "kind": "function"}]

    rendered = render_markdown(report)

    assert "`scan`" in rendered
    assert "(class)" not in rendered
    assert "42" in rendered


def test_class_label_reaches_the_prompt_the_pr_comment_and_sarif() -> None:
    report = flagged_class_report()

    assert "`ScanWorker` (class) (260 lines, warn)" in render_ai_prompt(report)
    assert "`ScanWorker` (class) (260 lines, warn)" in render_pr_comment(report)
    message = report_to_sarif(report)["runs"][0]["results"][0]["message"]["text"]
    assert message == "ScanWorker (class) (260 lines, warn)."


def test_hotspots_without_a_kind_are_read_as_functions() -> None:
    """Baselines and reports written before 0.4.0 have no `kind`."""
    report = flagged_class_report()
    report["function_hotspots"] = [{key: value for key, value in CLASS_HOTSPOT.items() if key != "kind"}]

    rendered = render_markdown(report)

    assert "(class)" not in rendered
    assert "42" in rendered

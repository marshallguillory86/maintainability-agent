"""2.7: the adapters proven against recorded tool output.

Split from `test_adapters` when the contract additions crossed this
project's own 500-line gate. Same discipline as everything in that file:
the payloads are what the real tools printed, not what a parser would
find convenient, so a format drift upstream fails here before it ships
a silent zero.
"""
from __future__ import annotations

import pytest

from maintainability_audit._generic import declared_adapter
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import adapter_for


def _ran(stdout: str = "", stderr: str = "") -> ToolResult:
    return ToolResult(slug="t", outcome=Outcome.RAN, stdout=stdout, stderr=stderr, exit_code=0)


def _registered_adapter(slug: str):
    adapter = adapter_for(slug) or declared_adapter(slug)
    assert adapter is not None, f"{slug} has no native or declared adapter"
    return adapter


def test_fortitude_parses_real_json_output() -> None:
    """Recorded fortitude 0.9.2 `--output-format json`.

    Two things this pins that a hand-written fixture would not. The
    location key is `line`, where ruff — whose output is otherwise the
    same shape — spells it `row`; reading ruff's spelling here would drop
    every line number silently, leaving findings that name a file and no
    place in it. And `C191` is the one rule that is not style: code after
    a `return` is unreachable, which is dead code by any reading.
    """
    payload = """[
      {
        "code": "PORT021",
        "filename": "src/sample.f90",
        "location": {"column": 9, "line": 6},
        "end_location": {"column": 11, "line": 6},
        "fix": {"applicability": "unsafe", "message": "Replace with 'real(8)'"},
        "message": "'real*8' uses non-standard syntax"
      },
      {
        "code": "C191",
        "filename": "src/sample.f90",
        "location": {"column": 5, "line": 8},
        "end_location": {"column": 12, "line": 8},
        "fix": null,
        "message": "code following `return` is unreachable"
      }
    ]"""
    extraction = _registered_adapter("fortitude").parse(_ran(payload))

    assert not extraction.measurements, "a linter's verdicts cannot supply a scored rate"
    assert [
        (finding.path, finding.line, finding.rule, finding.concept)
        for finding in extraction.findings
    ] == [
        ("src/sample.f90", 6, "PORT021", "style"),
        ("src/sample.f90", 8, "C191", "dead-code"),
    ]


def test_fortitude_does_not_claim_to_type_check_fortran() -> None:
    """`implicit none` and `intent` are declarations, not type checking.

    Fortitude's correctness rules are the reason a Fortran maintainer
    would run it, and they are *about* types — which makes `types` the
    tempting concept to declare. It would be wrong: a coverage record
    reading `types` says this repository is type-checked, and nothing
    here type-checks Fortran. The same mistake was already caught once,
    for a C++ tree claiming mypy's coverage.
    """
    adapter = _registered_adapter("fortitude")

    assert "types" not in adapter.concepts
    assert set(adapter.concepts) == {"style", "dead-code"}


def test_flake8_parses_real_default_output() -> None:
    """Recorded flake8 7.3 default output keeps its actionable location and rule."""
    payload = (
        "src/app.py:3:5: F841 local variable 'unused' is assigned to but never used\n"
        "src/app.py:7:1: E302 expected 2 blank lines, found 1\n"
        "src/app.py:10:5: C901 'complex' is too complex (12)\n"
    )
    extraction = _registered_adapter("flake8").parse(_ran(payload))

    assert not extraction.measurements, "flake8 verdicts cannot supply a scored rate"
    assert [
        (finding.path, finding.line, finding.rule)
        for finding in extraction.findings
    ] == [
        ("src/app.py", 3, "F841"),
        ("src/app.py", 7, "E302"),
        ("src/app.py", 10, "C901"),
    ]


def test_cohesion_parses_real_verbose_output() -> None:
    """Recorded cohesion 1.2.0 output preserves each class's measured percentage."""
    payload = """File: example.py
  Class: ExampleClass1 (1:0)
    Function: func1 2/3 66.67%
    Function: func2 1/3 33.33%
    Function: func3 0/3 0.00%
    Total: 33.33%
  Class: ExampleClass2 (23:0)
    Function: func1 1/1 100.00%
    Total: 100.00%
"""
    extraction = _registered_adapter("cohesion").parse(_ran(payload))

    assert not extraction.findings, "raw cohesion percentages are measurements, not gates"
    assert [
        (measurement.path, measurement.line, measurement.unit, measurement.value)
        for measurement in extraction.measurements
    ] == [
        ("example.py", 1, "example.py::ExampleClass1", pytest.approx(33.33)),
        ("example.py", 23, "example.py::ExampleClass2", pytest.approx(100.0)),
    ]


def test_xenon_is_deliberately_unadapted() -> None:
    """A gate over radon adds no independent reading.

    xenon re-ranks radon's own cyclomatic numbers against thresholds. An
    adapter would put a fourth "independent" complexity source into the
    pool that is strictly derived from one already counted, inflating
    apparent corroboration without adding evidence. Two tools agreeing
    because one *is* the other is worse than one tool alone, because it
    looks like confirmation.
    """
    assert adapter_for("xenon") is None

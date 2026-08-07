"""Python declaration detection via ``ast``, and the function budget.

Python is the one language where ranges are exact rather than inferred:
``ast.end_lineno`` gives the real body span. These are the regressions
that pinned that behaviour when the detector still derived an end from
the *next* declaration. The inferred path for every other language lives
in ``test_declaration_ranges.py``; how a range is then graded lives in
``test_declaration_grading.py``.

Split out of ``test_audit_components.py`` (2026-08-06) alongside the
``metrics.py`` → ``declarations.py`` split.
"""
from __future__ import annotations

from pathlib import Path

from maintainability_audit.cli import DEFAULT_CONFIG
from maintainability_audit.declarations import detect_functions, function_status
from maintainability_audit.metrics import read_lines


def _detect(tmp_path: Path, source: str, filename: str = "module.py") -> list:
    path = tmp_path / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return detect_functions(tmp_path, path, read_lines(path), DEFAULT_CONFIG["thresholds"])


def test_function_status_warning_paths() -> None:
    thresholds = {
        "max_function_lines": 10,
        "warn_function_lines": 5,
        "max_complexity": 10,
        "warn_complexity": 5,
    }

    assert function_status(7, 1, thresholds) == "warn"
    assert function_status(1, 7, thresholds) == "warn"


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

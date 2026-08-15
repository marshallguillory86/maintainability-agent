"""Grading a declaration: where it starts, how long it is, what it costs.

Extracted from ``metrics.py`` (2026-08-06). ``metrics`` answers "which
files, and how big"; this module answers "which declarations inside
them, and are they within budget". The detection strategies it dispatches
to live in ``_ranges`` (brace-bounded, for C-family sources) and in the
stdlib ``ast`` (exact, for Python).
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

from ._cognitive import brace_cognitive, python_cognitive
from ._finding_match import normalized_body_digest
from ._metrics_types import COMPLEXITY_RE, FUNC_PATTERNS, DeclRange, FunctionMetric
from ._ranges import indent_bounded_end, java_declaration_ranges, js_declaration_ranges

# Extensions handled by the brace-bounded scanner in ``_ranges``.
# `.mjs` and `.cjs` are the same JavaScript as `.js` — only the module
# system differs, and that is invisible to a brace-bounded scan. Their
# absence was not a decision: babel carried 1,503 unread `.mjs`/`.cjs`
# files, 8.5% of its source, while its `.js` was read normally.
BRACE_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".html"}

# Every extension we attempt declaration detection on at all.
# `.java` is listed separately from `BRACE_SUFFIXES`: Java is
# brace-delimited but its declarations are not the JS scanner's — it has
# constructors, annotations and generic parameter lists that the JS
# patterns would misread — so it gets its own detector in `_ranges`.
DECLARATION_SUFFIXES = {".py", ".java"} | BRACE_SUFFIXES


def function_status(lines: int, complexity: int, thresholds: dict[str, int], cognitive: int = 0) -> str:
    """Grade a function on length, branch count, and reading cost.

    ``cognitive`` defaults to 0 so callers that predate it — and configs
    without the thresholds — behave exactly as before.
    """
    max_cognitive = thresholds.get("max_cognitive_complexity")
    warn_cognitive = thresholds.get("warn_cognitive_complexity")
    if (
        lines > thresholds["max_function_lines"]
        or complexity > thresholds["max_complexity"]
        or (max_cognitive is not None and cognitive > max_cognitive)
    ):
        return "fail"
    if (
        lines > thresholds["warn_function_lines"]
        or complexity > thresholds["warn_complexity"]
        or (warn_cognitive is not None and cognitive > warn_cognitive)
    ):
        return "warn"
    return "ok"


def class_status(lines: int, thresholds: dict[str, int]) -> str:
    """Grade a class on length only, against its own budget.

    Two reasons this is not ``function_status``. A class is a container,
    so the per-function line budget is the wrong yardstick — an ordinary
    six-method class blew past ``max_function_lines`` and was reported
    as an over-long "function". And ``ast.walk`` yields a class *and*
    each of its methods, so the class's complexity is the sum of its
    methods' branches, already counted against those methods.
    """
    if lines > thresholds["max_class_lines"]:
        return "fail"
    if lines > thresholds["warn_class_lines"]:
        return "warn"
    return "ok"


def declaration_status(
    kind: str, lines: int, complexity: int, thresholds: dict[str, int], cognitive: int = 0
) -> str:
    if kind == "class":
        return class_status(lines, thresholds)
    return function_status(lines, complexity, thresholds, cognitive)


def _python_function_ranges(source: str) -> list[DeclRange] | None:
    """Parse Python source and return a ``DeclRange`` for every top-level
    or nested function/class definition.

    Uses ``ast.end_lineno`` (Python 3.8+) so the body length reflects the
    actual indented block, not the distance to the next sibling definition.
    Returns ``None`` if the source cannot be parsed so the caller can fall
    back to the regex-based detector.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return None
    ranges: list[DeclRange] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            end = getattr(node, "end_lineno", None) or node.lineno
            is_class = isinstance(node, ast.ClassDef)
            # A class is a container, not a thing that is read top to
            # bottom, so it carries no cognitive cost of its own — its
            # methods are charged individually.
            cognitive = 0 if is_class else python_cognitive(node)
            kind = "class" if is_class else "function"
            ranges.append(DeclRange(node.lineno, end, node.name, kind, cognitive))
    ranges.sort(key=lambda item: (item.start, item.end))
    return ranges


def _regex_function_ranges(lines: list[str]) -> list[DeclRange]:
    """Last-resort detector for Python that ``ast`` could not parse.

    That is its whole live domain. ``SourceIndex`` and ``collect_metrics``
    both gate on ``DECLARATION_SUFFIXES``, so no unknown extension reaches
    here — and none should: ``FUNC_PATTERNS`` matches ``def``, ``function``
    and arrows, so running it over Java or Go would report zero
    declarations found rather than no parser available, which is the
    difference between a wrong answer and an honest withhold.

    Each body is bounded by indentation rather than by the *next* pattern
    match. The old "next match minus one" rule silently assumed the
    pattern list was exhaustive; when it wasn't, one declaration absorbed
    everything to the following match or to end-of-file.
    """
    ranges: list[DeclRange] = []
    for number, line in enumerate(lines, start=1):
        for pattern, kind in FUNC_PATTERNS:
            match = pattern.search(line)
            if match:
                end = max(indent_bounded_end(lines, number), number)
                ranges.append(DeclRange(number, end, match.group(1), kind))
                break
    return ranges


def declaration_ranges(path: Path, lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Return declaration ranges plus the lines to score complexity against.

    JS/TS/HTML score against a comment- and string-masked copy of the
    source so ``if`` in a doc comment or ``?`` in a URL is not counted as
    a branch.
    """
    if path.suffix == ".py":
        parsed = _python_function_ranges("\n".join(lines))
        if parsed is not None:
            return parsed, lines
    if path.suffix == ".java":
        # Its own detector, never the last-resort patterns: those match
        # `def`, `function` and arrows, so on Java they find nothing and
        # report a confident zero. A zero that came from looking in the
        # wrong language is indistinguishable in the report from a file
        # with no methods in it.
        return java_declaration_ranges(lines)
    if path.suffix in BRACE_SUFFIXES:
        return js_declaration_ranges(lines)
    return _regex_function_ranges(lines), lines


def detect_functions(
    root: Path,
    path: Path,
    lines: list[str],
    thresholds: dict[str, int],
    parsed: tuple[list[DeclRange], list[str]] | None = None,
) -> list[FunctionMetric]:
    """Grade every declaration in one file.

    ``parsed`` lets a caller hand in ranges it has already computed —
    ``SourceIndex`` does, so a file is parsed once per audit rather than
    once per scanner. Passing nothing parses here, which keeps this
    usable standalone.
    """
    ranges, code = parsed if parsed is not None else declaration_ranges(path, lines)
    rel = str(path.relative_to(root)).replace(os.sep, "/")
    funcs: list[FunctionMetric] = []
    for decl in ranges:
        block = code[decl.start - 1 : decl.end]
        complexity = 1 + sum(len(COMPLEXITY_RE.findall(line)) for line in block)
        count = max(1, len(block))
        # Python declarations arrive with an exact figure from the AST;
        # everything else is inferred from brace depth over the body.
        cognitive = decl.cognitive if decl.cognitive is not None else brace_cognitive(block)
        funcs.append(
            FunctionMetric(
                path=rel,
                name=decl.name,
                start_line=decl.start,
                lines=count,
                complexity=complexity,
                status=declaration_status(decl.kind, count, complexity, thresholds, cognitive),
                kind=decl.kind,
                cognitive=cognitive,
                body_digest=normalized_body_digest(block),
            )
        )
    return funcs

"""Grading a declaration: where it starts, how long it is, what it costs.

Extracted from ``metrics.py`` (2026-08-06). ``metrics`` answers "which
files, and how big"; this module answers "which declarations inside
them, and are they within budget". The detection strategies it dispatches
to live in the stdlib ``ast`` (exact, for Python) and in one module per
language — ``_ranges_js``, ``_ranges_java``, ``_ranges_c`` — over the
shared brace machinery in ``_ranges_core``. ``SCANNERS`` below is the
whole dispatch: a language is a row in it, not a branch in a function.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path

from ._cognitive import brace_cognitive, python_cognitive
from ._finding_match import normalized_body_digest
from ._metrics_types import COMPLEXITY_RE, FUNC_PATTERNS, DeclRange, FunctionMetric
from ._ranges_c import c_declaration_ranges
from ._ranges_core import indent_bounded_end
from ._ranges_cpp import cpp_declaration_ranges
from ._ranges_java import java_declaration_ranges
from ._ranges_js import js_declaration_ranges

# One set per language, then one table binding each to its scanner.
#
# A language belongs here when this project can actually detect and score
# it — the rule the claim follows, rather than the other way round
# (Decision 10, amended 2026-08-26). Everything outside these sets keeps
# the honest path: file length, duplication and risk are measured, and
# declaration rates are **withheld** with the missing parser named, which
# is what P7 requires of a population nobody read.
PYTHON_SUFFIXES = {".py"}
# Java is brace-delimited but its declarations are not the JS scanner's —
# constructors, annotations and generic parameter lists the JS patterns
# would misread — so it has its own scanner, as every language here does.
JAVA_SUFFIXES = {".java"}
# `.h` stays C. It is the one extension both languages write, and C is
# the safer reading: the C scanner finds a C++ header's free functions
# and structs and misses its classes, which under-reports. The C++
# scanner aimed at a C header would read nothing it does not already.
C_SUFFIXES = {".c", ".h"}
# C++ (1.2.0). Classes with members, namespaces, templates, operator
# overloads and out-of-line definitions — none of which the C scanner
# knows, which is why it is a sibling module and not a C flag.
CPP_SUFFIXES = {".cpp", ".hpp", ".cc", ".cxx", ".hh"}
# `.mjs` and `.cjs` are the same JavaScript as `.js` — only the module
# system differs, and that is invisible to a brace-bounded scan. Their
# absence was not a decision: babel carried 1,503 unread `.mjs`/`.cjs`
# files, 8.5% of its source, while its `.js` was read normally.
BRACE_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".html"}

# Suffix set -> the scanner that reads it, tried in order. Python is not
# here: it is parsed exactly by `ast` and only falls back to a scan, so
# `declaration_ranges` handles it before consulting this table.
#
# **Adding a language is a row here, a module beside `_ranges_c`, and a
# row in `docs/language-support.md`** — no edit to the dispatcher, and no
# edit to `_ranges_core`. The three move together or the suite fails:
# `test_claimed_languages` compares this set against the documented one
# in both directions, and `test_every_claimed_language_has_its_own
# _scanner` fails if a suffix reaches the last-resort patterns.
SCANNERS: tuple[tuple[set[str], object], ...] = (
    (JAVA_SUFFIXES, java_declaration_ranges),
    (C_SUFFIXES, c_declaration_ranges),
    (CPP_SUFFIXES, cpp_declaration_ranges),
    (BRACE_SUFFIXES, js_declaration_ranges),
)

# Every extension we attempt declaration detection on at all.
DECLARATION_SUFFIXES = (
    PYTHON_SUFFIXES | JAVA_SUFFIXES | C_SUFFIXES | CPP_SUFFIXES | BRACE_SUFFIXES
)


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
    if path.suffix in PYTHON_SUFFIXES:
        parsed = _python_function_ranges("\n".join(lines))
        if parsed is not None:
            return parsed, lines
        # Only a syntax error reaches the patterns below, and only for
        # Python — which is the one language they were written for.
        return _regex_function_ranges(lines), lines
    for suffixes, scanner in SCANNERS:
        if path.suffix in suffixes:
            # Always the language's own scanner, never the last-resort
            # patterns: those match `def`, `function` and arrows, so on
            # Java or C they find nothing and report a confident zero. A
            # zero that came from looking in the wrong language is
            # indistinguishable in the report from a file that genuinely
            # has no declarations in it.
            return scanner(lines)
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

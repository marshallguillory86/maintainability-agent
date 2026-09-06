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

from ._cognitive import (
    brace_cognitive,
    cobol_cognitive,
    fortran_cognitive,
    python_cognitive,
    swift_cognitive,
)
from ._finding_match import normalized_body_digest
from ._metrics_types import (
    FUNC_PATTERNS,
    DeclRange,
    FunctionMetric,
    branch_points,
    cobol_branch_points,
    fortran_branch_points,
    go_branch_points,
    php_branch_points,
    ruby_branch_points,
    rust_branch_points,
    swift_branch_points,
)
from ._ranges_c import c_declaration_ranges
from ._ranges_cobol import cobol_declaration_ranges
from ._ranges_core import indent_bounded_end
from ._ranges_cpp import cpp_declaration_ranges
from ._ranges_csharp import csharp_declaration_ranges
from ._ranges_fortran import (
    fixed_form_declaration_ranges,
    fortran_declaration_ranges,
)
from ._ranges_go import go_declaration_ranges
from ._ranges_java import java_declaration_ranges
from ._ranges_js import js_declaration_ranges
from ._ranges_php import php_declaration_ranges
from ._ranges_ruby import ruby_declaration_ranges
from ._ranges_rust import rust_declaration_ranges
from ._ranges_swift import swift_declaration_ranges

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
# C# (1.3.0). Nearest to Java — types holding members, the same
# generics — and still its own module: namespaces in two forms,
# `record`, and properties, which are deliberately not declarations.
CSHARP_SUFFIXES = {".cs"}
SWIFT_SUFFIXES = {".swift"}
# Go: one extension, and no header/source split to worry about.
GO_SUFFIXES = {".go"}
RUST_SUFFIXES = {".rs"}
# PHP: `.phtml` is the same language with a template-first convention.
PHP_SUFFIXES = {".php", ".phtml"}
# Ruby: `.rake` and `.gemspec` are Ruby with a different job.
RUBY_SUFFIXES = {".rb", ".rake", ".gemspec"}
# COBOL, and the copybooks it includes. A `.cpy` carries DATA
# DIVISION text and no PROCEDURE DIVISION, so it mints nothing and is
# scanned for size like a C header full of prototypes.
COBOL_SUFFIXES = {".cbl", ".cob", ".cpy", ".CBL", ".COB", ".CPY"}
# Fortran (1.4.0), free-form only. `.F90` is the same language with the
# C preprocessor run over it, and `.pf` is pFUnit test source — both are
# free-form and both are read. Fixed-form (`.f`, `.for`, `.ftn`) is
# column-sensitive, a different scanner, and deliberately unclaimed:
# reading it with free-form rules would be an approximation nobody
# asked for, on the trees where our findings are least actionable.
FORTRAN_SUFFIXES = {".f90", ".f95", ".f03", ".f08",
                    ".F90", ".F95", ".F03", ".F08", ".pf"}
# Fixed-form Fortran (1.6.0). The same language and the same program
# units, laid out for punched cards: label in columns 1-5, a
# continuation marker in 6, the statement in 7-72. It shares the
# recogniser and the `end` bounding and differs only in how a line
# becomes a statement — which is why it is a masker rather than a
# second scanner. Claimed in 1.6.0 because legacy Fortran is where
# these findings are worth the most, and 1.4.0 left it unread.
FIXED_FORM_SUFFIXES = {".f", ".for", ".ftn", ".F", ".FOR", ".FTN"}
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
    (CSHARP_SUFFIXES, csharp_declaration_ranges),
    (SWIFT_SUFFIXES, swift_declaration_ranges),
    (GO_SUFFIXES, go_declaration_ranges),
    (RUST_SUFFIXES, rust_declaration_ranges),
    (PHP_SUFFIXES, php_declaration_ranges),
    (RUBY_SUFFIXES, ruby_declaration_ranges),
    (COBOL_SUFFIXES, cobol_declaration_ranges),
    (FORTRAN_SUFFIXES, fortran_declaration_ranges),
    (FIXED_FORM_SUFFIXES, fixed_form_declaration_ranges),
    (BRACE_SUFFIXES, js_declaration_ranges),
)

# How a declaration is *measured*, per language — the companion to
# SCANNERS, which decides how it is *found*. Both default to the C
# family; a language whose branches or nesting are spelled differently
# says so here.
#
# Fortran is why this table exists. It was measured with the C-family
# reading until 1.6.0, and the numbers were not approximate but wrong:
# `do` is not in the C pattern, so six nested loops scored complexity
# 1; `.and.`/`.or.` are not `&&`/`||`, so five operators scored 3;
# `end if` contains `if`, so every branch counted twice; and nesting
# was read from braces, which Fortran does not have, so four flat
# `if`s and four deeply nested ones both scored 8.
METRICS: tuple[tuple[set[str], object, object], ...] = (
    # Swift is braced and reads its nesting the C-family way; only the
    # keyword vocabulary differs, and `guard` is the difference that
    # matters — without it a guard-heavy function reads as branchless.
    (SWIFT_SUFFIXES, swift_branch_points, swift_cognitive),
    # Go has no `while`, no ternary and no `catch`, and it has `select` —
    # the concurrency branch the C pattern never looks for. A dispatch
    # loop counted only its cases, so the construct choosing between them
    # decided nothing.
    (GO_SUFFIXES, go_branch_points, brace_cognitive),
    # Rust branches on `match` arms, not on the `match` keyword — the
    # Fortran `select case` lesson — and `?` propagates an error rather
    # than deciding anything, while idiomatic Rust is full of it.
    (RUST_SUFFIXES, rust_branch_points, brace_cognitive),
    # PHP spells its multi-way branch `elseif`, one word with no boundary
    # inside it, so the C pattern matched neither `if` nor `elif` and a
    # dispatch chain scored zero. `foreach` is its primary loop and
    # `and`/`or`/`xor` are word operators.
    (PHP_SUFFIXES, php_branch_points, brace_cognitive),
    # Ruby's guard clause is `unless` and its negated loop is `until`,
    # neither of which the C pattern looks for, and `elsif` has one `e`
    # so `elif` misses it. A guard-heavy method read as branchless.
    (RUBY_SUFFIXES, ruby_branch_points, brace_cognitive),
    # COBOL closes scopes with hyphenated `END-` words and with the
    # period that ends a sentence; neither is in the C-family reading.
    (COBOL_SUFFIXES, cobol_branch_points, cobol_cognitive),
    (FORTRAN_SUFFIXES, fortran_branch_points, fortran_cognitive),
    (FIXED_FORM_SUFFIXES, fortran_branch_points, fortran_cognitive),
)


def metrics_for(suffix: str) -> tuple[object, object]:
    """``(branch counter, cognitive reader)`` for one suffix."""
    for suffixes, counter, cognitive in METRICS:
        if suffix in suffixes:
            return counter, cognitive
    return branch_points, brace_cognitive


# Every extension we attempt declaration detection on at all.
DECLARATION_SUFFIXES = (
    PYTHON_SUFFIXES | JAVA_SUFFIXES | C_SUFFIXES | CPP_SUFFIXES
    | CSHARP_SUFFIXES | SWIFT_SUFFIXES | GO_SUFFIXES | RUST_SUFFIXES
    | PHP_SUFFIXES | RUBY_SUFFIXES
    | COBOL_SUFFIXES
    | FORTRAN_SUFFIXES | FIXED_FORM_SUFFIXES
    | BRACE_SUFFIXES
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
    count_branches, read_cognitive = metrics_for(path.suffix)
    funcs: list[FunctionMetric] = []
    for decl in ranges:
        block = code[decl.start - 1 : decl.end]
        complexity = 1 + sum(count_branches(line) for line in block)
        count = max(1, len(block))
        # Python declarations arrive with an exact figure from the AST;
        # everything else is read from the body, by whichever reader the
        # language's nesting is written in.
        cognitive = decl.cognitive if decl.cognitive is not None else read_cognitive(block)
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

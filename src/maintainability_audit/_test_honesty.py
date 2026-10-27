"""Test honesty: where a suite has stopped testing (Decision 19).

After Ken Pugh's AlignThree Spectables, whose generated stubs fail until they
are written, so an unwritten step can never pass. A suite reports a skipped,
pending or expected-failure test as something other than a failure, and to a
reader who looks only at the result a skip is a pass. This names each one.

Reported only. Nothing here reaches `score_report` or a gate: the block is
attached after the score is sealed, on ADR 003's terms for findings whose
precision is unmeasured.
"""

from __future__ import annotations

import ast
import re
from collections import Counter
from pathlib import Path
from typing import Any

from ._metrics_types import is_test_path
from ._oracle import SUPPRESSION_MARKERS, _is_quoted
from .source import SourceIndex

CREDIT = ("After Ken Pugh's AlignThree Spectables (https://alignthree.com): "
          "a test that is not written, or not run, never counts as passing, "
          "and a test that computes its own expected value is testing itself.")

_SKIP_LABELS = frozenset({"skipped test", "disabled test", "ignored test"})

#: A skip written as a directive, from the oracle's own marker set, and as a
#: call, which a suite reports the same way.
_SKIPS = tuple(re.compile(pattern, re.IGNORECASE)
               for pattern, label in SUPPRESSION_MARKERS if label in _SKIP_LABELS) + (
    re.compile(r"\bpytest\.skip\("),
    re.compile(r"\bx(?:it|describe|test)\("),
    re.compile(r"\b(?:it|describe|test)\.(?:skip|todo)\("),
    re.compile(r"\bthis\.skip\(\)"),
)


def _skip_in(text: str) -> bool:
    """Whether this line skips a test, rather than mentioning a skip."""
    for pattern in _SKIPS:
        match = pattern.search(text)
        if match and not _is_quoted(text, match.start()):
            return True
    return False


def skipped_tests(root: Path, files: list[Path], source: SourceIndex) -> list[dict[str, Any]]:
    """Every skip in a test file of `files`, by path and line, in path order."""
    found: list[dict[str, Any]] = []
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        if not is_test_path(rel):
            continue
        for number, text in enumerate(source.lines(path), 1):
            if _skip_in(text):
                found.append({"path": rel, "line": number, "text": text.strip()[:180]})
    return found


_ARITHMETIC = (ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow)
_VARIABLE = (ast.Name, ast.Attribute, ast.Subscript)
_EQUALITY_METHODS = frozenset({"assertEqual", "assertEquals"})


_LITERAL_CONTAINERS = (ast.Set, ast.List, ast.Dict, ast.Tuple)


def _calls(node: ast.AST) -> bool:
    return any(isinstance(child, ast.Call) for child in ast.walk(node))


def _builds_text(node: ast.AST) -> bool:
    """A `/` or `+` over a string: a path join or a concatenation, not arithmetic."""
    return any((isinstance(leaf, ast.Constant) and isinstance(leaf.value, (str, bytes)))
               or isinstance(leaf, ast.JoinedStr) for leaf in ast.walk(node))


def _computes(node: ast.AST, from_calls: set[str]) -> bool:
    """Arithmetic on a variable, with no call: an expectation worked out, not stated.

    Arithmetic on literals alone (`2 * 60`) is a stated value written
    legibly. A variable holding another call's result (`plain + 1`, with
    `plain = measure(b)`) makes the comparison a relation between two
    results, which is a legitimate test, not a computed expectation.
    """
    if _calls(node) or _builds_text(node):
        return False
    if any(isinstance(leaf, ast.Name) and leaf.id in from_calls for leaf in ast.walk(node)):
        return False
    return any(isinstance(child, ast.BinOp) and isinstance(child.op, _ARITHMETIC)
               and any(isinstance(leaf, _VARIABLE) for leaf in ast.walk(child))
               for child in ast.walk(node))


def _subject(node: ast.AST) -> bool:
    """Whether this side is the code under test: a call, not a literal holding one."""
    return not isinstance(node, _LITERAL_CONTAINERS) and _calls(node)


def _equalities(function: ast.AST) -> list[tuple[ast.AST, ast.AST, int]]:
    """Each `assert a == b` and `assertEqual(a, b)` in `function`, as (a, b, line)."""
    found = []
    for node in ast.walk(function):
        if (isinstance(node, ast.Assert) and isinstance(node.test, ast.Compare)
                and len(node.test.ops) == 1 and isinstance(node.test.ops[0], ast.Eq)):
            found.append((node.test.left, node.test.comparators[0], node.lineno))
        elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
              and node.func.attr in _EQUALITY_METHODS and len(node.args) >= 2):
            found.append((node.args[0], node.args[1], node.lineno))
    return found


def _computed_lines(tree: ast.AST) -> set[int]:
    """Lines comparing a call's result with an expectation computed beside it."""
    lines: set[int] = set()
    for function in ast.walk(tree):
        if isinstance(function, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines |= _FunctionScope(function).computed_lines()
    return lines


class _FunctionScope:
    """One test function's local names, read once, for its comparisons."""

    def __init__(self, function: ast.AST) -> None:
        self.function = function
        # One hop through a local name: `expected = price * qty` or
        # `result = total(items)` stands for its value.
        self.assigned = {target.id: node.value for node in ast.walk(function)
                         if isinstance(node, ast.Assign)
                         for target in node.targets if isinstance(target, ast.Name)}
        self.from_calls = {name for name, value in self.assigned.items() if _calls(value)}
        self.reads = Counter(node.id for node in ast.walk(function)
                             if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load))

    def resolved(self, side: ast.AST) -> ast.AST:
        return self.assigned.get(side.id, side) if isinstance(side, ast.Name) else side

    def expectation(self, side: ast.AST) -> bool:
        # A name read anywhere else also built the input (`range(count)`),
        # so comparing against it is an invariant, not a worked-out answer.
        if isinstance(side, ast.Name) and self.reads[side.id] > 1:
            return False
        return _computes(self.resolved(side), self.from_calls)

    def computed_lines(self) -> set[int]:
        return {line for left, right, line in _equalities(self.function)
                if (_subject(self.resolved(left)) and self.expectation(right))
                or (_subject(self.resolved(right)) and self.expectation(left))}


def computed_expectations(root: Path, files: list[Path], source: SourceIndex) -> list[dict[str, Any]]:
    """Every Python test comparison whose expected value is computed in the test."""
    found: list[dict[str, Any]] = []
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        if path.suffix != ".py" or not is_test_path(rel):
            continue
        text = source.lines(path)
        try:
            tree = ast.parse("\n".join(text))
        except (SyntaxError, ValueError):
            continue
        found.extend({"path": rel, "line": line, "text": text[line - 1].strip()[:180]}
                     for line in sorted(_computed_lines(tree)))
    return found


def test_honesty(root: Path, files: list[Path], source: SourceIndex) -> dict[str, Any]:
    """The report block: findings and the credit they carry."""
    return {
        "skipped": skipped_tests(root, files, source),
        "computed_expected": computed_expectations(root, files, source),
        "credit": CREDIT,
    }

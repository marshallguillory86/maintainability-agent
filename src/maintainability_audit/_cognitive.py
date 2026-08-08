"""Cognitive complexity: how hard a body is to *read*, not how many paths it has.

The cyclomatic count this tool already emits is a keyword tally, and it is
blind to the thing that actually costs a reader. These two score
identically under it:

    def flat(a, b, c, d, e):        def nested(a, b, c, d, e):
        if a: return 1                  if a:
        if b: return 2                      if b:
        if c: return 3                          if c:
        if d: return 4                              if d:
        if e: return 5                                  if e:
        return 0                                            return 5
                                        return 0

Five guard clauses read top to bottom and can be understood one at a
time. Five levels of nesting must be held in the head at once. Counting
branches says they are the same; anyone who has maintained both knows
they are not.

So each flow break is charged *plus the depth it sits at*, following the
shape of SonarSource's cognitive complexity: nesting is what compounds.
``else`` costs one flat point rather than a nested one, because it
resolves a branch already being tracked instead of opening a new context.

Python is measured exactly from the AST. C-family sources have no parser
here, so nesting is inferred from brace depth over the ``_masking``-
scrubbed copy — approximate, and under-reports on brace-free single
statement bodies, which is the safe direction.
"""
from __future__ import annotations

import ast
import re

from ._masking import mask_lines

# Constructs that both cost a point and deepen the nesting for whatever
# they contain.
_NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)

# Constructs that deepen nesting without costing a point of their own: a
# nested function is a new context to hold, but defining one is not
# itself a branch.
_NESTING_ONLY = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)

_CONTROL_RE = re.compile(r"\b(if|for|while|catch|switch|case|elif|except)\b")
_ELSE_RE = re.compile(r"\belse\b")
_BOOLEAN_RE = re.compile(r"&&|\|\|")


def python_cognitive(node: ast.AST) -> int:
    """Exact cognitive complexity for one Python declaration."""
    return _walk_python(node, nesting=0, top=True)


def _boolean_sequences(node: ast.AST) -> int:
    """One point per run of boolean operators, not per operator.

    ``a and b and c`` is a single idea to read; charging it three times
    would push ordinary guard conditions over a threshold for no reason.
    """
    return sum(1 for child in ast.walk(node) if isinstance(child, ast.BoolOp))


def _walk_python(node: ast.AST, nesting: int, top: bool = False) -> int:
    score = 0
    for child in ast.iter_child_nodes(node):
        score += _score_python_child(child, nesting)
    if top:
        score += _boolean_sequences(node)
    return score


def _score_python_child(child: ast.AST, nesting: int) -> int:
    if isinstance(child, ast.If) and _is_elif_chain(child):
        # `elif` continues a decision already being tracked. Charge it
        # flat, and keep its body at the same depth as the `if` above it.
        return 1 + _walk_python(child, nesting)
    if isinstance(child, _NESTING_NODES):
        score = 1 + nesting + _walk_python(child, nesting + 1)
        return score + (1 if getattr(child, "orelse", None) else 0)
    if isinstance(child, _NESTING_ONLY):
        return _walk_python(child, nesting + 1)
    return _walk_python(child, nesting)


def _is_elif_chain(node: ast.If) -> bool:
    """Whether this ``If`` is the ``elif`` arm of the one above it.

    ``ast`` represents ``elif`` as an ``If`` that is the sole element of
    the parent's ``orelse``. There is no parent pointer, so the caller's
    perspective is unavailable; this checks the inverse — a node whose own
    ``orelse`` is exactly one ``If`` is the head of an elif chain, and its
    arms are charged flat by ``_score_python_child``.
    """
    orelse = node.orelse
    return len(orelse) == 1 and isinstance(orelse[0], ast.If)


def brace_cognitive(lines: list[str]) -> int:
    """Approximate cognitive complexity for a C-family declaration body.

    Nesting is read from brace depth relative to the declaration's own
    line, so a control keyword two braces deep costs three. Bodies written
    without braces (``if (x) return;``) are charged flat, which
    under-reports rather than over-reports.
    """
    masked = mask_lines(lines)
    score = 0
    depth = 0
    base: int | None = None
    for line in masked:
        opens = line.count("{")
        closes = line.count("}")
        # Closers that lead the line belong to the enclosing level, so
        # apply them before scoring anything on this line.
        leading = len(line) - len(line.lstrip())
        if line[leading : leading + 1] == "}":
            depth = max(0, depth - 1)
            closes -= 1
        if base is None and opens:
            base = depth
        nesting = max(0, depth - (base if base is not None else 0))
        score += _score_brace_line(line, nesting)
        depth = max(0, depth + opens - closes)
    return score


def _score_brace_line(line: str, nesting: int) -> int:
    score = 0
    for _ in _CONTROL_RE.finditer(line):
        score += 1 + nesting
    if _ELSE_RE.search(line):
        score += 1
    score += len(_BOOLEAN_RE.findall(line))
    return score

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

from ._masking import mask_fortran_lines, mask_lines

# Both live in `parsing`, and `_ranges_core` reaches nothing here, so this
# is a sibling import rather than a cycle. COBOL's mask is not in
# `_masking` with the others because it needs the whole file to know which
# division a line is in — see `_ranges_cobol.mask_cobol_lines`.
from ._ranges_cobol import mask_cobol_lines

# Constructs that both cost a point and deepen the nesting for whatever
# they contain.
_NESTING_NODES = (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler, ast.IfExp)

# Constructs that deepen nesting without costing a point of their own: a
# nested function is a new context to hold, but defining one is not
# itself a branch.
_NESTING_ONLY = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)

_CONTROL_RE = re.compile(r"\b(if|for|while|catch|switch|case|elif|except)\b")
#: Swift adds `guard` — an early exit that is its primary branching idiom —
#: and `repeat`, its do-while. Without them a function built from guards
#: reads as having no branches at all, which is the Fortran `do` defect in
#: another language: six nested loops once scored complexity 1 because the
#: pattern did not know the keyword.
_SWIFT_CONTROL_RE = re.compile(
    r"\b(if|for|while|catch|switch|case|guard|repeat)\b"
)
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


# Fortran opens blocks with keywords and closes them with `end`, so the
# brace reader sees no nesting at all in it: measured before this
# existed, four sequential `if`s and four *deeply nested* `if`s both
# scored 8. Cognitive complexity exists to say that nesting is what
# makes code hard to hold in your head, so on Fortran the metric was
# reporting the one thing it is for as absent.
#
# `if (...) then` opens; a single-line `if (...) x = 1` does not. That
# `then` is the whole difference, and it is why this reads the statement
# rather than counting keywords.
_F_OPENS_RE = re.compile(
    r"^\s*(?:\w+\s*:\s*)?(?:"
    # `do <label>` is Fortran 77's loop, closed by the labelled statement
    # rather than by `end do`. Counting it as an opener here would raise
    # the nesting depth and never lower it, over-charging every construct
    # after it — so it is left out, and nesting inside a labelled loop is
    # under-counted instead.
    r"if\b.*\bthen\s*$|do\b(?!\s+\d)|select\s+(?:case|type)\b|where\s*\(.*\)\s*$|"
    r"associate\b|block\s*$|forall\s*\(.*\)\s*$|critical\b|team\b"
    r")",
    re.I,
)
_F_CLOSES_RE = re.compile(
    r"^\s*end\s*(?:if|do|where|forall|select|associate|block|critical|team)\b",
    re.I,
)
# `else`, `else if` and `elsewhere` are the continuation of a decision
# already charged, so they cost one flat — the same rule the brace
# reader applies to `else`.
_F_ELSE_RE = re.compile(r"^\s*(?:else\b|elsewhere\b|case\b)", re.I)
_F_CONTROL_RE = re.compile(
    r"\b(?:if|do|where|forall)\b|\bselect\s+(?:case|type)\b", re.I
)
_F_BOOLEAN_RE = re.compile(r"\.and\.|\.or\.", re.I)
_F_CLOSER_WORD_RE = re.compile(
    r"\bend\s*(?:if|do|where|forall|select|associate|block|critical|team)\b", re.I
)


def fortran_cognitive(lines: list[str]) -> int:
    """Cognitive complexity for a Fortran program unit.

    Nesting is counted from the constructs themselves — `if … then`,
    `do`, `select case`, `where`, `associate`, `block` — because there
    are no braces to read it from. A control keyword two constructs deep
    costs three, exactly as in the brace reader, so the two languages'
    numbers mean the same thing.
    """
    masked = mask_fortran_lines(lines)
    score = 0
    depth = 0
    for line in masked:
        statement = line.split("!", 1)[0].rstrip()
        if _F_CLOSES_RE.match(statement):
            depth = max(0, depth - 1)
            continue
        if _F_ELSE_RE.match(statement):
            score += 1
            score += len(_F_BOOLEAN_RE.findall(statement))
            continue
        body = _F_CLOSER_WORD_RE.sub(" ", statement)
        for _ in _F_CONTROL_RE.finditer(body):
            score += 1 + depth
        score += len(_F_BOOLEAN_RE.findall(body))
        if _F_OPENS_RE.match(statement):
            depth += 1
    return score


_CB_CLOSES_RE = re.compile(r"\bEND-(?:IF|EVALUATE|PERFORM|SEARCH|READ|STRING)\b", re.I)
_CB_OPENS_RE = re.compile(
    r"\bIF\b|\bEVALUATE\b|\bPERFORM\b(?=[^.]*\b(?:UNTIL|VARYING|TIMES)\b)|\bSEARCH\b",
    re.I,
)
_CB_ELSE_RE = re.compile(r"^\s*ELSE\b|\bWHEN\b", re.I)  # noqa: S5850 - alternation is intended
_CB_BOOLEAN_RE = re.compile(r"\b(?:AND|OR)\b", re.I)
_CB_CONTROL_RE = re.compile(r"\b(?:IF|EVALUATE|UNTIL|VARYING|TIMES|SEARCH)\b", re.I)


def cobol_cognitive(lines: list[str]) -> int:
    """Cognitive complexity for a COBOL paragraph.

    Nesting is read from the constructs themselves, as in Fortran, since
    COBOL has no braces either. What COBOL adds is a second way to close
    every open scope at once: **a period ends the sentence and with it
    every construct the sentence opened.** Classic COBOL leans on that
    entirely — `IF X DISPLAY Y.` opens and closes an `IF` with no
    `END-IF` anywhere — and a reader that only counted `END-` terminators
    would let depth climb monotonically through a paragraph and charge
    the last statement for every branch above it.

    The `PERFORM` lookahead is the other judgment. `PERFORM SOME-PARA` is
    a call and opens nothing; `PERFORM UNTIL DONE` is a loop and does.
    Counting every `PERFORM` as nesting would make an ordinary
    call-per-line paragraph read as deeply nested.
    """
    masked = mask_cobol_lines(lines)
    score = 0
    depth = 0
    for line in masked:
        statement = line.rstrip()
        if not statement.strip():
            continue
        if _CB_CLOSES_RE.search(statement):
            depth = max(0, depth - len(_CB_CLOSES_RE.findall(statement)))
        body = _CB_CLOSES_RE.sub(" ", statement)
        if _CB_ELSE_RE.search(body):
            score += 1
            score += len(_CB_BOOLEAN_RE.findall(body))
        else:
            for _ in _CB_CONTROL_RE.finditer(body):
                score += 1 + depth
            score += len(_CB_BOOLEAN_RE.findall(body))
        depth += len(_CB_OPENS_RE.findall(body))
        if statement.rstrip().endswith("."):
            # The sentence ended, and with it every scope it opened.
            depth = 0
    return score


def brace_cognitive(lines: list[str], control: re.Pattern[str] | None = None) -> int:
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
        score += _score_brace_line(line, nesting, control or _CONTROL_RE)
        depth = max(0, depth + opens - closes)
    return score


def _score_brace_line(line: str, nesting: int, control: re.Pattern[str]) -> int:
    score = 0
    for _ in control.finditer(line):
        score += 1 + nesting
    if _ELSE_RE.search(line):
        score += 1
    score += len(_BOOLEAN_RE.findall(line))
    return score


def swift_cognitive(lines: list[str]) -> int:
    """`brace_cognitive` reading Swift's control keywords.

    Swift is braced, so nesting is read the same way; only the vocabulary
    differs, and `guard` is the difference that matters.
    """
    return brace_cognitive(lines, _SWIFT_CONTROL_RE)

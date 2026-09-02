"""Declaration ranges for free-form Fortran.

The first language in this family that has no braces. C, C++, C# and
Java all share `_ranges_core.scan_bounded` because a body sits between
`{` and `}`; Fortran closes a program unit with a *keyword* — a
`subroutine` ends at `end subroutine`, a `module` at `end module`, and a
bare `end` is legal for several of them.

So the rule is shared and the mechanism is not. `scan_bounded` takes a
`find_end` argument, and this module supplies `_fortran_end`: the same
guarantee — a range never runs past its own body, and never to
end-of-file — enforced by counting program units instead of braces.

**Free-form only** (`.f90`, `.f95`, `.f03`, and their preprocessed
`.F90` spellings, plus pFUnit's `.pf`). Fixed-form (`.f`, `.for`,
`.ftn`) is column-sensitive — a comment is `C` in column 1, a
continuation is any character in column 6 — which is a different scanner
with different failure modes, and it stays unclaimed rather than being
approximated here.

Two Fortran-specific rules earn their place:

- An `interface` block is **stepped over, not descended into**. It holds
  procedure signatures with no bodies, so walking in would mint a
  declaration for every procedure a module merely *describes*, each one
  a line or two long, diluting the population every rate divides by.
- A `function` may be written with a type prefix
  (`real(dp) function norm(v)`) or a `result` clause
  (`function norm(v) result(r)`). Both name `norm`.
"""
from __future__ import annotations

import re

from ._masking import mask_fixed_form_lines, mask_fortran_lines
from ._metrics_types import DeclRange
from ._ranges_core import indent_bounded_end, scan_bounded

_NAME = r"[A-Za-z_]\w*"
# Prefixes that may lead a procedure statement. `recursive`, `pure`,
# `elemental` and friends are modifiers; a type prefix (`real(dp)`,
# `integer`, `type(point)`, `character(len=*)`) is part of a function's
# return type and is stripped for the same reason C's is.
_PREFIX = (
    r"(?:(?:recursive|pure|impure|elemental|module|non_recursive)\s+)*"
    r"(?:(?:integer|real|double\s+precision|complex|logical|character|type|class)"
    r"(?:\s*\([^)]*\)|\s*\*\s*\d+)?\s+)?"
    r"(?:(?:recursive|pure|impure|elemental)\s+)*"
)
_SUBROUTINE_RE = re.compile(rf"^{_PREFIX}subroutine\s+({_NAME})", re.I)
_FUNCTION_RE = re.compile(rf"^{_PREFIX}function\s+({_NAME})", re.I)
# Containers. `submodule (parent) child` names the child.
_MODULE_RE = re.compile(rf"^module\s+({_NAME})\s*$", re.I)
_SUBMODULE_RE = re.compile(rf"^submodule\s*\([^)]*\)\s*({_NAME})", re.I)
_PROGRAM_RE = re.compile(rf"^program\s+({_NAME})", re.I)
# A derived type definition: `type :: point`, `type, extends(base) :: p`,
# or the older `type point`. `type(point) :: v` declares a *variable* and
# is excluded by requiring `::` or end-of-statement after the name.
_TYPE_RE = re.compile(
    rf"^type(?:\s*,[^:]*)?(?:\s*::\s*|\s+)({_NAME})\s*$", re.I
)
# An interface block, named or not. Stepped over: signatures, no bodies.
_INTERFACE_RE = re.compile(r"^(?:abstract\s+)?interface(?:\s+(\S+))?\s*$", re.I)
# `end`, `end subroutine`, `end subroutine name`, `endsubroutine`.
_END_RE = re.compile(
    r"^end\s*(program|module|submodule|subroutine|function|type|interface|block\s*data)?\b",
    re.I,
)
# Statements that open a unit for the purpose of depth counting. A
# `module procedure` inside an interface is not an opener, and `module`
# as a procedure prefix (`module subroutine f`) is matched as the
# subroutine it leads rather than as a module.
_OPENERS = (
    _SUBMODULE_RE, _MODULE_RE, _PROGRAM_RE, _SUBROUTINE_RE,
    _FUNCTION_RE, _TYPE_RE, _INTERFACE_RE,
)
# `if (...) then` / `do` / `select case` open blocks that also close with
# `end`, so they must be counted or a unit ends at the first `end if`.
_BLOCK_OPENER_RE = re.compile(
    r"^(?:\w+\s*:\s*)?(?:if\b.*\bthen\s*$|do\b|select\s+(?:case|type)\b|"
    r"associate\b|block\s*$|where\b.*\)\s*$|forall\b|critical\b|"
    r"enum\b|team\b)",
    re.I,
)
_BLOCK_END_RE = re.compile(
    r"^end\s*(if|do|select|associate|block|where|forall|critical|enum|team)\b", re.I
)
# `contains` separates a unit's body from the procedures it holds. It is
# not a declaration and does not open or close anything.
_CONTAINS_RE = re.compile(r"^contains\s*$", re.I)
# Fortran 77's loop: `DO 20 I = 1, N`, closed by the statement
# labelled 20 — usually `20 CONTINUE` — and not by an `END DO`. A
# reader that counts it as an opener and waits for `END DO` never
# balances, so the enclosing procedure never finds its own end.
_LABELLED_DO_RE = re.compile(r"^do\s+(\d+)\b", re.I)
_LEADING_LABEL_RE = re.compile(r"^(\d+)\b")


def _statement(text: str) -> str:
    """One line reduced to the statement a scanner can read.

    Free-form Fortran comments start with `!` anywhere outside a string,
    and `_masking` has already blanked strings, so cutting at the first
    `!` is safe here. A trailing `&` is a continuation marker and says
    nothing about the statement's shape.
    """
    statement = text.split("!", 1)[0].strip()
    return statement[:-1].strip() if statement.endswith("&") else statement


def _unlabelled(statement: str) -> str:
    """A statement with any leading fixed-form label removed."""
    label = _LEADING_LABEL_RE.match(statement)
    return statement[label.end():].strip() if label else statement


def _fortran_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a Fortran program unit on one masked line."""
    statement = _unlabelled(_statement(text))
    if not statement:
        return None

    interface = _INTERFACE_RE.match(statement)
    if interface is not None:
        return interface.group(1) or "interface", "interface"

    for pattern, kind in (
        (_SUBMODULE_RE, "class"), (_MODULE_RE, "class"), (_PROGRAM_RE, "class"),
        (_TYPE_RE, "class"),
        (_SUBROUTINE_RE, "function"), (_FUNCTION_RE, "function"),
    ):
        match = pattern.match(statement)
        if match is not None:
            return match.group(1), kind
    return None


def _fortran_end(masked: list[str], lines: list[str], start: int) -> int:
    """The line closing the program unit opened at ``start``.

    Depth-counted rather than matched by name, because `end` alone
    legally closes a subroutine and because `if`/`do`/`select` blocks
    close with `end` too — matching the first `end` would stop a
    procedure at its first `end if`. Everything that opens is counted,
    everything that ends decrements, and the unit closes when the count
    returns to zero.

    Falls back to indentation when the unit never closes, so a truncated
    file costs one declaration rather than everything after it.
    """
    depth = 0
    pending_labels: list[str] = []
    for number in range(start, len(masked) + 1):
        statement = _statement(masked[number - 1])
        if not statement:
            continue
        label = _LEADING_LABEL_RE.match(statement)
        if label is not None:
            # The statement carrying a pending label closes the loop that
            # named it. Several loops may share one terminator, so every
            # match is popped.
            while pending_labels and pending_labels[-1] == label.group(1):
                pending_labels.pop()
                depth -= 1
            statement = statement[label.end():].strip()
            if not statement:
                continue
        if _END_RE.match(statement) or _BLOCK_END_RE.match(statement):
            depth -= 1
            if depth <= 0:
                return number
            continue
        labelled_do = _LABELLED_DO_RE.match(statement)
        if labelled_do is not None:
            pending_labels.append(labelled_do.group(1))
            depth += 1
            continue
        if _BLOCK_OPENER_RE.match(statement) or any(
            pattern.match(statement) for pattern in _OPENERS
        ):
            depth += 1
    return max(indent_bounded_end(lines, start), start)


def fortran_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Program units, each bounded by its own `end`.

    Modules, submodules, programs and derived types are descended into,
    because that is where procedures live; a subroutine or function body
    is stepped over, so no statement inside one is read as a declaration.
    Interface blocks are stepped over without being graded.

    Everything it misses, it misses in the safe direction:

    - **Fixed-form source** (`.f`, `.for`, `.ftn`) is not claimed at all,
      rather than being read with free-form rules.
    - **Statement functions** — a one-line `f(x) = x*2` — are not
      declarations here.
    - **Declarations produced by `#include` or a preprocessor macro** are
      invisible, as in C.
    - **A procedure whose `end` is missing** is bounded by indentation,
      which in Fortran is a weak signal; it costs that one declaration.
    """
    return scan_bounded(
        lines,
        _fortran_declaration,
        descend=("class",),
        ignore=("interface",),
        skip_bare=False,
        find_end=_fortran_end,
        mask=mask_fortran_lines,
    )


def fixed_form_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """The same program units, read from fixed-form source (1.6.0).

    Fortran 77 laid its source out for punched cards: a label in columns
    1-5, a continuation marker in column 6, the statement in 7-72, and a
    sequence number after that. `C` in column 1 is a comment.

    None of that changes what a program unit *is*, so this shares the
    recogniser and the `end`-keyword bounding with free-form and differs
    only in how a line becomes a statement — which is the whole reason
    `scan_bounded` takes a masker. The scanner that reads a `SUBROUTINE`
    is the scanner that reads a `subroutine`.

    Two limits are worth stating. Indentation carries no meaning in
    fixed-form, so the fallback for an unclosed unit is weaker here than
    in free-form — it will usually bound at the next unit rather than
    sensibly. And a `D` in column 1 is a debug line in several legacy
    dialects but is not standard, so it is read as code rather than
    guessed at.
    """
    return scan_bounded(
        lines,
        _fortran_declaration,
        descend=("class",),
        ignore=("interface",),
        skip_bare=False,
        find_end=_fortran_end,
        mask=mask_fixed_form_lines,
    )

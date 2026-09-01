"""Declaration ranges for C.

One of the per-language scanners split out of ``_ranges.py`` in 1.1.0,
and the first member of the C *family*: the C++ (1.2.0) and C# (1.3.0)
increments arrive as siblings beside it, sharing ``_ranges_core`` the
same way rather than extending each other.

Kept separate from Java for the reason Java is kept separate from JS: they
share brace-bounding (``_block_end``, ``_is_bare_signature`` and
``indent_bounded_end`` all serve C unchanged) and nothing else. C has no
classes or methods — its declarations are file-scope functions and the
``struct``/``enum``/``union`` types — no ``function`` keyword, no generics,
and a preprocessor that writes function-shaped macros the other scanners
never meet. The house rule holds: mask comments and strings first, bound each body
by its own braces, and under-report — a construct not recognised costs one
missed finding, never a cascade.
"""
from __future__ import annotations

import re

from ._masking import mask_lines
from ._metrics_types import DeclRange
from ._ranges_core import _block_end, _is_bare_signature, indent_bounded_end

# Storage/qualifier keywords stripped once per line so the function pattern
# stays simple. Type keywords (`const`, `unsigned`, `long`, `struct`) are NOT
# stripped: they are part of the return type the name pattern reads.
_C_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:static|inline|extern|register|auto|_Noreturn|_Thread_local"
    r"|__inline|__inline__|__forceinline)\s+)*"
)
# `struct Foo {`, `enum E {`, `union U {`, and their `typedef` forms. The body
# brace — or a bare name before one opens on the next line — is what separates
# a type definition from a variable of that type (`struct Foo bar;`) or a
# forward declaration (`struct Foo;`), neither of which matches.
_C_TYPE_RE = re.compile(
    r"^(?:typedef\s+)?(struct|enum|union)\s+([A-Za-z_]\w*)\s*(?:\{|$)"
)
# A return type (one or more word/pointer tokens), then the function name, then
# its parameter list. The non-greedy prefix takes the *last* identifier before
# `(` as the name, so `const char *dup(` yields `dup`. A line with no return
# type before the name — `if (`, a call `foo(` — cannot match, which is what
# keeps control-flow and call expressions out without a keyword list doing it.
_C_FUNCTION_RE = re.compile(r"^[A-Za-z_][\w \t*]*?[ \t*]([A-Za-z_]\w*)\s*\(")
# `name(` shapes that are never a declaration even with a leading token.
_C_NOT_A_DECLARATION = frozenset(
    {"if", "for", "while", "switch", "return", "sizeof", "do", "else",
     "goto", "case", "default", "typedef", "struct", "enum", "union"}
)


def _c_declaration(text: str) -> tuple[str, str] | None:
    """``(name, kind)`` for a C declaration on one masked, non-# line."""
    body = text[_C_MODIFIER_RE.match(text).end():]
    type_match = _C_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(2), "class"
    func = _C_FUNCTION_RE.match(body)
    if func is None or func.group(1) in _C_NOT_A_DECLARATION:
        return None
    return func.group(1), "function"


def c_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """File-scope functions and `struct`/`enum`/`union` types, each bounded by
    its own body.

    Prototypes (`int f(int);`) open no body and are dropped by
    `_is_bare_signature`, so a header of declarations mints no population.
    Preprocessor lines are skipped outright — a function-like macro
    (`#define MAX(a, b) ...`) is not a function. A function's body is stepped
    over once its end is known, so no statement inside it is offered to the
    matcher; a type's body is stepped over too, because its members are
    fields, not declarations.

    Deliberate limitations, all under-reporting:

    - A return type on its own line above the name (`static int\\ncompute(...)`)
      is not joined, so that definition is missed.
    - An anonymous `typedef struct { ... } Name;` is not named or counted.
    - Function-pointer typedefs and K&R parameter declarations end on `;` and
      read as signatures.
    """
    masked = mask_lines(lines)
    ranges: list[DeclRange] = []
    number = 1
    while number <= len(masked):
        text = masked[number - 1]
        if text.lstrip().startswith("#"):        # preprocessor directive
            number += 1
            continue
        found = _c_declaration(text)
        if found is None:
            number += 1
            continue
        end = _block_end(masked, number)
        if end is None:
            end = indent_bounded_end(lines, number)
        end = max(end, number)
        if _is_bare_signature(masked, number, end):
            number = end + 1                     # a prototype: a shape, no body
            continue
        ranges.append(DeclRange(number, end, found[0], found[1]))
        number = end + 1                         # step over the body; no descent
    ranges.sort(key=lambda item: (item.start, item.end))
    return ranges, masked

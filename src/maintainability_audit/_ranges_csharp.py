"""Declaration ranges for C#.

The third C-family increment (1.3.0), and the one that most resembles
Java: types holding members, generics written the same way, and
attributes where Java writes annotations. It still gets its own module,
because the differences are the kind that a shared regex family turns
into a list of exceptions — namespaces (including the file-scoped
``namespace Foo;`` form), ``record``, properties, and expression-bodied
members.

The walk is ``scan_bounded`` from ``_ranges_core``, shared with C, C++
and Java, and ``_mask_generics`` is shared with Java. What lives here is
only what C# spells differently.

**Properties are deliberately not declarations.** ``public int Count {
get; set; }`` has braces and would bound cleanly, and counting it would
put a member nobody maintains into the denominator of every declaration
rate — thousands of them in an ordinary C# tree, each one line long,
each diluting the population that the score is computed from. They are
skipped by construction rather than by a rule: a property has no
parameter list, and every pattern here requires one.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _mask_generics, _matching_paren, scan_bounded

# Modifiers stripped once per line so the patterns stay small. `async`,
# `partial` and `required` are here for the same reason `static` is: they
# lead a declaration and say nothing about what it is.
_CS_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|internal|static|abstract|virtual|override"
    r"|sealed|async|partial|readonly|unsafe|extern|new|const|event|volatile"
    r"|implicit|explicit|required|file)\s+)*"
)
# `namespace Foo {`, and C# 10's file-scoped `namespace Foo;`. Neither is
# a declaration anyone maintains; the braced form is walked into, and the
# file-scoped form declares nothing at all and is simply not matched.
_CS_NAMESPACE_RE = re.compile(r"^namespace\s+[A-Za-z_][\w.]*\s*\{")
_CS_FILE_SCOPED_NAMESPACE_RE = re.compile(r"^namespace\s+[A-Za-z_][\w.]*\s*;")
# `class W`, `interface I`, `struct S`, `record R`, `record struct P`,
# `enum E`. The name may be followed by a body, a base list, a generic
# constraint (`where`), or end of line when the brace opens below.
_CS_TYPE_RE = re.compile(
    r"^(?:class|interface|struct|enum|record(?:\s+(?:class|struct))?)"
    r"\s+([A-Za-z_]\w*)\s*(?:\{|:(?!:)|where\b|$)"
)
# An attribute on its own line — `[Test]`, `[Obsolete("x")]` — leads a
# declaration and is not one. Stripped rather than matched, so the
# declaration below it is still read.
_CS_ATTRIBUTE_RE = re.compile(r"^\s*\[[^\]]*\]\s*")
# An optional return type, then the name, then the parameter list. `=` is
# excluded from the return-type characters so `var x = F();` cannot read
# as a declaration of `F`.
_CS_NAME = r"~?[A-Za-z_]\w*"
_CS_MEMBER_RE = re.compile(rf"^(?:[\w.<>,\[\]?\s]+?[\s\]?])?({_CS_NAME})\s*\(")
# What may follow the parameter list: a body, an expression body, a
# constructor chain (`: base(...)`), a generic constraint, or `;` for a
# declaration the caller then skips as bodyless.
_CS_MEMBER_TAIL_RE = re.compile(r"^\s*(?:$|\{|;|=>|:(?!:)|where\b)")
# `name(` is also the shape of a call, a control-flow header and a
# `base(...)` chain. Kept short for the reason Java's list is: every
# entry also blocks a legitimate method of that name.
_CS_NOT_A_DECLARATION = frozenset(
    {"if", "for", "foreach", "while", "switch", "catch", "lock", "using",
     "fixed", "return", "new", "base", "this", "throw", "do", "else",
     "checked", "unchecked", "nameof", "typeof", "sizeof", "await", "yield",
     "when", "with", "get", "set", "add", "remove", "value"}
)


def _csharp_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a C# declaration on one masked line.

    ``kind`` is ``None`` for a braced namespace: walk in, grade nothing.
    """
    line = _CS_ATTRIBUTE_RE.sub("", _mask_generics(text), count=1)
    body = line[_CS_MODIFIER_RE.match(line).end():]

    if _CS_FILE_SCOPED_NAMESPACE_RE.match(body):
        return None
    if _CS_NAMESPACE_RE.match(body):
        return "namespace", None

    type_match = _CS_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(1), "class"

    member = _CS_MEMBER_RE.match(body)
    if member is None or member.group(1).lstrip("~") in _CS_NOT_A_DECLARATION:
        return None
    opening = body.index("(", member.end(1))
    closing = _matching_paren(body, opening)
    if closing is None:
        # Parameters continue on the next line. This line is not inside a
        # method body — those are stepped over — so the shape is enough,
        # and the body's own braces still bound the range.
        return member.group(1), "function"
    if not _CS_MEMBER_TAIL_RE.match(body[closing + 1:]):
        return None
    return member.group(1), "function"


def csharp_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Methods, constructors and types, each bounded by its own body.

    Types are descended into, because that is where members live; a
    method body is stepped over, so no statement inside one is read as a
    declaration. Braced namespaces are walked into without being graded,
    and a file-scoped `namespace Foo;` declares nothing and is ignored.

    Bodyless members are skipped, as in C and C++: an interface method,
    an abstract method and a positional `record Point(int X, int Y);`
    are shapes with nothing to measure, and grading them would put
    one-line members into the population every rate divides by.

    Everything it misses, it misses in the safe direction:

    - **Properties and expression-bodied members without parameters**
      (`public int Area => w * h;`) are not declarations here.
    - **Local functions** live inside a method body and are not counted.
    - **A declaration produced by a source generator** is not in the
      tree and is not seen.
    - **Conditional compilation is not evaluated**, so a member in a
      disabled `#if` arm still counts.
    """
    return scan_bounded(
        lines, _csharp_declaration, descend=("class",), skip_preprocessor=True
    )

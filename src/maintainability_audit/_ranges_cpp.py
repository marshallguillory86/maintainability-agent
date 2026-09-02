"""Declaration ranges for C++.

The second member of the C family (1.2.0), a sibling of ``_ranges_c``
rather than an extension of it. C++ is not C with more keywords: it has
classes with members, namespaces, templates, operator overloads,
constructors with initialiser lists, and out-of-line definitions written
``void Widget::draw()``. A scanner that tried to be both would be a list
of exceptions to itself, which is the reason Java and JS are separate
too.

What it shares is the part that must never diverge: the walk. Both use
``scan_bounded`` from ``_ranges_core``, so a body is bounded by its own
braces in exactly the same way, and a fix to that rule reaches every
language at once.

Two behaviours are borrowed from either side deliberately. Types are
**descended into**, as in Java, because a C++ class holds its methods.
Bodyless signatures are **skipped**, as in C, because a declaration in a
header (``void draw();``, ``virtual void f() = 0;``, ``Widget() =
default;``) is a shape and not a definition — counting it would report a
population the file does not contain.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _matching_paren, scan_bounded

# Storage, linkage and specifier keywords, stripped once per line so the
# patterns below stay small. Type keywords (`const`, `unsigned`, `long`)
# are NOT here: they are part of the return type the name pattern reads.
_CPP_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:static|inline|virtual|explicit|friend|mutable|extern|register"
    r"|constexpr|consteval|constinit|thread_local|__forceinline"
    r"|\[\[[^\]]*\]\])\s+)*"
)
# `template <...>` may sit on its own line or lead the declaration. Either
# way it is not itself a declaration, so it is stripped and whatever
# follows is matched. Balanced `<>` are not tracked: a template header
# spanning lines leaves an empty line the loop simply walks past.
_CPP_TEMPLATE_RE = re.compile(r"^\s*template\s*<[^;{]*>\s*")
# `namespace ns {` — walked into, never graded. A namespace is a
# container for declarations and is not a declaration anyone maintains.
_CPP_NAMESPACE_RE = re.compile(r"^namespace(?:\s+([A-Za-z_][\w:]*))?\s*(?:\{|$)")
# `class W {`, `struct S final : public B {`, `union U {`, `enum class E {`.
# A name followed by `{`, a base-clause `:`, or end of line (the brace
# opens below). `struct Foo bar;` and `struct Foo;` match none of those,
# so a variable and a forward declaration stay uncounted.
_CPP_TYPE_RE = re.compile(
    r"^(?:typedef\s+)?(?:class|struct|union|enum(?:\s+(?:class|struct))?)"
    r"\s+(?:\[\[[^\]]*\]\]\s*)?([A-Za-z_]\w*)(?:\s+final)?\s*(?:\{|:(?!:)|$)"
)
# `public:` / `private:` / `protected:` and a lone label are not
# declarations, and must not be read as one before the member patterns run.
_CPP_ACCESS_RE = re.compile(r"^(?:public|private|protected)\s*:")
# An optional return type, then the name, then the parameter list. The
# name may be qualified (`Widget::draw`), a destructor (`~Widget`), or an
# operator (`operator==`, `operator()`, `operator[]`). `=` is excluded
# from the return-type characters so `int x = f();` cannot be read as a
# declaration of `f`.
_CPP_NAME = r"(?:~?[A-Za-z_]\w*(?:\s*::\s*~?[A-Za-z_]\w*)*|operator\s*(?:\(\)|\[\]|[^\s(]{1,3}))"
# Group 1 is the return type, if one is written. Whether it is present
# decides whether an end-of-line tail may be trusted — see below.
_CPP_FUNCTION_RE = re.compile(
    rf"^((?:[\w:<>,\s*&\[\]]+?[\s*&])?)({_CPP_NAME})\s*\("
)
# What may follow the parameter list of a real function: a body, a
# trailing return type, an initialiser list, a cv/ref/exception
# qualifier, a `= default`/`= delete`/`= 0`, or a `;` for a declaration
# the caller will then skip as bodyless.
_CPP_FUNCTION_TAIL_RE = re.compile(
    r"^\s*(?:\{|;|:(?!:)|->|const\b|noexcept\b|override\b|final\b|volatile\b"
    r"|&&?\s*(?:\{|;|const\b|noexcept\b)|=\s*(?:0|default|delete)\b|throw\b)"
)
# `name(` is also the shape of a control-flow header, a cast and a
# `sizeof`. None of those can be a declaration. Kept short for the reason
# Java's list is: every entry also blocks a legitimate member of that name.
_CPP_NOT_A_DECLARATION = frozenset(
    {"if", "for", "while", "switch", "catch", "return", "sizeof", "new",
     "delete", "throw", "do", "else", "case", "default", "static_assert",
     "decltype", "noexcept", "alignof", "static_cast", "dynamic_cast",
     "const_cast", "reinterpret_cast", "typedef", "using", "namespace",
     "class", "struct", "union", "enum", "template", "requires"}
)


def _cpp_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a C++ declaration on one masked line.

    ``kind`` is ``None`` for a namespace: walk in, grade nothing.
    """
    line = _CPP_TEMPLATE_RE.sub("", text, count=1)
    if _CPP_ACCESS_RE.match(line.strip()):
        return None
    body = line[_CPP_MODIFIER_RE.match(line).end():]

    namespace = _CPP_NAMESPACE_RE.match(body)
    if namespace is not None:
        return namespace.group(1) or "(anonymous)", None

    type_match = _CPP_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(1), "class"

    function = _CPP_FUNCTION_RE.match(body)
    if function is None:
        return None
    name = re.sub(r"\s+", "", function.group(2))
    if name.split("::")[-1].lstrip("~") in _CPP_NOT_A_DECLARATION:
        return None
    # The tail is what follows the *closing* paren, so the parameter list
    # is skipped over rather than read as one. Checking from the opening
    # paren instead matched `void f(const T& v)` on its own parameter and
    # missed every function whose parameters were not empty.
    opening = body.index("(", function.end(2))
    closing = _matching_paren(body, opening)
    if closing is None:
        # Parameters continue on the next line. This line is not inside a
        # function body — those are stepped over — so the shape is enough,
        # and the body's own braces still bound the range.
        return name, "function"
    tail = body[closing + 1:]
    if not tail.strip():
        # Nothing after the parameter list: Allman bracing, with the body
        # opening on the line below. Trusted only when a return type was
        # written or the name is qualified, because `MY_MACRO(x)` on its
        # own line has neither — and accepting it made the macro swallow
        # the *next* declaration's braces, reporting a function that does
        # not exist and hiding the one that does. An in-class constructor
        # braced Allman has neither either, so it is missed: one
        # declaration, which is the direction this design errs in.
        return (name, "function") if function.group(1).strip() or "::" in name else None
    if not _CPP_FUNCTION_TAIL_RE.match(tail):
        return None
    return name, "function"


def cpp_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, methods and types, each bounded by its own body.

    Classes, structs, unions and enums are descended into so their
    members are measured individually; a function body is stepped over,
    so nothing inside one is ever read as a declaration. Namespaces are
    walked into without being graded.

    Everything it misses, it misses in the safe direction:

    - **Declarations produced by macros** are invisible, as in C.
    - **A method defined inside a lambda or a local class** sits inside a
      function body and is not counted.
    - **A template header spanning several lines** leaves the declaration
      unrecognised — one missed declaration, never a cascade.
    - **Conditional compilation is not evaluated**, so a declaration in a
      disabled `#if` arm still counts.
    """
    return scan_bounded(
        lines, _cpp_declaration, descend=("class",), skip_preprocessor=True
    )

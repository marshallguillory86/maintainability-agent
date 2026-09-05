"""Declaration ranges for Swift.

Braced, so it reuses `scan_bounded` with C, C++, C# and Java. What is
different is worth stating, because two of the differences are the whole
job and one of them is a trap this project has already fallen into once.

**Every declaration is keyword-led.** `func`, `init`, `subscript`, `class`,
`struct`, `enum`, `protocol`, `actor`, `extension`. That makes recognition
*easier* than C++, where a bare `name(` is equally a call, a macro and a
constructor, and where a wrong guess let a macro swallow the next
declaration's braces. Nothing here has to guess.

**An `extension` adds members to a type declared elsewhere**, often in
another file. `extension Widget { func draw() }` must report `Widget.draw`
rather than a second bare `draw` indistinguishable from every other type's,
which is the same rule C++ applies to an out-of-line `void geo::Widget::draw()`.
The extension itself is walked into and not graded: it is a container, and
grading it would count its members twice.

**Computed properties are not declarations**, and this is the C# properties
problem in Swift spelling. `var area: Double { w * h }` has braces and would
bound perfectly cleanly; an ordinary Swift type has many, each a line or
two, none anybody's maintenance burden. Counting them would dilute the
population every declaration rate divides by. They are excluded by
construction rather than by a rule: every pattern here requires either a
parameter list or a type keyword, and a property has neither.

**A protocol requirement has no body** — `func draw()` with nothing after
it — so it mints nothing, exactly as a C prototype and a pure virtual do.
A protocol of forty requirements is not forty declarations.

One claim was corrected while writing this. The roadmap said Swift's string
interpolation "puts braces inside literals, so masking has to run before
depth counting". It does not: Swift interpolates with `\\(expr)` —
parentheses, not braces — and string contents are masked before any
counting regardless. The real reason masking matters here is the ordinary
one every language shares: a brace inside a string literal, `"{}"`, would
desync depth.
"""
from __future__ import annotations

import re

from ._masking import mask_swift_lines
from ._metrics_types import DeclRange
from ._ranges_core import _mask_generics, scan_bounded

# Stripped once per line so the patterns stay small: these lead a
# declaration and say nothing about what it is.
_SW_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:public|private|internal|fileprivate|open|static|final"
    r"|override|mutating|nonmutating|convenience|required|lazy|weak|unowned"
    r"|indirect|dynamic|optional|async|throws|rethrows|infix|prefix|postfix"
    r"|package)\s+)*"
)
# `class` is both a declaration keyword and a modifier: `class Widget` is a
# type, `class func make()` is a type-level method. Stripping it with the
# other modifiers cost every `final class Store` its keyword — the type
# vanished and only its members were reported. So it is removed only where
# a declaration keyword follows it, and left alone otherwise.
_SW_CLASS_MODIFIER_RE = re.compile(r"^class\s+(?=(?:func|var|let|subscript)\b)")
# `@objc`, `@available(iOS 13, *)`, `@MainActor` — an attribute leads a
# declaration and is not one. Stripped, so what follows is still read.
_SW_ATTRIBUTE_RE = re.compile(r"^\s*(?:@[A-Za-z_]\w*(?:\([^)]*\))?\s*)+")
# `extension Widget`, `extension Widget: Drawable`, `extension Array where …`
_SW_EXTENSION_RE = re.compile(r"^extension\s+([A-Za-z_][\w.]*)")
# The container keywords. `protocol` is here so its body is walked into —
# its requirements are then skipped for having no body, which is what makes
# a forty-requirement protocol mint nothing.
_SW_TYPE_RE = re.compile(
    r"^(?:class|struct|enum|protocol|actor)\s+([A-Za-z_]\w*)"
)
# `func name(`, and the three declarations that carry no `func` keyword.
_SW_FUNC_RE = re.compile(r"^func\s+([A-Za-z_]\w*|[^\s(]+)\s*(?:<[^>]*>)?\s*\(")
_SW_INIT_RE = re.compile(r"^(init\??|deinit|subscript)\b")


def _swift_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a Swift declaration on one masked line.

    ``kind`` is ``None`` for an `extension`: walk in, grade nothing.
    """
    line = _SW_ATTRIBUTE_RE.sub("", _mask_generics(text), count=1)
    body = line[_SW_MODIFIER_RE.match(line).end():]
    body = _SW_CLASS_MODIFIER_RE.sub("", body, count=1)
    body = body[_SW_MODIFIER_RE.match(body).end():]

    extension = _SW_EXTENSION_RE.match(body)
    if extension is not None:
        # The extended type's name, carried so its members can be reported
        # as `Widget.draw` rather than as a second bare `draw`.
        return extension.group(1), None

    type_match = _SW_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(1), "class"

    func = _SW_FUNC_RE.match(body)
    if func is not None:
        return (func.group(1), "function") if _opens_a_body(body) else None

    special = _SW_INIT_RE.match(body)
    if special is not None:
        return (special.group(1).rstrip("?"), "function") if _opens_a_body(body) else None

    # Anything else — `var`, `let`, a computed property, a `case` — is not
    # a declaration this tool measures. Falling through rather than listing
    # exclusions keeps the rule "a declaration is keyword-led and named".
    return None


def _opens_a_body(body: str) -> bool:
    """Whether this line starts a body, or is a requirement with none.

    Swift has no statement terminator, so the shared `skip_bare` check
    cannot work here: it looks for a signature that closes without opening
    a brace, and in C or C# that is a `;`. A Swift protocol requirement
    simply ends at the newline, so the end-finder walks on and adopts the
    *next* declaration's brace — which is how `func describe() -> String`
    inside a protocol came back measured as two lines of body.

    The rule that replaces it: a signature whose parentheses balance on
    this line and which then shows no `{` has no body. A wrapped signature
    leaves its parentheses unbalanced, so it is still read as a
    declaration and its body is found normally:

        func draw(          <- unbalanced here, kept
            into: Canvas
        ) throws {

    A body written Allman — `func f()` with `{` alone on the next line —
    is missed and mints nothing. That is legal Swift and vanishingly rare
    in it, and missing one declaration is the cheaper error than counting
    every protocol requirement in the tree.
    """
    if "{" in body:
        return True
    return body.count("(") != body.count(")")


def swift_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, initialisers and types, each bounded by its own body.

    Types and extensions are descended into, because that is where members
    live; a function body is stepped over, so nothing inside one is read as
    a declaration.

    Bodyless declarations mint nothing, as in C, C++ and C#: a protocol
    requirement is a signature with nothing to measure, and grading it
    would put one-line members into the population every rate divides by.

    Everything it misses, it misses in the safe direction:

    - **Computed properties** (`var area: Double { w * h }`) are not
      declarations, the same call C# makes for the same reason.
    - **A closure assigned to a property** is a body without a declaration
      keyword and is not counted.
    - **Declarations produced by a macro** (`@freestanding`, `#`-macros)
      are not in the source and are not seen, as in C and C++.
    - **Conditional compilation is not evaluated**, so a declaration in a
      disabled `#if` arm still counts.
    """
    ranges, masked = scan_bounded(
        lines, _swift_declaration, descend=("class",), skip_preprocessor=True,
        # Multiline literals are blanked before anything reads a line. The
        # default line-local mask left a `func` inside a `"""` block
        # looking like a declaration — see `mask_swift_lines`.
        mask=mask_swift_lines,
    )
    return _qualify_extension_members(ranges, masked), masked


def _extension_spans(masked: list[str]) -> list[tuple[int, int, str]]:
    """Every `extension X { … }` as (start, end, extended type)."""
    def only_extensions(text: str) -> tuple[str, str | None] | None:
        found = _swift_declaration(text)
        if found is None:
            return None
        name, kind = found
        return (name, "class") if kind is None else None

    spans, _ = scan_bounded(
        masked, only_extensions, descend=(), skip_preprocessor=True
    )
    return [(item.start, item.end, item.name) for item in spans]


def _qualify_extension_members(
    ranges: list[DeclRange], masked: list[str]
) -> list[DeclRange]:
    """Report an extension's members under the type they extend.

    `extension Widget { func draw() }` becomes `Widget.draw`. Without it
    the report carries a bare `draw` indistinguishable from every other
    type's `draw`, and a reader given "shorten `draw`" cannot find which
    one — the same reason C++ keeps the qualification on an out-of-line
    `void geo::Widget::draw()`, except that in Swift the source does not
    write it and the scanner has to carry it.

    A member already qualified is left alone, and a nested type inside an
    extension keeps its own name: the prefix answers "which type does this
    belong to", which a named type already answers for itself.
    """
    spans = _extension_spans(masked)
    if not spans:
        return ranges
    qualified = []
    for item in ranges:
        owner = next(
            (name for start, end, name in spans
             if start < item.start <= end and item.kind == "function"),
            None,
        )
        if owner is None or "." in item.name:
            qualified.append(item)
            continue
        qualified.append(
            DeclRange(item.start, item.end, f"{owner}.{item.name}", item.kind)
        )
    return qualified

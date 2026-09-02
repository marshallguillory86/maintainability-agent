"""Declaration ranges for Java.

One of the per-language scanners split out of ``_ranges.py`` in 1.1.0.
The brace machinery lives in ``_ranges_core``; this module owns Java's
patterns and nothing else. The dependency runs one way — a language
module imports the core, and the core never learns a language.

Kept separate from the JS scanner rather than folded into it. They share
brace-bounding — ``_block_end`` serves both — and nothing else: Java has no
``function`` keyword, no arrow bodies and no assigned-function idiom, while it
does have constructors, annotations and generic parameter lists that the JS
patterns would read as declarations. One regex family stretched across both
would be a list of exceptions to itself.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _NAME, _mask_generics, _matching_paren, scan_bounded

_JAVA_TYPE_KEYWORD = r"(?:class|interface|enum|record|@interface)"
_JAVA_TYPE_RE = re.compile(rf"^{_JAVA_TYPE_KEYWORD}\s+({_NAME})\b")
# Optional return type, then the name and its parameter list. Generics are
# already blanked by `_mask_generics`, so `List<T> sorted(` arrives as
# `List     sorted(` and the return type is one plain token.
_JAVA_MEMBER_RE = re.compile(rf"^(?:[\w$.\[\]]+\s+)?({_NAME})\s*\(")
_JAVA_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:public|protected|private|static|final|abstract|synchronized"
    r"|native|strictfp|default|transient|volatile)\s+)*"
)
# `name(` is also the shape of a call, a control-flow header and a
# `super(...)` delegation. None of those can be a declaration.
_JAVA_NOT_A_DECLARATION = frozenset(
    {"if", "for", "while", "switch", "catch", "return", "new", "super", "this",
     "do", "else", "synchronized", "throw", "assert", "yield"}
)
# What may follow the parameter list of a real declaration: a body, a
# throws clause, or nothing at all for an abstract or interface method.
_JAVA_MEMBER_TAIL_RE = re.compile(r"^\s*(?:\{|throws\b|;)")


def _strip_java_annotations(text: str) -> str:
    """Drop leading annotations, including any parenthesised value.

    `@Deprecated(since = "1.2")` is the case that most resembles a method
    signature: an identifier followed by a parameter list. Counting it
    would put things that are not declarations into the denominator of
    every declaration rate.
    """
    while True:
        stripped = text.lstrip()
        if not stripped.startswith("@") or stripped.startswith("@interface"):
            return text
        offset = len(text) - len(stripped)
        match = re.match(rf"@{_NAME}", stripped)
        if match is None:
            return text
        end = offset + match.end()
        if end < len(text) and text[end] == "(":
            closing = _matching_paren(text, end)
            if closing is None:
                return ""      # value list runs onto the next line
            end = closing + 1
        text = text[end:]


def _java_declaration(text: str) -> tuple[str, str] | None:
    """``(name, kind)`` for a Java declaration on one masked line."""
    line = _strip_java_annotations(_mask_generics(text))
    body = line[_JAVA_MODIFIER_RE.match(line).end():]

    type_match = _JAVA_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(1), "class"

    member = _JAVA_MEMBER_RE.match(body)
    if member is None or member.group(1) in _JAVA_NOT_A_DECLARATION:
        return None
    opening = body.index("(", member.end(1))
    closing = _matching_paren(body, opening)
    if closing is None:
        # Parameters continue on the next line. A call cannot appear here
        # — this line is not inside a method body — so the shape is
        # enough, and the body's own braces still bound the range.
        return member.group(1), "function"
    if not _JAVA_MEMBER_TAIL_RE.match(body[closing + 1:]):
        return None
    return member.group(1), "function"


def java_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Methods, constructors and types, each bounded by its own body.

    A type is descended into, because that is where its members live; a
    method's body is stepped over once its end is known, so no statement
    inside it can be read as a declaration. That single rule is what
    keeps a nested class and its methods visible while `doThing(x);`
    never becomes a declaration named `doThing`.

    Bodyless signatures are kept, unlike C and C++: an abstract or
    interface method is a real declaration in Java.

    Deliberate limitations, all under-reporting:

    - Declarations inside anonymous classes and lambdas are not seen,
      because those live inside a method body.
    - Text blocks (``\"\"\"``) are not masked, so a brace inside one can
      desync depth; the indentation fallback bounds that to one
      declaration.
    - A field initialised with a method reference or an inline array is
      not a declaration and is not reported as one.
    """
    return scan_bounded(lines, _java_declaration, descend=("class",), skip_bare=False)

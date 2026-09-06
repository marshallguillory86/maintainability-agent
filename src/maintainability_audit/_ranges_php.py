"""Declaration ranges for PHP.

Brace-bounded, so the walk is ``scan_bounded`` from ``_ranges_core``,
shared with C, C++, C#, Java, Go and Rust. PHP's declarations are
ordinary — ``function``, ``class``, ``interface``, ``trait``, ``enum`` —
and the difficulty is somewhere else entirely.

**A `.php` file is a template that happens to contain code.** It is HTML
until ``<?php`` says otherwise and HTML again after ``?>``, and the text
in between those blocks is not source. That text is full of braces — a
CSS rule, an inline script, a snippet in a paragraph — and a brace
counted from markup moves depth. A desynced depth does not mis-bound the
declaration it appeared in; it mis-bounds every declaration after it.

So ``mask_php_lines`` blanks everything outside the tags before anything
reads a line, in the same way Swift's multiline literals are blanked
before its scanner runs. It is the first thing that happens rather than a
refinement.

**A method carries its class**, ``Store::get``, for the reason every
other language here does: ``get`` alone is not an instruction in a tree
with eleven of them. PHP writes the class on the container rather than on
the member, so the qualification is carried down by a span pass, exactly
as Rust's ``impl`` and Swift's ``extension`` are.

**Bodyless members mint nothing.** An interface method and an
``abstract`` method are signatures with nothing to maintain, as a C
prototype and a Swift protocol requirement are.
"""
from __future__ import annotations

import re

from ._masking import mask_php_lines
from ._metrics_types import DeclRange
from ._ranges_core import _NAME, scan_bounded

# Visibility and the rest, stripped once per line so the patterns stay
# small. `abstract` and `final` lead a declaration and say nothing about
# what it is.
_PHP_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:public|private|protected|static|abstract|final|readonly)\s+)*"
)
# `class Store`, `interface Reader`, `trait Countable`, `enum Suit`.
_PHP_TYPE_RE = re.compile(rf"^(?:class|interface|trait|enum)\s+({_NAME})\b")
# `function get(` — always keyword-led, which makes PHP easier to
# recognise than C++: a bare `name(` is a call and never a definition.
_PHP_FUNCTION_RE = re.compile(rf"^function\s*&?\s*({_NAME})\s*\(")
#: An anonymous function — `function (int $x) { … }` or `fn ($x) => …`.
#: It has no name, lives inside a body, and is stepped over with that
#: body rather than counted.
_PHP_CLOSURE_RE = re.compile(r"^function\s*\(")


def _php_declaration(text: str) -> tuple[str, str] | None:
    """``(name, kind)`` for a PHP declaration on one masked line."""
    body = text[_PHP_MODIFIER_RE.match(text).end():]

    container = _PHP_TYPE_RE.match(body)
    if container is not None:
        return container.group(1), "class"

    if _PHP_CLOSURE_RE.match(body):
        return None
    function = _PHP_FUNCTION_RE.match(body)
    if function is not None:
        return function.group(1), "function"
    return None


def _class_spans(masked: list[str]) -> list[tuple[int, int, str]]:
    """Every `class X { … }` as (start, end, class name)."""
    def only_types(text: str) -> tuple[str, str] | None:
        found = _php_declaration(text)
        return found if found is not None and found[1] == "class" else None

    spans, _ = scan_bounded(masked, only_types, descend=(), mask=lambda lines: lines)
    return [(span.start, span.end, span.name) for span in spans]


def _qualify_methods(ranges: list[DeclRange], masked: list[str]) -> list[DeclRange]:
    """Report each method under the class that holds it.

    The innermost enclosing class wins, so a method in a class nested
    inside another is named for the one it actually belongs to.
    """
    spans = _class_spans(masked)
    if not spans:
        return ranges
    qualified: list[DeclRange] = []
    for entry in ranges:
        holders = [
            span for span in spans
            if span[0] < entry.start and entry.end <= span[1]
        ]
        if entry.kind == "function" and holders:
            innermost = max(holders, key=lambda span: span[0])
            qualified.append(
                DeclRange(entry.start, entry.end, f"{innermost[2]}::{entry.name}",
                          entry.kind, entry.cognitive)
            )
        else:
            qualified.append(entry)
    return qualified


def php_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, methods and types, each bounded by its own body.

    Deliberate limitations, all under-reporting rather than over:

    - A closure or arrow function assigned inside a body is stepped over
      with that body and is never counted, as Rust's closures and Go's
      function literals are.
    - **Text outside `<?php … ?>` is not read at all**, so a declaration
      written in markup — which would not execute — is correctly absent.
    - Heredoc and nowdoc bodies (``<<<EOT``) are not masked, so a brace
      inside one can desync depth; the indentation fallback in
      ``_ranges_core`` bounds that to a single declaration.
    - A method defined by ``__call`` or by a trait's ``insteadof``
      resolution does not exist in the source and is not seen.
    """
    ranges, masked = scan_bounded(
        lines, _php_declaration, descend=("class",), mask=mask_php_lines,
    )
    return _qualify_methods(ranges, masked), masked

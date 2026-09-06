"""Declaration ranges for Go.

Brace-bounded, so the walk is ``scan_bounded`` from ``_ranges_core``,
shared with C, C++, C# and Java. This module owns Go's patterns and
nothing else; the dependency runs one way, as it does for every language
here.

Go is easier to recognise than its siblings and harder in one place.
Easier because every declaration is keyword-led — ``func`` or ``type`` —
so a bare ``name(`` is always a call and never a definition, which is the
ambiguity that makes C++ expensive. Harder because of the receiver: a
method is written ``func (s *Store) Get(...)``, and the parameter list
that follows ``func`` is *not* the method's parameters.

**A method carries its receiver type.** ``Get`` alone is not an
instruction in a tree with eleven of them, so the range is named
``Store.Get``. Swift's extension members forced the same judgment for the
same reason; the difference is that Go writes the qualification into the
signature already, so it is kept rather than reconstructed.

**Containers are descended into, not graded.** ``type Store struct`` and
``type Reader interface`` hold members. Measuring the container as well
as its members counts the same lines twice, which is why ``descend``
exists.

**An interface method is a requirement, not a declaration.** It has no
body — nothing to maintain and nothing to measure — so ``skip_bare``
drops it, exactly as it drops a C prototype and a Swift protocol
requirement. Counting them would put a pile of one-line members into the
denominator of every declaration rate.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _NAME, _matching_paren, scan_bounded

# `type Store struct {`, `type Reader interface {`. The brace may open on
# the next line, so it is not required here.
_GO_TYPE_RE = re.compile(rf"^type\s+({_NAME})\s+(struct|interface)\b")
# A type alias or definition that is neither — `type ID string`. It holds
# no members, has no body, and is not a unit anybody maintains.
_GO_PLAIN_TYPE_RE = re.compile(rf"^type\s+{_NAME}\s+")
# `func Name(`, with the name captured. Generic type parameters are
# written `[T any]` between the name and the parameter list.
_GO_FUNC_RE = re.compile(rf"^func\s+({_NAME})\s*(\[|\()")
# `func (s *Store) Get(` — receiver first, then the real name. The
# receiver name is optional: `func (*Store) Get(...)` is legal.
_GO_METHOD_RE = re.compile(
    rf"^func\s*\(\s*(?:{_NAME}\s+)?\*?({_NAME})\s*\)\s*({_NAME})\s*(\[|\()"
)


def _skip_type_parameters(text: str, opening: int) -> int | None:
    """The index just past a `[T any]` list, or the list's own opening.

    Go 1.18 generics sit between the name and the parameter list, and a
    scanner that read them as the parameters would take `[T any]` for the
    signature — reporting a function that takes one argument named `T`,
    and losing the real list entirely.
    """
    if text[opening] != "[":
        return opening
    depth = 0
    for index in range(opening, len(text)):
        if text[index] == "[":
            depth += 1
        elif text[index] == "]":
            depth -= 1
            if depth == 0:
                remainder = text[index + 1:]
                offset = len(remainder) - len(remainder.lstrip())
                after = index + 1 + offset
                return after if after < len(text) and text[after] == "(" else None
    return None


def _go_declaration(text: str) -> tuple[str, str] | None:
    """``(name, kind)`` for a Go declaration on one masked line."""
    line = text.lstrip()

    method = _GO_METHOD_RE.match(line)
    if method is not None:
        receiver, name, bracket = method.group(1), method.group(2), method.group(3)
        opening = _skip_type_parameters(line, line.index(bracket, method.end(2)))
        if opening is None or _matching_paren(line, opening) is None:
            # Parameters continue on the next line. This line cannot be a
            # call — `func` leads it — so the shape is enough, and the
            # body's own braces still bound the range.
            return f"{receiver}.{name}", "function"
        return f"{receiver}.{name}", "function"

    function = _GO_FUNC_RE.match(line)
    if function is not None:
        return function.group(1), "function"

    container = _GO_TYPE_RE.match(line)
    if container is not None:
        return container.group(1), "class"

    if _GO_PLAIN_TYPE_RE.match(line):
        # A named type with no members. Not a container, not a unit.
        return None
    return None


def go_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, methods and container types, each bounded by its body.

    Deliberate limitations, all under-reporting rather than over:

    - A function literal assigned to a variable — ``f := func() {…}`` —
      lives inside a body, so it is stepped over and never counted. Go
      uses these for callbacks and goroutine bodies, and a long one is
      invisible to this scanner.
    - Methods on a generic receiver (``func (s *Store[T]) Get``) are read
      through the receiver's base name, so ``Store[T]`` reports as
      ``Store``. That is the name a reader searches for.
    - A raw string literal (backticks) is not masked, so a brace inside
      one can desync depth; the indentation fallback in ``_ranges_core``
      bounds that damage to a single declaration.
    - ``type ID string`` and other plain type definitions are not
      declarations here. They hold nothing and have no body.
    """
    return scan_bounded(lines, _go_declaration, descend=("class",))

"""Declaration ranges for Rust.

Brace-bounded, so the walk is ``scan_bounded`` from ``_ranges_core``,
shared with C, C++, C#, Java and Go. This module owns Rust's patterns and
nothing else.

**A method belongs to the type its ``impl`` block names.** Rust splits
data from behaviour: ``struct Store`` holds the fields and ``impl Store``
holds the methods, often far apart and sometimes in another file. ``get``
alone is not an instruction in a tree with eleven of them, so a method
inside ``impl Store`` reports as ``Store::get``.

That is the same problem Swift's extensions posed, and it is solved the
same way — a post-pass over the ``impl`` spans, because the qualification
is on the block rather than on the member. Go needed none of this: its
receiver is written on the method itself.

**An ``impl`` block is not graded.** It is a container, exactly as a
Swift ``extension`` is, and measuring it as well as its methods counts
the same lines twice.

**A bodyless ``fn`` mints nothing.** A trait requirement is a signature
with nothing to maintain, as a C prototype and a Swift protocol
requirement are. A trait method *with* a body is a default
implementation and is real.

Generics are angle-bracketed as in Java, so ``_mask_generics`` already
handles them, and lifetimes (``<'a>``) ride along in the same syntax.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _NAME, _mask_generics, scan_bounded

# `pub`, `pub(crate)`, `async`, `unsafe`, `const`, `extern "C"`. Stripped
# once per line so the patterns stay small.
_RS_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:pub(?:\s*\([^)]*\))?|async|unsafe|const|default"
    r"|extern(?:\s+\"[^\"]*\")?)\s+)*"
)
# `#[derive(Clone)]`, `#![allow(...)]`. A name and a parenthesised list —
# the shape of a signature — so it is stripped rather than matched, as
# Java's annotations are.
_RS_ATTRIBUTE_RE = re.compile(r"^\s*#!?\[[^\]]*\]\s*")
_RS_FN_RE = re.compile(rf"^fn\s+({_NAME})\s*[(<]")
# `struct S`, `enum E`, `trait T`, `union U`. `mod` is a container of
# declarations rather than a unit, and is walked into without grading.
_RS_TYPE_RE = re.compile(rf"^(?:struct|enum|trait|union)\s+({_NAME})\b")
_RS_MOD_RE = re.compile(rf"^mod\s+({_NAME})\s*\{{")
# `impl Store`, `impl<T> Store<T>`, `impl Display for Widget`. Generics
# are already blanked, so what remains is the trait, the type, or both.
# The captured name is the type being implemented — the thing a reader
# searches for — never the trait, which is how it behaves.
_RS_IMPL_RE = re.compile(
    rf"^impl\s+(?:({_NAME}(?:::{_NAME})*)\s+for\s+)?({_NAME}(?:::{_NAME})*)"
)


_RS_TRAIT_RE = re.compile(r"^trait\s")


def _strip_leading(text: str) -> str:
    """Attributes and modifiers removed, so a keyword test sees the keyword."""
    line = _mask_generics(text)
    while True:
        stripped = _RS_ATTRIBUTE_RE.sub("", line, count=1)
        if stripped == line:
            break
        line = stripped
    return line[_RS_MODIFIER_RE.match(line).end():]


def _rust_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a Rust declaration on one masked line.

    ``kind`` is ``None`` for ``impl`` and ``mod``: walk in, grade nothing.
    """
    line = _mask_generics(text)
    while True:
        stripped = _RS_ATTRIBUTE_RE.sub("", line, count=1)
        if stripped == line:
            break
        line = stripped
    body = line[_RS_MODIFIER_RE.match(line).end():]

    impl = _RS_IMPL_RE.match(body)
    if impl is not None:
        return impl.group(2), None

    module = _RS_MOD_RE.match(body)
    if module is not None:
        return module.group(1), None

    container = _RS_TYPE_RE.match(body)
    if container is not None:
        return container.group(1), "class"

    function = _RS_FN_RE.match(body)
    if function is not None:
        return function.group(1), "function"
    return None


def _impl_spans(masked: list[str]) -> list[tuple[int, int, str]]:
    """Every `impl … { … }` as (start, end, implemented type)."""
    def only_impls(text: str) -> tuple[str, str | None] | None:
        found = _rust_declaration(text)
        if found is None:
            return None
        name, kind = found
        # Re-kinded to "class" purely so the walk *records* it. A `None`
        # kind always walks in and is never recorded, so a span pass that
        # returned None would find nothing — which is exactly what the
        # first version did.
        #
        # Traits are spans too: a default implementation inside `trait
        # Reader` is `Reader::describe`, for the same reason a method
        # inside `impl Store` is `Store::get`. Structs are harmless here
        # because no function lives inside one.
        if kind is None or _RS_TRAIT_RE.match(_strip_leading(text)):
            return name, "class"
        return None

    spans, _ = scan_bounded(masked, only_impls, descend=())
    return [(span.start, span.end, span.name) for span in spans]


def _qualify_impl_members(
    ranges: list[DeclRange], masked: list[str]
) -> list[DeclRange]:
    """Prefix each method with the type its enclosing `impl` names.

    The innermost enclosing span wins, so a method inside `impl Store`
    nested in `mod store` is `Store::get` rather than `store::get`: the
    type is what a work order has to name.
    """
    spans = _impl_spans(masked)
    if not spans:
        return ranges
    qualified: list[DeclRange] = []
    for entry in ranges:
        holders = [
            span for span in spans
            if span[0] < entry.start and entry.end <= span[1] and span[2]
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


def rust_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, methods and types, each bounded by its own body.

    Deliberate limitations, all under-reporting rather than over:

    - A closure — ``|x| { … }`` — lives inside a body and is stepped
      over, so a long one is invisible here. Rust uses them heavily for
      iterators and error handling.
    - **Declarations produced by a macro are not in the source and are
      not seen**, as in C, C++ and Swift. A ``macro_rules!`` body is
      brace-delimited and is stepped over as a unit rather than read.
    - A raw string (``r#"…"#``) is not masked, so a brace inside one can
      desync depth; the indentation fallback bounds that to a single
      declaration.
    - Conditional compilation is not evaluated, so a declaration behind a
      disabled ``#[cfg]`` still counts.
    - A generic ``impl`` reports through its base name: ``impl Store<T>``
      qualifies members as ``Store::``, which is the name a reader
      searches for.
    """
    ranges, masked = scan_bounded(
        lines, _rust_declaration, descend=("class",),
    )
    return _qualify_impl_members(ranges, masked), masked

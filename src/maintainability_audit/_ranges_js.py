"""Declaration ranges for JavaScript, TypeScript, JSX and HTML.

Renamed from ``_ranges.py`` in 1.1.0 so that every language sits in a
module named for it and the shared machinery sits in ``_ranges_core``.
The history below is this scanner's, and it is why the shared rule
exists at all.

Declarations used to be measured with "next regex match minus one",
which is only safe when the pattern list matches *every* declaration in
the file. It never did: ``export function``, generic signatures, and
object/class methods were all invisible, so the first matched
declaration absorbed the rest of the file. On a TypeScript client that
turned a 4-line ``function csrfToken()`` into a reported 262-line /
complexity-35 failure and graded a clean file an F.

Known, deliberate limitations — all of which under-report rather than
over-report:

- Regex literals are not tokenized, so an unbalanced brace inside one
  (``/[{]/``) can desync brace depth. ``indent_bounded_end`` bounds the
  fallout to the one declaration.
- Object-literal properties holding arrow functions (``onSave: () =>``)
  are not treated as declarations; class fields and ``const`` bindings
  are.
- An inline object return type (``function f(): { a: string } {``) can
  end the range at the annotation when no second ``{`` follows on the
  same line.
"""
from __future__ import annotations

import re

from ._masking import mask_lines
from ._metrics_types import DeclRange
from ._ranges_core import (
    _NAME,
    _block_end,
    _is_bare_signature,
    _matching_paren,
    _open_depth,
    indent_bounded_end,
)

# `[^()]*` cannot cross into the parameter list, so this stops at the
# last `>` before `(` — enough for `<T>` and `<T extends Foo<Bar>>`.
# Trailing `\s*` lives inside the group so it never sits next to
# another `\s*` and force the engine to backtrack over whitespace.
_GENERICS = r"(?:<[^()]*>\s*)?"

# Leading keywords are stripped once per line so the declaration
# patterns below stay small and don't each repeat the modifier list.
_MODIFIER_PREFIX_RE = re.compile(
    r"^\s*(?:(?:export|default|declare|abstract|async|const|let|var|override"
    r"|public|private|protected|static|readonly|get|set)\s+)*"
)
# A class member may be private (`#name`); member patterns allow a leading `#`.
_MEMBER_NAME = rf"#?{_NAME}"
_CLASS_RE = re.compile(rf"^class\s+({_NAME})\b")
_FUNCTION_RE = re.compile(rf"^function\s*\*?\s*({_NAME})\s*{_GENERICS}\(")
# `load = async (…) =>`, `parse = function`, `toId = x => x.id`, `#tick = () =>`.
_ASSIGNED_RE = re.compile(rf"^({_MEMBER_NAME})\s*(?::[^=;]*)?=\s*(?:async\s+)?(?:function\b|{_NAME}\s*=>|{_GENERICS}\()")

# Object-literal members: `{ onSave: (a) => {...} }` and
# `{ onLoad: function (b) {...} }`. This is how a React or Node codebase
# writes most of its interesting logic, and none of it was detected --
# so an audit of such a tree scored whatever loose `function`
# declarations sat beside the handlers and reported the file examined
# (D86). A `name:` prefix cannot be a control keyword, which is what
# keeps this off `if (` and `for (`.
_PROPERTY_RE = re.compile(
    rf"^({_NAME})\s*:\s*(?:async\s+)?(?:function\b\s*\*?\s*\(|{_NAME}\s*=>|\([^)]*\)\s*=>)"
)
# A class field typed as a function -- `onSave: (e: Event) => void;` -- is
# a type annotation, not a function. In a class body `name: T` declares a
# field of type T; a value would need `name = ...`, so `name: (...) => X`
# can only be a function-type annotation, with X a return type and no
# body. D93 skipped these inside `interface`/`type` blocks but not inside
# a class, so class fields still minted a declaration population (Grok
# e88b429 audit). The `;` terminator and the absence of a block `{` after
# the arrow are what tell an annotation from a real arrow-valued property
# (`onSave: (a) => { ... }`), which keeps its body and stays counted.
_FUNCTION_TYPE_ANNOTATION_RE = re.compile(
    rf"^({_NAME})\s*:\s*(?:async\s+)?\([^)]*\)\s*=>\s*[^{{;=]+;\s*$"
)
_METHOD_RE = re.compile(rf"^\*?\s*({_MEMBER_NAME})\s*{_GENERICS}\(")

# A TypeScript type block. Its members use the same `name: (a) => …`
# shape as an object literal, and they declare a *type*, not a function
# body -- so counting them as declarations invented a population.
#
# An audit measured what that was worth: forty files of real functions
# scored `insufficient` and were refused a grade, and the same forty
# with an `interface` of three typed arrows each reported 160
# declarations, crossed the population floor, diluted band pressure
# fourfold and issued a verified C. The type members are what bought
# the letter (D93).
# A property whose key was a *string*. Masking blanks string literals
# before any pattern runs, so `"onSave": (a) => {` arrives as
# `        : (a) => {` and `_PROPERTY_RE` -- which needs a name -- cannot
# see it. D86 closed the unquoted case and its example was the instance
# masking does not destroy; quoted keys stayed invisible, and a lone
# `function helper()` beside them still marked the file examined. Some
# keys *must* be quoted: `"on-error"` is not a valid identifier (D94).
_BLANKED_PROPERTY_RE = re.compile(
    r"^\s*:\s*(?:async\s+)?(?:function\b\s*\*?\s*\(|\([^)]*\)\s*=>|[A-Za-z_$][\w$]*\s*=>)"
)
#: The same shape for method shorthand: `"on-error"(e) {`.
_BLANKED_METHOD_RE = re.compile(r"^\s*\([^)]*\)\s*\{")
#: Recovers the name from the line before masking blanked it.
_QUOTED_KEY_RE = re.compile(r"""^\s*(['"])([^'"\\]+)\1\s*:?""")


def _quoted_property(masked: str, original: str) -> str | None:
    """The name of a string-keyed member, or None."""
    if not (_BLANKED_PROPERTY_RE.match(masked) or _BLANKED_METHOD_RE.match(masked)):
        return None
    key = _QUOTED_KEY_RE.match(original)
    return key.group(2) if key else None


_TYPE_BLOCK_RE = re.compile(
    rf"^(?:export\s+)?(?:declare\s+)?(?:interface\s+{_NAME}|type\s+{_NAME}\s*=)"
)

# Control-flow keywords share the `name(` shape with a method
# declaration. Without this list `if (ready) {` reads as a method named
# `if`. Kept deliberately short: every entry also blocks a legitimate
# method of that name, and `delete`/`get`/`new`/`import` are ordinary
# names on a REST client. Keywords that cannot be followed by `(` —
# `try`, `else`, `class` — need no entry.
_NOT_A_DECLARATION = frozenset(
    {"await", "case", "catch", "for", "function", "if", "return", "switch", "throw", "typeof", "while", "with"}
)


def _is_method(tail: str, match: re.Match[str]) -> bool:
    """Reject the call expressions that share a method's ``name(`` shape.

    ``useEffect(() => {`` and ``describe("x", () => {`` also open with an
    identifier and a paren, but their argument list does not finish on the
    same line while it still ends in ``{``.

    When the paren closes on the line, a real method opens a body brace
    after it -- run-on (`f(x) {`) or single-line (`f(x) { return x }`). A
    trailing-`{` test missed the single-line one (Grok 63ab820 audit); a
    call (`foo(x);`) or a signature (`foo(): T;`) has no brace and stays out.
    """
    trimmed = tail.rstrip()
    closing = _matching_paren(tail, match.end() - 1)
    if closing is None:
        return trimmed.endswith(("(", ","))
    return "{" in tail[closing + 1:]


def _is_assignment(tail: str) -> bool:
    """Distinguish `handler = (event) => {` from `total = (a + b);`."""
    return "=>" in tail or "function" in tail or _open_depth(tail) > 0


def _named(match: re.Match[str] | None) -> bool:
    return match is not None and match.group(1) not in _NOT_A_DECLARATION


def _strip_modifiers(line: str) -> str:
    """Everything after any leading `export`, `async`, `public` and friends.

    The prefix pattern is `^\\s*(?:...)*`, so it always matches — possibly
    zero-width — and `.end()` is safe. That safety is a property of the
    pattern rather than of this call, and a later edit removing the
    trailing `*` would turn it into an AttributeError on every line. The
    fallback states the invariant instead of relying on it.
    """
    prefix = _MODIFIER_PREFIX_RE.match(line)
    return line[prefix.end():] if prefix else line


def _declaration(line: str) -> tuple[str, str] | None:
    """Return ``(name, kind)`` when a masked line opens a declaration."""
    tail = _strip_modifiers(line)
    match = _CLASS_RE.match(tail)
    if match:
        return match.group(1), "class"
    match = _FUNCTION_RE.match(tail)
    if match:
        return match.group(1), "function"

    # Bound and checked in one place: `_named` already tests for None, but
    # the type checker cannot see through it, and neither can a reader
    # skimming for what guards the `.group` two lines later.
    assigned = _ASSIGNED_RE.match(tail)
    if assigned is not None and _named(assigned) and _is_assignment(tail):
        return assigned.group(1), "function"
    prop = _PROPERTY_RE.match(tail)
    if prop is not None and _named(prop):
        return prop.group(1), "function"
    method = _METHOD_RE.match(tail)
    if method is not None and _named(method) and _is_method(tail, method):
        return method.group(1), "function"
    return None


def js_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Return brace-bounded declaration ranges plus the masked source.

    The masked copy is handed back so the caller can score complexity
    against code alone, without keywords that only appear inside
    comments or string literals.
    """
    masked = mask_lines(lines)
    ranges: list[DeclRange] = []
    type_block_ends: int | None = None
    for number, text in enumerate(masked, start=1):
        # Inside `interface X { … }` or `type X = { … }` nothing is a
        # declaration: its members are types wearing a function's shape
        # (D93).
        if type_block_ends is not None and number <= type_block_ends:
            continue
        type_block_ends = None
        if _TYPE_BLOCK_RE.match(_strip_modifiers(text).strip()):
            end = _block_end(masked, number)
            type_block_ends = end if end is not None else number
            continue
        if _FUNCTION_TYPE_ANNOTATION_RE.match(_strip_modifiers(text).strip()):
            # A class field typed as a function, not a function (D93).
            continue
        found = _declaration(text)
        if found is None:
            name = _quoted_property(text, lines[number - 1])
            found = (name, "function") if name else None
        if found is None:
            continue
        end = _block_end(masked, number)
        if end is None:
            end = indent_bounded_end(lines, number)
        end = max(end, number)
        if _is_bare_signature(masked, number, end):
            continue  # declare/overload/abstract: a shape with no body (63ab820)
        ranges.append(DeclRange(number, end, found[0], found[1]))
    return ranges, masked

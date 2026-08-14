"""Declaration-range detection for non-Python sources.

Python gets exact ranges from ``ast.end_lineno``. Everything else used
to be measured with "next regex match minus one", which is only safe
when the pattern list matches *every* declaration in the file. It never
did: ``export function``, generic signatures, and object/class methods
were all invisible, so the first matched declaration absorbed the rest
of the file. On a TypeScript client that turned a 4-line
``function csrfToken()`` into a reported 262-line / complexity-35
failure and graded a clean file an F.

The fix is to stop deriving a declaration's end from the *next*
declaration. Each body is bounded by its own braces, counted over the
``_masking``-scrubbed copy of the source, so a declaration this module
fails to recognise costs one missed finding instead of a cascade of
false ones. ``indent_bounded_end`` gives the same guarantee to the
plain regex fallback.

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

_NAME = r"[A-Za-z_$][\w$]*"
# `[^()]*` cannot cross into the parameter list, so this stops at the
# last `>` before `(` — enough for `<T>` and `<T extends Foo<Bar>>`.
# Trailing `\s*` lives inside the group so it never sits next to
# another `\s*` and force the engine to backtrack over whitespace.
_GENERICS = r"(?:<[^()]*>\s*)?"

# Leading keywords are stripped once per line so the declaration
# patterns below stay small and don't each repeat the modifier list.
_MODIFIER_PREFIX_RE = re.compile(
    r"^\s*(?:(?:export|default|declare|abstract|async|const|let|var"
    r"|public|private|protected|static|readonly|get|set)\s+)*"
)
_CLASS_RE = re.compile(rf"^class\s+({_NAME})\b")
_FUNCTION_RE = re.compile(rf"^function\s*\*?\s*({_NAME})\s*{_GENERICS}\(")
# `load = async (…) =>`, `parse = function`, `toId = x => x.id`.
_ASSIGNED_RE = re.compile(rf"^({_NAME})\s*(?::[^=;]*)?=\s*(?:async\s+)?(?:function\b|{_NAME}\s*=>|{_GENERICS}\()")
_METHOD_RE = re.compile(rf"^\*?\s*({_NAME})\s*{_GENERICS}\(")

# Control-flow keywords share the `name(` shape with a method
# declaration. Without this list `if (ready) {` reads as a method named
# `if`. Kept deliberately short: every entry also blocks a legitimate
# method of that name, and `delete`/`get`/`new`/`import` are ordinary
# names on a REST client. Keywords that cannot be followed by `(` —
# `try`, `else`, `class` — need no entry.
_NOT_A_DECLARATION = frozenset(
    {"await", "case", "catch", "for", "function", "if", "return", "switch", "throw", "typeof", "while", "with"}
)

# A declaration whose body brace has not appeared within this many
# lines is treated as expression-bodied (one line) rather than being
# allowed to run on.
_MAX_HEADER_LINES = 12

_BRACKET_DEPTH = {"(": (0, 1), ")": (0, -1), "[": (1, 1), "]": (1, -1)}


def _matching_paren(line: str, opening: int) -> int | None:
    depth = 0
    for index in range(opening, len(line)):
        if line[index] == "(":
            depth += 1
        elif line[index] == ")":
            depth -= 1
            if depth == 0:
                return index
    return None


def _open_depth(line: str) -> int:
    return sum(1 for char in line if char in "([{") - sum(1 for char in line if char in ")]}")


def _is_method(tail: str, match: re.Match[str]) -> bool:
    """Reject the call expressions that share a method's ``name(`` shape.

    ``useEffect(() => {`` and ``describe("x", () => {`` also open a line
    with an identifier, a paren, and close it with a brace. What sets
    them apart from a real method is that their argument list does not
    finish on the same line while the line still ends in ``{``.
    """
    trimmed = tail.rstrip()
    if _matching_paren(tail, match.end() - 1) is None:
        return trimmed.endswith(("(", ","))
    return trimmed.endswith("{")


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
    method = _METHOD_RE.match(tail)
    if method is not None and _named(method) and _is_method(tail, method):
        return method.group(1), "function"
    return None


def _at_top_level(depth: list[int], opened: bool) -> bool:
    return not opened and depth == [0, 0, 0]


def _close_brace(text: str, index: int, depth: list[int], opened: bool) -> tuple[bool, bool]:
    """Apply a ``}``. Returns ``(opened, finished)``.

    Clamped at zero so an unmatched closer — a masking slip, or a range
    that somehow started mid-block — reads as "back at the top level"
    rather than pushing depth negative and never closing again.
    """
    depth[2] = max(0, depth[2] - 1)
    if not opened or depth[2] > 0:
        return opened, False
    if "{" not in text[index + 1 :]:
        return opened, True
    # What closed was a return-type object literal, not the body.
    depth[2] = 0
    return False, False


def _scan_line(text: str, depth: list[int], opened: bool) -> tuple[bool, bool]:
    """Advance brace/paren depth across one masked line.

    ``depth`` is ``[paren, bracket, brace]`` and is mutated in place.
    Returns ``(opened, finished)``.
    """
    for index, char in enumerate(text):
        step = _BRACKET_DEPTH.get(char)
        if step is not None:
            depth[step[0]] = max(0, depth[step[0]] + step[1])
        elif char == "{":
            opened = opened or (depth[0] == 0 and depth[1] == 0)
            depth[2] += 1
        elif char == "}":
            opened, finished = _close_brace(text, index, depth, opened)
            if finished:
                return opened, True
        elif char == ";" and _at_top_level(depth, opened):
            return opened, True
    return opened, False


def _block_end(masked: list[str], start: int) -> int | None:
    """Last line of the block opened at 1-based line ``start``.

    Returns ``start`` for an expression-bodied or signature-only
    declaration, and ``None`` when the body never closes so the caller
    can fall back to indentation.
    """
    depth = [0, 0, 0]
    opened = False
    for number in range(start, len(masked) + 1):
        opened, finished = _scan_line(masked[number - 1], depth, opened)
        if finished:
            return number
        if not opened and number - start >= _MAX_HEADER_LINES:
            return start
    return None


def _indent_width(text: str) -> int:
    return len(text) - len(text.lstrip())


def indent_bounded_end(lines: list[str], start: int) -> int:
    """Last line of the block at 1-based ``start``, judged by indentation.

    Used wherever brace matching is unavailable or inconclusive. The
    block ends at the first later non-blank line that returns to the
    declaration's own indentation: that line itself when it opens with a
    closing bracket, otherwise the line before it.
    """
    base = _indent_width(lines[start - 1])
    for number in range(start + 1, len(lines) + 1):
        text = lines[number - 1]
        if not text.strip() or _indent_width(text) > base:
            continue
        return number if text.lstrip()[0] in "}])" else number - 1
    return len(lines)


def js_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Return brace-bounded declaration ranges plus the masked source.

    The masked copy is handed back so the caller can score complexity
    against code alone, without keywords that only appear inside
    comments or string literals.
    """
    masked = mask_lines(lines)
    ranges: list[DeclRange] = []
    for number, text in enumerate(masked, start=1):
        found = _declaration(text)
        if found is None:
            continue
        end = _block_end(masked, number)
        if end is None:
            end = indent_bounded_end(lines, number)
        ranges.append(DeclRange(number, max(end, number), found[0], found[1]))
    return ranges, masked


# ---------------------------------------------------------------------------
# Java
# ---------------------------------------------------------------------------
#
# Kept separate from the JS scanner rather than folded into it. They share
# brace-bounding — `_block_end` serves both — and nothing else: Java has no
# `function` keyword, no arrow bodies and no assigned-function idiom, while it
# does have constructors, annotations and generic parameter lists that the JS
# patterns would read as declarations. One regex family stretched across both
# would be a list of exceptions to itself.

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


def _mask_generics(text: str) -> str:
    """Blank balanced ``<...>`` so a type argument cannot be read as syntax.

    `Foo<T extends Bar>` must not end at the first `>`, and
    `Map<String, List<Integer>> index()` must yield the name `index`
    rather than something from inside the brackets. Unbalanced `<` — a
    comparison — is left alone, so the failure direction is "generic not
    recognised", never "half a line erased".
    """
    out = list(text)
    stack: list[int] = []
    for index, char in enumerate(text):
        if char == "<":
            stack.append(index)
        elif char == ">" and stack:
            for position in range(stack.pop(), index + 1):
                out[position] = " "
    return "".join(out)


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

    Walks member context only. A method's body is skipped once its end is
    known, so no statement inside it can be read as a declaration; a
    type's body is walked, because that is where its members live. That
    single rule is what keeps a nested class and its methods visible
    while `doThing(x);` never becomes a declaration named `doThing`.

    Deliberate limitations, all under-reporting:

    - Declarations inside anonymous classes and lambdas are not seen,
      because those live inside a method body.
    - Text blocks (``\"\"\"``) are not masked, so a brace inside one can
      desync depth; `indent_bounded_end` bounds the fallout to the one
      declaration.
    - A field initialised with a method reference or an inline array is
      not a declaration and is not reported as one.
    """
    masked = mask_lines(lines)
    ranges: list[DeclRange] = []
    number = 1
    while number <= len(masked):
        found = _java_declaration(masked[number - 1])
        if found is None:
            number += 1
            continue
        end = _block_end(masked, number)
        if end is None:
            end = indent_bounded_end(lines, number)
        end = max(end, number)
        ranges.append(DeclRange(number, end, found[0], found[1]))
        # Descend into a type to find its members; step over a method so
        # its statements are never offered to the matcher.
        number = number + 1 if found[1] == "class" else end + 1
    ranges.sort(key=lambda item: (item.start, item.end))
    return ranges, masked

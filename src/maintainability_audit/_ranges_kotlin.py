"""Kotlin declarations: keyword-led like Swift, bodied unlike it.

Braced and keyword-led, so the walk is `scan_bounded`'s and only the
patterns live here. Four judgments are Kotlin's own, and each is the
reason a shared default reaches the wrong answer:

**An extension function writes its own receiver.** `fun Widget.draw()`
is already `Widget.draw` in the source. Swift spells the same idea
`extension Widget { func draw() }` and `_ranges_swift` runs a second
pass to carry the type name onto the member; Kotlin needs none. This is
the one place Kotlin is easier, and it is worth saying out loud because
the rest of this module is the opposite.

**An expression body has no brace.** `fun area() = w * h` is idiomatic
Kotlin, not a corner — and `_block_end` bounds a body by its braces,
while `indent_bounded_end` walks to the closing `}` of the *enclosing*
class and reports a one-line function as two. So the end-finder is
Kotlin's own, and it decides between the two shapes by reading what
follows the signature.

**`_is_bare_signature` looks for `=>`.** That is the arrow JavaScript
and C# use for an expression member; Kotlin uses `=`. Left to the shared
check, every expression-bodied function in the tree would be dropped as
a signature with nothing behind it. So `skip_bare` is off here and the
bodyless rule lives in the recogniser, as it does in Swift and for the
same reason: only this module knows what a body looks like in this
language.

**A type with no body is still a type.** `data class Point(val x: Int)`
is a complete, useful class and mints a declaration; `fun draw()` inside
an interface is a requirement and mints nothing. The bodyless rule is
therefore about functions, not about declarations in general — which is
where C++ and Swift, whose bodyless *types* are forward declarations,
are not a guide.

Everything it misses, it misses in the safe direction:

- **Properties are not declarations**, accessor or not. `val area: Int
  get() = w * h` is the computed property C# and Swift already exclude:
  an ordinary type has many, each a line or two, and counting them
  dilutes the population every rate divides by.
- **An anonymous `object : Foo { }` expression** is a body with no
  declaration keyword leading the line and is not counted.
- **A destructuring or delegated property** (`by lazy { … }`) is a
  property, so its lambda is not measured as a function.
- **Conditional compilation does not exist in Kotlin**, so unlike C
  there is no disabled arm to mis-count.
"""

from __future__ import annotations

import re

from ._masking import mask_swift_lines
from ._metrics_types import DeclRange
from ._ranges_core import _block_end, _mask_generics, indent_bounded_end, scan_bounded

# Stripped once per line so the patterns stay small. Kotlin writes what
# other languages call a keyword as a modifier on `class` or `object` —
# `data`, `sealed`, `enum`, `annotation`, `value`, `inner`, `companion` —
# so they belong here and the declaration keyword underneath them is
# still `class` or `object`. That is the Swift `final class Store`
# lesson applied in advance: strip the modifier, keep the keyword.
_KT_MODIFIER_RE = re.compile(
    r"^\s*(?:(?:public|private|internal|protected|open|final|abstract"
    r"|override|suspend|inline|noinline|crossinline|reified|operator"
    r"|infix|tailrec|external|const|lateinit|vararg|sealed|data|inner"
    r"|enum|annotation|value|expect|actual|actualtypealias)\s+)*"
)
# `@JvmStatic`, `@Suppress("UNCHECKED_CAST")`, `@field:Named("x")`.
_KT_ATTRIBUTE_RE = re.compile(r"^\s*(?:@[\w:]+(?:\([^)]*\))?\s*)+")
# `class Widget`, `interface Drawable`. `object` is separate below
# because it may be anonymous and `companion` may lead it.
_KT_TYPE_RE = re.compile(r"^(?:class|interface)\s+([A-Za-z_]\w*)")
# `object Registry`, `companion object`, `companion object Factory`.
# Kotlin's own default name for an anonymous companion is `Companion`,
# and naming it is what lets the walk descend: a companion object is
# where Kotlin puts its factories, and returning no name would leave
# every one of them unmeasured.
_KT_OBJECT_RE = re.compile(r"^(companion\s+)?object\b\s*([A-Za-z_]\w*)?")
# `fun name(`, `fun Widget.draw(`, `fun <T> List<T>.second(`. The
# receiver is part of the name on purpose — it is what makes the report
# say `Widget.draw` rather than a bare `draw` indistinguishable from
# every other type's.
_KT_FUNC_RE = re.compile(
    r"^fun\s+(?:<[^>]*>\s*)?((?:[A-Za-z_][\w.]*\.)?[A-Za-z_]\w*)\s*\("
)
_KT_SPECIAL_RE = re.compile(r"^(constructor|init)\b")
# `=` that assigns an expression body, and not `==`, `!=`, `<=`, `>=`.
_KT_ASSIGN_RE = re.compile(r"(?<![=!<>])=(?!=)")


def _kotlin_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a Kotlin declaration on one masked line."""
    line = _KT_ATTRIBUTE_RE.sub("", _mask_generics(text), count=1)
    body = line[_KT_MODIFIER_RE.match(line).end():]

    type_match = _KT_TYPE_RE.match(body)
    if type_match is not None:
        return type_match.group(1), "class"

    object_match = _KT_OBJECT_RE.match(body)
    if object_match is not None:
        return object_match.group(2) or "Companion", "class"

    func = _KT_FUNC_RE.match(body)
    if func is not None:
        return (func.group(1), "function") if _opens_a_body(body) else None

    special = _KT_SPECIAL_RE.match(body)
    if special is not None:
        return (special.group(1), "function") if _opens_a_body(body) else None

    # Anything else — `val`, `var`, a property with an accessor, an
    # `enum` entry — is not a declaration this tool measures. Falling
    # through rather than listing exclusions keeps the rule "a
    # declaration is keyword-led and named".
    return None


def _tail(body: str) -> str:
    """What follows the signature's closing parenthesis, or all of it.

    A default argument puts `=` inside the parentheses (`f(x: Int = 3)`)
    and a lambda parameter puts `{`-shaped text there too, so neither
    question can be asked of the whole line.
    """
    depth = 0
    for index, character in enumerate(body):
        if character == "(":
            depth += 1
        elif character == ")":
            depth -= 1
            if depth == 0:
                return body[index + 1:]
    return body if "(" not in body else ""


def _opens_a_body(body: str) -> bool:
    """Whether this function line has a body, or is a requirement.

    Kotlin has no statement terminator, so the shared `skip_bare` check
    cannot see where a requirement ends — and its own rule looks for
    `=>`, which is JavaScript's and C#'s arrow, not Kotlin's `=`.

    Three shapes have a body: a brace, an `=` after the signature, and a
    signature whose parentheses have not closed yet, which is a wrapped
    header whose brace is on a later line. Everything else is an
    interface requirement or an abstract member, and mints nothing.
    """
    if "{" in body:
        return True
    if body.count("(") != body.count(")"):
        return True
    return _KT_ASSIGN_RE.search(_tail(body)) is not None


def _signature_end(masked: list[str], start: int) -> int:
    """Last line of the signature that begins at ``start``.

    A wrapped header leaves its parentheses open; this closes them so
    the caller can read what follows the signature rather than what
    follows the first line of it.
    """
    depth = 0
    for number in range(start, len(masked) + 1):
        depth += masked[number - 1].count("(") - masked[number - 1].count(")")
        if depth <= 0:
            return number
    return start


def _expression_end(lines: list[str], start: int, signature: int) -> int:
    """Where an expression body ends: its own line, or its continuation.

    `fun area() = w * h` ends on its own line. `fun area(w, h) =` with
    the expression beneath it ends at the last line indented past the
    declaration. Indentation is the only thing available — there is no
    terminator and no brace — and the enclosing block's closing `}` sits
    at or before the declaration's own indent, which is what stops it.
    """
    base = len(lines[start - 1]) - len(lines[start - 1].lstrip())
    end = max(signature, start)
    for number in range(end + 1, len(lines) + 1):
        text = lines[number - 1]
        if not text.strip():
            continue
        if len(text) - len(text.lstrip()) <= base:
            break
        end = number
    return end


def _kotlin_end(masked: list[str], lines: list[str], start: int) -> int:
    """Where the declaration at ``start`` ends: braces, or indentation.

    The shared finder bounds a body by its braces and falls back to
    indentation. That fallback is wrong for an expression body, because
    the next line at or under the declaration's indent is the enclosing
    class's closing `}` — so a one-line `fun area() = w * h` came back
    two lines long, with the brace that ends its *container* counted as
    its last line.
    """
    signature = _signature_end(masked, start)
    tail = _tail("".join(masked[start - 1:signature]))
    if "{" in tail or "{" in masked[start - 1]:
        end = _block_end(masked, start)
        if end is None:
            end = indent_bounded_end(lines, start)
        return max(end, start)
    if _KT_ASSIGN_RE.search(tail) is not None:
        return _expression_end(lines, start, signature)
    return max(signature, start)


def kotlin_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Functions, constructors and types, each bounded by its own body.

    Types and objects are descended into, because that is where members
    live; a function body is stepped over, so a local function inside
    one is never read as a declaration of its own.

    `skip_bare` is off because the shared check reads `=>` as the mark
    of an expression member, and Kotlin writes `=`. The bodyless
    question is answered in `_opens_a_body` instead, where the language
    is known.
    """
    ranges, masked = scan_bounded(
        lines,
        _kotlin_declaration,
        descend=("class",),
        skip_bare=False,
        find_end=_kotlin_end,
        # Kotlin's raw string is `"""`, the same construct Swift spells
        # with optional `#` delimiters, and the same hazard: a line-local
        # mask leaves a `fun` inside a raw string looking like a
        # declaration.
        mask=mask_swift_lines,
    )
    return ranges, masked

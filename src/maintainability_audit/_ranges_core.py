"""The brace machinery every C-family scanner shares.

Split out of ``_ranges.py`` in 1.1.0, when C arrived and made the shape
of the problem obvious: one module was holding both the language-neutral
rule and one language's patterns, so every new language either grew that
file or reached into it for private names.

The rule this module owns is the one the whole design rests on: **a
declaration's range is bounded by its own body, never by where the next
declaration starts.** ``_block_end`` walks brace depth over a
``_masking``-scrubbed copy of the source; ``_is_bare_signature`` tells a
definition from a bodyless one; ``indent_bounded_end`` bounds what braces
cannot resolve. A language this project fails to recognise therefore
costs one missed finding, never a cascade of false ones.

Nothing here knows any language. The scanners — ``_ranges_js``,
``_ranges_java``, ``_ranges_c`` — import from this module, and it imports
from none of them, so adding a language is additive: a new module beside
them, a row in ``declarations.SCANNERS``, and no edit here.
"""
from __future__ import annotations

from collections.abc import Callable

from ._masking import mask_lines
from ._metrics_types import DeclRange

_NAME = r"[A-Za-z_$][\w$]*"

# A declaration whose body brace has not appeared within this many
# lines is treated as expression-bodied (one line) rather than being
# allowed to run on.
_MAX_HEADER_LINES = 12

_BRACKET_DEPTH = {"(": (0, 1), ")": (0, -1), "[": (1, 1), "]": (1, -1)}


def _mask_generics(text: str) -> str:
    """Blank balanced ``<...>`` so a type argument cannot be read as syntax.

    Shared by Java and C# (1.3.0), which write generics the same way.
    Moved here from ``_ranges_java`` when the second language needed it,
    rather than copied — one of the two would have grown a fix the
    other never got.

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


def _is_bare_signature(masked: list[str], start: int, end: int) -> bool:
    """A declaration that terminates without opening a body or an arrow
    value: `declare function f(): void;`, a TS overload signature, an
    abstract method. No body to measure, so counting one mints a member
    with no code behind it (Grok 63ab820 audit). A real function/method
    opens a block `{`; an expression member carries `=>`; neither, closed
    on `;`, is signature only. `f() {}` and `g = () => x;` still count.
    """
    depth = [0, 0, 0]
    opened = False
    for number in range(start, end + 1):
        text = masked[number - 1]
        if "=>" in text:
            return False
        opened, _finished = _scan_line(text, depth, opened)
        if opened:
            return False
    return True


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


# A recogniser answers one question about one masked line: is a
# declaration written here, and if so what is it called and what kind is
# it. `None` for the kind means "walk into this, but do not grade it" —
# a C++ namespace holds declarations and is not itself one.
Recogniser = Callable[[str], "tuple[str, str | None] | None"]
# Where the declaration starting at a 1-based line ends. Braces by
# default; Fortran supplies an `end`-keyword finder of its own.
EndFinder = Callable[[list[str], list[str], int], int] | None
# Blanks comments and string literals, preserving line length.
Masker = Callable[[list[str]], list[str]] | None


def _bounded_end(masked: list[str], lines: list[str], start: int) -> int:
    """Where the declaration at ``start`` ends.

    Its own braces when they resolve, indentation when they do not, and
    never before the line it started on. Held apart from the walk so the
    fallback is one statement there rather than three, and so the two
    ways a body can be bounded are named in one place.
    """
    end = _block_end(masked, start)
    if end is None:
        end = indent_bounded_end(lines, start)
    return max(end, start)


def scan_bounded(
    lines: list[str],
    recognise: Recogniser,
    *,
    descend: tuple[str, ...] = (),
    ignore: tuple[str, ...] = (),
    skip_preprocessor: bool = False,
    skip_bare: bool = True,
    find_end: EndFinder = None,
    mask: Masker = None,
) -> tuple[list[DeclRange], list[str]]:
    """Walk a masked source once, bounding each declaration by its body.

    Every brace-delimited language scans the same way and differs only in
    what it recognises, so the loop lives here and the patterns live in
    the language modules. Java and C each had their own copy of this
    before 1.2.0; C++ and C# would have made four, which is how a fix
    lands in three of them and the fourth keeps the bug.

    The rules the loop enforces, identically for every language:

    - A body is bounded by its own braces (`_block_end`), and by
      indentation when braces cannot resolve it. Nothing runs to
      end-of-file.
    - A declaration whose body is stepped over cannot contribute
      declarations of its own, so no statement inside a function is ever
      offered to `recognise`. Kinds named in `descend` are walked into
      instead, because that is where members live.
    - `skip_bare` drops a signature with no body — a C prototype, a C++
      pure virtual. Java leaves it off: an abstract method is a real
      declaration there.
    - `skip_preprocessor` drops `#`-led lines whole, so a function-shaped
      macro is never measured as a function.
    - Kinds named in `ignore` are stepped over and never recorded. A
      Fortran `interface` block is the case: it holds signatures with no
      bodies, and walking into one would mint a declaration for every
      procedure the module merely *describes*.
    - `find_end` decides where a body ends, and is the only part of this
      walk that is language-shaped. It defaults to braces. Fortran passes
      its own (1.4.0), because a `subroutine` ends at `end subroutine`
      and there is not a brace in the language — the *rule* that a range
      never runs past its own body is what is shared, not the mechanism
      that enforces it.
    - `mask` blanks comments and string literals before anything is
      read. It defaults to the C-family masker; Fortran passes its
      own, because `!` starts a comment there and is negation here.
      The masked copy is returned and is what complexity is scored
      over, so a language masked wrongly is a language *measured*
      wrongly, not merely parsed wrongly.
    """
    resolve_end = find_end or _bounded_end
    blank = mask or mask_lines
    masked = blank(lines)
    ranges: list[DeclRange] = []
    number = 1
    while number <= len(masked):
        text = masked[number - 1]
        if skip_preprocessor and text.lstrip().startswith("#"):
            number += 1
            continue
        found = recognise(text)
        if found is None:
            number += 1
            continue
        name, kind = found
        end = resolve_end(masked, lines, number)
        if skip_bare and _is_bare_signature(masked, number, end):
            number = end + 1          # a shape with no body: not a definition
            continue
        if kind in ignore:
            number = end + 1          # described, not defined: nothing to grade
            continue
        if kind is not None:
            ranges.append(DeclRange(number, end, name, kind))
        walk_in = kind is None or kind in descend
        number = number + 1 if walk_in else end + 1
    ranges.sort(key=lambda item: (item.start, item.end))
    return ranges, masked

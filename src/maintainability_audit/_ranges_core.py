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

_NAME = r"[A-Za-z_$][\w$]*"

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

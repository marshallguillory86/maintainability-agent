"""Lexical scrubbing for C-family sources.

Extracted from ``_ranges.py`` (2026-08-06), the same way
``_metrics_types.py`` was extracted from ``metrics.py``: this is a
separate concern (which characters are code) from the structural
question ``_ranges`` answers (where a declaration ends), and keeping
them apart holds both modules inside the self-audit's file-length
budget.

Everything here is line-oriented and preserves line length, so a masked
copy stays index- and line-number-compatible with the original source.
"""
from __future__ import annotations

import re

# Alternation order matters: whichever token starts earliest wins, so a
# `//` inside a string literal is consumed by the string, and a quote
# inside a comment is consumed by the comment.
_STRING_TOKEN = r"'(?:\\.|[^'\\])*'?|\"(?:\\.|[^\"\\])*\"?|`(?:\\.|[^`\\])*`?"
_TOKEN_RE = re.compile(rf"//|/\*|{_STRING_TOKEN}")

# A `/` begins a regex literal only where a *value* may begin. After an
# identifier, a number or a closing bracket it is division. This is the
# standard heuristic and it is the whole disambiguation JavaScript
# offers without a parser.
#
# Unmasked, a regex literal's contents were read as code: every `?` in
# `/a?b?c?d?e?/` counted as a decision point, so a one-line function
# returning a pattern scored cyclomatic 6 against a McCabe number of 1
# (D86). `_ranges` separately notes that an unbalanced brace inside one
# can desync brace depth, which this also closes.
_REGEX_TOKEN = r"/(?![/*])(?:\\.|\[(?:\\.|[^\]\\])*\]|[^/\\\n\[])+/[dgimsuvy]*"
_REGEX_RE = re.compile(_REGEX_TOKEN)
_VALUE_MAY_BEGIN = re.compile(r"(?:^|[({\[,;:!&|?+\-*%=<>~^]|\b(?:return|typeof|case|in|of|do|else|yield|await|new|delete|void|throw))\s*$")

#: `)` is the one position the character alone cannot decide. `if (x) /re/`
#: begins a value; `f(x) / 2` is division. What separates them is the token
#: owning the matching `(`, so the paren is walked back to and asked. D86
#: masked regex literals and its closer used `return`, already in the list
#: above, so `if (x) /a?b?c?d?e?/` kept scoring 7 against a McCabe 2 (D95).
_CONTROL_PAREN = re.compile(r"\b(?:if|while|for|switch|catch)\s*\($")


def _value_may_begin(before: str) -> bool:
    """Whether a `/` at the end of `before` opens a regex literal."""
    if _VALUE_MAY_BEGIN.search(before):
        return True
    trimmed = before.rstrip()
    if not trimmed.endswith(")"):
        return False
    depth = 0
    for index in range(len(trimmed) - 1, -1, -1):
        char = trimmed[index]
        if char == ")":
            depth += 1
        elif char == "(":
            depth -= 1
            if depth == 0:
                return bool(_CONTROL_PAREN.search(trimmed[: index + 1]))
    return False


def _blank(text: str) -> str:
    return " " * len(text)


def _mask_code(text: str) -> tuple[str, bool, bool]:
    """Blank comments and string literals in one line of open code.

    Returns the masked line plus the ``(in_block_comment, in_template)``
    state to carry into the next line. An unterminated ``'``/``"`` is
    not carried over: JavaScript cannot continue one across a newline,
    so keeping it line-local bounds the damage when the opening quote
    was really an apostrophe inside a regex literal or HTML prose.
    """
    parts: list[str] = []
    position = 0
    while True:
        match = _TOKEN_RE.search(text, position)
        if match is None:
            tail = text[position:]
            gap = _REGEX_RE.search(tail)
            if gap is not None and _value_may_begin(tail[: gap.start()]):
                parts.append(tail[: gap.start()])
                parts.append(_blank(gap.group(0)))
                position = position + gap.end()
                continue
            parts.append(tail)
            return "".join(parts), False, False
        before = text[position : match.start()]
        token = match.group(0)
        # A regex literal starting before this token would swallow it,
        # so look for one in the gap first.
        gap = _REGEX_RE.search(before)
        if gap is not None and _value_may_begin(before[: gap.start()]):
            parts.append(before[: gap.start()])
            parts.append(_blank(gap.group(0)))
            position = position + gap.end()
            continue
        parts.append(before)
        position = match.end()
        if token == "//":
            return "".join(parts) + _blank(text[match.start() :]), False, False
        if token == "/*":
            stop = text.find("*/", position)
            if stop < 0:
                return "".join(parts) + _blank(text[match.start() :]), True, False
            parts.append(_blank(text[match.start() : stop + 2]))
            position = stop + 2
            continue
        parts.append(_blank(token))
        if token.startswith("`") and not token.endswith("`", 1):
            return "".join(parts), False, True


def _mask_line(line: str, in_block: bool, in_template: bool) -> tuple[str, bool, bool]:
    """Mask one line, resuming a block comment or template from the last."""
    if in_block:
        stop = line.find("*/")
        if stop < 0:
            return _blank(line), True, False
        masked, in_block, in_template = _mask_code(line[stop + 2 :])
        return _blank(line[: stop + 2]) + masked, in_block, in_template
    if in_template:
        stop = line.find("`")
        if stop < 0:
            return _blank(line), False, True
        masked, in_block, in_template = _mask_code(line[stop + 1 :])
        return _blank(line[: stop + 1]) + masked, in_block, in_template
    return _mask_code(line)


def mask_lines(lines: list[str]) -> list[str]:
    """Return ``lines`` with comments and string literals blanked out.

    Length is preserved per line so reported line numbers still match
    the original source, and complexity scored over the masked copy no
    longer counts keywords that appear only in prose or literals.
    """
    masked: list[str] = []
    in_block = False
    in_template = False
    for line in lines:
        text, in_block, in_template = _mask_line(line, in_block, in_template)
        masked.append(text)
    return masked

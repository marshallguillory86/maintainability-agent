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
            parts.append(text[position:])
            return "".join(parts), False, False
        parts.append(text[position : match.start()])
        token = match.group(0)
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

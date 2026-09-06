"""Lexical scrubbing for C-family sources.

Extracted from ``_ranges.py`` (2026-08-06, now ``_ranges_js``), the same way
``_metrics_types.py`` was extracted from ``metrics.py``: this is a
separate concern (which characters are code) from the structural
question the ``_ranges*`` scanners answer (where a declaration ends), and keeping
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
# (D86). `_ranges_js` separately notes that an unbalanced brace inside one
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


# A Fortran string, or the `!` that starts a comment. The closing quote
# is optional so an unterminated literal blanks to end of line rather
# than escaping the mask, and a doubled quote inside a literal is matched
# by the alternation rather than by a state flag.
_FORTRAN_LITERAL_RE = re.compile(r"'(?:[^']|'')*'?|\"(?:[^\"]|\"\")*\"?|!")


def _mask_fortran_line(line: str) -> str:
    """One free-form Fortran line, with its comment and strings blanked.

    Written as a scan over literals rather than a character walk with a
    quote flag. The walk was correct and this project's own audit put it
    at cognitive 19 — fair, for what is a small lexer — and the reason
    was the state flag, which this formulation does not need.
    """
    out = list(line)
    for match in _FORTRAN_LITERAL_RE.finditer(line):
        stop = len(line) if match.group() == "!" else match.end()
        for position in range(match.start(), stop):
            out[position] = " "
        if match.group() == "!":
            break
    return "".join(out)


def mask_fortran_lines(lines: list[str]) -> list[str]:
    """``mask_lines`` for free-form Fortran, whose comments are its own.

    The C-family masker cannot serve here: Fortran comments start at an
    unquoted ``!``, and in C ``!`` is logical negation. Teaching one
    masker both would blank half of every ``if (!ready)`` in the C
    family, so Fortran gets its own pass — and needs one, because
    complexity is counted over the masked copy. Unmasked, the comment
    ``! loop while the residual is large`` reads as two branch points.

    Strings are single- or double-quoted and escape by doubling the
    quote. Length is preserved per line, so reported line numbers still
    match the source.
    """
    return [_mask_fortran_line(line) for line in lines]


# Fixed-form Fortran is column-significant, and the columns mean what
# punched cards meant. 1-5: a statement label. 6: any non-blank marks
# this line as a continuation of the one above. 7-72: the statement.
# 73-80: sequence numbers, ignored by the compiler and often holding
# junk. A `C`, `c`, `*` or `!` in column 1 makes the whole line a
# comment.
_FIXED_COMMENT_MARKERS = frozenset("Cc*!")
_FIXED_LABEL_COLUMNS = 5
_FIXED_CONTINUATION_COLUMN = 5   # 0-based index of column 6
_FIXED_STATEMENT_START = 6
_FIXED_STATEMENT_END = 72


def _fixed_form_statement(line: str) -> tuple[str, bool]:
    """``(statement text, is a continuation)`` for one fixed-form line."""
    if not line.strip() or line[:1] in _FIXED_COMMENT_MARKERS:
        return "", False
    marker = line[_FIXED_CONTINUATION_COLUMN : _FIXED_CONTINUATION_COLUMN + 1]
    continuation = bool(marker.strip()) and marker != "0"
    # The label in columns 1-5 is kept, blanking only the continuation
    # column between it and the statement. A Fortran 77 `DO 20 I = 1, N`
    # is terminated by the statement *labelled* 20, not by an `END DO`,
    # so a reader that dropped labels could never find where the loop
    # closes — and then never finds where the procedure closes either.
    label = line[:_FIXED_CONTINUATION_COLUMN]
    statement = line[_FIXED_STATEMENT_START:_FIXED_STATEMENT_END]
    return f"{label} {statement}", continuation


def mask_fixed_form_lines(lines: list[str]) -> list[str]:
    """Fixed-form Fortran, reduced to one statement per line.

    Three things happen here, and all three are needed before a scanner
    can read a line at all. Comment lines — `C` in column 1, which is how
    Fortran 77 wrote every comment — are blanked. Columns 1-6 and 73-80
    are dropped, because a statement label and a sequence number are not
    code. And a continuation line is **joined onto the statement it
    continues**, then blanked itself.

    That last one is not tidiness. A condition written

        IF (A .GT. B .AND.
       &    C .LT. D) THEN

    has its `THEN` on the continuation line. Read line by line, the first
    line looks like a single-line `IF` — no block opened — and the
    matching `END IF` then closes something that was never opened,
    ending the enclosing procedure early and reading the rest of its body
    as top-level code. Joining first is what makes the statement true.

    The line *count* is preserved so declaration ranges still point at
    real lines; only the text moves.
    """
    masked = ["" for _ in lines]
    parent: int | None = None
    for index, line in enumerate(lines):
        statement, continuation = _fixed_form_statement(line)
        if not statement.strip():
            continue
        if continuation and parent is not None:
            masked[parent] = f"{masked[parent].rstrip()} {statement.strip()}"
            continue
        masked[index] = statement
        parent = index
    return mask_fortran_lines(masked)


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


#: Swift's multiline literal, in both spellings: `"""` and the raw form
#: `#"""` … `"""#` (any number of `#`). Matched loosely on purpose — the
#: delimiter is what matters, not how many hashes surround it.
_SWIFT_MULTILINE_RE = re.compile(r'#*"""#*')


def mask_swift_lines(lines: list[str]) -> list[str]:
    """Swift, with multiline string literals blanked before anything reads it.

    `mask_lines` is line-local: it blanks `"a"` on the line it appears on
    and knows nothing about a literal that spans lines. Swift's
    triple-quoted block therefore survived it, and every line between the
    delimiters was read as code — so a `func` written inside a
    documentation string came back as a declaration, with a name, a length
    and a complexity nobody wrote.

    `_ranges_java` discloses exactly this hole for Java text blocks. It is
    disclosed there and closed here rather than copied: Swift's multiline
    strings carry sample code far more often than Java's, and a
    declaration invented out of documentation is the P7 failure — a number
    a reader with the file in front of them would call absurd.

    The delimiter lines keep their own text up to and after the marker, so
    `let a = \"\"\"` still reads as an assignment. Length is preserved per
    line, as everywhere else here, or every range after the literal would
    shift.
    """
    masked: list[str] = []
    inside = False
    for line in lines:
        out = []
        position = 0
        for match in _SWIFT_MULTILINE_RE.finditer(line):
            segment = line[position:match.start()]
            out.append(" " * len(segment) if inside else segment)
            out.append(match.group(0))
            inside = not inside
            position = match.end()
        rest = line[position:]
        out.append(" " * len(rest) if inside else rest)
        masked.append("".join(out))
    return mask_lines(masked)

#: PHP's open and close tags, including the short echo form `<?=`. A
#: `.php` file is a template that happens to contain code: it is HTML
#: until an opening tag says otherwise, and HTML again after `?>`.
_PHP_OPEN_RE = re.compile(r"<\?(?:php\b|=)?")
_PHP_CLOSE_RE = re.compile(r"\?>")


def mask_php_lines(lines: list[str]) -> list[str]:
    """PHP, with everything outside `<?php … ?>` blanked before it is read.

    This is not a refinement, it is the first thing that has to happen.
    Text outside the tags is markup, and markup is full of braces — a
    CSS rule, an inline script, a snippet of sample code in a `<p>`.
    Counted, they move depth, and a desynced depth mis-bounds every
    declaration after it rather than just the one it appeared in.

    A file with no opening tag at all is entirely markup and reads as
    empty, which is correct: a `.php` file that never enters PHP declares
    nothing.

    Length is preserved per line, as in every masker here, so reported
    line numbers still match the original source.
    """
    masked: list[str] = []
    inside = False
    for line in lines:
        out = []
        position = 0
        while position < len(line):
            pattern = _PHP_CLOSE_RE if inside else _PHP_OPEN_RE
            match = pattern.search(line, position)
            if match is None:
                rest = line[position:]
                out.append(rest if inside else " " * len(rest))
                position = len(line)
                break
            segment = line[position:match.start()]
            out.append(segment if inside else " " * len(segment))
            # The tag itself is never code.
            out.append(" " * len(match.group(0)))
            inside = not inside
            position = match.end()
        masked.append("".join(out))
    return mask_lines(masked)

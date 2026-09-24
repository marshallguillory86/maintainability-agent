"""Shell declarations: braced like C, written in text C would misread.

A shell function's body is a brace group or a subshell, so the walk is
`scan_bounded`'s and only the patterns and the masker live here. The
masker is the module: shell's text breaks every assumption the C-family
masker makes, and a masking slip here does not misread one line — it
moves the end of a function.

**`#` starts a comment only at the start of a word.** `$#` is the
argument count, `${#list[@]}` a length and `${path#prefix}` a trim.
Blanking from any of them to the end of the line hides the `if` that
tests it.

**`//` and `/*` are not comments.** `rm -rf "$dir"/*` is ordinary shell,
and the C masker would blank the rest of that line, or wait through the
rest of the file for a `*/` that never comes.

**A heredoc body is text.** Usage messages, generated config and
embedded scripts all live in heredocs and routinely contain braces, `fi`
and function-shaped lines. `<<-` strips leading tabs from the
terminator, so an indented `END` still closes one.

**A double-quoted string may span lines**, which usage text does, so the
masker carries its state from one line to the next.

Quote characters are kept and only their contents are blanked. `case`
arms are written `"start"|"stop")`, and a pattern that could not see the
quotes could not tell an arm from a subshell.

Three definition forms are read — POSIX `name()`, and bash's `function
name` with or without the parentheses. The body may open on the next
line, and may be a subshell `( … )` rather than a brace group. What is
missed, is missed in the safe direction:

- **A body that is some other compound command** (`f() if …; fi`) is
  legal POSIX and almost never written; it is read as one line.
- **A nested definition is part of its parent**, as a local function is
  in every other language here.
- **A file with no suffix** is not opened: a script found only by its
  `#!` line is outside the suffix-based discovery every language uses.
"""

from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import _block_end, indent_bounded_end, scan_bounded

# bash allows `-`, `:` and `.` in a function name; `lib::log` is the
# Google style guide's package form.
_SH_NAME = r"[A-Za-z_][\w:.\-]*"
_SH_FUNCTION_RE = re.compile(
    rf"^\s*function\s+({_SH_NAME})\s*(?:\(\s*\))?\s*(?:[{{(]|$)"
    rf"|^\s*({_SH_NAME})\s*\(\s*\)\s*(?:[{{(]|$)"
)
# `<<EOF`, `<<-EOF`, `<< 'EOF'`, `<<"EOF"`, `<<\EOF`. Not `<<<`, which
# is a here-string and lives on its own line.
_SH_HEREDOC_RE = re.compile(r"<<(-?)\s*(?:'(\w+)'|\"(\w+)\"|\\?(\w+))")
# Where a word begins, and so where `#` would begin a comment.
_WORD_START = frozenset(" \t;&|()")


def _starts_comment(line: str, index: int) -> bool:
    return line[index] == "#" and (index == 0 or line[index - 1] in _WORD_START)


def _heredoc_at(line: str, index: int, pending: list[tuple[str, bool]]) -> int | None:
    """Record a heredoc announced at ``index``; return where its operator ends.

    The body begins on the next line, so all this line keeps is the
    terminator to wait for and whether `<<-` lets it be tab-indented.
    """
    if not line.startswith("<<", index) or line.startswith("<<<", index):
        return None
    heredoc = _SH_HEREDOC_RE.match(line, index)
    if heredoc is None:
        return None
    word = heredoc.group(2) or heredoc.group(3) or heredoc.group(4)
    pending.append((word, heredoc.group(1) == "-"))
    return heredoc.end()


def _mask_code(line: str, index: int, pending: list[tuple[str, bool]]) -> tuple[list[str], int, str | None]:
    """Mask one line from ``index`` in open code.

    Returns the masked characters, where masking stopped, and the quote
    that is still open at the end of the line (or ``None``).
    """
    out: list[str] = []
    while index < len(line):
        if _starts_comment(line, index):
            out.append(" " * (len(line) - index))
            return out, len(line), None
        if line[index] in "'\"":
            masked, index, open_quote = _mask_quoted(line, index)
            out.append(masked)
            if open_quote is not None:
                return out, index, open_quote
            continue
        end = _code_step(line, index, pending)
        out.append(line[index:end])
        index = end
    return out, index, None


def _mask_quoted(line: str, index: int) -> tuple[str, int, str | None]:
    """The string opening at ``index``, quote kept and contents blanked."""
    quote = line[index]
    ansi = quote == "'" and line[index - 1:index] == "$"
    masked, after, open_quote = _mask_string(line, index + 1, quote, escapes=quote == '"' or ansi)
    return quote + masked, after, open_quote


def _code_step(line: str, index: int, pending: list[tuple[str, bool]]) -> int:
    """Where the next unit of open code ends: a heredoc operator, an escape, a character."""
    after = _heredoc_at(line, index, pending)
    if after is not None:
        return after
    return index + (2 if line[index] == "\\" else 1)


def _mask_string(line: str, index: int, quote: str, *, escapes: bool) -> tuple[str, int, str | None]:
    """Blank a string's contents from ``index``; keep its closing quote.

    Returns the masked text, the index after it, and ``quote`` when the
    string runs past the end of the line.
    """
    out: list[str] = []
    while index < len(line):
        char = line[index]
        if escapes and char == "\\":
            out.append(" " * len(line[index:index + 2]))
            index += 2
            continue
        if char == quote:
            out.append(quote)
            return "".join(out), index + 1, None
        out.append(" ")
        index += 1
    return "".join(out), index, quote


def _heredoc_ends(line: str, word: str, strip_tabs: bool) -> bool:
    text = line.lstrip("\t") if strip_tabs else line
    return text.rstrip() == word


def mask_shell_lines(lines: list[str]) -> list[str]:
    """Blank comments, string contents and heredoc bodies, line by line.

    State crosses lines in two ways: a quoted string left open, and the
    heredocs a line has announced, whose bodies begin on the next line.
    Length is preserved per line, as in every masker here, so reported
    line numbers and columns still match the source.
    """
    masked: list[str] = []
    open_quote: str | None = None
    heredocs: list[tuple[str, bool]] = []
    for line in lines:
        if heredocs:
            masked.append(" " * len(line))
            if _heredoc_ends(line, *heredocs[0]):
                heredocs.pop(0)
            continue
        out: list[str] = []
        index = 0
        if open_quote is not None:
            text, index, open_quote = _mask_string(line, 0, open_quote, escapes=open_quote == '"')
            out.append(text)
        if open_quote is None:
            code, index, open_quote = _mask_code(line, index, heredocs)
            out.extend(code)
        masked.append("".join(out))
    return masked


def _shell_declaration(text: str) -> tuple[str, str] | None:
    """``(name, "function")`` for a definition on one masked line."""
    found = _SH_FUNCTION_RE.match(text)
    if found is None:
        return None
    return found.group(1) or found.group(2), "function"


def _body_opener(masked: list[str], start: int) -> tuple[int, int] | None:
    """Line and column of the `{` or `(` that opens the body.

    On the definition's own line after its `()`, or on the next line that
    is not blank — the brace-on-its-own-line style.
    """
    header = masked[start - 1]
    after = header.find(")") + 1 if "()" in header.replace(" ", "") else _SH_FUNCTION_RE.match(header).end(1)
    for number in range(start, len(masked) + 1):
        text = masked[number - 1][after:] if number == start else masked[number - 1]
        stripped = text.lstrip()
        if stripped:
            column = len(masked[number - 1]) - len(stripped)
            return (number, column) if stripped[0] in "{(" else None
    return None


def _subshell_end(masked: list[str], line: int, column: int) -> int | None:
    """Line of the `)` that closes the subshell opened at ``line``/``column``."""
    depth = 0
    for number in range(line, len(masked) + 1):
        text = masked[number - 1][column:] if number == line else masked[number - 1]
        for char in text:
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return number
    return None


def _shell_end(masked: list[str], lines: list[str], start: int) -> int:
    """Where the function at ``start`` ends: its brace group or its subshell."""
    opener = _body_opener(masked, start)
    if opener is None:
        return start
    line, column = opener
    subshell = masked[line - 1][column] == "("
    end = _subshell_end(masked, line, column) if subshell else _block_end(masked, start)
    if end is None:
        end = indent_bounded_end(lines, start)
    return max(end, start)


def shell_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Every function, bounded by its own body.

    A function body is stepped over, so a definition nested inside one is
    part of it. `skip_bare` is off because shell has no bodyless
    signature to drop, and a subshell body has no `{` for the shared
    check to find.
    """
    return scan_bounded(
        lines,
        _shell_declaration,
        skip_bare=False,
        find_end=_shell_end,
        mask=mask_shell_lines,
    )

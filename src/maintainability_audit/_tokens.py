"""Reducing a declaration body to a shape that survives renaming.

An LLM asked twice for the same helper rarely emits the same text twice.
It emits the same *structure* with different names — ``formatUserName``
and ``getUserDisplayName``, identical bodies, different identifiers. Exact
text matching cannot see that, which is why the existing duplicate-block
scanner misses precisely the duplication this tool most wants to report.

So a body is reduced to a token sequence in which identifiers are
replaced by the order in which they first appear. Two functions that
differ only by naming produce identical sequences; two that differ in
control flow, operators, or literal structure do not.

The normalization is deliberately lossy in one direction only. It cannot
tell ``a + b`` from ``x + y``, which is the point. It *can* still tell
``if`` from ``while`` and one call-shape from another, so it does not
collapse everything into a single blob.

Python is tokenized with the stdlib ``tokenize`` module — exact, and free.
Everything else is tokenized with a regex over the ``_masking``-scrubbed
source, so comments and string contents never reach the fingerprint.
"""
from __future__ import annotations

import io
import keyword
import re
import token as token_module
import tokenize

from ._masking import mask_lines

# Identifiers, numbers, and any single punctuation character.
#
# Multi-character operators are deliberately not special-cased: ``===``
# becomes three ``=`` tokens. Enumerating them would triple this pattern
# for no gain, because the shingles compare *runs* of tokens — three
# consecutive ``=`` is as distinctive a run as one ``===``.
_TOKEN_RE = re.compile(r"[A-Za-z_$][\w$]*|\d[\d.]*|[^\s\w]")

# Reserved words are structure, not naming: keeping them verbatim is what
# stops two differently-shaped functions from matching after identifiers
# are anonymized.
_JS_KEYWORDS = frozenset({
    "async", "await", "break", "case", "catch", "class", "const", "continue", "default", "delete",
    "do", "else", "export", "extends", "finally", "for", "function", "get", "if", "import", "in",
    "instanceof", "let", "new", "of", "return", "set", "static", "super", "switch", "this", "throw",
    "try", "typeof", "var", "void", "while", "with", "yield",
})

_LITERAL = "L"
_STRING = "S"


def _anonymize(name: str, seen: dict[str, str], reserved: frozenset[str]) -> str:
    """Map an identifier to its first-appearance index; keep keywords."""
    if name in reserved:
        return name
    if name not in seen:
        seen[name] = f"V{len(seen)}"
    return seen[name]


def python_tokens(source: str) -> list[str]:
    """Normalized token sequence for Python source.

    Returns an empty list when the fragment does not tokenize — a
    declaration body sliced out of its file is often not valid Python on
    its own (it is indented), so callers must treat empty as "unknown",
    never as "no content".
    """
    seen: dict[str, str] = {}
    out: list[str] = []
    try:
        for tok in tokenize.generate_tokens(io.StringIO(source).readline):
            if tok.type == token_module.NAME:
                out.append(_anonymize(tok.string, seen, frozenset(keyword.kwlist)))
            elif tok.type == token_module.NUMBER:
                out.append(_LITERAL)
            elif tok.type == token_module.STRING:
                out.append(_STRING)
            elif tok.type == token_module.OP:
                out.append(tok.string)
    except (tokenize.TokenError, SyntaxError):
        # IndentationError is a SyntaxError subclass and needs no entry.
        return []
    return out


def brace_tokens(lines: list[str]) -> list[str]:
    """Normalized token sequence for C-family source.

    Runs over the masked copy, so a brace or keyword inside a comment or
    string literal cannot enter the fingerprint.
    """
    seen: dict[str, str] = {}
    out: list[str] = []
    for line in mask_lines(lines):
        for match in _TOKEN_RE.finditer(line):
            text = match.group(0)
            if text[0].isdigit():
                out.append(_LITERAL)
            elif text[0].isalpha() or text[0] in "_$":
                out.append(_anonymize(text, seen, _JS_KEYWORDS))
            else:
                out.append(text)
    return out


def declaration_tokens(suffix: str, lines: list[str]) -> list[str]:
    """Normalized tokens for one declaration body, dispatched by language.

    Python bodies are dedented first: a method sliced out of a class does
    not tokenize at its original indentation, and an un-tokenizable body
    would silently drop out of duplicate detection entirely.
    """
    if suffix == ".py":
        source = _dedent("\n".join(lines))
        return python_tokens(source)
    return brace_tokens(lines)


def _dedent(source: str) -> str:
    body = source.expandtabs()
    indents = [len(line) - len(line.lstrip()) for line in body.splitlines() if line.strip()]
    if not indents:
        return body
    margin = min(indents)
    return "\n".join(line[margin:] if line.strip() else "" for line in body.splitlines())

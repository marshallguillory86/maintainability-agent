"""Declaration ranges for Ruby.

The second language here with no braces, and the harder of the two.
Fortran's closer names what it closes — a ``subroutine`` ends at ``end
subroutine`` — so its end-finder can look for a specific word. Ruby's one
bare ``end`` closes a method, a class, a module, a block, an ``if``, a
``while``, a ``case`` and a ``begin``, and telling them apart means
counting openers rather than matching names.

**That counting is the whole module.** A method containing one
``items.each do |item| … end`` ends at its *own* ``end``, not the block's,
and a naive ``def``/``end`` pairing reports half the method. The lengths
and complexities drawn from that are not approximately wrong; they
describe a different span of code.

Three things make the count wrong if they are not handled first:

**Modifier forms open nothing.** ``return 0 if value.nil?`` has an ``if``
that never needs an ``end``. Counted as an opener, it eats the enclosing
method and everything after it. A keyword only opens when it *leads* the
statement.

**``=begin``/``=end`` blocks are comments**, and ``=end`` is not an
``end``. Prose inside one would otherwise close a method.

**Heredoc bodies are not code.** ``<<~SQL`` … ``SQL`` can contain the
word ``end`` in a query, in prose, in anything.

All three are blanked or discounted before a single keyword is counted,
because a miscount does not corrupt one declaration — it shifts every
range after it.
"""
from __future__ import annotations

import re

from ._masking import mask_lines
from ._metrics_types import DeclRange
from ._ranges_core import scan_bounded

#: A Ruby method name may end in `?`, `!` or `=`, and an operator method
#: may be `<=>` or `[]`. The common forms are enough here: a name that is
#: not matched is not reported, which under-reports rather than invents.
_RB_NAME = r"[A-Za-z_]\w*[?!=]?"
_RB_DEF_RE = re.compile(rf"^def\s+(?:(self)\s*\.\s*)?({_RB_NAME})")
_RB_CLASS_RE = re.compile(r"^(?:class|module)\s+([A-Z]\w*(?:::[A-Z]\w*)*)")
#: `=begin` and `=end` must start at column zero to be a comment block.
_RB_COMMENT_OPEN_RE = re.compile(r"^=begin\b")
_RB_COMMENT_CLOSE_RE = re.compile(r"^=end\b")
#: `<<~SQL`, `<<-EOT`, `<<EOT`, and the quoted forms. The terminator is
#: the captured word, on a line of its own.
_RB_HEREDOC_RE = re.compile(r"<<[-~]?([\"']?)([A-Z_]\w*)\1")

#: Keywords that open a block needing an `end`, when they *lead* the
#: statement. `do` is handled separately: it opens mid-line, after the
#: iterator call it belongs to.
_RB_OPENERS = (
    "def", "class", "module", "if", "unless", "while", "until", "case",
    "begin", "for",
)
_RB_OPENER_RE = re.compile(rf"^({'|'.join(_RB_OPENERS)})\b")
#: `do` opening a block, and `{`-form blocks are not counted: a `{` block
#: is closed by `}` on the same or a later line and never by `end`.
_RB_DO_RE = re.compile(r"\bdo\b(\s*\|[^|]*\|)?\s*$")
_RB_END_RE = re.compile(r"^end\b")
#: Ruby 3.0's endless method: `def square(x) = x * x`. It has no body and
#: no `end`, so counting its `def` as an opener leaves depth never
#: returning to zero — and the declaration swallows whatever follows it.
_RB_ENDLESS_RE = re.compile(r"^def\s+[^=]*?\)\s*=(?!=)|^def\s+\w+[?!]?\s*=(?!=)")


def mask_ruby_lines(lines: list[str]) -> list[str]:
    """Blank comment blocks and heredoc bodies before anything is counted.

    `mask_lines` is line-local and knows nothing about a body that spans
    lines, so a `=begin` block or a heredoc survives it and every line
    inside is read as code. In a language where a bare `end` closes the
    nearest opener, one stray `end` in a SQL string does not mis-read a
    line — it closes a method early and shifts everything after it.

    Length is preserved per line, as in every masker here, so reported
    line numbers still match the original source.
    """
    masked: list[str] = []
    in_comment = False
    heredoc: str | None = None
    for line in lines:
        if heredoc is not None:
            masked.append(" " * len(line))
            if line.strip() == heredoc:
                heredoc = None
            continue
        if in_comment:
            masked.append(" " * len(line))
            if _RB_COMMENT_CLOSE_RE.match(line):
                in_comment = False
            continue
        if _RB_COMMENT_OPEN_RE.match(line):
            in_comment = True
            masked.append(" " * len(line))
            continue
        opener = _RB_HEREDOC_RE.search(line)
        if opener is not None:
            heredoc = opener.group(2)
        masked.append(line)
    return mask_lines(masked)


def _opens(text: str) -> int:
    """How many `end`s this line will need.

    A keyword opens only when it *leads* the statement. `return 0 if x`
    is a modifier and needs no `end`; counting it as an opener consumes
    the enclosing method whole.
    """
    stripped = text.strip()
    if _RB_ENDLESS_RE.match(stripped):
        return 0
    count = 1 if _RB_OPENER_RE.match(stripped) else 0
    if _RB_DO_RE.search(stripped):
        count += 1
    return count


def _ruby_end(masked: list[str], lines: list[str], start: int) -> int:
    """The line whose `end` closes the declaration beginning at `start`.

    Depth counting rather than name matching, because Ruby's closer does
    not say what it closes. A one-line `def add(a, b) = a + b` endless
    method (3.0) opens nothing and ends where it starts.
    """
    depth = 0
    for number in range(start, len(masked) + 1):
        text = masked[number - 1].strip()
        if _RB_END_RE.match(text):
            depth -= 1
            if depth <= 0:
                return number
        else:
            depth += _opens(text)
        if number == start and depth == 0:
            return number          # endless method: no body to bound
    return len(masked)


def _ruby_declaration(text: str) -> tuple[str, str] | None:
    """``(name, kind)`` for a Ruby declaration on one masked line."""
    stripped = text.strip()
    container = _RB_CLASS_RE.match(stripped)
    if container is not None:
        return container.group(1), "class"
    method = _RB_DEF_RE.match(stripped)
    if method is not None:
        receiver, name = method.group(1), method.group(2)
        # `def self.build` is a class method, written `Store.build`; an
        # instance method is written `Store#get`. The qualifier is added
        # by the span pass, which needs to know which separator to use.
        return (f".{name}" if receiver else f"#{name}"), "function"
    return None


def _container_spans(masked: list[str]) -> list[tuple[int, int, str]]:
    """Every `class`/`module` body as (start, end, name)."""
    def only_containers(text: str) -> tuple[str, str] | None:
        found = _ruby_declaration(text)
        return found if found is not None and found[1] == "class" else None

    spans, _ = scan_bounded(
        # Descends, or a class inside a class is never seen and every
        # nested method is attributed to the outermost container —
        # naming a method that is not there.
        masked, only_containers, descend=("class",), find_end=_ruby_end,
        mask=lambda lines: lines,
        # `_is_bare_signature` looks for a brace to decide whether a
        # declaration has a body. Ruby has none, so every container reads
        # as bare and the span pass returned nothing — leaving every
        # method unqualified. The main scan already passes this; the span
        # pass inheriting the default was the bug.
        skip_bare=False,
    )
    return [(span.start, span.end, span.name) for span in spans]


def _qualify(ranges: list[DeclRange], masked: list[str]) -> list[DeclRange]:
    """Name each method for the class or module that holds it.

    A method outside any container keeps its bare name with the leading
    separator stripped: a top-level `def add` is `add`, not `#add`.
    """
    spans = _container_spans(masked)
    qualified: list[DeclRange] = []
    for entry in ranges:
        if entry.kind != "function":
            qualified.append(entry)
            continue
        holders = [
            span for span in spans
            if span[0] < entry.start and entry.end <= span[1]
        ]
        if holders:
            innermost = max(holders, key=lambda span: span[0])
            name = f"{innermost[2]}{entry.name}"
        else:
            name = entry.name.lstrip("#.")
        qualified.append(
            DeclRange(entry.start, entry.end, name, entry.kind, entry.cognitive)
        )
    return qualified


def ruby_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Methods, classes and modules, each bounded by its own `end`.

    Deliberate limitations, all under-reporting rather than over:

    - **Metaprogrammed declarations are not in the source and are not
      seen.** `define_method`, `attr_accessor` and anything built by
      `class_eval` produce methods no scanner can read, exactly as C and
      Swift macros do. Ruby leans on these more than most languages, so
      this is the largest gap here and it is stated first.
    - A `{ … }` block is closed by `}` rather than `end` and is not
      counted as an opener; a multi-line `{` block containing a `def`
      would therefore mis-bound. Idiomatic Ruby uses `do … end` for
      multi-line blocks, which is counted.
    - A singleton class body (`class << self`) is read as a container
      named `self`, so its methods qualify oddly.
    - Operator method names beyond the ordinary forms (`<=>`, `[]=`) are
      not matched and are not reported.
    """
    ranges, masked = scan_bounded(
        lines, _ruby_declaration, descend=("class",),
        find_end=_ruby_end, mask=mask_ruby_lines, skip_bare=False,
    )
    return _qualify(ranges, masked), masked

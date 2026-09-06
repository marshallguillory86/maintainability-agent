"""Internal value-types + regex constants used by ``metrics.py``.

Extracted from ``metrics.py`` (2026-05-11) so the metrics module
stays under the maintainability config's warn threshold for file
length — eating our own dogfood on the A+ grade. Not a public API;
import from ``metrics`` if you need any of these symbols externally.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NamedTuple

# Last-resort detector, used for unparseable Python and for any
# extension without a dedicated scanner. JS/TS/HTML go through
# ``_ranges_js.js_declaration_ranges`` instead, which bounds each body by
# its own braces. Ranges from these patterns are bounded by
# indentation, never by the next match — see ``_ranges`` for why.
FUNC_PATTERNS = [
    (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][\w]*)\s*\("), "function"),
    (re.compile(r"^\s*(?:(?:export|default|async)\s+)*function\s+([A-Za-z_$][\w$]*)\s*(?:<[^()]*>\s*)?\("), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)\b"), "class"),
    # Object-literal members. `{ onSave: (a) => {...} }` and
    # `{ onLoad: function (b) {...} }` are how a React or Node codebase
    # writes most of its interesting logic, and neither was detected --
    # so an audit of such a tree scored whatever loose `function`
    # declarations happened to sit beside them and reported the file as
    # examined (D86). A `name:` prefix cannot be a control keyword, so
    # these do not collide with `if (`/`for (` the way bare method
    # shorthand would.
    (re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>"), "function"),
    (re.compile(r"^\s*([A-Za-z_$][\w$]*)\s*:\s*(?:async\s+)?function\s*\*?\s*\("), "function"),
]

# Decision points. The `?` alternatives are three distinct operators in
# JavaScript and the first version counted them as one character each,
# which was both over-broad and arithmetically wrong (D78):
#
# * `?.` optional chaining — not a decision. `u?.a?.b?.c` is one member
#   access written defensively, and it was scoring four.
# * `??` nullish coalescing — one decision, like `||`. Two characters,
#   so a bare `\?` counted every one of them twice.
# * `?` ternary — one decision, which is the only case originally meant.
#
# Together those made `return u?.user?.profile?.settings?.theme ?? "x"`
# a complexity-12 warning for a function whose McCabe number is 1. A
# rate computed from that is not a measurement of the code (P7), and it
# fires hardest on exactly the modern JavaScript this project claims to
# score.
COMPLEXITY_RE = re.compile(
    r"\b(if|elif|for|while|except|case|catch)\b|&&|\|\||\?\?|\?(?![.?])"
)


#: Swift's `guard` is an early exit and its primary branching idiom, and
#: `repeat` is its do-while. Neither is in the C-family pattern, so a
#: guard-heavy function would read as branchless — the same defect Fortran
#: had with `do`.
SWIFT_COMPLEXITY_RE = re.compile(
    r"\b(if|for|while|case|catch|guard|repeat)\b|&&|\|\||\?\?|\?(?![.?])"
)


def swift_branch_points(line: str) -> int:
    """Decision points on one line of Swift."""
    return len(SWIFT_COMPLEXITY_RE.findall(line))


#: Go's vocabulary is *smaller* than C's, not larger, and that is the
#: point. It has no `while` (`for` covers looping), no ternary, no
#: `catch` — `if err != nil` carries what other languages put in a catch
#: block, and it is already counted as an `if`. What the C pattern misses
#: is `select`, the concurrency branch: a dispatch loop built from
#: `select` and its cases scored only its cases, so the construct that
#: decides which case runs decided nothing. That is the Fortran defect in
#: miniature, and the reason this table exists at all.
GO_COMPLEXITY_RE = re.compile(
    r"\b(if|for|case|select|goto)\b|&&|\|\|"
)


#: Rust branches on `match` arms rather than on the `match` keyword, the
#: way Fortran branches on its cases rather than on `select case` — count
#: both and the construct and its first arm each score. And `?` is *not*
#: a ternary here: it propagates an error and decides nothing, while
#: idiomatic Rust is full of it. Counting it would make ordinary error
#: handling read as branching, which is D78's optional-chaining defect in
#: another language.
RUST_COMPLEXITY_RE = re.compile(
    r"\b(if|for|while|loop)\b|&&|\|\||=>"
)


#: PHP spells its multi-way branch `elseif`, one word, and there is no
#: word boundary inside it — so the C-family pattern matches neither `if`
#: nor `elif` there and a dispatch chain scores *zero*. It also spells
#: `foreach` for its primary loop and offers `and`/`or`/`xor` as word
#: operators. Measured with C's keywords, ordinary PHP reads as
#: branchless: Fortran's defect, in a language nobody expected it in.
PHP_COMPLEXITY_RE = re.compile(
    r"\b(elseif|if|for|foreach|while|case|catch|and|or|xor)\b"
    r"|&&|\|\||\?\?|\?(?![.?:])"
)


#: Ruby writes its negated conditional and loop as words the C pattern
#: never looks for — `unless` and `until` — and both are ordinary rather
#: than exotic: `return 0 unless value` is the idiomatic guard clause.
#: `elsif` is spelled with one `e`, so `elif` misses it too. Measured with
#: C's keywords, a guard-heavy Ruby method reads as branchless.
RUBY_COMPLEXITY_RE = re.compile(
    r"\b(if|elsif|unless|while|until|for|when|rescue)\b|&&|\|\||\band\b|\bor\b"
)


def ruby_branch_points(line: str) -> int:
    """Decision points on one line of Ruby."""
    return len(RUBY_COMPLEXITY_RE.findall(line))


def php_branch_points(line: str) -> int:
    """Decision points on one line of PHP."""
    return len(PHP_COMPLEXITY_RE.findall(line))


def rust_branch_points(line: str) -> int:
    """Decision points on one line of Rust."""
    return len(RUST_COMPLEXITY_RE.findall(line))


def go_branch_points(line: str) -> int:
    """Decision points on one line of Go."""
    return len(GO_COMPLEXITY_RE.findall(line))


def branch_points(line: str) -> int:
    """Decision points on one line, for the C family and Python."""
    return len(COMPLEXITY_RE.findall(line))


# Fortran branches on keywords the C-family pattern never looks for, and
# the pattern it does use is actively wrong here. Measured before this
# existed: six nested `do` loops scored complexity 1, because `do` — the
# language's primary loop — is not in it; five `.and.`/`.or.` operators
# scored 3, because Fortran spells them with dots rather than `&&`; and
# every `if` was counted twice, because `end if` contains the word `if`.
# Scientific Fortran is mostly nested loops, so a numerical kernel read
# as trivial.
#
# `end <thing>` closes a construct and decides nothing, so it is removed
# before anything is counted. `select case` is the header of a construct
# whose *cases* are the branches, so it goes too — otherwise the header
# and its first case both count.
_FORTRAN_CLOSER_RE = re.compile(
    r"\bend\s*(?:if|do|where|forall|select|associate|block|critical|team|"
    r"function|subroutine|module|program|type|interface)\b",
    re.I,
)
_FORTRAN_SELECT_RE = re.compile(r"\bselect\s+(?:case|type)\b", re.I)
# `case default` is the else of a select: it adds no path of its own.
_FORTRAN_DEFAULT_RE = re.compile(r"\bcase\s+default\b", re.I)
_FORTRAN_BRANCH_RE = re.compile(
    r"\b(?:if|do|case|where|elsewhere|forall)\b|\.and\.|\.or\.", re.I
)


def fortran_branch_points(line: str) -> int:
    """Decision points on one Fortran statement.

    Counted after the closers and the `select` header are removed, so
    `end if` is not a second `if` and `select case (n)` is not a case.
    """
    text = _FORTRAN_CLOSER_RE.sub(" ", line)
    text = _FORTRAN_SELECT_RE.sub(" ", text)
    text = _FORTRAN_DEFAULT_RE.sub(" ", text)
    return len(_FORTRAN_BRANCH_RE.findall(text))


# COBOL's closers are hyphenated words — `END-IF`, `END-PERFORM` — and a
# word boundary sits between the hyphen and the keyword, so `\bif\b` finds
# the `IF` inside `END-IF` and every construct counts twice. Stripped
# first, exactly as Fortran strips `end if` for the same reason.
_COBOL_CLOSER_RE = re.compile(r"\bEND-[A-Z]+\b", re.I)
# `WHEN OTHER` is EVALUATE's default arm: the branch not taken by any
# other, and not a decision of its own — the same call `case default`
# gets in Fortran.
_COBOL_DEFAULT_RE = re.compile(r"\bWHEN\s+OTHER\b", re.I)
_COBOL_BRANCH_RE = re.compile(
    # `IF`/`ELSE` and `EVALUATE`'s `WHEN` arms are the conditionals.
    # `UNTIL`, `VARYING` and `TIMES` are the three ways a `PERFORM`
    # becomes a loop — a bare `PERFORM SOME-PARA` is a call, not a
    # branch, which is why `PERFORM` itself is absent.
    # `AND`/`OR` are the boolean operators, counted like `&&` and `||`.
    r"\b(?:IF|ELSE|WHEN|UNTIL|VARYING|TIMES|AND|OR)\b",
    re.I,
)


def cobol_branch_points(line: str) -> int:
    """Decision points on one COBOL statement.

    Counted after the scope terminators and `WHEN OTHER` are removed, so
    `END-IF` is not a second `IF` and a default arm is not a decision.
    """
    text = _COBOL_CLOSER_RE.sub(" ", line)
    text = _COBOL_DEFAULT_RE.sub(" ", text)
    return len(_COBOL_BRANCH_RE.findall(text))


class DeclRange(NamedTuple):
    """A detected declaration: 1-based inclusive line span, name, kind.

    ``kind`` is ``"function"`` or ``"class"``. It exists so a class is
    not graded against the per-function line budget: a 113-line class of
    six short methods is ordinary, a 113-line function is not.
    """

    start: int
    end: int
    name: str
    kind: str
    # Cognitive complexity, when the detector could compute it exactly
    # (Python, from the AST). ``None`` means the caller should derive it
    # from the body text instead.
    cognitive: int | None = None


@dataclass
class FileMetric:
    path: str
    lines: int
    status: str


@dataclass
class FunctionMetric:
    path: str
    name: str
    start_line: int
    lines: int
    complexity: int
    status: str
    kind: str = "function"
    # Nesting-weighted reading cost. Reported alongside `complexity`
    # rather than replacing it: they answer different questions, and a
    # function can be high in one and low in the other.
    cognitive: int = 0
    # 12-char sha256 of the normalized body (ADR 009): dedented, trailing
    # whitespace stripped, comments and identifiers untouched. Computed at
    # scan time because presentation may never open the audited tree; ""
    # where a producer predates the field.
    body_digest: str = ""


@dataclass
class RiskFinding:
    path: str
    line: int
    name: str
    text: str


@dataclass(frozen=True)
class Measurement:
    """One value, for one unit, from one tool.

    Lives here rather than beside the adapters because both scanners and
    scoring touch it: an adapter produces measurements, corroboration
    reduces them, and the layering rule forbids scoring from importing a
    scanner. A shared type in foundations is what lets both sides speak
    without one depending on the other.
    """

    concept: str
    unit: str
    value: float
    tool: str
    path: str
    line: int | None = None


@dataclass(frozen=True)
class Finding:
    """A located problem a tool named, with no rate attached."""

    concept: str
    path: str
    line: int | None
    message: str
    tool: str
    rule: str | None = None


def is_test_path(rel: str) -> bool:
    """Identify test files by conventional path/name shape.

    Lives in the foundation layer because *both* tiers need it and they
    sit on opposite sides of the graph: the built-in scanners split
    production from test code before counting, and `_pressures` must make
    the identical split on analyzer measurements or the two numbers are
    computed over different populations. Importing it upward from
    `metrics` would have put a scanner in the scoring layer's
    dependencies, which `test_scoring_never_imports_scanners_or_assembly`
    correctly refused.

    Used so test-code pressure is reported separately and excluded from
    `testability` / `analyzability` scoring: growing a test file should
    not lower the score of how testable the production code is.
    """
    normalized = rel.replace("\\", "/").lower()
    parts = normalized.split("/")
    if any(segment in {"tests", "test", "__tests__", "spec", "specs"} for segment in parts[:-1]):
        return True
    name = parts[-1]
    if name.startswith(("test_", "test.")):
        return True
    # pFUnit source is test source by definition: a `.pf` file exists to
    # be preprocessed into a test suite and holds nothing else.
    if name.endswith(".pf"):
        return True
    stem = name.rsplit(".", 1)[0]
    return stem.endswith(("_test", ".test", ".spec", "_spec"))


# Every file extension this project recognises as source code, and the
# language it belongs to. Wider on purpose than `include_extensions`: the
# point is to notice code the scan is *not* configured to read, which
# cannot be done from the include list alone.
#
# The validation sample is why this exists. curl reported 4.3 from its
# Markdown and Python test scripts while 20,547 declarations of C went
# unopened; gson withheld its score citing "below the calibration floor"
# while holding 9,639 unread Java declarations. A score computed from a
# minority of a repository is a false report about the repository, and it
# is false in the flattering direction — documentation and scripts are
# simpler than the code they describe.
KNOWN_SOURCE_SUFFIXES: dict[str, str] = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin", ".scala": "Scala",
    ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++", ".cxx": "C++",
    ".hh": "C++", ".hpp": "C++", ".hxx": "C++",
    ".cs": "C#", ".fs": "F#", ".vb": "Visual Basic",
    ".go": "Go", ".rs": "Rust", ".swift": "Swift", ".m": "Objective-C", ".mm": "Objective-C",
    ".rb": "Ruby", ".php": "PHP", ".pl": "Perl", ".pm": "Perl",
    ".lua": "Lua", ".r": "R", ".jl": "Julia", ".dart": "Dart",
    ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang", ".hrl": "Erlang",
    ".hs": "Haskell", ".ml": "OCaml", ".mli": "OCaml", ".clj": "Clojure", ".cljs": "Clojure",
    ".f": "Fortran", ".f90": "Fortran", ".f95": "Fortran", ".f03": "Fortran",
    ".for": "Fortran", ".ftn": "Fortran", ".f08": "Fortran",
    ".F": "Fortran", ".FOR": "Fortran", ".FTN": "Fortran",
    # A capital F means "run the C preprocessor first". Suffixes are
    # matched case-sensitively everywhere here, so the two spellings
    # are two entries or half of real Fortran is invisible.
    ".F90": "Fortran", ".F95": "Fortran", ".F03": "Fortran", ".F08": "Fortran",
    # COBOL, in both spellings. `.cpy` is a copybook — DATA DIVISION
    # text with no PROCEDURE DIVISION — and is still COBOL source.
    ".cbl": "COBOL", ".cob": "COBOL", ".cpy": "COBOL",
    ".CBL": "COBOL", ".COB": "COBOL", ".CPY": "COBOL",
    # pFUnit test source: free-form Fortran plus `@test` directives.
    ".pf": "Fortran",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".groovy": "Groovy", ".vue": "Vue", ".svelte": "Svelte",
    ".zig": "Zig", ".nim": "Nim", ".cr": "Crystal", ".d": "D", ".ada": "Ada", ".adb": "Ada",
}

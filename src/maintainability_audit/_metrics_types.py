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
    r"\b(if|elif|for|while|except|case|catch)\b|&&|\|\||\?\?"
    # A ternary needs both halves, so the `:` is required. Without it a
    # `?` in *type* position counted as a decision: C#'s `int? v`,
    # TypeScript's `v?: number`, Java's `List<?>`. Each is a nullable or
    # optional marker that decides nothing, and each was scoring one —
    # D78's optional-chaining defect again, in three more spellings.
    #
    # The cost is a ternary split across lines, which is not counted.
    # That under-reports, which is the direction this project errs in.
    r"|\?(?![.?:])(?=[^?]*:)"
)


#: Swift's `guard` is an early exit and its primary branching idiom, and
#: is not in the C-family pattern, so a guard-heavy function read as
#: branchless — the same defect Fortran had with `do`.
#:
#: Two corrections from checking every construct in the language guide
#: against an independent implementation:
#:
#: `repeat` is **not** counted. `repeat { … } while cond` is one loop
#: with one condition and the `while` carries it, exactly as PHP's
#: `do … while` does.
#:
#: A `?` needs a following `:` to be a ternary. Swift spells optionals
#: `Int?`, so every optional parameter and property in the language was
#: scoring as a decision — the same defect found in C#, TypeScript, PHP
#: and Java, in a fifth spelling.
SWIFT_COMPLEXITY_RE = re.compile(
    r"\b(if|for|while|case|catch|guard)\b|&&|\|\||\?\?"
    # Same rule as the C family: a ternary needs both halves. Swift
    # writes optionals as `Int?`, so without the `:` every optional
    # parameter and property in the language scored as a decision.
    r"|\?(?![.?:])(?=[^?]*:)"
)


def swift_branch_points(line: str) -> int:
    """Decision points on one line of Swift."""
    return len(SWIFT_COMPLEXITY_RE.findall(line))


#: Go's vocabulary is *smaller* than C's, not larger. It has no `while`
#: (`for` covers looping), no ternary, and no `catch` — `if err != nil`
#: is already an `if`.
#:
#: This pattern first added `select` and `goto` and both were wrong,
#: which is worth keeping written down. A `select` with two cases has two
#: paths: its **cases** are the branches and the header decides nothing,
#: exactly as a `switch` header does not — `select {}` with no cases
#: simply blocks. And `goto` transfers control unconditionally, so it
#: adds an edge without adding a decision.
#:
#: The C-family pattern already counted `case`, so Go's select dispatch
#: was measured correctly before either was added. A test written from
#: the wrong intuition failed, and the code was changed to satisfy the
#: test rather than the grammar. Caught by comparing construct-by-
#: construct against an independent implementation.
GO_COMPLEXITY_RE = re.compile(
    r"\b(if|for|case)\b|&&|\|\|"
)


#: Rust, corrected construct-by-construct against the reference after
#: three disagreements, all of them this project's.
#:
#: `loop` is **not** counted: it is unconditional, and the `if … break`
#: inside it is what decides. Counting the head as well double-counts,
#: exactly as `goto` did in Go.
#:
#: `?` **is** counted, reversing an earlier claim that it "propagates an
#: error and decides nothing". It decides: `let x = f()?` continues or
#: returns early, and it expands to a `match` with two arms. Idiomatic
#: Rust being full of them is a fact about idiomatic Rust, not a reason
#: to under-count it.
#:
#: `match` arms are counted except the wildcard. Two real arms and a `_`
#: is three paths, the same shape as two `case`s and a `default`, which
#: is what Go already scores. lizard reads a whole `match` as one
#: decision and this project does not follow it there — see
#: `tests/test_grammar_constructs.py`, where that divergence is declared
#: with its reason rather than silently absorbed.
RUST_COMPLEXITY_RE = re.compile(
    r"\b(if|for|while)\b|&&|\|\||\?|(?<!_\s)(?<!_)=>"
)


#: PHP spells its multi-way branch `elseif`, one word with no boundary
#: inside it, so the C-family pattern matched neither `if` nor `elif`
#: there and a dispatch chain scored *zero*. `foreach` is its primary
#: loop and `and`/`or`/`xor` are word operators.
#:
#: Three corrections after checking every construct in the reference
#: against an independent implementation:
#:
#: `do` is not counted. `do { … } while (cond)` is one loop with one
#: condition, and the `while` clause already carries it.
#:
#: `goto` is not counted. It transfers control unconditionally — the
#: same reasoning that removed it from Go.
#:
#: A `?` immediately followed by an identifier character is a **nullable
#: type hint**, not a ternary. `?int $v` decides nothing, and counting it
#: made every nullable parameter in the language a branch. This is D78's
#: optional-chaining defect wearing different syntax.
PHP_COMPLEXITY_RE = re.compile(
    r"\b(elseif|if|for|foreach|while|match|case|catch|and|or|xor)\b"
    r"|&&|\|\||\?\?"
    # A ternary, but not a nullable type hint. `?int $v` is a type
    # declaration and decides nothing; counted, every nullable parameter
    # in the language read as a branch. `?` followed immediately by an
    # identifier character is a type, and a ternary is written with the
    # expression separated: `$x ? 1 : 2`.
    r"|\?(?![.?:\w])"
)


#: Ruby writes its negated conditional and loop as words the C pattern
#: never looks for — `unless` and `until` — and both are ordinary rather
#: than exotic: `return 0 unless value` is the idiomatic guard clause.
#: `elsif` is spelled with one `e`, so `elif` misses it too. Measured with
#: C's keywords, a guard-heavy Ruby method reads as branchless.
RUBY_COMPLEXITY_RE = re.compile(
    r"\b(if|elsif|unless|while|until|for|when|rescue)\b"
    r"|&&|\|\||\band\b|\bor\b"
    # The ternary. Not `&.` (safe navigation decides nothing, as `?.`
    # does not in JavaScript — D78), and not a method name ending in
    # `?`, which is why a word character may not precede it.
    r"|(?<![\w&.])\?(?![.?])"
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


#: Python's decision points, from the language reference rather than
#: from the C family it was borrowed from. `and` and `or` are the boolean
#: operators — the shared pattern looked for `&&` and `||`, which Python
#: does not have, so every one of them was invisible: 3,199 in this
#: repository alone. `if` covers the statement, the ternary
#: (`a if b else c`) and the comprehension condition, all of which are
#: decisions. `case` counts and `match` does not, by the arms-not-header
#: rule shared with Go, PHP, Ruby and Fortran. `not` decides nothing, and
#: neither does `else`.
# `case` carries the branch and `match` does not — the arms-not-header
# rule shared with Go, PHP, Ruby and Fortran. The wildcard `case _` is
# excluded because it is Python's `default`: it always matches, so it
# adds a path without a decision to reach it, exactly as Go's `default:`
# and Rust's `_ =>` do. `case _ if guard:` is excluded here too and
# counted by its `if`, which is the decision; `case _name:` and
# `case [_, x]:` are ordinary patterns and still count.
PYTHON_COMPLEXITY_RE = re.compile(
    r"\b(?:if|elif|for|while|except|and|or)\b"
    r"|\bcase\b(?!\s+_\s*(?::|if\b))"
)


def python_branch_points(line: str) -> int:
    """Decision points on one line of Python."""
    return len(PYTHON_COMPLEXITY_RE.findall(line))


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

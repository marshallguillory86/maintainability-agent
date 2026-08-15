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
# ``_ranges.js_declaration_ranges`` instead, which bounds each body by
# its own braces. Ranges from these patterns are bounded by
# indentation, never by the next match — see ``_ranges`` for why.
FUNC_PATTERNS = [
    (re.compile(r"^\s*(?:async\s+)?def\s+([A-Za-z_][\w]*)\s*\("), "function"),
    (re.compile(r"^\s*(?:(?:export|default|async)\s+)*function\s+([A-Za-z_$][\w$]*)\s*(?:<[^()]*>\s*)?\("), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"), "function"),
    (re.compile(r"^\s*(?:export\s+)?(?:default\s+)?class\s+([A-Za-z_$][\w$]*)\b"), "class"),
]

COMPLEXITY_RE = re.compile(r"\b(if|elif|for|while|except|case|catch)\b|&&|\|\||\?")


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
    ".for": "Fortran", ".ftn": "Fortran",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell", ".ps1": "PowerShell",
    ".sql": "SQL", ".groovy": "Groovy", ".vue": "Vue", ".svelte": "Svelte",
    ".zig": "Zig", ".nim": "Nim", ".cr": "Crystal", ".d": "D", ".ada": "Ada", ".adb": "Ada",
}

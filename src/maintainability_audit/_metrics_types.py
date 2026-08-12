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

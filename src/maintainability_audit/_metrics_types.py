"""Internal value-types + regex constants used by ``metrics.py``.

Extracted from ``metrics.py`` (2026-05-11) so the metrics module
stays under the maintainability config's warn threshold for file
length — eating our own dogfood on the A+ grade. Not a public API;
import from ``metrics`` if you need any of these symbols externally.
"""
from __future__ import annotations

import re
from dataclasses import dataclass


FUNC_PATTERNS = [
    re.compile(r"^\s*def\s+([A-Za-z_][\w]*)\s*\("),
    re.compile(r"^\s*(?:async\s+)?function\s+([A-Za-z_$][\w$]*)\s*\("),
    re.compile(r"^\s*(?:export\s+)?(?:const|let|var)\s+([A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>"),
    re.compile(r"^\s*(?:export\s+default\s+)?class\s+([A-Za-z_$][\w$]*)\b"),
]

COMPLEXITY_RE = re.compile(r"\b(if|elif|for|while|except|case|catch)\b|&&|\|\||\?")


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


@dataclass
class RiskFinding:
    path: str
    line: int
    name: str
    text: str

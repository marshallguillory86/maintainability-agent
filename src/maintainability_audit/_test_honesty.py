"""Test honesty: where a suite has stopped testing (Decision 19).

After Ken Pugh's AlignThree Spectables, whose generated stubs fail until they
are written, so an unwritten step can never pass. A suite reports a skipped,
pending or expected-failure test as something other than a failure, and to a
reader who looks only at the result a skip is a pass. This names each one.

Reported only. Nothing here reaches `score_report` or a gate: the block is
attached after the score is sealed, on ADR 003's terms for findings whose
precision is unmeasured.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from ._metrics_types import is_test_path
from ._oracle import SUPPRESSION_MARKERS, _is_quoted
from .source import SourceIndex

CREDIT = ("After Ken Pugh's AlignThree Spectables (https://alignthree.com): "
          "a test that is not written, or not run, never counts as passing.")

_SKIP_LABELS = frozenset({"skipped test", "disabled test", "ignored test"})

#: A skip written as a directive, from the oracle's own marker set, and as a
#: call, which a suite reports the same way.
_SKIPS = tuple(re.compile(pattern, re.IGNORECASE)
               for pattern, label in SUPPRESSION_MARKERS if label in _SKIP_LABELS) + (
    re.compile(r"\bpytest\.skip\("),
    re.compile(r"\bx(?:it|describe|test)\("),
    re.compile(r"\b(?:it|describe|test)\.(?:skip|todo)\("),
    re.compile(r"\bthis\.skip\(\)"),
)


def _skip_in(text: str) -> bool:
    """Whether this line skips a test, rather than mentioning a skip."""
    for pattern in _SKIPS:
        match = pattern.search(text)
        if match and not _is_quoted(text, match.start()):
            return True
    return False


def skipped_tests(root: Path, files: list[Path], source: SourceIndex) -> list[dict[str, Any]]:
    """Every skip in a test file of `files`, by path and line, in path order."""
    found: list[dict[str, Any]] = []
    for path in sorted(files):
        rel = path.relative_to(root).as_posix()
        if not is_test_path(rel):
            continue
        for number, text in enumerate(source.lines(path), 1):
            if _skip_in(text):
                found.append({"path": rel, "line": number, "text": text.strip()[:180]})
    return found


def test_honesty(root: Path, files: list[Path], source: SourceIndex) -> dict[str, Any]:
    """The report block: findings and the credit they carry."""
    return {"skipped": skipped_tests(root, files, source), "credit": CREDIT}

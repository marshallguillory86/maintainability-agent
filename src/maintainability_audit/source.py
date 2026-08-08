"""Read each file once, parse each file once.

Every scanner needs the same two things: a file's lines, and the
declarations inside it. Each was computing them independently, so an
audit read every file five times and parsed every source file three
times. On Django that was most of a ten-second run doing work it had
already done.

This holds both, keyed by path, for the life of a single audit. It is
deliberately not a global or a decorator cache: a long-lived process
auditing many repositories should not accumulate every file it has ever
seen, and a second audit of the same repo should see current content
rather than a snapshot. ``build_report`` creates one and passes it down;
anything called without one falls back to reading directly, so every
entry point still works standalone.
"""
from __future__ import annotations

from pathlib import Path

from ._metrics_types import DeclRange
from .declarations import DECLARATION_SUFFIXES, declaration_ranges


class SourceIndex:
    """Per-audit cache of file contents and parsed declarations."""

    def __init__(self) -> None:
        self._lines: dict[Path, list[str]] = {}
        self._declarations: dict[Path, tuple[list[DeclRange], list[str]]] = {}

    def lines(self, path: Path) -> list[str]:
        cached = self._lines.get(path)
        if cached is None:
            cached = _read(path)
            self._lines[path] = cached
        return cached

    def declarations(self, path: Path) -> tuple[list[DeclRange], list[str]]:
        """Declaration ranges plus the lines to score them against.

        Returns empty for extensions with no detector, so callers can ask
        about any file without checking the suffix first.
        """
        cached = self._declarations.get(path)
        if cached is None:
            lines = self.lines(path)
            cached = declaration_ranges(path, lines) if path.suffix in DECLARATION_SUFFIXES else ([], lines)
            self._declarations[path] = cached
        return cached


def _read(path: Path) -> list[str]:
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()


def index_or_new(index: SourceIndex | None) -> SourceIndex:
    """The caller's index, or a throwaway one for standalone use."""
    return index if index is not None else SourceIndex()

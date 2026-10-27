"""Spectables specifications, read where a repository keeps them (Decision 19).

Ken Pugh's AlignThree Spectables (https://alignthree.com) writes behaviour as
typed Given/When/Then tables in `.spectable` files; its own tooling writes and
runs them. This module reports three authoring mistakes from the published
grammar (alignthree.com/syntax.html), so a repository that keeps such specs
hears about them in the same audit as its code:

- ``column-count``: a table row whose cell count differs from its first row;
- ``duplicate-scenario``: a second scenario of the same name in one file;
- ``undefined-reference``: an ``=Name`` cell naming no ``Define`` in any
  specification read — "`=Name` must refer to a valid Define block".

Unknown types are not reported: the grammar publishes no list of built-in
types, so every primitive would read as unknown. Reported only; nothing here
reaches `score_report`.
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from .metrics import is_excluded

LINK = "https://alignthree.com"
SUFFIX = ".spectable"

_DEFINE_NAMED = re.compile(r"^\s*Define\s+([A-Za-z_]\w*)")
_DEFINE_BARE = re.compile(r"^\s*Define\s*$")
_SCENARIO = re.compile(r"^\s*Scenario:?\s+(\S.*)")
_REFERENCE = re.compile(r"^=([A-Za-z_]\w*)$")
_UNESCAPED_PIPE = re.compile(r"(?<!\\)\|")


def _cells(row: str) -> list[str]:
    inner = row.strip()[1:]
    if inner.endswith("|") and not inner.endswith("\\|"):
        inner = inner[:-1]
    return [cell.strip() for cell in _UNESCAPED_PIPE.split(inner)]


class _Spec:
    """One file's tables, defines, scenarios and references, read in one pass."""

    def __init__(self, rel: str, lines: list[str]) -> None:
        self.rel = rel
        self.defines: set[str] = set()
        self.references: list[tuple[int, str]] = []
        self.findings: list[dict[str, Any]] = []
        self._scenarios: dict[str, int] = {}
        # The table being read: its first row's width, and for a bare
        # `Define` table the column whose cells each declare a name.
        self._width: int | None = None
        self._name_column: int | None = None
        self._bare_define = False
        in_docstring = False
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == '"""':
                in_docstring = not in_docstring
            elif in_docstring or stripped.startswith("#"):
                continue
            elif stripped.startswith("|"):
                self._row(number, _cells(line))
            else:
                self._text(number, line)

    def _finding(self, line: int, check: str, message: str) -> None:
        self.findings.append({"path": self.rel, "line": line, "check": check, "message": message})

    def _text(self, number: int, line: str) -> None:
        """A line outside a table: it ends the table and may declare or name."""
        self._width, self._name_column = None, None
        self._bare_define = bool(_DEFINE_BARE.match(line)) or (self._bare_define and not line.strip())
        if match := _DEFINE_NAMED.match(line):
            self.defines.add(match.group(1))
        if match := _SCENARIO.match(line):
            name = " ".join(match.group(1).split())
            if name in self._scenarios:
                self._finding(number, "duplicate-scenario",
                              f"scenario `{name}` repeats the one on line {self._scenarios[name]}")
            else:
                self._scenarios[name] = number

    def _row(self, number: int, cells: list[str]) -> None:
        """A table row: the first sets the width; each later one is held to it."""
        if self._width is None:
            self._width = len(cells)
            if self._bare_define and "Name" in cells:
                self._name_column = cells.index("Name")
            self._bare_define = False
        else:
            if len(cells) != self._width:
                noun = "cell" if len(cells) == 1 else "cells"
                self._finding(number, "column-count",
                              f"row has {len(cells)} {noun}; the table's first row has {self._width}")
            column = self._name_column
            if column is not None and column < len(cells) and cells[column]:
                self.defines.add(cells[column])
        self.references.extend((number, match.group(1)) for cell in cells
                               if (match := _REFERENCE.match(cell)))


def spectable_files(root: Path, config: dict[str, Any], only_paths: set[str] | None) -> list[Path]:
    """Every `.spectable` under `root` the audit may read, in path order.

    Not in `paths.include_extensions`, which would give a specification a
    file-length score; walked here, pruned by the same exclusions, never
    following a symlinked directory out of the tree.
    """
    patterns = list(config.get("paths", {}).get("exclude_patterns") or [])
    found: list[Path] = []
    for directory, subdirectories, names in os.walk(root, followlinks=False):
        base = Path(directory)
        subdirectories[:] = sorted(
            name for name in subdirectories
            if name != ".git" and not is_excluded((base / name).relative_to(root).as_posix() + "/", patterns))
        for name in names:
            path = base / name
            rel = path.relative_to(root).as_posix()
            if (name.endswith(SUFFIX) and not path.is_symlink() and not is_excluded(rel, patterns)
                    and (only_paths is None or rel in only_paths)):
                found.append(path)
    return sorted(found)


def spectables(root: Path, config: dict[str, Any], only_paths: set[str] | None = None) -> dict[str, Any]:
    """The report block: files read, findings, and where Spectables lives."""
    specs = [_Spec(path.relative_to(root).as_posix(),
                   path.read_text(encoding="utf-8", errors="replace").splitlines())
             for path in spectable_files(root, config, only_paths)]
    defined = set().union(*(spec.defines for spec in specs))
    findings = [finding for spec in specs for finding in spec.findings]
    findings += [{"path": spec.rel, "line": line, "check": "undefined-reference",
                  "message": f"`={name}` names no Define in the specifications read"}
                 for spec in specs for line, name in spec.references if name not in defined]
    findings.sort(key=lambda finding: (finding["path"], finding["line"], finding["check"]))
    return {"files": len(specs), "findings": findings, "link": LINK}

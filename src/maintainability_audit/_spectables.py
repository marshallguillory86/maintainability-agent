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
_SCENARIO = re.compile(r"^\s*Scenario:?\s+(.+?)\s*$")
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
        self._read(lines)

    def _finding(self, line: int, check: str, message: str) -> None:
        self.findings.append({"path": self.rel, "line": line, "check": check, "message": message})

    def _read(self, lines: list[str]) -> None:
        width: int | None = None
        bare_define = False
        name_column: int | None = None
        in_docstring = False
        scenarios: dict[str, int] = {}
        for number, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped == '"""':
                in_docstring = not in_docstring
                continue
            if in_docstring or stripped.startswith("#"):
                continue
            if not stripped.startswith("|"):
                width, name_column = None, None
                bare_define = bool(_DEFINE_BARE.match(line)) or (bare_define and not stripped)
                if match := _DEFINE_NAMED.match(line):
                    self.defines.add(match.group(1))
                if match := _SCENARIO.match(line):
                    name = " ".join(match.group(1).split())
                    if name in scenarios:
                        self._finding(number, "duplicate-scenario",
                                      f"scenario `{name}` repeats the one on line {scenarios[name]}")
                    else:
                        scenarios[name] = number
                continue
            cells = _cells(line)
            if width is None:
                width = len(cells)
                if bare_define and "Name" in cells:
                    name_column = cells.index("Name")
                bare_define = False
            else:
                if len(cells) != width:
                    self._finding(number, "column-count",
                                  f"row has {len(cells)} cells; the table's first row has {width}")
                if name_column is not None and name_column < len(cells) and cells[name_column]:
                    self.defines.add(cells[name_column])
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

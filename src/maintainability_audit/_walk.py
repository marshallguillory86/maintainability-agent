"""The one walk of an audited tree.

`Path.rglob` descends into `.git` and raises `FileNotFoundError` when a
directory it listed is gone by the time it opens it, so a worktree git added
and removed during an audit aborted the whole audit (2026-10-30). This walk
never enters `.git`, never follows a symlinked directory out of the tree, and
treats a directory it cannot open as empty: what vanished was not there to
audit. Every walk of the audited tree uses it; a structural test refuses
`rglob` anywhere else in the package.
"""

from __future__ import annotations

import fnmatch
import os
from collections.abc import Iterator
from pathlib import Path


def walk(root: Path, pattern: str = "*") -> Iterator[Path]:
    """Every file and directory below `root` whose name matches `pattern`, as `rglob` gives them."""
    for directory, subdirectories, names in os.walk(root, followlinks=False):
        subdirectories[:] = sorted(name for name in subdirectories if name != ".git")
        base = Path(directory)
        for name in (*subdirectories, *sorted(names)):
            if fnmatch.fnmatchcase(name, pattern):
                yield base / name

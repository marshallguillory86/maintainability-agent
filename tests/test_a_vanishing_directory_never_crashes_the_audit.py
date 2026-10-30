"""A directory that disappears or cannot be read mid-walk never crashes the audit.

Found 2026-10-30: the full suite failed in `test_readme_claims` with
`FileNotFoundError: '.git/worktrees'`. Discovery walked the tree with
`Path.rglob("*")`, which descends into `.git` and raises when a directory it
listed is gone by the time it is opened — here a worktree another process was
adding and removing. On a developer's machine that is git, an IDE or a build
running beside the audit, and one such directory aborted the whole audit.

Every walk of the audited tree goes through `_walk.walk`, which never enters
`.git`, never follows a symlinked directory, and treats a directory it cannot
open as empty. The structural test holds the class: no `rglob` anywhere in the
package outside `_walk.py`.
"""
from __future__ import annotations

import copy
import os
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"


def _vanishing(monkeypatch: pytest.MonkeyPatch, name: str) -> None:
    """`os.scandir` of any directory called `name` fails as if it had just been removed."""
    real = os.scandir

    def scandir(path: os.PathLike[str] | str = ".") -> os.ScandirIterator[str]:  # type: ignore[type-var]
        if Path(path).name == name:
            raise FileNotFoundError(2, "No such file or directory", str(path))
        return real(path)

    monkeypatch.setattr(os, "scandir", scandir)


def _tree(tmp_path: Path) -> Path:
    root = tmp_path / "tree"
    for rel, text in {
        "src/app.py": "def run():\n    return 1\n",
        "gone/inner.py": "def lost():\n    return 2\n",
        ".git/worktrees/w1/HEAD": "ref: refs/heads/x\n",
        ".git/objects/ab/cdef.py": "def not_source():\n    return 3\n",
    }.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return root


def test_the_walk_skips_dot_git_and_survives_a_vanishing_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from maintainability_audit._walk import walk

    root = _tree(tmp_path)
    _vanishing(monkeypatch, "gone")

    found = {path.relative_to(root).as_posix() for path in walk(root) if path.is_file()}
    assert found == {"src/app.py"}


def test_the_walk_matches_a_name_pattern_like_rglob(tmp_path: Path) -> None:
    from maintainability_audit._walk import walk

    root = _tree(tmp_path)

    assert {p.relative_to(root).as_posix() for p in walk(root, "*.py")} == {
        "src/app.py", "gone/inner.py"}


def test_a_full_audit_survives_a_directory_that_vanishes_mid_walk(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _tree(tmp_path)
    _vanishing(monkeypatch, "worktrees")
    _vanishing(monkeypatch, "gone")

    report = build_report(root, copy.deepcopy(load_config(None)), run_analyzers=False)

    paths = {item["path"] for item in report["largest_files"]}
    assert "src/app.py" in paths
    assert not any(path.startswith(".git/") for path in paths)


def test_no_module_walks_the_tree_except_through_the_one_walker() -> None:
    offenders = [
        f"{path.name}:{number}"
        for path in sorted(PACKAGE.glob("*.py")) if path.name != "_walk.py"
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if re.search(r"\.rglob\(", line) and not line.lstrip().startswith("#")
    ]
    assert offenders == []

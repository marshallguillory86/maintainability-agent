"""The fix-breadth window must not depend on how the cache was built.

Two audits found this measurement reading different numbers from the
same pinned commit depending on the local clone's depth, and each fix
closed only the case that had been demonstrated. These tests cover the
property itself, with synthetic repositories, so neither shape returns:

- a shallow cache already sitting at the pinned commit must be deepened
  rather than accepted (it previously yielded zero fixes where a deep
  cache yielded ninety-six, silently dropping the repository)
- the oldest commit a shallow clone holds has no parent, so git diffs it
  against the empty tree and reports its whole tree as added; that
  commit must never contribute a fabricated diff size
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "calibration"))

import measure_fix_breadth as breadth  # noqa: E402
from _git_path import GIT_PATH

ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
    "PATH": GIT_PATH,
}


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, env={**ENV, "HOME": str(cwd)})


def _origin(root: Path, pad_before: int) -> Path:
    """A repo whose one fix commit rewrites a file, ``pad_before`` commits deep.

    The fix both adds and removes lines, so a diff taken against the
    empty tree (what a parentless commit produces) cannot coincidentally
    match the real one.
    """
    origin = root / "origin"
    origin.mkdir()
    _run("git", "init", "-q", ".", cwd=origin)
    (origin / "f.py").write_text("\n".join(f"line {i}" for i in range(40)) + "\n")
    _run("git", "add", "-A", cwd=origin)
    _run("git", "commit", "-qm", "initial", cwd=origin)
    (origin / "f.py").write_text("\n".join(f"CHANGED {i}" for i in range(35)) + "\n")
    _run("git", "add", "-A", cwd=origin)
    _run("git", "commit", "-qm", "fix: rewrite f", cwd=origin)
    for index in range(pad_before):
        (origin / "pad.txt").write_text(f"pad {index}\n")
        _run("git", "add", "-A", cwd=origin)
        _run("git", "commit", "-qm", f"chore: pad {index}", cwd=origin)
    return origin


def test_a_grafted_boundary_commit_never_contributes_a_fabricated_diff(tmp_path: Path) -> None:
    """The shallow boundary must not report the whole tree as one fix.

    Reproduces the audit's case exactly: clone to a depth that lands the
    fix commit on the shallow boundary. Measured deep the fix is one
    file and seventy-five lines; measured at the boundary git reported
    two files and thirty-nine, because it diffed a parentless commit
    against nothing. Either the commit is excluded or it measures
    correctly — what it must never do is report a different number.
    """
    origin = _origin(tmp_path, pad_before=2)
    deep = breadth.fix_commits(origin)
    assert deep == [(1, 75)], "synthetic fixture changed; the boundary case below depends on it"

    shallow = tmp_path / "shallow"
    subprocess.run(["git", "clone", "-q", "--depth", "3", f"file://{origin}", str(shallow)],
                   check=True, capture_output=True, env={**ENV, "HOME": str(tmp_path)})
    assert breadth._grafted_commits(shallow), "fixture must actually be shallow at the fix commit"

    measured = breadth.fix_commits(shallow)

    assert measured in ([], deep), f"boundary commit reported a fabricated diff: {measured}"


def test_a_shallow_cache_at_the_pinned_commit_is_deepened_not_accepted(tmp_path: Path) -> None:
    """Depth is repaired independently of HEAD.

    The audit's finding: the deepening step was gated on the cached HEAD
    differing from the pin, so a depth-one cache already at the pin was
    used as-is and the window silently vanished.
    """
    origin = _origin(tmp_path, pad_before=4)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=origin, capture_output=True,
                          text=True, check=True).stdout.strip()

    cache = tmp_path / "cache"
    cache.mkdir()
    subprocess.run(["git", "clone", "-q", "--depth", "1", f"file://{origin}", str(cache / "subject")],
                   check=True, capture_output=True, env={**ENV, "HOME": str(tmp_path)})
    assert breadth._reachable_commits(cache / "subject") == 1
    assert breadth.fix_commits(cache / "subject") == [], "fixture must start with the fix hidden"

    repaired = breadth.clone(
        {"name": "subject", "full_name": "t/subject", "url": f"file://{origin}", "commit": head}, cache
    )

    assert repaired is not None
    assert breadth._reachable_commits(repaired) > 1, "shallow cache at the pin was accepted unchanged"
    assert breadth.fix_commits(repaired) == breadth.fix_commits(origin)


@pytest.mark.parametrize("depth", [2, 3, 4, 5])
def test_the_window_reads_the_same_fix_at_every_cache_depth(tmp_path: Path, depth: int) -> None:
    """Whatever depth a cache arrives at, the repaired clone agrees with
    a full one — the property both previous fixes claimed and neither
    checked across depths."""
    origin = _origin(tmp_path, pad_before=3)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=origin, capture_output=True,
                          text=True, check=True).stdout.strip()

    cache = tmp_path / f"cache{depth}"
    cache.mkdir()
    subprocess.run(["git", "clone", "-q", "--depth", str(depth), f"file://{origin}", str(cache / "subject")],
                   check=True, capture_output=True, env={**ENV, "HOME": str(tmp_path)})

    repaired = breadth.clone(
        {"name": "subject", "full_name": "t/subject", "url": f"file://{origin}", "commit": head}, cache
    )

    assert repaired is not None
    assert breadth.fix_commits(repaired) == breadth.fix_commits(origin)

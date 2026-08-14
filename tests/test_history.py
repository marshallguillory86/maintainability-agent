"""History metrics: churn, hotspots, change coupling.

The first review of this module (before it ever shipped) found three
bugs, each pinned here: multi-segment rename notation kept literal
braces, an empty rename side minted a ``//`` path that silently failed
tracked-matching, and the sweep filter ran after the tracked filter so a
500-file dependency bump could still pollute coupling counts.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from maintainability_audit.history import (
    FileChurn,
    _rename_target,
    change_coupling,
    file_churn,
    has_history,
    hotspots,
)

# ---------------------------------------------------------------------------
# Rename notation
# ---------------------------------------------------------------------------

def test_plain_paths_pass_through() -> None:
    assert _rename_target("src/app.py") == "src/app.py"


def test_whole_path_rename() -> None:
    assert _rename_target("old.py => new.py") == "new.py"


def test_braced_rename_resolves_to_the_new_path() -> None:
    assert _rename_target("src/{old => new}/leaf.py") == "src/new/leaf.py"


def test_multiple_braced_segments_all_resolve() -> None:
    """The first version resolved only the first segment, keeping the
    second's braces literally — inventing a path that never existed."""
    assert _rename_target("a/{b => c}/x/{d => e}/y.py") == "a/c/x/e/y.py"


def test_empty_new_side_collapses_the_doubled_slash() -> None:
    """``src/{old => }/leaf`` is a directory flattening. Without the
    collapse it produced ``src//leaf``, which then silently failed to
    match any tracked path — dropping the file's churn on the floor."""
    assert _rename_target("src/{old => }/leaf.py") == "src/leaf.py"


# ---------------------------------------------------------------------------
# Churn and hotspots (pure functions first)
# ---------------------------------------------------------------------------

def test_hotspots_require_both_churn_and_complexity() -> None:
    """The product is the point: complex-but-stable and busy-but-simple
    files must both stay off the list."""
    churn = {
        "stable.py": FileChurn("stable.py", commits=1, added=5, removed=1),
        "busy.py": FileChurn("busy.py", commits=30, added=900, removed=400),
        "hot.py": FileChurn("hot.py", commits=10, added=300, removed=100),
    }
    complexity = {"stable.py": 500, "busy.py": 0, "hot.py": 200}

    ranked = hotspots(churn, complexity)

    assert [item["file"] for item in ranked] == ["hot.py"]
    assert ranked[0]["score"] == 10 * 200


# ---------------------------------------------------------------------------
# Against a real repository built commit by commit
# ---------------------------------------------------------------------------

def _git(path: Path, *args: str) -> None:
    subprocess.run(
        ["git", *args], cwd=path, check=True, capture_output=True,
        env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "PATH": "/usr/bin:/bin",
             "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
             "HOME": str(path)},
    )


def _repo(tmp_path: Path) -> Path:
    _git(tmp_path, "init", "--quiet")
    return tmp_path


def _commit(root: Path, message: str, **files: str) -> None:
    for name, content in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    _git(root, "add", "-A")
    _git(root, "commit", "--quiet", "-m", message)


def test_file_churn_counts_commits_lines_and_authors(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _commit(root, "one", **{"a.py": "x = 1\n"})
    _commit(root, "two", **{"a.py": "x = 1\ny = 2\n", "b.py": "z = 3\n"})

    churn = file_churn(root, since="10 years ago")

    assert churn["a.py"].commits == 2
    assert churn["a.py"].added == 2  # one line each commit
    assert churn["b.py"].commits == 1
    assert len(churn["a.py"].authors) == 1


def test_tracked_filter_drops_untracked_paths(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _commit(root, "one", **{"a.py": "x = 1\n", "vendor/lib.js": "var x\n"})

    churn = file_churn(root, since="10 years ago", tracked={"a.py"})

    assert set(churn) == {"a.py"}


def test_coupling_finds_files_that_change_together(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    for index in range(6):
        _commit(root, f"pair {index}", **{
            "left.py": f"a = {index}\n",
            "right.py": f"b = {index}\n",
        })
    _commit(root, "solo", **{"left.py": "a = 99\n"})

    coupled = change_coupling(root, since="10 years ago")

    assert len(coupled) == 1
    assert coupled[0]["files"] == ["left.py", "right.py"]
    assert coupled[0]["co_changes"] == 6
    # right.py changed 6 times, always with left.py
    assert coupled[0]["confidence"] == 1.0


def test_sweep_commits_are_judged_on_raw_size(tmp_path: Path) -> None:
    """A dependency bump touching 40 files must not couple the tracked
    handful it brushes. The first version filtered to tracked paths
    *before* the size check, so exactly this commit sailed through."""
    root = _repo(tmp_path)
    sweep = {f"gen/f{index}.txt": "x\n" for index in range(40)}
    sweep["a.py"] = "a = 1\n"
    sweep["b.py"] = "b = 1\n"
    for index in range(6):
        bumped = {name: f"v{index}\n" for name in sweep}
        _commit(root, f"bump {index}", **bumped)

    coupled = change_coupling(root, since="10 years ago", tracked={"a.py", "b.py"})

    assert coupled == []


def test_shallow_history_is_reported_as_unknown(tmp_path: Path) -> None:
    """No history and no changes are opposite findings."""
    assert has_history(tmp_path) is False  # not a repo at all

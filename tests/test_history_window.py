"""D56: an empty history window is unknown, not perfect.

`_history_rate_aspect` returned 5.0 for `files_changed == 0` — "had
history to read; nothing changed in the window". So a repository whose
only commit predates the twelve-month window scored full marks on every
history aspect, with a working tree the photograph could see and the
window could not.

It fails in the direction P3 names, which is what makes it worse than a
wrong number: *withholding* the history object lowers the result, and
*supplying* an empty window raises it. Evidence that said nothing
outscored evidence that was absent.

This is D37's collapse one layer up. There a failed `git log` produced
zeros and the zeros read as quiet, and the fix made the spawner raise.
Here the log succeeds and produces the same zeros honestly — and they
mean the same thing. A rate needs a denominator; zero files changed is
no denominator, which is the state a shallow clone is in, and the
function's own docstring already said a shallow clone must not grade as
either clean or dirty.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from maintainability_audit._aspects import _history_rate_aspect
from maintainability_audit.config import load_config
from maintainability_audit.evidence import HistoryEvidence, Measured
from maintainability_audit.report import build_report


def _window(**counts: int) -> HistoryEvidence:
    """History whose counts are *measured*, not merely present.

    The first draft of these tests passed plain integers. `measured()`
    returns None for anything that is not a `Measured`, so every
    assertion below held regardless of what the code did — the shape of
    vacuous test this project keeps catching. `Measured(0)` is the
    scanner having looked and found none, which is the whole point.
    """
    return HistoryEvidence(**{
        name: Measured(value, "git log") for name, value in counts.items()
    })


def test_an_empty_window_is_unknown_rather_than_perfect() -> None:
    """Zero files changed is no denominator, so there is no rate."""
    empty = _window(
        files_changed=0,
        qualifying_hotspots=0,
        code_coupling_pairs=0,
        multi_commit_files=0,
        single_author_files=0,
    )
    assert _history_rate_aspect(empty, "qualifying_hotspots") is None, (
        "an empty window scored as perfect history; a repository whose only "
        "commit predates the window would grade A+ on every history aspect"
    )
    assert _history_rate_aspect(empty, "code_coupling_pairs") is None


def test_a_window_with_commits_still_scores() -> None:
    """The fix must not have withheld every history rate."""
    busy = _window(
        files_changed=100,
        qualifying_hotspots=0,
        code_coupling_pairs=0,
        multi_commit_files=10,
        single_author_files=1,
    )
    assert _history_rate_aspect(busy, "qualifying_hotspots") == 5.0, (
        "a real window with no hotspots stopped scoring well, which is a "
        "different claim from having no window at all"
    )


def test_a_repository_whose_commits_predate_the_window_gets_no_verified_grade(
    real_population_floors: object,
) -> None:
    """The reproduction, end to end, on a real repository.

    One commit outside the window and a dirty working tree: history has
    nothing to say, and the report must not say it said something good.
    """
    with tempfile.TemporaryDirectory() as work:
        root = Path(work) / "stale"
        root.mkdir()
        (root / "README.md").write_text("# r\n", encoding="utf-8")
        for index in range(60):
            (root / f"m{index}.py").write_text(
                "def f():\n    return 1\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        old = "2024-01-01T00:00:00"
        subprocess.run(
            ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
             "-c", "commit.gpgsign=false", "commit", "-qm", "old",
             "--date", old],
            check=True,
            env={"GIT_COMMITTER_DATE": old, "PATH": __import__("os").environ["PATH"]},
        )
        report = build_report(root, load_config(None))

    history = report.get("history") or {}
    assert history.get("files_changed") in (0, None), (
        "the fixture's commit landed inside the window; the case is not "
        f"being exercised: {history.get('files_changed')}"
    )
    aspects = report["score"]["aspects"]
    for name in ("churn_hotspots", "change_coupling", "knowledge_concentration"):
        assert aspects.get(name) != 5.0, (
            f"{name} scored a perfect 5.0 from a window containing no commits"
        )

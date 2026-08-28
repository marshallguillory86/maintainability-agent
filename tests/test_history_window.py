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

import pytest

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


def _commit(root: Path, message: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "-c", "commit.gpgsign=false", "commit", "-qm", message],
        check=True,
    )


def _repo(work: str, name: str) -> Path:
    """A git repository with a first commit inside the window."""
    root = Path(work) / name
    root.mkdir()
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for index in range(60):
        (root / f"m{index}.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    _commit(root, "base")
    return root


def test_the_window_counts_what_the_log_actually_held(
    real_population_floors: object,
) -> None:
    """D66: the report carries both counts, from a real repository.

    Without these two numbers the three causes of `files_changed: 0` are
    indistinguishable downstream, which is the whole defect.
    """
    with tempfile.TemporaryDirectory() as work:
        root = _repo(work, "counted")
        (root / "m0.py").write_text("def f():\n    return 2\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "."], check=True)
        _commit(root, "second")
        report = build_report(root, load_config(None))

    history = report["history"]
    assert history["commits_in_window"] == 2, history
    assert history["commits_considered"] == 2, history
    assert history["files_changed"] >= 1, history


def test_a_window_filtered_to_empty_says_so() -> None:
    """Commits landed; none touched a file this audit scans.

    The lockfile case. `file_churn` restricts to tracked source paths, so
    a window of dependency bumps produces `files_changed: 0` from a log
    that read every one of them -- and the reader was told nothing was
    committed at all.
    """
    from maintainability_audit.evidence import (
        NO_SCANNED_FILES_CHANGED,
        NotApplicable,
        _normalize_history,
    )
    from maintainability_audit.renderers import render_history_markdown

    report = _empty_window_report(commits_in_window=7, commits_considered=7)
    state = _normalize_history(report).qualifying_hotspots
    assert isinstance(state, NotApplicable), state
    assert state.reason == NO_SCANNED_FILES_CHANGED, (
        "seven commits were read and filtered out, and the reader was told "
        f"the window was empty: {state.reason}"
    )

    rendered = "\n".join(render_history_markdown(report))
    assert "filtered to empty" in rendered, rendered
    assert "No commit falls inside" not in rendered, (
        "the report claims nothing was committed in a window holding seven "
        f"commits: {rendered}"
    )


def test_a_merge_only_window_is_not_reported_as_a_quiet_one() -> None:
    """Every commit in the window is a merge, so `--no-merges` emptied it."""
    from maintainability_audit.evidence import (
        MERGES_ONLY,
        NotApplicable,
        _normalize_history,
    )
    from maintainability_audit.renderers import render_history_markdown

    report = _empty_window_report(commits_in_window=4, commits_considered=0)
    state = _normalize_history(report).multi_commit_files
    assert isinstance(state, NotApplicable) and state.reason == MERGES_ONLY, state
    rendered = "\n".join(render_history_markdown(report))
    assert "are merges" in rendered, rendered
    assert "No commit falls inside" not in rendered, rendered


def test_a_genuinely_empty_window_still_reads_as_empty() -> None:
    """The case D56 closed must not become collateral of D66's wording."""
    from maintainability_audit.evidence import (
        EMPTY_WINDOW,
        NotApplicable,
        _normalize_history,
    )
    from maintainability_audit.renderers import render_history_markdown

    report = _empty_window_report(commits_in_window=0, commits_considered=0)
    state = _normalize_history(report).qualifying_hotspots
    assert isinstance(state, NotApplicable) and state.reason == EMPTY_WINDOW, state
    assert "No commit falls inside" in "\n".join(render_history_markdown(report))


def test_a_report_written_before_the_counts_existed_still_normalizes() -> None:
    """Reports already on disk carry neither count and must not crash."""
    from maintainability_audit.evidence import (
        EMPTY_WINDOW,
        NotApplicable,
        _normalize_history,
    )
    from maintainability_audit.renderers import render_history_markdown

    report = _empty_window_report()
    state = _normalize_history(report).code_coupling_pairs
    assert isinstance(state, NotApplicable) and state.reason == EMPTY_WINDOW, state
    assert "No commit falls inside" in "\n".join(render_history_markdown(report))


def _empty_window_report(**counts: int) -> dict:
    """A report whose window produced no churn, however it got there."""
    history = {
        "window": "12 months ago",
        "files_changed": 0,
        "qualifying_hotspots": 0,
        "code_coupling_pairs": 0,
        "multi_commit_files": 0,
        "single_author_files": 0,
    }
    history.update(counts)
    # Normalized through `_normalize_history` rather than the public
    # entry point: the whole-report path needs a summary this case has
    # no opinion about, and inventing one would put the fixture's
    # numbers in front of the behaviour under test.
    return {"history": history}


@pytest.mark.parametrize(
    "counts",
    [
        pytest.param({"commits_in_window": True, "commits_considered": 0}, id="bool-is-an-int"),
        pytest.param({"commits_in_window": -4, "commits_considered": 0}, id="negative window"),
        pytest.param({"commits_in_window": 2, "commits_considered": -1}, id="negative subset"),
        pytest.param({"commits_in_window": 2, "commits_considered": 9}, id="subset exceeds set"),
        pytest.param({"commits_in_window": "7", "commits_considered": 7}, id="string count"),
        pytest.param({"commits_in_window": 3.5, "commits_considered": 0}, id="fractional commits"),
        pytest.param({"commits_in_window": 7}, id="half the pair"),
    ],
)
def test_an_incoherent_pair_of_counts_earns_the_least_specific_reason(
    counts: dict[str, object],
) -> None:
    """D66's reason must be *right*, and it cannot be from nonsense.

    These two fields are not `HistoryEvidence` members, so nothing
    upstream validates them. The first version asked only
    `isinstance(..., int)` -- under which `True` is an int worth one
    commit, so `commits_in_window: true` with `commits_considered: 0`
    told the reader, confidently, that every commit in their window was
    a merge. An audit found it by handing over a corrupt report.

    A wrong reason stated confidently is the exact defect D66 exists to
    remove, so an incoherent pair falls back to the plain empty-window
    wording rather than to whichever specific story it happens to fit.
    """
    from maintainability_audit.evidence import (
        EMPTY_WINDOW,
        NotApplicable,
        _normalize_history,
    )

    report = _empty_window_report(**counts)  # type: ignore[arg-type]
    state = _normalize_history(report).qualifying_hotspots
    assert isinstance(state, NotApplicable), state
    assert state.reason == EMPTY_WINDOW, (
        f"counts {counts} are not two coherent commit counts and produced a "
        f"confident explanation anyway: {state.reason}"
    )

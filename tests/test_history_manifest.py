"""ADR 001 stage 9: history is pinned, and a drifted cache is refused.

The last stage of the evidence migration, and the one with a shipped
false result behind it. `measure_fix_breadth` used to clone and measure in
one step, so what got measured depended on whatever the cache happened to
hold. Six audits went into that area; the last found the reason the
numbers moved:

    the oldest commit a shallow clone holds has no parent locally, so git
    diffs it against the empty tree and `--numstat` reports the entire
    tree as added

One fix commit measured (1 file, 75 lines) in a full clone and (2 files,
39 lines) at the shallow boundary. Same commit, same window, different
answer — and nothing could catch it, because there was nothing to check
the cache *against*.

These tests build real git repositories on disk and clone them shallow
over `file://`, so the boundary condition is the genuine article rather
than a mock of it. Nothing here touches the network.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools" / "calibration"))

import history_manifest as hm  # noqa: E402


def _run(*args: str, cwd: Path) -> str:
    result = subprocess.run(  # noqa: S603
        args, cwd=cwd, capture_output=True, text=True, check=True, timeout=120,
    )
    return result.stdout.strip()


def _repo_with(commits: int, tmp_path: Path, name: str = "origin") -> Path:
    """A real repository with a linear history of `commits` commits."""
    path = tmp_path / name
    path.mkdir(parents=True)
    _run("git", "init", "--quiet", "-b", "main", cwd=path)
    _run("git", "config", "user.email", "test@example.invalid", cwd=path)
    _run("git", "config", "user.name", "Test", cwd=path)
    _run("git", "config", "commit.gpgsign", "false", cwd=path)
    for index in range(commits):
        (path / "file.txt").write_text(f"line {index}\n" * (index + 1), encoding="utf-8")
        _run("git", "add", "file.txt", cwd=path)
        _run("git", "commit", "--quiet", "-m", f"fix: change {index}", cwd=path)
    return path


def _shallow_clone(origin: Path, depth: int, tmp_path: Path, name: str) -> Path:
    target = tmp_path / name
    _run("git", "clone", "--quiet", "--depth", str(depth), f"file://{origin}", str(target),
         cwd=tmp_path)
    return target


@pytest.fixture
def pinned(tmp_path: Path) -> tuple[Path, Path, dict]:
    """An origin, a deep-enough cache, and the manifest built from it."""
    origin = _repo_with(8, tmp_path)
    head = _run("git", "rev-parse", "HEAD", cwd=origin)
    cache = tmp_path / "cache"
    cache.mkdir()
    entry = {"name": "subject", "full_name": "org/subject",
             "url": f"file://{origin}", "commit": head, "declarations": 10}
    monkey_window = 5
    original = hm.WINDOW_COMMITS
    hm.WINDOW_COMMITS = monkey_window
    hm.FETCH_DEPTH = monkey_window + 1
    try:
        manifest = hm.build({"test": [entry]}, cache)
    finally:
        hm.WINDOW_COMMITS = original
        hm.FETCH_DEPTH = original + 1
    manifest["window_commits"] = original  # keep verify's comparability check happy
    return origin, cache, manifest


def test_the_manifest_records_the_window_it_selected(pinned) -> None:
    """A manifest that does not name its commits pins nothing."""
    _origin, _cache, manifest = pinned
    subject = manifest["subjects"]["org/subject"]

    assert subject["pinned_head"], "the manifest must name the head it pinned"
    assert subject["window_commits"], "the manifest must list the commits it selected"
    assert manifest["selection_rule"], "the manifest must state the rule it selected under"
    assert manifest["tool_version"], "a manifest built by another version is not comparable"


def test_a_matching_cache_verifies_clean(pinned) -> None:
    _origin, cache, manifest = pinned
    assert hm.verify(manifest, cache) == []


def test_a_missing_clone_is_refused_not_measured(pinned, tmp_path: Path) -> None:
    _origin, _cache, manifest = pinned
    empty = tmp_path / "empty-cache"
    empty.mkdir()

    problems = hm.verify(manifest, empty)

    assert problems, "an absent clone must be reported, never treated as measurable"
    assert "no clone in the cache" in problems[0]


def test_a_cache_at_the_wrong_commit_is_refused(pinned) -> None:
    """The cache drifting off the pin is the whole reproducibility question."""
    _origin, cache, manifest = pinned
    subject = cache / "subject"
    older = _run("git", "rev-parse", "HEAD~2", cwd=subject)
    _run("git", "checkout", "--quiet", older, cwd=subject)

    problems = hm.verify(manifest, cache)

    assert problems, "a cache that has moved off the pinned commit must be refused"
    assert "manifest pins" in problems[0]


def test_a_cache_missing_a_required_parent_is_refused(tmp_path: Path) -> None:
    """The defect that shipped a false number, reproduced exactly.

    The manifest is built from a cache deep enough to have every parent.
    Measurement then runs against a genuinely shallow clone of the same
    origin at the same commit — which is precisely the case an earlier
    audit found being accepted and measured: correct pinned commit,
    missing history behind it.
    """
    origin = _repo_with(8, tmp_path)
    head = _run("git", "rev-parse", "HEAD", cwd=origin)
    entry = {"name": "subject", "full_name": "org/subject",
             "url": f"file://{origin}", "commit": head, "declarations": 10}

    deep_cache = tmp_path / "deep"
    deep_cache.mkdir()
    original = hm.WINDOW_COMMITS
    hm.WINDOW_COMMITS, hm.FETCH_DEPTH = 5, 6
    try:
        manifest = hm.build({"test": [entry]}, deep_cache)
        shallow_cache = tmp_path / "shallow"
        shallow_cache.mkdir()
        _shallow_clone(origin, 2, shallow_cache, "subject")
        problems = hm.verify(manifest, shallow_cache)
    finally:
        hm.WINDOW_COMMITS, hm.FETCH_DEPTH = original, original + 1

    assert problems, (
        "a shallow cache sitting at the correct pinned commit must be refused: "
        "this is the shape that measured one fix commit as (1 file, 75 lines) "
        "deep and (2 files, 39 lines) shallow"
    )
    assert any(
        "empty tree" in line or "pinned window commits" in line for line in problems
    ), f"the refusal must name why the number would be wrong, got: {problems}"


def test_measurement_never_reaches_the_network(tmp_path: Path, monkeypatch) -> None:
    """Stage 9's actual claim: measuring reads, it does not fetch.

    `measure` used to call `clone`. Any subprocess that would clone or
    fetch fails this test, so the separation is enforced rather than
    described.
    """
    sys.path.insert(0, str(ROOT / "tools" / "calibration"))
    import measure_fix_breadth as mfb

    origin = _repo_with(8, tmp_path)
    cache = tmp_path / "cache"
    cache.mkdir()
    _run("git", "clone", "--quiet", f"file://{origin}", str(cache / "subject"), cwd=tmp_path)

    real_run = subprocess.run

    def _no_network(args, *rest, **kwargs):
        if isinstance(args, (list, tuple)) and len(args) > 1:
            forbidden = {"clone", "fetch", "pull", "remote", "ls-remote"}
            if args[0] == "git" and forbidden.intersection(args):
                raise AssertionError(f"measurement reached the network: {list(args)}")
        return real_run(args, *rest, **kwargs)

    monkeypatch.setattr(subprocess, "run", _no_network)

    head = _run("git", "rev-parse", "HEAD", cwd=origin)
    result = mfb.measure(
        {"name": "subject", "full_name": "org/subject", "commit": head, "declarations": 10},
        cache,
    )

    assert result is not None, "a materialized cache must measure"
    assert result["fix_commits"] >= 5


def test_an_unmaterialized_subject_is_skipped_not_fetched(tmp_path: Path) -> None:
    sys.path.insert(0, str(ROOT / "tools" / "calibration"))
    import measure_fix_breadth as mfb

    cache = tmp_path / "cache"
    cache.mkdir()

    result = mfb.measure(
        {"name": "absent", "full_name": "org/absent", "commit": "0" * 40, "declarations": 1},
        cache,
    )

    assert result is None, "an unmaterialized subject must be skipped, never cloned on demand"


def test_the_checked_in_manifest_is_shaped_as_the_verifier_expects() -> None:
    """The file in the repository is the pin; it has to load and be complete."""
    path = ROOT / "tools" / "calibration" / "history_manifest.json"
    if not path.exists():
        pytest.skip("no manifest materialized in this checkout")

    manifest = json.loads(path.read_text(encoding="utf-8"))

    assert manifest["manifest_version"] == hm.MANIFEST_VERSION
    assert manifest["window_commits"] == hm.WINDOW_COMMITS
    assert manifest["selection_rule"] == hm.SELECTION_RULE
    assert manifest["subjects"], "a manifest with no subjects pins nothing"
    for name, subject in manifest["subjects"].items():
        assert subject["pinned_head"], f"{name} has no pinned head"
        assert subject["window_commits"], f"{name} selected no commits"

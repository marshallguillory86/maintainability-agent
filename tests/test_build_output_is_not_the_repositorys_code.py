"""A build does not change what an audit scores (D175).

A Maven build copied jsoup's test resources into `target/test-classes`, and
the next audit scored 29 more files — one of them a failing file — as the
team's own. The same commit scored one way before `mvn test` and another
after it, which is P1 failing on the working tree rather than on the code.

ADR 010 §1 forbids the obvious fix: `target/` on a list of names is the
`ggml/` mistake again, waiting for the next build tool to pick another word.
The repository already says which paths are not its source: its own
`.gitignore`, for paths git does not track.

The claim: **every file the scanner reads, placed in an untracked path the
repository ignores, leaves the scored population and is counted** — and
nothing else does. The population is every suffix in the shipped
`include_extensions`, so HTML, XML and JSON are covered along with source.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def _config() -> dict[str, Any]:
    from maintainability_audit.config import load_config

    return load_config(None)


def _failing_file(path: Path, config: dict[str, Any]) -> None:
    """A file the scanner reads and grades as failing, whatever its suffix."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = int(config["thresholds"]["max_file_lines"]) + 5
    path.write_text("".join(f"line {number}\n" for number in range(lines)), encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("def run():\n    return 1\n", encoding="utf-8")
    (repo / ".gitignore").write_text("out/\n", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "add", ".")
    return repo


def _scored(report: dict[str, Any]) -> dict[str, Any]:
    summary = report["summary"]
    return {
        "files_scanned": summary["files_scanned"],
        "file_failures": summary["file_failures"],
        "function_failures": summary["function_failures"],
        "failing_paths": sorted(item["path"] for item in report["largest_files"]
                                if item["status"] == "fail"),
    }


def _suffixes(config: dict[str, Any]) -> list[str]:
    suffixes = sorted(set(config["paths"]["include_extensions"]))
    assert suffixes, "the shipped config reads no suffixes; this sweep would pass vacuously"
    return suffixes


def test_ignored_untracked_build_output_leaves_the_score_and_is_counted(tmp_path) -> None:
    from maintainability_audit.report import build_report

    config = _config()
    repo = _repo(tmp_path)
    before = _scored(build_report(repo, config, run_analyzers=False))

    suffixes = _suffixes(config)
    for index, suffix in enumerate(suffixes):
        _failing_file(repo / "out" / "classes" / f"artifact{index}{suffix}", config)
    after = build_report(repo, config, run_analyzers=False)

    assert _scored(after) == before, (
        "ignored, untracked build output changed the scored population: "
        f"before={before} after={_scored(after)}"
    )
    assert after["summary"]["generated_files"] == len(suffixes), (
        f"{len(suffixes)} build-output files left the score but "
        f"{after['summary']['generated_files']} were counted"
    )
    owners = {entry["path"]: entry["evidence"] for entry in after["summary"]["classifications"]}
    assert "out" in owners and ".gitignore" in owners["out"], owners


def test_a_tracked_file_under_an_ignore_rule_is_still_scored(tmp_path) -> None:
    """Git tracking it is the repository saying it is source, whatever the rule matches.

    Covers existing behaviour: before D175 nothing read the ignore rules, so a
    force-added file was scored then too. It guards the fix against treating
    a pattern match as the verdict.
    """
    from maintainability_audit.report import build_report

    config = _config()
    repo = _repo(tmp_path)
    _failing_file(repo / "out" / "Kept.java", config)
    _git(repo, "add", "-f", "out/Kept.java")
    report = build_report(repo, config, run_analyzers=False)
    assert "out/Kept.java" in _scored(report)["failing_paths"]


def test_an_untracked_file_nothing_ignores_is_still_scored(tmp_path) -> None:
    """Uncommitted work stays visible (D56); only ignored paths leave.

    Covers existing behaviour: untracked files were scored before D175, and
    this pins that the fix keys on the ignore rule, not on being untracked.
    """
    from maintainability_audit.report import build_report

    config = _config()
    repo = _repo(tmp_path)
    _failing_file(repo / "src" / "draft.py", config)
    report = build_report(repo, config, run_analyzers=False)
    assert "src/draft.py" in _scored(report)["failing_paths"]


def test_a_personal_global_ignore_file_does_not_change_the_score(tmp_path, monkeypatch) -> None:
    """Only the repository's own `.gitignore` decides — never one machine's (P1).

    `--exclude-standard` would read the user's `core.excludesFile`, so two
    laptops with different global ignores would score one commit differently.

    Covers existing behaviour: before D175 no ignore file was read, global or
    not; this guards the fix against reading the wrong one.
    """
    from maintainability_audit.report import build_report

    config = _config()
    repo = _repo(tmp_path)
    _failing_file(repo / "src" / "personal.py", config)
    global_ignore = tmp_path / "global-ignore"
    global_ignore.write_text("personal.py\n", encoding="utf-8")
    global_config = tmp_path / "global-gitconfig"
    global_config.write_text(f"[core]\n\texcludesFile = {global_ignore}\n", encoding="utf-8")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(global_config))

    report = build_report(repo, config, run_analyzers=False)
    assert "src/personal.py" in _scored(report)["failing_paths"], (
        "a path ignored only by this machine's global excludes left the score"
    )


def test_a_tree_git_cannot_read_is_scored_as_it_always_was(tmp_path) -> None:
    """No repository, no evidence: nothing leaves.

    Covers existing behaviour: a non-git tree had no ignore evidence before
    D175 either; this guards that a failing git query is not read as a verdict.
    """
    from maintainability_audit.report import build_report

    config = _config()
    tree = tmp_path / "tree"
    (tree / "src").mkdir(parents=True)
    (tree / ".gitignore").write_text("out/\n", encoding="utf-8")
    _failing_file(tree / "out" / "artifact.html", config)
    report = build_report(tree, config, run_analyzers=False)
    assert "out/artifact.html" in _scored(report)["failing_paths"]

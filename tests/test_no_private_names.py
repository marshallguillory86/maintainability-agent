"""No private repository's name appears in this public one.

This repository is public, and its owner's other repositories are not. A
private product's name reached the tree anyway — in the changelog, the defect
register, a document's file name, code comments, test docstrings and the scan
history — because the guard that existed checked only the lines a change
added, against a term list that had never been given the name. Nothing
looked at what was already there.

`tools/check_private_names.py` reads every tracked file and every tracked
path, and on request every commit message in a range, against the names it
is given. The names never live in this tree: they come from the
`FORBIDDEN_TERMS` and `PRIVATE_NAMES` environment variables (CI secrets) and
from `~/.config/private-names`, which is generated from the owner's private
repositories. A match is reported by file and line, never by the text that
matched, and a run with no names fails rather than passing having checked
nothing.
"""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]

# Loaded from this checkout's file, not from whichever `tools/` is on the
# path: the falsifier prover runs with the original checkout's `tools/` on
# it, so an import by name reached the tool its proof had removed.
_SPEC = importlib.util.spec_from_file_location("check_private_names", ROOT / "tools" / "check_private_names.py")
guard = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(guard)

# A made-up name: the real ones must never be written here.
NAME = "Quillfeather"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp_path: Path, files: dict[str, str]) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    for path, text in files.items():
        (root / path).parent.mkdir(parents=True, exist_ok=True)
        (root / path).write_text(text, encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    return root


def test_a_name_anywhere_in_a_tracked_file_is_found_whatever_its_case(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.md": "fine\nsee quillFEATHER's audit\n", "b.py": "x = 1\n"})

    assert guard.scan(root, [NAME]) == [("a.md", 2)]


def test_a_name_in_a_file_name_is_found(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"docs/defects-from-quillfeather.md": "nothing here\n"})

    assert guard.scan(root, [NAME]) == [("docs/defects-from-quillfeather.md", 0)]


def test_a_commit_message_in_the_range_is_found(tmp_path: Path) -> None:
    root = _repo(tmp_path, {"a.md": "fine\n"})
    (root / "a.md").write_text("still fine\n", encoding="utf-8")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "fix the Quillfeather defects")

    hits = guard.scan_messages(root, "HEAD~1..HEAD", [NAME])

    assert len(hits) == 1 and len(hits[0]) == 40


def test_the_report_never_repeats_the_name(tmp_path: Path, capsys, monkeypatch) -> None:
    root = _repo(tmp_path, {"a.md": "Quillfeather\n"})
    monkeypatch.setenv("PRIVATE_NAMES", NAME)
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)

    code = guard.main(["--root", str(root), "--no-default-file"])

    out = capsys.readouterr()
    assert code == 1
    assert "a.md:1" in out.out
    assert NAME.lower() not in (out.out + out.err).lower()


def test_no_names_fails_rather_than_passing(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path, {"a.md": "anything\n"})
    monkeypatch.delenv("PRIVATE_NAMES", raising=False)
    monkeypatch.delenv("FORBIDDEN_TERMS", raising=False)

    assert guard.main(["--root", str(root), "--no-default-file"]) == 2


def test_names_come_from_both_variables_and_the_file_and_comments_are_ignored(tmp_path: Path, monkeypatch) -> None:
    names = tmp_path / "private-names"
    names.write_text("# generated\nalpha-repo\n\n  Beta  \n", encoding="utf-8")
    monkeypatch.setenv("FORBIDDEN_TERMS", "gamma\n")
    monkeypatch.setenv("PRIVATE_NAMES", "delta")

    assert guard.load_names([names]) == ["alpha-repo", "beta", "delta", "gamma"]


def test_a_clean_tree_passes(tmp_path: Path, monkeypatch) -> None:
    root = _repo(tmp_path, {"a.md": "nothing private\n"})
    monkeypatch.setenv("PRIVATE_NAMES", NAME)

    assert guard.main(["--root", str(root), "--no-default-file"]) == 0


def test_this_repository_names_no_private_repository() -> None:
    """The real tree, against the real names, wherever they are available.

    On a machine without `~/.config/private-names` there is nothing to check
    against, which is reported as a skip rather than a pass. In CI the
    required "Commit identity and signatures" job runs the same tool with the
    names from secrets, and there their absence fails the job.
    """
    names = guard.load_names([guard.DEFAULT_FILE])
    if not names:
        pytest.skip(f"no private names on this machine ({guard.DEFAULT_FILE} is absent)")

    assert guard.scan(ROOT, names) == []

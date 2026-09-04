"""Reading what a diff *added*, against real repositories.

`added_lines` is what lets the conformance record say "this change
introduced a suppression" rather than "this file contains one". The
distinction is the whole signal: a `# noqa` that has been in the tree for
three years says nothing about the agent that just touched the file, and
attributing a decade of accumulated directives to one diff would bury the
case that matters.

Built on real `git` repositories rather than fixture strings, because the
one defect this function had was not in its parsing. This module runs git
under a read-only config that neutralises `diff.external`, which costs
nothing for `--name-only` — no diff is produced — and kills a content diff
outright: git tries to execute the empty string and reports
`cannot run : No such file or directory`. Only a real repository and a real
diff surface that, so the fixtures are real.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from maintainability_audit.git_tools import added_lines


def _run(*args: str, cwd: Path) -> None:
    subprocess.run(args, cwd=cwd, check=True, capture_output=True, timeout=120)  # noqa: S603


def _repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    _run("git", "init", "--quiet", "-b", "main", cwd=path)
    _run("git", "config", "user.email", "test@example.invalid", cwd=path)
    _run("git", "config", "user.name", "Test", cwd=path)
    _run("git", "config", "commit.gpgsign", "false", cwd=path)
    return path


def _commit(path: Path, message: str) -> None:
    _run("git", "add", "-A", cwd=path)
    _run("git", "commit", "--quiet", "-m", message, cwd=path)


def test_a_content_diff_runs_at_all(tmp_path: Path) -> None:
    """The defect this function shipped with, reproduced as a test.

    Without `--no-ext-diff` this raises `GitCommandFailed`: the read-only
    config sets `diff.external=` and git tries to run it.
    """
    repo = _repo(tmp_path)
    (repo / "widget.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "widget.py").write_text("def f():\n    return 2\n", encoding="utf-8")
    _commit(repo, "second")

    added = added_lines(repo, "HEAD~1...HEAD")

    assert added, "no added lines were read from a diff that plainly has one"


def test_only_added_lines_are_reported(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "widget.py").write_text("keep me\nremove me\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "widget.py").write_text("keep me\nbrand new\n", encoding="utf-8")
    _commit(repo, "second")

    added = added_lines(repo, "HEAD~1...HEAD")

    texts = [text for _line, text in added["widget.py"]]
    assert texts == ["brand new"], f"expected only the added line, got {texts}"


def test_added_lines_carry_their_line_numbers(tmp_path: Path) -> None:
    """A suppression is reported at a line somebody can open."""
    repo = _repo(tmp_path)
    (repo / "widget.py").write_text("one\ntwo\nthree\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "widget.py").write_text("one\ntwo\nthree\nfour  # noqa\n", encoding="utf-8")
    _commit(repo, "second")

    added = added_lines(repo, "HEAD~1...HEAD")

    assert added["widget.py"] == [(4, "four  # noqa")]


def test_several_files_are_kept_apart(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "a.py").write_text("a\n", encoding="utf-8")
    (repo / "b.py").write_text("b\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "a.py").write_text("a\nadded to a\n", encoding="utf-8")
    (repo / "b.py").write_text("b\nadded to b\n", encoding="utf-8")
    _commit(repo, "second")

    added = added_lines(repo, "HEAD~1...HEAD")

    assert [t for _n, t in added["a.py"]] == ["added to a"]
    assert [t for _n, t in added["b.py"]] == ["added to b"]


def test_a_diff_that_adds_nothing_reports_nothing(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "widget.py").write_text("one\ntwo\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "widget.py").write_text("one\n", encoding="utf-8")
    _commit(repo, "deletion only")

    assert added_lines(repo, "HEAD~1...HEAD") == {}


def test_a_new_file_reports_every_line_as_added(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    (repo / "existing.py").write_text("x\n", encoding="utf-8")
    _commit(repo, "first")
    (repo / "fresh.py").write_text("line one\nline two\n", encoding="utf-8")
    _commit(repo, "second")

    added = added_lines(repo, "HEAD~1...HEAD")

    assert added["fresh.py"] == [(1, "line one"), (2, "line two")]

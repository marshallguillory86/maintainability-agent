"""D71/D81: reading a repository must not let git rewrite it.

Every git command this package runs is a read. Git runs housekeeping of
its own after many of them, and housekeeping repacks objects and writes
commit-graphs *inside* `.git`, so a read-only audit was still writing to
the tree it audited.

Two witnesses, because the first one alone stopped being independent.
`test_git_argv` sweeps the source for argv construction; the snapshot
tests in `test_mcp_server` watch a tree before and after an audit. But
the conftest guard exports `GIT_CONFIG_*` for the whole suite -- so that
a *fixture's* own `git commit` cannot schedule detached maintenance --
and that guard covers the product too. Delete the settings from
`run_git` and all 36 snapshot tests still pass.

So the witness here watches the product: it records the argv of every
git a real audit spawns. Deterministic where the snapshot is
probabilistic, and indifferent to what the environment says.
"""

from __future__ import annotations

import contextlib
import os
import subprocess
from pathlib import Path

import pytest

from maintainability_audit.git_tools import READ_ONLY_GIT_CONFIG


def _audit_a_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> list[list[str]]:
    """Audit a one-commit repository; return every git argv it spawned.

    Shared by the two witnesses below, which otherwise duplicated this
    setup verbatim and tripped the project's own duplication gate.

    The original `subprocess.run` is captured before patching, because
    `git_tools.subprocess` is this same module object and patching its
    `run` would replace the function the wrapper calls through to. The
    recorder is installed *after* the fixture's own init/add/commit,
    which are this file's setup rather than the product's behaviour.
    """
    import subprocess as real_subprocess

    from maintainability_audit import _backfill, git_tools
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = tmp_path / "repo"
    root.mkdir()
    (root / "m.py").write_text("def f():\n    return 1\n", encoding="utf-8")
    real_subprocess.run(["git", "init", "-q", str(root)], check=True)
    real_subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    real_subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one"], check=True)

    spawned: list[list[str]] = []
    original_run = real_subprocess.run

    def recording_run(argv, *args, **kwargs):  # type: ignore[no-untyped-def]
        if isinstance(argv, (list, tuple)) and argv and argv[0] == "git":
            spawned.append(list(argv))
        return original_run(argv, *args, **kwargs)  # noqa: S603

    monkeypatch.setattr(git_tools.subprocess, "run", recording_run)
    monkeypatch.setattr(_backfill.subprocess, "run", recording_run)
    build_report(root, load_config(None))
    return spawned


def test_the_suites_own_git_has_maintenance_disabled(tmp_path: Path) -> None:
    """The conftest guard reaches git, rather than merely being set.

    `GIT_CONFIG_COUNT`/`KEY`/`VALUE` are honoured by git 2.31+. Asserting
    the environment variables exist would prove only that conftest ran;
    this asks git what it actually resolved, which is the thing the
    fixture repositories depend on.
    """

    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    for key, expected in (("gc.auto", "0"), ("maintenance.auto", "false")):
        seen = subprocess.run(
            ["git", "-C", str(tmp_path), "config", "--get", key],
            capture_output=True, text=True, check=False,
        ).stdout.strip()
        assert seen == expected, (
            f"git resolved {key}={seen!r}, not {expected!r}: a fixture's own "
            "commit can still schedule detached maintenance and write "
            ".git/objects/maintenance.lock into a tree a test is watching"
        )


def test_a_real_audit_spawns_no_git_without_the_read_only_settings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The witness that does not share fate with the environment.

    D71's snapshot tests -- "the MCP tool wrote the tree" -- watch a
    temporary repository before and after an audit. Since the conftest
    guard exports `GIT_CONFIG_*` for the whole suite, git would not run
    maintenance in those tests even if the product stopped asking it not
    to. An audit put it plainly: delete `READ_ONLY_GIT_CONFIG` from
    `run_git` tomorrow and every one of those tests still passes.

    So this one watches the *product*: it records the argv of every git
    the audit actually spawns and asserts each carries the settings. It
    is deterministic where the snapshot is probabilistic -- auto
    maintenance fires on accumulated loose objects, which is why D71
    took two CI runs to appear -- and it does not care what the
    environment says, which is the property the snapshot lost.
    """
    spawned = _audit_a_repository(tmp_path, monkeypatch)


    assert spawned, "the audit spawned no git at all; this witness saw nothing"
    naked = [
        argv for argv in spawned
        if not all(part in argv for part in READ_ONLY_GIT_CONFIG)
    ]
    assert not naked, (
        "the audit spawned git without the read-only settings, so git may "
        f"repack objects into the repository it was only reading: {naked}"
    )


#: Git subcommands this package is allowed to run. All of them read.
READ_ONLY_SUBCOMMANDS = frozenset({
    "log", "rev-list", "rev-parse", "status", "diff", "show",
    "cat-file", "ls-files", "ls-tree", "for-each-ref", "worktree",
    # `branch` reads as this package invokes it (`--show-current`) and
    # writes with `-d`/`-D`/`-m`/`-M`, so the subcommand alone is too
    # coarse and the flags are checked as well.
    "branch",
})

#: Flags that turn a listed subcommand into a write.
WRITING_FLAGS = frozenset({
    "-d", "-D", "-m", "-M", "--delete", "--move", "--force", "-f",
    "--set-upstream-to", "--edit-description", "--prune", "--add",
})


def test_the_product_runs_only_git_commands_that_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D88: why the argv recorder is the *only* witness available here.

    The objection was fair: the recorder above watches the argv, the
    promise is about the tree, and the 36 snapshot tests still share an
    environment with the fixtures -- so they would not notice if
    `READ_ONLY_GIT_CONFIG` vanished.

    Two attempts at a tree witness failed, and the second failure is the
    answer. Removing the suite's guard was not enough: maintenance is
    threshold-driven and merely *allowed* to fire. Making the
    environment hostile with `gc.auto=1` was not enough either, and that
    one passed with the settings deleted -- which would have shipped a
    test that passes either way into the entry that exists to stop them.

    The reason is that git runs housekeeping after commands that
    **write** -- `commit`, `merge`, `fetch` -- and this package runs
    none of them. The `maintenance.lock` that opened D71 was scheduled
    by a *fixture's* `git commit`, which is what D71's second half
    already concluded. No audit of an unmodified repository can produce
    the write a snapshot would catch, so a passing snapshot proves
    nothing in either direction.

    What is checkable is the premise. It found one the list had missed
    -- `git branch --show-current` -- on its first run. If a writing
    subcommand is ever added the reasoning above stops holding and this
    fails; the argv guarantee does not depend on the premise and stands
    on its own.
    """
    spawned = _audit_a_repository(tmp_path, monkeypatch)
    assert spawned, "the audit spawned no git; this check saw nothing"

    writing = []
    for argv in spawned:
        subcommand = next(
            (part for part in argv[1:]
             if not part.startswith("-") and part != "-C"
             and "=" not in part and not part.startswith("/")),
            None,
        )
        if subcommand is not None and subcommand not in READ_ONLY_SUBCOMMANDS or WRITING_FLAGS.intersection(argv):
            writing.append(argv)
    assert not writing, (
        "the audit ran a git subcommand outside the read-only set, so git "
        "may schedule housekeeping after it and the reasoning in this "
        f"docstring no longer holds: {writing}"
    )


#: Repository config keys git will execute, each with a payload shape and
#: the command that reaches it. A key added to `READ_ONLY_GIT_CONFIG`
#: without a row here is a claim nobody checked.
EXECUTING_KEYS = [
    ("core.fsmonitor", "fsmonitor", ["status", "--short"]),
    ("core.alternateRefsCommand", "plain", ["rev-list", "--count", "HEAD"]),
    ("diff.external", "plain", ["diff"]),
]


def _repo_that_runs_a_script(root: Path, key: str, shape: str) -> Path:
    """A repository whose own config points `key` at a script."""
    import subprocess as real_subprocess

    root.mkdir()
    marker = root / "EXECUTED"
    script = root / "payload.sh"
    body = f'#!/bin/sh\ntouch "{marker}"\n'
    if shape == "fsmonitor":
        body += 'printf "/\\0"\n'
    script.write_text(body, encoding="utf-8")
    script.chmod(0o755)
    (root / "a.txt").write_text("x\n", encoding="utf-8")
    real_subprocess.run(["git", "init", "-q", str(root)], check=True)
    real_subprocess.run(["git", "-C", str(root), "add", "a.txt"], check=True)
    real_subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "one"], check=True)
    real_subprocess.run(
        ["git", "-C", str(root), "config", key, str(script)], check=True)
    return marker


@pytest.mark.parametrize(
    ("key", "shape", "argv"), EXECUTING_KEYS,
    ids=[key for key, _shape, _argv in EXECUTING_KEYS],
)
def test_the_audited_repository_cannot_choose_what_this_process_runs(
    key: str, shape: str, argv: list[str], tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D92: Decision 9 covers git, which it did not.

    "This agent never executes the audited repository's code, and its
    configuration is code." The analyzer adapters were held to that --
    eslint refused outright, pylint and mypy pointed at `/dev/null`.
    **Git was not.** `core.fsmonitor` names a command git runs, and
    `worktree_status` runs `git status` on every git-backed audit, so a
    repository could execute arbitrary code in this process simply by
    being audited. The demonstration also wrote a file into the
    worktree, which the MCP door promises never happens.

    `READ_ONLY_GIT_CONFIG` disabled housekeeping (D71) and said nothing
    about hooks. Every key here is checked, not only the one an audit
    demonstrated, because the previous rule scoped to the commands of
    the day missed the spawn that lived elsewhere (D73).
    """
    from maintainability_audit.git_tools import run_git

    # The system and global tiers are scrubbed so only the repository's
    # own config can be responsible for anything that happens.
    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)

    root = tmp_path / "hostile"
    marker = _repo_that_runs_a_script(root, key, shape)
    # A failing git is fine here: what is on trial is whether the
    # repository's config ran, not whether the command succeeded.
    with contextlib.suppress(Exception):
        run_git(argv, root)

    assert not marker.exists(), (
        f"the audited repository's {key} ran a script in this process; "
        "Decision 9 says configuration is code and this agent does not "
        "run the audited tree's"
    )


def test_worktree_status_on_a_hostile_repository_changes_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The reproduction as reported, through the function that runs it.

    `worktree_status` is on the default path of every git-backed audit,
    which is what made `core.fsmonitor` reachable without anyone opting
    in to anything.
    """
    from maintainability_audit.git_tools import worktree_status

    monkeypatch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)

    root = tmp_path / "hostile"
    marker = _repo_that_runs_a_script(root, "core.fsmonitor", "fsmonitor")
    before = {path.name for path in root.rglob("*")}

    worktree_status(root)

    assert not marker.exists(), "the repository's config executed on an audit"
    assert {path.name for path in root.rglob("*")} == before, (
        "auditing the repository added a file to its worktree"
    )

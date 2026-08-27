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

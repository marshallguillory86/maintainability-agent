"""Installing the pre-commit hook, and the two cases where it refuses.

A hook a user has to hand-write is a feature that ships half-finished:
the shell line is easy to get wrong in ways that fail open, and a hook
that fails open is worse than no hook because it reports safety it is
not providing. So this writes it.

Entry layer, beside `_skill_install`, and for the same reason: it
performs a setup action against the user's machine and exits. Nothing
below entry writes outside the report artifacts.

Two refusals, both about not destroying somebody else's work:

**A hook that is not ours is never overwritten.** Repositories carry
real pre-commit hooks — formatters, secret scanners, `pre-commit`
framework shims — and replacing one silently would remove a control the
team is relying on. The refusal prints the one line to add to the
existing hook instead, which is the answer they actually need.

**A hook that *is* ours is replaced without ceremony.** That is an
upgrade, not a clobber, and demanding `--force` for it would train
people to pass `--force` — at which point the first refusal stops
working too.

`core.hooksPath` is asked of git rather than assumed. A repository that
redirects its hooks (the `pre-commit` framework does, and so does any
shared-hooks setup) would otherwise get a file written into `.git/hooks`
that git never runs: an install that reports success and does nothing,
which is the exact failure this project files defects for.
"""
from __future__ import annotations

import contextlib
import os
import stat
import sys
from pathlib import Path

from .git_tools import GitCommandFailed, run_git

#: Written into the hook and looked for on the way back in. This is how
#: "ours, upgrade it" is told from "somebody else's, refuse" — content,
#: not a sidecar file that can drift away from the thing it describes.
MARKER = "# installed by maintainability-agent --install-precommit-hook"

HOOK_TEMPLATE = """#!/bin/sh
{marker}
# Scans what the index will commit against this repository's thresholds.
# No score is produced: a diff has no population to draw a rate from.
# Remove this file to uninstall, or commit with --no-verify to skip once.
exec {python} -m maintainability_audit --staged --root "$(git rev-parse --show-toplevel)"
"""


#: Config scopes, most specific first. Deliberately scope-restricted
#: reads: this project runs every git command under
#: `core.hooksPath=/dev/null` so an audit can never execute the audited
#: tree's hooks (D92), and that override lives in the command-line scope.
#: `rev-parse --git-path hooks` would therefore answer `/dev/null` —
#: the safety control is right, and the question has to be asked in a
#: way that does not read it back as the user's setting.
_HOOKS_PATH_SCOPES = ("--local", "--global", "--system")


def _configured_hooks_path(root: Path) -> str:
    """`core.hooksPath` as the user's config files state it, or ''.

    `--default ''` is what keeps this from raising: `git config --get`
    exits 1 when a key is unset, and `run_git` is strict by design.
    """
    for scope in _HOOKS_PATH_SCOPES:
        try:
            value = run_git(
                ["config", scope, "--default", "", "--get", "core.hooksPath"], root
            ).strip()
        except GitCommandFailed:
            # A scope with no readable file is not an error, it is an
            # absent setting. The local scope always exists in a
            # repository, so a real failure surfaces from `git_dir`.
            continue
        if value:
            return value
    return ""


def hooks_directory(root: Path) -> Path:
    """Where git will actually look for hooks in this repository.

    Two questions, not one. `core.hooksPath` redirects hooks (the
    `pre-commit` framework sets it, and so does any shared-hooks setup),
    and `--git-common-dir` is what makes this correct in a linked
    worktree and where `.git` is a file rather than a directory.
    Guessing `.git/hooks` is right most of the time, and an install that
    is right most of the time is one that silently does nothing for
    everybody else.

    A relative `core.hooksPath` resolves against the working tree's top
    level, which is what git itself does.
    """
    configured = _configured_hooks_path(root)
    if configured:
        expanded = Path(configured).expanduser()
        return expanded if expanded.is_absolute() else (root / expanded)
    common = run_git(["rev-parse", "--git-common-dir"], root).strip()
    if not common:
        raise GitCommandFailed("git did not say where its directory is")
    base = Path(common)
    return (base if base.is_absolute() else root / base) / "hooks"


#: The hooks directory, bound the way `_skill_install` binds the skill
#: root (D18): `O_NOFOLLOW` so a symlinked directory fails here instead
#: of resolving somewhere else, and the descriptor that comes back is
#: what every later operation uses. Validating a pathname and then
#: writing to it is the time-of-check/time-of-use hole an audit already
#: reproduced once in this project.
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW

HOOK_NAME = "pre-commit"
_STAGING_NAME = "pre-commit.maintainability-agent.tmp"


def _existing_owner(fd: int) -> str | None:
    """Who wrote the hook already there: 'ours', 'theirs', or None.

    Read through the bound descriptor, so the file inspected is the file
    in the directory that was opened — not whatever the name resolves to
    a moment later. A hook that cannot be read is treated as somebody
    else's, because the one thing worse than refusing an install is
    destroying a control a team relies on.
    """
    try:
        handle = os.open(HOOK_NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    except FileNotFoundError:
        return None
    except OSError:
        # ELOOP (a symlink, refused by O_NOFOLLOW), EISDIR, EACCES: all
        # mean something is there that this tool did not put there.
        return "theirs"
    try:
        with os.fdopen(handle, "r", encoding="utf-8", errors="replace") as stream:
            return "ours" if MARKER in stream.read() else "theirs"
    except OSError:
        return "theirs"


def _write_hook(fd: int, body: str) -> None:
    """Stage the hook beside its name, then replace through the descriptor.

    Staged and renamed rather than written in place, so a hook is never
    half-written: an interrupted install would otherwise leave a
    truncated shell script that git still executes.

    Both ends of the rename are bound to `fd`. A path-based `os.replace`
    is the unbounded write `test_no_module_stages_a_raw_write_outside_
    the_sanctioned_writers` exists to catch, and it is right to: the
    target sits inside `.git`, where a redirected write is worth the
    most to an attacker.
    """
    handle = os.open(
        _STAGING_NAME,
        os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW,
        0o700, dir_fd=fd,
    )
    try:
        with os.fdopen(handle, "w", encoding="utf-8", closefd=False) as stream:
            stream.write(body)
        # Owner only. Git runs a hook as the person committing, so group
        # and world bits buy nothing and hand a shared checkout an
        # executable file more people can read than need to. Set on the
        # handle rather than the path, because a path-based chmod
        # between the write and the rename is the TOCTOU hole this
        # project already closed once in `_safe_write`.
        os.fchmod(handle, stat.S_IRWXU)
        os.fsync(handle)
    except BaseException:
        os.close(handle)
        with contextlib.suppress(OSError):
            os.unlink(_STAGING_NAME, dir_fd=fd)
        raise
    os.close(handle)
    try:
        os.replace(_STAGING_NAME, HOOK_NAME, src_dir_fd=fd, dst_dir_fd=fd)
    except BaseException:
        with contextlib.suppress(OSError):
            os.unlink(_STAGING_NAME, dir_fd=fd)
        raise


def install_precommit_hook(root: Path) -> tuple[int, str]:
    """Write the hook, or explain what stopped it. Returns (exit code, message)."""
    try:
        hooks = hooks_directory(root)
    except GitCommandFailed as failure:
        return 2, f"maintainability-agent: not a git repository, or git could not answer ({failure})"

    hooks.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(hooks, _DIR_FLAGS)
    except OSError as unbindable:
        # Not a fallback to a path-based write. Something raced the
        # mkdir or the directory is a symlink, and writing on with
        # `dir_fd=None` would resolve every name against the process
        # working directory — the stray file an audit reproduced (D18).
        return 2, (
            f"maintainability-agent: {hooks} could not be opened as a real "
            f"directory ({unbindable}). Nothing was written."
        )
    try:
        owner = _existing_owner(fd)
        if owner == "theirs":
            return 1, (
                f"{hooks / HOOK_NAME} already exists and was not written by this tool.\n"
                "Refusing to replace a hook somebody else installed. To run both, "
                "add this line to it:\n\n"
                f'  {sys.executable} -m maintainability_audit --staged '
                '--root "$(git rev-parse --show-toplevel)" || exit 1\n'
            )
        _write_hook(fd, HOOK_TEMPLATE.format(marker=MARKER, python=sys.executable))
    finally:
        os.close(fd)

    verb = "updated" if owner == "ours" else "installed"
    return 0, (
        f"{verb} {hooks / HOOK_NAME}\n"
        "Staged content is now scanned before every commit. It reports "
        "threshold breaches only and never a score, runs no tests, and "
        "writes nothing. Skip it once with `git commit --no-verify`."
    )

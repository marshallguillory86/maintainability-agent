"""Git invocation, with failure kept distinguishable from emptiness.

Every call here spawns `git` as an argv list. There is no shell anywhere
in this module and no string is ever interpolated into one.

**Failure is not data (D37).** `run_git` used to answer every error with
`""`, so a `git log` that failed for any reason — a timeout, a corrupt
object, git missing mid-run — arrived at the caller as "no commits" and
was reported as `files_changed: 0`. `history.has_history` exists
precisely to keep "no history available" apart from "no changes", and
the spawner underneath it was collapsing exactly that distinction. So
the default raises, and the two places where a non-zero exit is the
answer rather than a fault use `probe_git`, which says so at the call
site.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

# Long enough for a slow `git log` over a large history, short enough
# that a wedged child cannot hang the host that called the audit.
GIT_TIMEOUT_SECONDS = 120

# One inert revision or range. The first character must be
# alphanumeric, which is what makes a leading dash impossible: `git`
# reads `--output=<path>` as an option and creates that file, which is
# option injection even though no shell is involved. Lifted verbatim
# from the MCP door, which had it right, rather than written again —
# a second pattern is a second thing to get subtly wrong, and the
# first draft of this one admitted `-rf` by putting `-` in the class.
_REVSPEC = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@^~:+-]*(?:\.{2,3}[A-Za-z0-9._/@^~:+-]+)?")
MAX_REVSPEC = 200

# Git reads these from the environment and they outrank both `cwd` and
# `-C`, so an inherited value silently redirects every command in this
# module at another repository.
_OVERRIDING_GIT_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_CEILING_DIRECTORIES",
    "GIT_NAMESPACE",
)


class GitCommandFailed(RuntimeError):
    """A git invocation this code expected to succeed did not."""


class InvalidRevspec(ValueError):
    """A revision expression this module refuses to hand to git."""


def git_env() -> dict[str, str]:
    """The parent environment with git's location overrides removed."""
    env = {k: v for k, v in os.environ.items() if k not in _OVERRIDING_GIT_VARS}
    return env


def validate_revspec(revspec: str) -> str:
    """One inert revision expression, never a command-line option.

    Validation rather than `--end-of-options`, which needs git 2.24 and
    would make the guarantee depend on the host's git version.
    """
    if (not isinstance(revspec, str) or len(revspec) > MAX_REVSPEC
            or not _REVSPEC.fullmatch(revspec)):
        raise InvalidRevspec(
            "a revision must be one git expression without whitespace or "
            f"leading dashes, not {revspec!r}"
        )
    return revspec


def run_git(args: list[str], cwd: Path) -> str:
    """Run git and return its stdout. Raises if it does not succeed.

    The strict default is the point: see the module docstring.
    """
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, never a shell
            ["git", *args],
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=GIT_TIMEOUT_SECONDS,
            env=git_env(),
            check=False,
        )
    except subprocess.TimeoutExpired as expired:
        raise GitCommandFailed(
            f"git {args[0] if args else ''} timed out after "
            f"{GIT_TIMEOUT_SECONDS}s"
        ) from expired
    except OSError as unavailable:
        raise GitCommandFailed(f"git could not be run: {unavailable}") from unavailable

    if completed.returncode != 0:
        raise GitCommandFailed(
            f"git {args[0] if args else ''} exited {completed.returncode}"
        )
    return completed.stdout.strip()


def probe_git(args: list[str], cwd: Path) -> str:
    """Run git where a non-zero exit is an answer, not a fault.

    Only for questions whose negative case *is* a failing git command —
    "is this a repository at all". Everywhere else a failure that reads
    as an empty answer is the D37 defect.
    """
    try:
        return run_git(args, cwd)
    except GitCommandFailed:
        return ""


def changed_paths(root: Path, revspec: str) -> set[str]:
    """Paths touched by `revspec`, as forward-slash relative strings.

    `--` terminates the revision list so nothing after it can be read as
    a path or an option, and the revspec is validated before it is
    handed over at all.
    """
    output = run_git(["diff", "--name-only", validate_revspec(revspec), "--"], root)
    if not output:
        return set()
    return {line.strip().replace(os.sep, "/") for line in output.splitlines() if line.strip()}

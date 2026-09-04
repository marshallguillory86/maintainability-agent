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


#: Config that stops git writing to, or **running code from**, the
#: repository we only meant to read.
#:
#: Two rules, learned in that order.
#:
#: *Do not write.* Git runs housekeeping of its own after many commands,
#: and housekeeping repacks objects and writes commit-graphs inside
#: `.git`. A macOS CI run caught it as `.git/objects/maintenance.lock`
#: appearing in a tree the MCP tool promises never to write (D71).
#:
#: *Do not execute.* Decision 9 says this agent never runs the audited
#: repository's code and that configuration counts as code. The analyzer
#: adapters were held to that; **git was not**. A repository whose
#: `.git/config` sets `core.fsmonitor` gets arbitrary code execution in
#: this process on `git status`, which `worktree_status` runs on every
#: git-backed audit — and the demonstration wrote a file into the
#: worktree, which the MCP door separately promises never happens (D92).
#:
#: The list is wider than the one vector that was demonstrated. Every
#: key here is one git will execute, whether or not today's command set
#: reaches it, because the command set grows and the last rule scoped to
#: today's commands (D73) missed the one spawn that lived elsewhere.
#:
#: Content filters (`filter.<driver>.clean`/`.smudge`) and
#: `diff.<driver>.textconv` execute too, and are keyed by a driver name
#: the tree chooses in its `.gitattributes`, so no fixed `-c` can name
#: them away. D92 disclosed them as residual on the belief that this
#: package only diffs two commits by name and status. That was false:
#: `worktree_status` runs `git status --short`, which runs a `clean`
#: filter whenever it must re-hash a file (a racy-clean mtime, a fresh
#: checkout), and that is host code execution on any tree that merely
#: exists as a git repository. Demonstrated, not theorised.
#:
#: The fix is not another named key but `attr.tree` (below), which cuts
#: off the selection those drivers depend on: git reads gitattributes
#: from the given tree instead of the worktree, and an empty tree has
#: none, so no driver is ever chosen and neither filter nor textconv
#: nor external diff runs, whatever `.gitattributes` says.
READ_ONLY_GIT_CONFIG = (
    # Housekeeping: do not write (D71).
    "-c", "gc.auto=0",
    "-c", "maintenance.auto=false",
    # Execution: do not run the tree's code (D92).
    "-c", "core.fsmonitor=false",
    "-c", "core.hooksPath=/dev/null",
    "-c", "core.pager=cat",
    "-c", "core.sshCommand=false",
    "-c", "core.alternateRefsCommand=",
    "-c", "diff.external=",
    "-c", "credential.helper=",
    "-c", "protocol.ext.allow=never",
)

#: The empty tree, per object format. `attr.tree` needs an actual tree
#: object of the repository's own format: pointing it at a missing ref
#: silently falls back to the worktree's `.gitattributes` (unsafe), and a
#: hash of the wrong format is ignored the same way. Both are the
#: well-known constants git ships; there is nothing to look up.
_EMPTY_TREE = {
    "sha1": "4b825dc642cb6eb9a060e54bf8d69288fbee4904",
    "sha256": "6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321",
}

#: One `git rev-parse` per repository, remembered. Detecting the object
#: format reads no worktree content and consults no gitattributes, so it
#: is safe to run before the `attr.tree` guard is in place.
_OBJECT_FORMAT_CACHE: dict[str, str] = {}


def _attr_tree_config(cwd: Path) -> tuple[str, ...]:
    """`-c attr.tree=<empty tree>` for this repository's object format.

    Returns nothing when the format cannot be determined -- that path is
    not a repository, so there is no `.gitattributes` for a driver to
    hide in, and the git command that follows will fail on its own terms
    rather than silently running unprotected.
    """
    key = str(cwd)
    fmt = _OBJECT_FORMAT_CACHE.get(key)
    if fmt is None:
        try:
            completed = subprocess.run(  # noqa: S603 - argv list, never a shell
                ["git", *READ_ONLY_GIT_CONFIG, "rev-parse", "--show-object-format"],
                cwd=cwd, text=True, capture_output=True,
                timeout=GIT_TIMEOUT_SECONDS, env=git_env(), check=False,
            )
        except (OSError, subprocess.SubprocessError):
            return ()
        fmt = completed.stdout.strip() if completed.returncode == 0 else ""
        _OBJECT_FORMAT_CACHE[key] = fmt
    empty = _EMPTY_TREE.get(fmt)
    return ("-c", f"attr.tree={empty}") if empty else ()


def run_git(args: list[str], cwd: Path) -> str:
    """Run git and return its stdout. Raises if it does not succeed.

    The strict default is the point: see the module docstring.
    """
    try:
        completed = subprocess.run(  # noqa: S603 - argv list, never a shell
            ["git", *READ_ONLY_GIT_CONFIG, *_attr_tree_config(cwd), *args],
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


def added_lines(root: Path, revspec: str) -> dict[str, list[tuple[int, str]]]:
    """Lines a revspec *adds*, per path, as (line number, text).

    Added lines only. A suppression that was already in the tree is not
    evidence about this change, and reading whole files instead of the diff
    would report a decade of accumulated `# noqa` as though this agent had
    just written them.

    `--unified=0` keeps context lines out, so every `+` is genuinely new.
    The revspec is validated and `--` terminates the revision list, as in
    `changed_paths`: nothing after it can be read as a path or an option.
    """
    # `--no-ext-diff` is load-bearing, not defensive. The read-only config
    # this module runs under neutralises `diff.external`, which costs
    # nothing for `--name-only` because no diff is produced — and kills a
    # content diff outright, because git then tries to execute the empty
    # string: "cannot run : No such file or directory".
    output = run_git(
        ["diff", "--no-ext-diff", "--unified=0", validate_revspec(revspec), "--"], root
    )
    added: dict[str, list[tuple[int, str]]] = {}
    path = ""
    line_number = 0
    for line in output.splitlines():
        if line.startswith("+++ b/"):
            path = line[6:].strip().replace(os.sep, "/")
        elif line.startswith("@@"):
            # @@ -old,count +new,count @@
            marker = line.split("+", 1)[1].split("@@", 1)[0].strip()
            start = marker.split(",", 1)[0]
            line_number = int(start) if start.lstrip("-").isdigit() else 0
        elif line.startswith("+") and not line.startswith("+++"):
            if path:
                added.setdefault(path, []).append((line_number, line[1:]))
            line_number += 1
    return added


def worktree_status(root: Path) -> str | None:
    """Porcelain status, or `None` when git cannot answer.

    `None` is not "clean". A gate that requires a clean worktree was
    reading a failed `git status` as an empty status and passing, so a
    plain directory satisfied `require_clean_worktree` — the negative
    answer there is "this is not a worktree", which is not the same
    claim and must not be allowed to stand in for it (D37).
    """
    try:
        return run_git(["status", "--short"], root)
    except GitCommandFailed:
        return None

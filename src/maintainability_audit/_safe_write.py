"""Writes into a repository that cannot be redirected by the repository.

Every file this agent writes into an audited tree goes through here.
The tree is untrusted input: a pull request can leave a symlink or a
hardlink where the agent expects a plain file, and the naive sequence —
check the path, then open the name — writes wherever the name points by
the time it is opened.

D18 paid for this once, for the packaged skill, and the lesson did not
travel. An audit on 2026-08-23 reproduced all three of the writes an
ordinary audit performs (D34):

* a dangling ``maintainability-agent.json`` symlink took first-run
  configuration outside the repository, because ``is_file()`` is false
  on a dangling link so setup believed nothing was there;
* ``.maintainability/history.jsonl`` hardlinked to an outside file was
  accepted by ``repository_path`` — which bounds the *name* and never
  the inode — and appended to;
* ``write_baseline`` with ``baseline_path="README.md"`` truncated
  source, in a tool whose stated contract is that it never writes
  source.

Two properties do the work, and both are needed. ``O_NOFOLLOW`` refuses
a symlink at the final component. Staging into a fresh file and
renaming means the destination inode is never opened for writing at
all, which is the only thing that defeats a hardlink — ``O_NOFOLLOW``
does not, because a hardlink is not a link in the sense it checks.
"""

from __future__ import annotations

import os
from pathlib import Path

from .config import PathNotAllowed, repository_path

_STAGING_FLAGS = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW


def bounded_target(root: Path, configured: str | None, default: str) -> Path:
    """The path a write may use, refused if it leaves the repository.

    Thin wrapper over `repository_path` so callers of this module never
    reach for the unbounded form by habit.
    """
    return repository_path(root, configured, default)


def write_bounded(root: Path, target: Path, body: str, *, append: bool = False) -> Path:
    """Write ``body`` to ``target``, refusing anything the tree redirects.

    ``append`` re-reads the existing contents and rewrites the whole
    file rather than opening it for appending. That costs a read of a
    scan history — a file of some kilobytes — and buys the guarantee
    that no existing inode is ever opened for writing, which is what an
    append cannot promise when the name might be a hardlink.
    """
    # Checked before resolution, and that ordering is the whole point.
    # `repository_path` resolves first, so asking the *resolved* path
    # whether it is a symlink always answers no — it is the target. The
    # question is whether the name the agent was told to write is a
    # link, whatever it points at (D34).
    if target.is_symlink():
        raise PathNotAllowed(
            f"{target} is a symlink. A link where a plain file is "
            "expected is how an audited tree redirects a write, and "
            "where it points does not make it safe."
        )
    resolved = repository_path(root, str(target), str(target))
    if resolved.exists() and not resolved.is_file():
        raise PathNotAllowed(
            f"{resolved} is not a regular file this agent may write."
        )
    _refuse_symlinked_parents(root, resolved)
    resolved.parent.mkdir(parents=True, exist_ok=True)

    existing = ""
    if append and resolved.is_file():
        existing = resolved.read_text(encoding="utf-8")
    return _stage_and_replace(resolved, existing + body)


def _refuse_symlinked_parents(root: Path, target: Path) -> None:
    """No directory between the root and the file may be a symlink.

    `repository_path` resolves before comparing, so a symlinked parent
    pointing back inside the root passes it — and then the write lands
    somewhere the operator never granted. Checked component by
    component, because the resolved path alone cannot show which link
    was followed to reach it.
    """
    root = Path(root).resolve()
    current = target.parent
    while current != root and root in current.parents or current == root:
        if current == root:
            return
        if current.is_symlink():
            raise PathNotAllowed(
                f"{current} is a symlinked directory on the way to "
                f"{target}; the audited tree cannot redirect where this "
                "agent writes."
            )
        current = current.parent


def _stage_and_replace(target: Path, body: str) -> Path:
    """A fresh file, then an atomic rename over the name.

    The destination inode is never opened, so a hardlink to something
    outside the repository keeps its contents and merely stops being
    this name — which is exactly what D18 established and D34 found
    missing here.
    """
    staging = target.parent / f".{target.name}.incoming"
    encoded = body.encode("utf-8")
    handle = os.open(staging, _STAGING_FLAGS, 0o644)
    try:
        written = 0
        while written < len(encoded):
            # A short write reported as success leaves a truncated
            # config or a corrupt history and says nothing (D18).
            sent = os.write(handle, encoded[written:])
            if sent <= 0:
                raise OSError(
                    f"writing {target.name} stopped after {written} of "
                    f"{len(encoded)} bytes; nothing was changed."
                )
            written += sent
        os.fsync(handle)
    finally:
        os.close(handle)

    try:
        os.replace(staging, target)
    except OSError:
        staging.unlink(missing_ok=True)
        raise
    return target

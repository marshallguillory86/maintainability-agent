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

import json
import os
import tempfile
from pathlib import Path

from .config import PathNotAllowed, repository_path


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


def write_artifact(
    grant_root: Path,
    target: Path,
    body: str,
    *,
    append: bool = False,
    json_artifact: bool = False,
) -> Path:
    """A product-artifact write on a path a person chose, still refusing
    what the audited tree could do to it.

    The CLI reaches here for the baseline and the rendered outputs
    (``--output``, ``--sarif-output``, the HTML report, the instruction
    pack). Each names a path a person picked, which may sit *outside* the
    audited tree -- a contract that predates D34 -- so unlike config and
    history this write is not bounded to the grant. What it still refuses
    is the audited tree's redirection:

    * A symlinked route the tree could plant exists only *inside* the
      tree. So when the named path falls within the grant the write goes
      through ``write_bounded`` and inherits the lexical route refusal --
      ``.maintainability -> src`` on both ``/var`` and ``/private/var``
      spellings of the same macOS path (Grok 63ab820 audit; the earlier
      ``write_bounded(target.parent, target)`` bound the check to the
      symlink itself and checked nothing). A path outside the grant is on
      ground the audited tree does not control; only the final component
      and the inode need defending there.
    * ``json_artifact`` refuses to overwrite a file that is not already
      JSON -- ``write_baseline(baseline_path="README.md")`` truncated a
      README once (D34), and a stage-and-replace still unlinks that inode
      from its name, so staging alone does not make the promise that this
      tool never writes source.
    """
    target_abs = Path(os.path.abspath(os.path.expanduser(str(target))))
    if json_artifact and target_abs.is_file():
        _refuse_nonjson_clobber(target_abs)
    grant_real = os.path.realpath(grant_root)
    # Membership is decided on the *real* path so a ``/var`` spelling of
    # the target and a ``/private/var`` spelling of the grant name the
    # same tree (Grok 63ab820 audit); the unresolved ``target_abs`` is
    # still what reaches ``write_bounded``, so its lexical route refusal
    # sees the ``.maintainability -> src`` link the real path erased.
    target_real = os.path.realpath(target_abs)
    within = target_real == grant_real or target_real.startswith(grant_real + os.sep)
    if within:
        return write_bounded(grant_root, target_abs, body, append=append)
    # Outside the grant: the person's own ground, which the audited tree
    # cannot reach a symlink into. Defend the name and the inode only.
    if target_abs.is_symlink():
        raise PathNotAllowed(
            f"{target_abs} is a symlink. A link where a plain file is "
            "expected is how a write is redirected, and where it points "
            "does not make it safe."
        )
    if target_abs.exists() and not target_abs.is_file():
        raise PathNotAllowed(
            f"{target_abs} is not a regular file this agent may write."
        )
    target_abs.parent.mkdir(parents=True, exist_ok=True)
    existing = ""
    if append and target_abs.is_file():
        existing = target_abs.read_text(encoding="utf-8")
    return _stage_and_replace(target_abs, existing + body)


def _refuse_nonjson_clobber(target: Path) -> None:
    """Refuse to truncate a file that is not already JSON.

    A JSON artifact (a baseline, the config) overwrites its own prior
    JSON and never source. Parsing the existing bytes is the honest test
    of "is this one of ours": a baseline parses, ``README.md`` and a
    Python module do not -- so the ``baseline_path="README.md"`` write
    that once truncated a README is refused before the stage begins.
    """
    try:
        raw = target.read_text(encoding="utf-8")
        json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as reason:
        raise PathNotAllowed(
            f"{target} already exists and is not a JSON artifact; this "
            "agent writes its JSON here and will not truncate another file."
        ) from reason


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

    The staging name is unique per call. A fixed `.{name}.incoming` was
    guessable, and the audited tree could plant that exact file: `O_EXCL`
    then raised `FileExistsError` and took the write primitive down with a
    crash the tree chose the timing of (Grok e88b429 audit). `mkstemp`
    creates an exclusive file under a random name in the same directory,
    so nothing the tree pre-places can collide with it, and it still lands
    on the same filesystem for an atomic `os.replace`.
    """
    encoded = body.encode("utf-8")
    handle, staging_name = tempfile.mkstemp(
        dir=target.parent, prefix=f".{target.name}.", suffix=".incoming"
    )
    staging = Path(staging_name)
    try:
        os.fchmod(handle, 0o644)  # mkstemp makes 0600; match the old mode
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
    except BaseException:
        os.close(handle)
        staging.unlink(missing_ok=True)
        raise
    else:
        os.close(handle)

    try:
        os.replace(staging, target)
    except OSError:
        staging.unlink(missing_ok=True)
        raise
    return target

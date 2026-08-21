"""Install the packaged agent skill — the D12 drift fix.

The skill teaching agents how to drive this tool ships inside the
package, and this module copies it into an agent's skills directory.
The defect this closes was found in the field: the repository's skill
went chat-primary (D12) while the installed copy on the operator's
machine kept teaching the dead CLI-first recipe for three days —
nothing syncs installed copies on its own. ``--install-skill`` after
every upgrade is that sync, and the packaged copy is pinned
byte-for-byte to the repository's ``skills/`` tree by test, so the
same drift cannot reopen internally.

**Every path is bound by descriptor, never by name (D18).** The skill
root is opened once with ``O_NOFOLLOW|O_DIRECTORY`` and every read,
write and unlink happens relative to that descriptor. Validating a
pathname and then writing to it is a time-of-check/time-of-use hole:
an audit swapped the validated directory for a symlink between the
two, and a plain reinstall wrote through it to a file outside the
skills tree. A descriptor keeps pointing at the inode that was
checked, whatever the name is made to mean afterwards.
"""

from __future__ import annotations

import contextlib
import os
import stat
from importlib import resources
from pathlib import Path

from .config import VERSION

_SKILL_NAME = "maintainability-agent"
_DIR_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


class SkillDrift(Exception):
    """The installed skill differs from the packaged one and force is off.

    A refusal, not a failure: overwriting a copy someone edited — or
    silently deleting files a previous version left behind — destroys
    work without consent. The message lists every differing path so the
    choice is informed; ``--force`` performs the full sync, deletions
    included.
    """


def install_skill(skills_dir: Path, *, force: bool = False) -> list[str]:
    """Sync the packaged skill into ``skills_dir``; return what was done.

    A missing or empty target installs outright. An identical copy is a
    no-op. Anything else — edited files, leftovers from an older
    version, missing files, or a symlink anywhere in the tree — is
    refused with the list unless ``force`` is set, in which case the
    target is made byte-identical to the package: files written,
    symlinks replaced with real files, stale files removed.
    """
    packaged = _packaged_files()
    target_root = skills_dir / _SKILL_NAME
    root_fd = _bind_root(target_root)
    try:
        existing, links = _read_tree(root_fd) if root_fd is not None else ({}, [])
        root_is_link = root_fd is None and target_root.is_symlink()
        drifted = _drift(packaged, existing, links, root_is_link=root_is_link)
        # Anything already there — files, symlinks, or a symlinked root
        # — makes this a sync rather than an install, and a sync needs
        # consent. An empty directory is still a fresh install (D19: a
        # nested symlink in an otherwise empty root slipped past this
        # gate when only regular files were counted).
        occupied = bool(existing or links or root_is_link)
        if occupied and drifted and not force:
            raise SkillDrift(
                "installed skill differs from the packaged one: "
                + ", ".join(drifted)
                + ". Re-run with --force to sync (overwrites edits, "
                "replaces symlinks, removes files the package no longer "
                "ships)."
            )

        written: list[str] = []
        if root_fd is None:
            if root_is_link:
                # Unlink the link, never its destination: the former
                # target keeps whatever it held.
                target_root.unlink()
                written.append(f"replaced symlinked skill root {target_root}")
            target_root.mkdir(parents=True, exist_ok=True)
            root_fd = _bind_root(target_root)
            if root_fd is None:
                # Something raced us to the name between mkdir and the
                # bind. Writing on with `dir_fd=None` would resolve
                # every path against the PROCESS WORKING DIRECTORY —
                # an audit reproduced a stray SKILL.md there (D18).
                raise SkillDrift(
                    f"{target_root} could not be bound after creation; "
                    "something changed it underneath. Nothing was "
                    "written. Re-run --install-skill."
                )
        try:
            _write_tree(root_fd, packaged, existing, links, written, target_root)
        except OSError as error:
            # The bound directory went away or changed under us. The
            # descriptor kept every write inside the inode that was
            # checked, so nothing landed elsewhere — say so plainly
            # rather than surfacing a traceback (D18).
            raise SkillDrift(
                f"the skill directory changed while installing ({error}); "
                "nothing was written outside it. Re-run --install-skill."
            ) from error
        written.append(f"skill {_SKILL_NAME} synced to version {VERSION}")
        return written
    finally:
        if root_fd is not None:
            os.close(root_fd)


def _bind_root(target_root: Path) -> int | None:
    """The skill root as a descriptor, or None when it is not a real directory.

    ``O_NOFOLLOW`` means a symlinked root fails here rather than
    resolving elsewhere, and the descriptor that comes back is what
    every later operation uses — so swapping the name afterwards
    cannot redirect a write (D18).
    """
    try:
        return os.open(target_root, _DIR_FLAGS)
    except OSError:
        return None


def _drift(packaged: dict[str, bytes], existing: dict[str, bytes],
           links: list[str], *, root_is_link: bool) -> list[str]:
    return sorted(
        set(packaged) ^ set(existing)
        | {name for name in packaged.keys() & existing.keys()
           if packaged[name] != existing[name]}
        | {f"{name} (not a packaged file)" for name in links}
        | ({f"{_SKILL_NAME} (symlinked directory)"} if root_is_link else set())
    )


def _read_tree(fd: int, prefix: str = "") -> tuple[dict[str, bytes], list[str]]:
    """Every entry under a bound directory, by descriptor.

    `links` is really "everything present that is not a regular file
    this tool wrote": symlinks, empty directories, FIFOs, sockets,
    devices. All of them are occupancy (D19) — an audit found an empty
    subdirectory and a FIFO each reading as a fresh install, and a FIFO
    named SKILL.md hanging the installer forever because opening it
    blocks. Nothing here opens a special file; `stat` with
    `follow_symlinks=False` answers from metadata alone.
    """
    files: dict[str, bytes] = {}
    others: list[str] = []
    for name in sorted(os.listdir(fd)):
        relative = f"{prefix}{name}"
        info = os.stat(name, dir_fd=fd, follow_symlinks=False)
        if stat.S_ISLNK(info.st_mode):
            others.append(relative)
        elif stat.S_ISDIR(info.st_mode):
            child = os.open(name, _DIR_FLAGS, dir_fd=fd)
            try:
                sub_files, sub_others = _read_tree(child, f"{relative}/")
            finally:
                os.close(child)
            if not sub_files and not sub_others:
                # An empty directory is still something present. The
                # register's own words are "anything already present".
                others.append(f"{relative}/")
            files.update(sub_files)
            others.extend(sub_others)
        elif stat.S_ISREG(info.st_mode):
            files[relative] = _read_file(fd, name)
        else:
            # FIFO, socket, device, or anything else: recorded as
            # present, never opened.
            others.append(relative)
    return files, others


def _read_file(fd: int, name: str) -> bytes:
    handle = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=fd)
    try:
        chunks = []
        while chunk := os.read(handle, 65_536):
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(handle)


def _write_tree(root_fd: int, packaged: dict[str, bytes],
                existing: dict[str, bytes], links: list[str],
                written: list[str], target_root: Path) -> None:
    """Clear what does not belong, write every packaged file, drop the stale."""
    for relative in sorted(links, reverse=True):
        # Deepest first, so an empty directory is removed after
        # whatever it contained. Directories need rmdir, and anything
        # this tool cannot safely remove is refused rather than forced.
        _in_parent(root_fd, relative.rstrip("/"), _remove_at)
        written.append(f"replaced {target_root / relative}")
    for relative, body in sorted(packaged.items()):
        _in_parent(root_fd, relative, _writer_for(body), create=True)
        written.append(str(target_root / relative))
    for relative in sorted(set(existing) - set(packaged)):
        _in_parent(root_fd, relative, _unlink_at)
        written.append(f"removed {target_root / relative}")


def _unlink_at(fd: int, name: str) -> None:
    os.unlink(name, dir_fd=fd)


def _remove_at(fd: int, name: str) -> None:
    """Remove one entry of any supported kind, or refuse it by name.

    Symlinks, regular files, FIFOs, sockets and empty directories all
    go. A device node or anything else unrecognised is refused: forcing
    a sync must not quietly delete something this tool does not
    understand (D19).
    """
    info = os.stat(name, dir_fd=fd, follow_symlinks=False)
    mode = info.st_mode
    if stat.S_ISDIR(mode):
        os.rmdir(name, dir_fd=fd)
    elif (stat.S_ISLNK(mode) or stat.S_ISREG(mode)
          or stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode)):
        os.unlink(name, dir_fd=fd)
    else:
        raise SkillDrift(
            f"{name} is a special file this tool will not remove; "
            "clear it yourself, then re-run --install-skill."
        )


def _writer_for(body: bytes):
    """Write via a fresh temporary file, then rename it into place.

    Opening the destination and truncating it modifies whatever inode
    the name points at — and ``O_NOFOLLOW`` does not help with a HARD
    link, so an audit replaced SKILL.md with a link to an external file
    and watched that file get overwritten (D18). A new file plus an
    atomic rename cannot touch the old inode: the link keeps its
    contents and simply stops being this name.
    """
    def write(fd: int, name: str) -> None:
        staging = f".{name}.incoming"
        handle = os.open(
            staging, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o644, dir_fd=fd,
        )
        try:
            written = 0
            while written < len(body):
                # os.write may write fewer bytes than asked. Reporting
                # success on a truncated file installs a skill that is
                # silently incomplete (D18).
                sent = os.write(handle, body[written:])
                if sent <= 0:
                    raise SkillDrift(
                        f"writing {name} stopped after {written} of "
                        f"{len(body)} bytes; nothing was installed."
                    )
                written += sent
            os.fsync(handle)
        except BaseException:
            os.close(handle)
            _discard(fd, staging)
            raise
        os.close(handle)
        try:
            os.replace(staging, name, src_dir_fd=fd, dst_dir_fd=fd)
        except BaseException:
            _discard(fd, staging)
            raise

    return write


def _discard(fd: int, name: str) -> None:
    """Remove a staging file, never masking the error that caused it."""
    with contextlib.suppress(OSError):
        os.unlink(name, dir_fd=fd)


def _in_parent(root_fd: int, relative: str, action, *, create: bool = False) -> None:
    """Run `action(parent_fd, name)` with every directory bound by descriptor."""
    parts = relative.split("/")
    opened: list[int] = []
    current = root_fd
    try:
        for part in parts[:-1]:
            try:
                child = os.open(part, _DIR_FLAGS, dir_fd=current)
            except FileNotFoundError:
                if not create:
                    return
                os.mkdir(part, dir_fd=current)
                child = os.open(part, _DIR_FLAGS, dir_fd=current)
            opened.append(child)
            current = child
        action(current, parts[-1])
    finally:
        for handle in reversed(opened):
            os.close(handle)


def _packaged_files() -> dict[str, bytes]:
    root = resources.files("maintainability_audit") / "_skill_data"
    return {name: entry.read_bytes() for name, entry in _files_under(root)}


def _files_under(node, prefix: str = ""):
    """Every file below a Traversable, with its relative posix path.

    ``importlib.resources`` Traversables have no ``rglob`` — an
    installed package may live in a zip, so the walk uses only the
    Traversable protocol.
    """
    for child in node.iterdir():
        relative = f"{prefix}{child.name}"
        if child.is_dir():
            yield from _files_under(child, f"{relative}/")
        else:
            yield relative, child

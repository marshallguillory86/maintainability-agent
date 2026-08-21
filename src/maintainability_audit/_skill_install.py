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
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path

from .config import VERSION

_SKILL_NAME = "maintainability-agent"


class SkillDrift(Exception):
    """The installed skill differs from the packaged one and force is off.

    A refusal, not a failure: overwriting a copy someone edited — or
    silently deleting files a previous version left behind — destroys
    work without consent (audit M5 on d5b1c50). The message lists every
    differing path so the choice is informed; ``--force`` performs the
    full sync, deletions included.
    """


def install_skill(skills_dir: Path, *, force: bool = False) -> list[str]:
    """Sync the packaged skill into ``skills_dir``; return what was done.

    A fresh directory installs outright. An existing identical copy is
    a no-op. An existing copy that differs — edited files, leftovers
    from an older version, missing files — is refused with the list
    unless ``force`` is set, in which case the target is made
    byte-identical to the package: files written AND stale files
    removed (audit M3: writing without deleting left obsolete files
    posing as current).
    """
    packaged = _packaged_files()
    target_root = skills_dir / _SKILL_NAME
    existing = _existing_files(target_root)

    drifted = sorted(
        set(packaged) ^ set(existing)
        | {name for name in packaged.keys() & existing.keys()
           if packaged[name] != existing[name]}
    )
    if existing and drifted and not force:
        raise SkillDrift(
            "installed skill differs from the packaged one: "
            + ", ".join(drifted)
            + ". Re-run with --force to sync (overwrites edits, removes "
            "files the package no longer ships)."
        )

    written: list[str] = []
    for name, body in sorted(packaged.items()):
        target = target_root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(body)
        written.append(str(target))
    for name in sorted(set(existing) - set(packaged)):
        (target_root / name).unlink()
        written.append(f"removed {target_root / name}")
    written.append(f"skill {_SKILL_NAME} synced to version {VERSION}")
    return written


def _packaged_files() -> dict[str, bytes]:
    root = resources.files("maintainability_audit") / "_skill_data"
    return {name: entry.read_bytes() for name, entry in _files_under(root)}


def _existing_files(target_root: Path) -> dict[str, bytes]:
    if not target_root.is_dir():
        return {}
    return {
        path.relative_to(target_root).as_posix(): path.read_bytes()
        for path in sorted(target_root.rglob("*"))
        if path.is_file()
    }


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

"""Whether a persisted root grant still names what the user consented to.

Four versions of this rule have been broken, each by comparing strings:

1. **Canonical only.** Dropped every ordinary macOS grant, because
   `/tmp` and `/var` are symlinks there.
2. **Canonical, or non-canonical whose leaf is not a link.** An audit
   retargeted the *parent*, one directory above the leaf it checked.
3. **Canonical or refused.** `Path.resolve()` is not `strict=True`, so a
   directory nobody has created "resolves to itself" and was honoured;
   and `resolve()` preserves case, so on APFS `/USERS/...` both exists
   and resolves to itself.

The pattern is the point. A path is a *name*, and names alias: symlinks,
case-insensitive volumes, bind mounts, a directory created after the
question was answered. Every fix that compared a better string moved the
hole rather than closing it, and the third version's own docstring said
so — *"a bare path with no record of what it resolved to when it was
granted cannot be defended: nothing to compare against means nothing to
detect"* — and then honoured bare paths anyway.

So this version stops comparing names. `persist_root_grant` records the
directory's identity — device and inode — at the moment of consent, and
a grant is honoured only when the directory at that path is still that
directory. Bind mounts and post-hoc creation change the inode, so they
are refused by the same check that refuses a swapped symlink, rather
than by a fifth special case (D79).

**A hand-written entry carries no identity and is refused.** That is the
deliberate consequence: it is exactly the "bare path with no record"
the rule cannot defend. `server_info` names it and says how to repair
it, and the repair is to grant the root through setup, which records
what it resolved to.
"""

from __future__ import annotations

import os
from pathlib import Path

#: Where `persist_root_grant` records what each grant resolved to.
IDENTITY_KEY = "allowed_root_identity"


class StaleStandingGrant(Exception):
    """A persisted grant no longer names the directory it was given for.

    Raised where the grant is *used*, not where it is loaded, and
    re-raised by the audit door as `PathNotAllowed` so the transport
    keeps its declared refusal type (D83).
    """

NO_IDENTITY = (
    "no record of what this path was when it was granted, so nothing here "
    "can tell it from a directory created or mounted afterwards"
)
NOT_CANONICAL = (
    "not a canonical path: it resolves to a different path, so this agent "
    "cannot tell a symlinked spelling from a directory that was swapped "
    "after you granted it"
)
NOT_A_DIRECTORY = "no directory exists at this path now"
WRONG_SPELLING = (
    "the filesystem spells this path differently, and on a case-insensitive "
    "volume two spellings name one directory"
)
CHANGED_IDENTITY = (
    "a directory exists here, but it is not the one you granted: it has been "
    "replaced, remounted, or recreated since"
)
REPAIR = (
    "grant this root again through setup, which records the directory it "
    "resolved to when you consented"
)


def directory_identity(path: Path) -> list[int] | None:
    """`[device, inode]` for a directory, or None when it is not one."""
    try:
        info = path.stat()
    except OSError:
        return None
    return [info.st_dev, info.st_ino] if path.is_dir() else None


def _spelled_as_the_filesystem_spells_it(candidate: Path) -> bool:
    """Whether every component matches its parent's own listing exactly.

    The only authority on how a path is spelled is the directory it
    lives in. `resolve()` is not: it preserves case, which is why a
    case-variant spelling passed the previous rule.
    """
    built = Path(candidate.anchor)
    for part in candidate.parts[1:]:
        try:
            if part not in os.listdir(built):
                return False
        except OSError:
            return False
        built = built / part
    return True


def refusal_reason(entry: str, recorded: object) -> str | None:
    """Why this stored grant is not honoured, or None when it is.

    `recorded` is the identity written at consent time — a two-element
    sequence — or anything else, including absent, for an entry nothing
    recorded.
    """
    candidate = Path(entry).expanduser()
    if not candidate.is_absolute():
        return NOT_CANONICAL
    try:
        if candidate.resolve() != candidate:
            return NOT_CANONICAL
        if not candidate.is_dir():
            return NOT_A_DIRECTORY
        if not _spelled_as_the_filesystem_spells_it(candidate):
            return WRONG_SPELLING
    except OSError:
        return NOT_CANONICAL

    if not isinstance(recorded, (list, tuple)) or len(recorded) != 2:
        return NO_IDENTITY
    if not all(isinstance(value, int) and not isinstance(value, bool)
               for value in recorded):
        return NO_IDENTITY
    if directory_identity(candidate) != list(recorded):
        return CHANGED_IDENTITY
    return None


def refuse_a_stale_standing_grant(
    root: Path, entries: list[str], identities: dict[str, object]
) -> None:
    """Re-check persisted grants at *use*, not only at start-up (D83).

    `allowed_roots()` runs once, when the server is built, and the
    ledger it produces is a tuple of paths. `authorize_repository` then
    only asked whether the request was *inside* one of them. So a
    standing grant whose directory was swapped after the process started
    kept authorizing whatever now sits at that path until the host died
    — and an MCP server is long-lived, which is the surface this product
    calls primary.

    This is D38's original shape: the in-process seam was already right,
    and a later read of a stored fact went around it. There the stored
    fact was a path; here it is an identity, and the later read was not
    happening at all.

    Launch roots (`--allow-root`, the environment, the working
    directory) carry no recorded identity and are not re-checked: they
    are this process's own configuration rather than a standing consent.
    """
    for entry in entries:
        # Resolved only to find which grant covers this request; the
        # grant itself is then re-validated by the rule that does not
        # trust resolution.
        try:
            granted = Path(entry).expanduser().resolve()
        except OSError:
            continue
        if not (root == granted or root.is_relative_to(granted)):
            continue
        if refusal_reason(entry, identities.get(entry)) is not None:
            raise StaleStandingGrant(
                "the standing grant covering this repository no longer "
                "names the directory it was given for, so it has been "
                "withdrawn. Grant it again when asked."
            )

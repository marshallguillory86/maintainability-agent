"""The persisted root-grant ledger: what is stored, and what is honoured.

Split out of ``_mcp_audit`` when that module crossed this project's own
file-size gate. The split is not only arithmetic: reading the ledger is
a different job from running an audit, and it has its own rule --
`_stored_grants` decides whether a stored grant still names the
directory the user consented to, and this module is what asks.

Sits above `_user_config` (which writes the ledger) and `_stored_grants`
(which judges it), and below the audit door that consumes the result.
"""

from __future__ import annotations

import os
from pathlib import Path

from ._stored_grants import IDENTITY_KEY, REPAIR, refusal_reason
from ._user_config import load_user_config

ALLOWED_ROOTS_ENV = "MAINTAINABILITY_MCP_ALLOWED_ROOTS"


def _resolved(path: str | Path, *, relative_to: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and relative_to is not None:
        candidate = relative_to / candidate
    return candidate.resolve()


def allowed_roots(explicit: tuple[str, ...] = ()) -> tuple[Path, ...]:
    """Resolve the server allow-list once, defaulting to its launch directory.

    "Always" grants the user made through the D10 elicitation live in
    the user-tier config and join whatever the launch configured — a
    standing grant must survive a restart, which launch flags alone
    cannot promise.
    """
    configured = explicit or tuple(filter(None, os.environ.get(ALLOWED_ROOTS_ENV, "").split(os.pathsep)))
    roots = configured or (str(Path.cwd()),)
    return tuple(_resolved(root) for root in (*roots, *_persisted_root_grants()))


def _grant_still_names_what_was_granted(entry: str, recorded: object = None) -> bool:
    """True when a stored grant still names the directory it named.

    The rule and the four versions it took live in `_stored_grants`.
    """
    return refusal_reason(entry, recorded) is None


def _stored_grants_and_identities() -> tuple[list[str], dict[str, object]]:
    """The persisted allow-list and what each entry resolved to."""
    config = load_user_config() or {}
    grants = config.get("allowed_roots")
    identities = config.get(IDENTITY_KEY)
    return (
        [str(entry) for entry in grants] if isinstance(grants, list) else [],
        identities if isinstance(identities, dict) else {},
    )


def _persisted_root_grants() -> tuple[str, ...]:
    """The stored grants this process honours."""
    entries, identities = _stored_grants_and_identities()
    return tuple(
        entry for entry in entries
        if refusal_reason(entry, identities.get(entry)) is None
    )


def refused_root_grants() -> tuple[dict[str, str], ...]:
    """Stored grants this process will not honour, and why (D38, D72).

    Surfaced through `server_info` so a hand-written entry quietly doing
    nothing can be seen — without disclosing what it resolved to.
    """
    entries, identities = _stored_grants_and_identities()
    refused = []
    for entry in entries:
        reason = refusal_reason(entry, identities.get(entry))
        if reason is None:
            continue
        # The entry is echoed because the user wrote it. What it resolves
        # to is not ours to publish: returning it told whatever host
        # reads `server_info` where a symlink the user named actually
        # points (D72).
        refused.append({"entry": entry, "reason": reason, "repair": REPAIR})
    return tuple(refused)

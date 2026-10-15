"""The refusals the MCP transport is allowed to declare.

One home, because the seams that translate them no longer live in one
module. The audit tool binds in `mcp_server`; the report resource and
its security validator moved to `_mcp_resources` when that module
crossed the file-length gate. A tuple defined beside one of them would
have to be imported by the other, and `mcp_server` already imports
`_mcp_resources` — so it lives below both instead.

Named types only, never bare `ValueError`. Modules below the transport
raise `ValueError` with internal state and file paths in the message,
and the crash path is right to withhold those. `PathNotAllowed`,
`ConfigUnreadable` and `PolicyError` all derive from `ValueError`, so
excepting the base class here would translate exactly the messages this
boundary exists to keep server-side. See architecture invariant 12 and
D48.
"""

from __future__ import annotations

from ._analysis import RepositoryModifiedError
from ._catalog import PolicyError
from ._mcp_audit import InvalidAuditArgument, PathNotAllowed
from ._mcp_setup import SetupRequired
from .baseline import StaleBaseline
from .config import ConfigUnreadable

ANTICIPATED_REFUSALS = (
    InvalidAuditArgument,
    PathNotAllowed,
    SetupRequired,
    StaleBaseline,
    PolicyError,
    # A configuration file that exists and cannot be parsed. The message
    # names the file the caller pointed at and says to repair or delete
    # it, which is the definition of a refusal someone can act on — and
    # it is why the seam cannot simply except `ValueError`, since this
    # type and `PathNotAllowed` both derive from it alongside the
    # internal ones that must stay crashes.
    ConfigUnreadable,
    # An analyzer changed the audited repository. The message names the
    # changed files and says to report the adapter: actionable, and a
    # grade must never be returned for code that is no longer what was
    # audited.
    RepositoryModifiedError,
)

__all__ = ["ANTICIPATED_REFUSALS"]

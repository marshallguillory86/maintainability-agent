"""D10 root grants: the ledger, the question, and the consent it binds.

Split out of ``mcp_server`` (transport assembly) when that file crossed
the repository's own size gate. Everything here serves one promise: a
grant authorizes exactly the directory the question named — session
grants live in the process, "always" grants persist to the user tier,
and nothing is granted without a completed consent round.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._mcp_audit import PathNotAllowed, authorize_repository
from ._mcp_setup import apply_answers

# The two affirmative D10 grant scopes (decision 5). "no" needs no
# constant: a refusal is the absence of a grant, not a kind of one.
_GRANT_SESSION = "this session"
_GRANT_ALWAYS = "always"


class _RootLedger:
    """The live allow-list: launch roots plus grants made through D10.

    A session grant extends this process's list and nothing else; an
    "always" grant additionally persists to the user-tier config, which
    ``allowed_roots`` folds back in at the next server start. The repo
    config never carries a grant — a repository must not be able to
    authorize itself.
    """

    def __init__(self, roots: tuple[Path, ...]) -> None:
        self._roots = list(roots)
        self._asked: dict[str, Path] = {}

    def current(self) -> tuple[Path, ...]:
        return tuple(self._roots)

    def note_ask(self, requested: str, resolved: Path) -> None:
        """Remember which directory the grant question actually named."""
        self._asked[requested] = resolved

    def consume_ask(self, requested: str) -> Path | None:
        """The path the user was shown, surrendered exactly once.

        The grant must authorize what the question named — resolving
        the request a second time would let a symlink retargeted
        during the elicitation round-trip swap the consented path for
        another (verification-audit TOCTOU on 6b2fb76).
        """
        return self._asked.pop(requested, None)

    def grant(self, root: Path, *, persist: bool) -> None:
        from ._user_config import persist_root_grant

        if root not in self._roots:
            self._roots.append(root)
        if persist:
            persist_root_grant(root)


def _grant_schema() -> Any:
    """One structured question: the scope of the root grant (decision 5)."""
    from typing import Literal

    from pydantic import Field, create_model

    return create_model(
        "RootGrant",
        root_access=(
            Literal["this session", "always", "no"],
            Field(
                default=_GRANT_SESSION,
                description=(
                    "Grant the audit read access to this repository? "
                    "'this session' lasts until the server restarts; "
                    "'always' is remembered in your user configuration; "
                    "'no' refuses."
                ),
            ),
        ),
    )


def _grant_resolver_for(ledger: _RootLedger, context_type: Any) -> Any:
    """The D10 ask as a resolver: one question instead of an error string.

    Asks only when the requested root is real, outside the live
    allow-list, and the client can elicit. Every other case returns
    ``None`` and the tool body raises (or proceeds) exactly as before —
    a missing capability costs the ask, never the boundary.
    """
    from mcp.server.mcpserver.resolve import Elicit

    def roots_grant(repository_root: str, ctx: Any = None) -> Any:
        try:
            authorize_repository(repository_root, ledger.current())
            return None  # inside the boundary: nothing to ask
        except PathNotAllowed:
            pass
        except ValueError:
            return None  # not a directory: the tool body raises the real error
        capabilities = getattr(ctx, "client_capabilities", None)
        if capabilities is None or capabilities.elicitation is None:
            return None
        # The question names the RESOLVED path — the one the grant will
        # actually authorize. A symlink or `..` in the request must not
        # let the modal show one directory while the ledger records
        # another (audit H2): the user consents to the real target.
        resolved = Path(repository_root).expanduser().resolve()
        ledger.note_ask(repository_root, resolved)
        return Elicit(
            message=(
                f"{resolved} is outside this server's allowed "
                "roots. Grant the audit read access to it?"
            ),
            schema=_grant_schema(),
        )

    roots_grant.__annotations__["ctx"] = context_type
    return roots_grant


def _granted_scope(grant: Any) -> str | None:
    """The accepted grant answer, or None when nothing was asked or given."""
    answer = getattr(grant, "data", None)
    if not hasattr(answer, "model_dump"):
        return None
    values = list(answer.model_dump().values())
    return str(values[0]) if values else None


def _apply_call_consents(ledger: _RootLedger, repository_root: str,
                         setup: Any, grant: Any) -> None:
    """Apply what this call's elicitations granted, before the audit runs.

    Grant first: an accepted D10 answer extends (and for "always"
    persists) the allow-list this very call is authorized against. The
    granted path is consumed from the ledger's record of the ask, never
    re-resolved — the user consented to the directory the question
    named, and only that directory (audit H2 and its TOCTOU residual).
    Then setup: accepted first-run answers persist so this call runs
    under the chosen configuration.
    """
    asked = ledger.consume_ask(repository_root)
    scope = _granted_scope(grant)
    if scope in (_GRANT_SESSION, _GRANT_ALWAYS) and asked is not None:
        ledger.grant(asked, persist=scope == _GRANT_ALWAYS)
    answers = getattr(setup, "data", None)
    if hasattr(answers, "model_dump"):
        root = authorize_repository(repository_root, ledger.current())
        apply_answers(root, answers.model_dump())

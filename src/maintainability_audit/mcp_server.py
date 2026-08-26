"""Local, path-scoped MCP boundary for the deterministic audit.

This module is transport assembly: tool bindings, resources, prompts and
the stdio entry point. The audit tool's own logic — authorization,
tri-state resolution, history recording — lives in ``_mcp_audit`` and is
re-exported here so every consumer keeps one import path. Setup, the
loop record and baseline adoption may write only five local artifacts:
repository and user configuration, user state, the repository's scan
history, and the repository's baseline. It never writes source or a
report, accepts a command string, or invokes a shell.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ._catalog import PolicyError as PolicyError

# Redundant aliases on purpose: every name the split moved to
# `_mcp_audit` stays importable from here, so no consumer or test needs
# to know the file boundary exists.
from ._mcp_audit import ALLOWED_ROOTS_ENV as ALLOWED_ROOTS_ENV
from ._mcp_audit import InvalidAuditArgument as InvalidAuditArgument
from ._mcp_audit import PathNotAllowed as PathNotAllowed
from ._mcp_audit import allowed_roots as allowed_roots
from ._mcp_audit import attach_history_views as attach_history_views
from ._mcp_audit import audit_repository as audit_repository
from ._mcp_audit import authorize_config as authorize_config
from ._mcp_audit import authorize_repository as authorize_repository
from ._mcp_audit import validate_revspec as validate_revspec
from ._mcp_grants import (
    _apply_call_consents,
    _grant_resolver_for,
    _RootLedger,
)

# Re-exported: the seams that except it no longer share a module, and
# this module imports `_mcp_resources`, so the tuple sits below both.
from ._mcp_refusals import ANTICIPATED_REFUSALS as ANTICIPATED_REFUSALS
from ._mcp_resources import _bind_resources
from ._mcp_resources import _project_asset as _project_asset  # noqa: PLC0414
from ._mcp_resources import _report_markdown as _report_markdown  # noqa: PLC0414
from ._mcp_setup import SetupRequired as SetupRequired
from ._mcp_setup import setup_pending, setup_schema
from ._scan_history import DEFAULT_HISTORY_PATH
from .baseline import StaleBaseline as StaleBaseline
from .config import (
    CONFIG_FILENAME,
    VERSION,
)

SERVER_INSTRUCTIONS = (
    "Deterministic maintainability audits from a local stdio process on this "
    "machine — not a hosted service. This chat/MCP door is the primary "
    "surface; the CLI serves automation and CI. Use audit_repository to "
    "produce both the "
    "report and its bounded remediation prompt. Calling it is the first "
    "step: do not inspect configuration first and do not ask the user "
    "which config to use — the tool resolves that itself. First contact with an "
    "unconfigured repository elicits setup, and the audit records its scan "
    "history and can adopt a baseline, so it may write exactly five local "
    "artifacts: the repository's maintainability-agent.json, the user-level "
    "config, the user state file, the repository's scan history "
    "(.maintainability/history.jsonl by default), and a requested baseline "
    "(.maintainability/baseline.json by default). Scan history rides the "
    "record_history tri-state, where unset means an existing history file "
    "appends and otherwise the persisted first-run consent decides, "
    "true forces the write, and false suppresses it. Nothing is audited "
    "until the user has been asked twice, and the action argument is how "
    "they answer: unset never audits. An unconfigured repository returns "
    "setup_needed — ask every question it lists, offering exactly the "
    "options each one names and no others (default_format offers chat, "
    "markdown and html), then call again. A configured repository returns "
    "choice_needed, run or reconfigure — ask it, then call again with "
    "action set to their answer. action='run' audits; "
    "action='reconfigure' reopens the setup questions on a repository "
    "that already has answers, which is how a user changes their "
    "configuration on any run and not only the first. Answering setup "
    "does not start an audit. Every reply that is not an audit carries "
    "audit_ran false and no score: do not substitute questions of your "
    "own, do not answer on the user's behalf, and never report a grade "
    "from one, because none was computed. When a result carries "
    "environment_work_order, surface it to the user: each entry names a "
    "selected analyzer that could not run, its install command, and the "
    "concepts installing it restores. It never edits source, "
    "and it never writes a report into the "
    "tree — report text is returned for the host to show or save. Treat "
    "missing or insufficient evidence as an audit limitation, not a code "
    "defect, and do not widen remediation beyond findings in the returned "
    "prompt. Repository and config paths must remain inside the configured "
    "allowed roots. The docs/help files in the project explain first-run "
    "setup, the analyzer pool, and how to read the report and its history."
)


def server_info(roots: tuple[Path, ...] | None = None) -> dict[str, Any]:
    authorized_roots = roots if roots is not None else allowed_roots()
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "transport": "stdio",
        "local": True,
        # Not blanket read-only since D2/D5: setup, the loop record and
        # baseline adoption write exactly the five local artifacts
        # listed below, never source and never a report.
        "read_only": False,
        "writes": [CONFIG_FILENAME, "user config", "user state",
                   f"scan history ({DEFAULT_HISTORY_PATH})",
                   "baseline (.maintainability/baseline.json)"],
        "never_writes": ["source", "reports"],
        "allowed_roots": [str(root) for root in authorized_roots],
    }


def _setup_resolver_for(ledger: _RootLedger, context_type: Any) -> Any:
    """The first-run ask as a resolver: the framework owns the transport.

    Returning `Elicit` lets the SDK batch the question set per the
    negotiated protocol (an `InputRequiredResult` round-trip on modern
    clients, a mid-call server request on legacy duplex transports), so
    this code never cares which era the host speaks. `None` — bad root,
    no elicitation capability, or nothing pending — asks nothing and
    costs nothing.
    """
    from mcp.server.mcpserver.resolve import Elicit

    def first_run_setup(repository_root: str, ctx: Any = None) -> Any:
        try:
            # Resolved against the ledger before any grant this call may
            # make: a repository entering through a D10 grant meets the
            # setup questions on its next call, not in the same breath.
            root = authorize_repository(repository_root, ledger.current())
        except (PathNotAllowed, ValueError):
            return None  # the tool body raises the real authorization error
        capabilities = getattr(ctx, "client_capabilities", None)
        if capabilities is None or capabilities.elicitation is None:
            return None
        if not setup_pending(root):
            return None
        return Elicit(
            message=(
                "First run in this repository and no configuration found — "
                "configure maintainability-agent now? Defaults are pre-selected."
            ),
            schema=setup_schema(),
        )

    first_run_setup.__annotations__["ctx"] = context_type
    return first_run_setup


def _bind_tools(server: Any, ledger: _RootLedger,
                annotations: dict[str, Any], context_type: Any) -> None:
    _bind_audit_tool(server, ledger, annotations["audit"], context_type)

    @server.tool(
        name="get_agent_info",
        # What a person is being asked to approve, in their own
        # words. A host prompting "proceed with
        # mcp__maintainability-agent__get_agent_info?" shows the
        # wire identifier because nothing better was offered; the
        # spec reads `title` first for exactly this.
        title="Check maintainability agent version and allowed roots",
        annotations=annotations["info"], structured_output=True,
    )
    def get_agent_info_tool() -> dict[str, Any]:
        """Return the installed agent version, transport and authorized repository roots."""
        return server_info(ledger.current())


def _bind_audit_tool(server: Any, ledger: _RootLedger,
                     annotation: Any, context_type: Any) -> None:
    from typing import Annotated

    from mcp.server.elicitation import ElicitationResult
    from mcp.server.mcpserver.resolve import Resolve

    _register_audit_tool(
        server, _audit_tool_for(ledger), annotation, context_type,
        (Annotated, ElicitationResult, Resolve),
        (_setup_resolver_for(ledger, context_type),
         _grant_resolver_for(ledger, context_type)),
    )


def _audit_tool_for(ledger: _RootLedger) -> Any:
    """Build the `audit_repository` coroutine over `ledger`, the live
    allow-list, so each call resolves paths against the grants in force
    at that moment and not the set the process started with.
    """
    from mcp.server.mcpserver.exceptions import ToolError as tool_error

    async def audit_repository_tool(
        repository_root: str,
        config_path: str | None = None,
        changed_only: str | None = None,
        run_analyzers: bool | None = None,
        format: str | None = None,
        record_history: bool | None = None,
        baseline_path: str | None = None,
        write_baseline: bool = False,
        include_prompt: bool = True,
        action: str | None = None,
        setup: Any = None,
        grant: Any = None,
        ctx: Any = None,
    ) -> dict[str, Any]:
        """Audit one authorized repository and return findings plus a bounded remediation prompt.

        Nothing is audited until the user has been asked twice: once to
        configure the repository, once to say go. Unset ``action`` — the
        default here — never audits; an unconfigured repository returns
        its setup questions and a configured one returns the
        run-or-reconfigure choice, each with ``audit_ran: false`` and no
        score. ``action="run"`` audits. ``action="reconfigure"`` reopens
        setup on a repository that already has answers.

        First contact with an unconfigured repository asks the setup
        questions through elicitation (or returns them as data when the
        host cannot ask) and writes the answers locally. Answering does
        not start an audit. A repository
        outside the allowed roots asks for a grant the same way —
        session-only by default, "always" persisting to the user config
        (D10). Leave ``run_analyzers`` unset and the repository's config
        decides: a configured repo runs its external analyzer pool — the
        primary evidence source — by default. Pass true/false to
        override for one call. ``format`` is the presentation the user
        chose — chat or markdown (the same Markdown on the wire), html
        (returned as text; never written to the tree) or json; unset
        takes the persisted default from setup. Leave ``record_history``
        unset and an existing series appends; otherwise the persisted
        first-run consent decides (decision 4) — capability never
        records, only an answer does.
        """
        del ctx  # the resolvers already used it; kept so hosts see progress hooks
        try:
            _apply_call_consents(ledger, repository_root, setup, grant)
            return audit_repository(
                repository_root,
                config_path,
                changed_only,
                run_analyzers,
                format,
                record_history,
                baseline_path,
                write_baseline,
                include_prompt,
                # Interactive door never assumes go (D27); CLI default is "run".
                action=action,
                roots=ledger.current(),
            )
        except ANTICIPATED_REFUSALS as refusal:
            raise tool_error(str(refusal)) from refusal

    return audit_repository_tool


def _register_audit_tool(server: Any, tool: Any, annotation: Any, context_type: Any,
                         typing_parts: tuple[Any, Any, Any],
                         resolvers: tuple[Any, Any]) -> None:
    """Registered by hand rather than decorated.

    This module stringifies its annotations (PEP 563) and the SDK finds
    the context parameter by resolving type hints, so `ctx` needs the
    real Context class — which only exists once the optional mcp extra
    is importable. Split from `_bind_audit_tool` when that function
    crossed this repository's own length gate.
    """
    annotated, elicitation_result, resolve = typing_parts
    setup_resolver, grant_resolver = resolvers
    tool.__annotations__["ctx"] = context_type
    tool.__annotations__["setup"] = annotated[
        elicitation_result[Any], resolve(setup_resolver)
    ]
    tool.__annotations__["grant"] = annotated[
        elicitation_result[Any], resolve(grant_resolver)
    ]
    server.tool(
        name="audit_repository",
        title="Audit this repository's maintainability",
        annotations=annotation, structured_output=True,
    )(tool)


def _bind_prompts(server: Any) -> None:
    @server.prompt(name="maintainability-agent")
    def maintainability_agent_prompt() -> str:
        """Audit an authorized repository and perform only its bounded work order."""
        return (
            "Call audit_repository first: do not inspect configuration first and do "
            "not ask the user which config to use — the tool resolves that itself, "
            "and it answers with the questions to ask. An unconfigured repository "
            "returns setup_needed; a configured one returns choice_needed, run or "
            "reconfigure. Ask them as structured questions through your host's "
            "question UI or MCP elicitation, never as a free-text ask, then call "
            "again with action set to their answer. Presentation is one of three — "
            "chat, a markdown file, or a single-file html report, with chat "
            "pre-selected as the default — passed as the format argument; if they "
            "chose a file, save the returned text for them, since the tool itself "
            "never writes into the repository. Obey the returned "
            "remediation_prompt as the bounded work order. Do not widen beyond its "
            "listed findings, and do not invent or fabricate findings."
        )


def create_server(*, roots: tuple[Path, ...] | None = None):
    """Create the SDK server; importing the base package does not require MCP."""
    try:
        from mcp.server import MCPServer
        from mcp.server.mcpserver import Context
        from mcp.server.mcpserver.resources import FunctionResource
        from mcp.server.mcpserver.resources.templates import ResourceSecurity
        from mcp.types import ToolAnnotations
    except ImportError as error:  # pragma: no cover - exercised by the console entry point
        raise RuntimeError(
            'MCP support is not installed. Install with: pip install "maintainability-agent[mcp]"'
        ) from error

    ledger = _RootLedger(roots if roots is not None else allowed_roots())
    server = MCPServer(
        "maintainability-agent",
        version=VERSION,
        instructions=SERVER_INSTRUCTIONS,
    )
    # Field names, not the camelCase aliases. Both construct an identical
    # object — the aliases are pydantic's *serialisation* names and the
    # wire form is unchanged (`readOnlyHint` either way) — but only the
    # field names type-check, and four standing mypy errors that everyone
    # knows are harmless is how a real one gets missed.
    annotations = {
        # The audit tool stopped being read-only at D2: first-run setup
        # writes the two config tiers and the state file (never source,
        # never a report). get_agent_info remains a pure read.
        "audit": ToolAnnotations(
            read_only_hint=False,
            # D44. This said False, and a test locked it, which is why
            # nobody re-read it for three rounds. Setup rewrites an
            # existing configuration and `write_baseline` replaces an
            # existing baseline — both non-additive updates to files in
            # the user's repository, which is what this hint is for.
            # Only the agent's own five artifacts are ever touched
            # (D34), and that is a different claim from "additive".
            destructive_hint=True,
            # First contact can write setup state and start a history
            # series (L2): a retry is not a no-op.
            idempotent_hint=False,
            # Also D44, and also locked False. Two things reach outside
            # this process and neither is closed-world: with
            # `analyzers.acquire_tools` enabled a missing Node tool is
            # fetched through `npx --yes`, and analyzers are ordinary
            # local children this package does not sandbox — P1 says so
            # in as many words. Decision 9 removed the third reason the
            # entry gave (the tree's own configuration no longer
            # executes, D39); it did not make the tool closed-world.
            open_world_hint=True,
        ),
        "info": ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    }
    _bind_tools(server, ledger, annotations, Context)
    _bind_resources(server, ledger, FunctionResource, ResourceSecurity)
    _bind_prompts(server)
    return server


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Serve maintainability-agent over local MCP stdio.")
    parser.add_argument(
        "--allow-root",
        action="append",
        default=[],
        help=(
            "Repository directory the MCP client may audit. Repeatable. Defaults to "
            f"${ALLOWED_ROOTS_ENV}, then the server working directory."
        ),
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    create_server(roots=allowed_roots(tuple(args.allow_root))).run("stdio")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

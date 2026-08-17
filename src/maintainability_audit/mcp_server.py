"""Local, path-scoped MCP boundary for the deterministic audit.

This module is transport assembly: tool bindings, resources, prompts and
the stdio entry point. The audit tool's own logic — authorization,
tri-state resolution, history recording — lives in ``_mcp_audit`` and is
re-exported here so every consumer keeps one import path. First-run
setup and the loop record may write only repository and user
configuration, user state, and the repository's scan history. It never
writes source or a report, accepts a command string, or invokes a shell.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

# Redundant aliases on purpose: every name the split moved to
# `_mcp_audit` stays importable from here, so no consumer or test needs
# to know the file boundary exists.
from ._mcp_audit import ALLOWED_ROOTS_ENV as ALLOWED_ROOTS_ENV
from ._mcp_audit import PathNotAllowed as PathNotAllowed
from ._mcp_audit import allowed_roots as allowed_roots
from ._mcp_audit import attach_history_views as attach_history_views
from ._mcp_audit import audit_repository as audit_repository
from ._mcp_audit import authorize_config as authorize_config
from ._mcp_audit import authorize_repository as authorize_repository
from ._mcp_audit import validate_revspec as validate_revspec
from ._mcp_setup import apply_answers, setup_pending, setup_schema
from ._scan_history import DEFAULT_HISTORY_PATH
from .config import CONFIG_FILENAME, VERSION, discovered_config, load_config
from .renderers import render_markdown
from .report import build_report

SERVER_INSTRUCTIONS = (
    "Deterministic maintainability audits from a local stdio process on this "
    "machine — not a hosted service. Use audit_repository to produce both the "
    "report and its bounded remediation prompt. First contact with an "
    "unconfigured repository elicits setup, and the audit records its scan "
    "history, so it may write exactly four local artifacts: the repository's "
    "maintainability-agent.json, the user-level config, the user state file, "
    "and the repository's scan history (.maintainability/history.jsonl by "
    "default). It never edits source, and it never writes a report into the "
    "tree — report text is returned for the host to show or save. Treat "
    "missing or insufficient evidence as an audit limitation, not a code "
    "defect, and do not widen remediation beyond findings in the returned "
    "prompt. Repository and config paths must remain inside the configured "
    "allowed roots."
)


def server_info(roots: tuple[Path, ...] | None = None) -> dict[str, Any]:
    authorized_roots = roots if roots is not None else allowed_roots()
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "transport": "stdio",
        "local": True,
        # Not blanket read-only since D2/D5: setup and the loop record
        # write exactly these four local artifacts, never source and
        # never a report.
        "read_only": False,
        "writes": [CONFIG_FILENAME, "user config", "user state",
                   f"scan history ({DEFAULT_HISTORY_PATH})"],
        "never_writes": ["source", "reports"],
        "allowed_roots": [str(root) for root in authorized_roots],
    }


def _project_asset(relative: str) -> str:
    """Read one shipped project fact without accepting a caller-controlled path."""
    path = Path(__file__).resolve().parents[2] / relative
    return path.read_text(encoding="utf-8")


def _report_markdown(repository_root: str, roots: tuple[Path, ...]) -> str:
    """Render the same report as the CLI would, through the same path boundary.

    No ``run_analyzers`` argument on purpose: ``build_report`` resolves
    the tri-state from the config, so a configured repository's resource
    render runs its pool — the last consumer that could receive a
    configured repo's fallback without asking for it (D1).
    """
    root = authorize_repository(repository_root, roots)
    config = load_config(discovered_config(root))
    return render_markdown(build_report(root, config))


def _setup_resolver_for(authorized_roots: tuple[Path, ...], context_type: Any) -> Any:
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
            root = authorize_repository(repository_root, authorized_roots)
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


def _bind_tools(server: Any, authorized_roots: tuple[Path, ...],
                annotations: dict[str, Any], context_type: Any) -> None:
    _bind_audit_tool(server, authorized_roots, annotations["audit"], context_type)

    @server.tool(name="get_agent_info", annotations=annotations["info"], structured_output=True)
    def get_agent_info_tool() -> dict[str, Any]:
        """Return the installed agent version, transport and authorized repository roots."""
        return server_info(authorized_roots)


def _bind_audit_tool(server: Any, authorized_roots: tuple[Path, ...],
                     annotation: Any, context_type: Any) -> None:
    from typing import Annotated

    from mcp.server.elicitation import ElicitationResult
    from mcp.server.mcpserver.resolve import Resolve

    resolver = _setup_resolver_for(authorized_roots, context_type)

    async def audit_repository_tool(
        repository_root: str,
        config_path: str | None = None,
        changed_only: str | None = None,
        run_analyzers: bool | None = None,
        format: str | None = None,
        record_history: bool | None = None,
        setup: Any = None,
        ctx: Any = None,
    ) -> dict[str, Any]:
        """Audit one authorized repository and return findings plus a bounded remediation prompt.

        First contact with an unconfigured repository asks the setup
        questions through elicitation (or returns them as data when the
        host cannot ask) and writes the answers locally. Leave
        ``run_analyzers`` unset and the repository's config decides: a
        configured repo runs its external analyzer pool — the primary
        evidence source — by default. Pass true/false to override for one
        call. ``format`` is the presentation the user chose — chat or
        markdown (the same Markdown on the wire), html (returned as
        text; never written to the tree) or json; unset takes the
        persisted default from setup. Leave ``record_history`` unset and
        an existing series appends; an interactive (elicitation-capable)
        client also starts one — the chat analog of the CLI's TTY rule.
        """
        if record_history is None:
            capabilities = getattr(ctx, "client_capabilities", None)
            if capabilities is not None and capabilities.elicitation is not None:
                record_history = True
        del ctx  # the resolver already used it; kept so hosts see progress hooks
        answers = getattr(setup, "data", None)
        if hasattr(answers, "model_dump"):
            # The user accepted first-run setup: persist before the audit
            # below, so this very call runs under the chosen configuration.
            root = authorize_repository(repository_root, authorized_roots)
            apply_answers(root, answers.model_dump())
        return audit_repository(
            repository_root,
            config_path,
            changed_only,
            run_analyzers,
            format,
            record_history,
            roots=authorized_roots,
        )

    # Registered by hand rather than decorated: this module stringifies
    # its annotations (PEP 563), and the SDK finds the context parameter
    # by resolving type hints — `ctx` needs the real Context class, which
    # only exists once the optional mcp extra is importable.
    audit_repository_tool.__annotations__["ctx"] = context_type
    audit_repository_tool.__annotations__["setup"] = Annotated[
        ElicitationResult[Any], Resolve(resolver)
    ]
    server.tool(name="audit_repository", annotations=annotation,
                structured_output=True)(audit_repository_tool)


def _bind_resources(
    server: Any,
    authorized_roots: tuple[Path, ...],
    function_resource: Any,
    resource_security: Any,
) -> None:
    class AuthorizedRootSecurity(resource_security):
        """Validate an absolute template argument against this server's allow-list."""

        def validate(self, params: dict[str, Any]) -> str | None:
            root = params.get("root")
            if not isinstance(root, str):
                return "root"
            authorize_repository(root, authorized_roots)
            return None

    @server.resource(
        "maintainability://standard",
        name="maintainability-standard",
        description="The applied maintainability rubric.",
        mime_type="text/markdown",
    )
    def standard_resource() -> str:
        return _project_asset("docs/standard.md")

    @server.resource(
        "maintainability://catalog",
        name="analyzer-catalog",
        description="The shipped analyzer catalog and its provenance.",
        mime_type="application/json",
    )
    def catalog_resource() -> str:
        return _project_asset("data/analyzer-catalog.json")

    @server.resource(
        "maintainability://report/{+root}",
        name="maintainability-report",
        description="The production Markdown report for an authorized repository root.",
        mime_type="text/markdown",
        security=AuthorizedRootSecurity(),
    )
    def report_resource(root: str) -> str:
        return _report_markdown(root, authorized_roots)

    def report_template_descriptor() -> str:
        """Replace ``{root}`` with an authorized absolute repository path."""
        return "Use maintainability://report/{root} with an authorized repository root."

    server.add_resource(function_resource.from_function(
        fn=report_template_descriptor,
        uri="maintainability://report/{root}",
        name="maintainability-report-template",
        description="Template descriptor for the Markdown report resource.",
        mime_type="text/markdown",
    ))


def _bind_prompts(server: Any) -> None:
    @server.prompt(name="maintainability-agent")
    def maintainability_agent_prompt() -> str:
        """Audit an authorized repository and perform only its bounded work order."""
        return (
            "First ask the user which presentation they want: chat (the default — just show "
            "the returned Markdown), a markdown file, or a single-file html report. Then call "
            "audit_repository with that choice as the format argument; if they chose a file, "
            "save the returned text for them — the tool itself never writes into the "
            "repository. Obey the returned remediation_prompt as the bounded work order. Do "
            "not widen beyond its listed findings, and do not invent or fabricate findings."
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

    authorized_roots = roots if roots is not None else allowed_roots()
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
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        "info": ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
    }
    _bind_tools(server, authorized_roots, annotations, Context)
    _bind_resources(server, authorized_roots, FunctionResource, ResourceSecurity)
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

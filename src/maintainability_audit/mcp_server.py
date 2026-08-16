"""Local, read-only MCP boundary for the deterministic audit.

The command-line application remains the product implementation. This module
adds transport and path authorization only: it calls the same configuration,
scan, report, renderer and remediation-prompt functions as the CLI. It never
accepts a command string, writes an artifact, edits source, or invokes a shell.
"""

from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from ._mcp_setup import (
    apply_answers,
    setup_pending,
    setup_questions,
    setup_schema,
)
from ._user_config import mark_repo_seen
from .config import (
    CONFIG_FILENAME,
    VERSION,
    analyzers_run_default,
    discovered_config,
    load_config,
)
from .git_tools import changed_paths, run_git
from .prompts import render_ai_prompt
from .renderers import render_markdown
from .report import build_report

ALLOWED_ROOTS_ENV = "MAINTAINABILITY_MCP_ALLOWED_ROOTS"
_REVSPEC = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@^~:+-]*(?:\.{2,3}[A-Za-z0-9._/@^~:+-]+)?")

SERVER_INSTRUCTIONS = (
    "Deterministic maintainability audits from a local stdio process on this "
    "machine — not a hosted service. Use audit_repository to produce both the "
    "report and its bounded remediation prompt. First contact with an "
    "unconfigured repository elicits setup and may write exactly three local "
    "artifacts: the repository's maintainability-agent.json, the user-level "
    "config, and the user state file. It never edits source, and it never "
    "writes a report into the tree — report text is returned for the host to "
    "show or save. Treat missing or insufficient evidence as an audit "
    "limitation, not a code defect, and do not widen remediation beyond "
    "findings in the returned prompt. Repository and config paths must remain "
    "inside the configured allowed roots."
)


class PathNotAllowed(ValueError):
    """A requested repository or config escaped the configured read boundary."""


def _resolved(path: str | Path, *, relative_to: Path | None = None) -> Path:
    candidate = Path(path).expanduser()
    if not candidate.is_absolute() and relative_to is not None:
        candidate = relative_to / candidate
    return candidate.resolve()


def allowed_roots(explicit: tuple[str, ...] = ()) -> tuple[Path, ...]:
    """Resolve the server allow-list once, defaulting to its launch directory."""
    configured = explicit or tuple(filter(None, os.environ.get(ALLOWED_ROOTS_ENV, "").split(os.pathsep)))
    roots = configured or (str(Path.cwd()),)
    return tuple(_resolved(root) for root in roots)


def _inside(path: Path, roots: tuple[Path, ...]) -> bool:
    return any(path == root or path.is_relative_to(root) for root in roots)


def authorize_repository(repository_root: str, roots: tuple[Path, ...]) -> Path:
    root = _resolved(repository_root)
    if not root.is_dir():
        raise ValueError(f"repository_root is not a directory: {root}")
    if not _inside(root, roots):
        allowed = ", ".join(str(item) for item in roots)
        raise PathNotAllowed(f"repository_root {root} is outside allowed roots: {allowed}")
    return root


def authorize_config(config_path: str | None, root: Path) -> str | None:
    if config_path is None:
        return None
    config = _resolved(config_path, relative_to=root)
    if not config.is_file():
        raise ValueError(f"config_path is not a file: {config}")
    if not (config == root or config.is_relative_to(root)):
        raise PathNotAllowed(f"config_path {config} is outside repository_root {root}")
    return str(config)


def validate_revspec(changed_only: str | None) -> str | None:
    """Admit one inert git revision expression, never command-line options."""
    if changed_only is None:
        return None
    if len(changed_only) > 200 or not _REVSPEC.fullmatch(changed_only):
        raise ValueError("changed_only must be one git revision or range without whitespace or options")
    return changed_only


def audit_repository(
    repository_root: str,
    config_path: str | None = None,
    changed_only: str | None = None,
    run_analyzers: bool | None = None,
    format: str | None = None,
    *,
    roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Run the production audit and return its report plus bounded work order.

    ``run_analyzers`` is tri-state (D1). ``None`` — the default — lets the
    repository's config decide, and a loaded config file defaults the pool
    on: the pool is the primary evidence source (ADR 006), and a caller
    should not need to know a flag to receive the product. Explicit
    ``True``/``False`` overrides for one call, in either direction.
    ``format`` follows the same rule: ``None`` takes the persisted default
    presentation from first-run setup (chat when nothing chose otherwise),
    and a per-call value always wins.

    A model reading this report is the reader the pool's findings were
    collected for — it can see what the scoring engine structurally
    cannot, which is why the default here follows the config rather than
    silently serving the six built-in detectors while the tools sit unused.
    """
    authorized_roots = roots if roots is not None else allowed_roots()
    root = authorize_repository(repository_root, authorized_roots)
    config = load_config(authorize_config(config_path, root) or discovered_config(root))
    revspec = validate_revspec(changed_only)
    only_paths = changed_paths(root, revspec) if revspec else None
    if run_analyzers is None:
        run_analyzers = analyzers_run_default(config)
    report = build_report(
        root, config,
        only_paths=only_paths,
        changed_revspec=revspec,
        run_analyzers=run_analyzers,
    )
    status = report.get("git_status_short", "")
    if format is None:
        format = (config.get("presentation") or {}).get("format") or "markdown"
    result = {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "source_commit": run_git(["rev-parse", "HEAD"], root) or None,
        "worktree_dirty": bool(status),
        "gate_passed": not report["hard_gate_failures"],
        # Stated at the top level so a caller cannot mistake an audit that
        # ran six built-in detectors for one that ran ten tools. Two
        # reports with different coverage are not comparable (P8).
        "analyzers_run": run_analyzers,
        "report": report,
        "report_markdown": render_markdown(report),
        "remediation_prompt": render_ai_prompt(report),
    }
    return _finish_result(result, format, root, config, report)


def _finish_result(result: dict[str, Any], format: str, root: Path,
                   config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Presentation, the degradation payload, and the first-contact record.

    8.5: the host asked the user which presentation and passes the answer
    here. HTML comes back as *text* for the host to save or show; files
    are the CLI's job (ADR 011 §4). Markdown is always present, because
    chat shows Markdown whatever else was requested — "chat" is accepted
    because the prompt itself offers it, and on the wire chat *is*
    Markdown (ADR 011 §2).
    """
    if format not in ("chat", "markdown", "html", "json"):
        raise ValueError(f"format must be chat, markdown, html or json, not {format!r}")
    if format == "html":
        from ._scan_history import DEFAULT_HISTORY_PATH, read_history
        from .renderers import render_html

        history = root / (config.get("paths", {}).get("history") or DEFAULT_HISTORY_PATH)
        result["report_html"] = render_html(report, read_history(history))
    result["format"] = format
    if setup_pending(root):
        # The host could not (or chose not to) elicit, and nothing is
        # configured: hand the same questions over as data so the host's
        # own question UI can ask and call again (D3's degradation rule).
        result["setup_needed"] = {"questions": setup_questions(load_config(None))}
    # First contact is now recorded whatever the gate said: "has this
    # tool ever run here" is about the run, not the verdict (D13).
    mark_repo_seen(root)
    return result


def server_info(roots: tuple[Path, ...] | None = None) -> dict[str, Any]:
    authorized_roots = roots if roots is not None else allowed_roots()
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "transport": "stdio",
        "local": True,
        # Not blanket read-only since D2: first-run setup writes exactly
        # these three local artifacts, never source and never a report.
        "read_only": False,
        "writes": [CONFIG_FILENAME, "user config", "user state"],
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
        persisted default from setup.
        """
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

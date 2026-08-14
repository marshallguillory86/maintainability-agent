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

from .config import VERSION, discovered_config, load_config
from .git_tools import changed_paths, run_git
from .prompts import render_ai_prompt
from .renderers import render_markdown
from .report import build_report

ALLOWED_ROOTS_ENV = "MAINTAINABILITY_MCP_ALLOWED_ROOTS"
_REVSPEC = re.compile(r"[A-Za-z0-9][A-Za-z0-9._/@^~:+-]*(?:\.{2,3}[A-Za-z0-9._/@^~:+-]+)?")

SERVER_INSTRUCTIONS = (
    "Read-only deterministic maintainability audits. Use audit_repository to produce both the "
    "report and its bounded remediation prompt. The tool never edits source or writes artifacts. "
    "Treat missing or insufficient evidence as an audit limitation, not a code defect, and do not "
    "widen remediation beyond findings in the returned prompt. Repository and config paths must "
    "remain inside the server's configured allowed roots."
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
    run_analyzers: bool = False,
    *,
    roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Run the production audit and return its report plus bounded work order.

    ``run_analyzers`` invokes the external analyzer pool (ADR 006), adding
    coverage, findings and measurements from the configured tools. Off by
    default to match the CLI: it costs seconds rather than milliseconds,
    and a caller polling for a gate result should not pay for it.

    Worth exposing here more than anywhere else, though. A model reading
    this report is the reader those findings were collected for -- it can
    see what the scoring engine structurally cannot, and without this flag
    it receives the six built-in detectors while ten tools sit unused.
    """
    authorized_roots = roots if roots is not None else allowed_roots()
    root = authorize_repository(repository_root, authorized_roots)
    config = load_config(authorize_config(config_path, root) or discovered_config(root))
    revspec = validate_revspec(changed_only)
    only_paths = changed_paths(root, revspec) if revspec else None
    report = build_report(
        root, config,
        only_paths=only_paths,
        changed_revspec=revspec,
        run_analyzers=run_analyzers,
    )
    status = report.get("git_status_short", "")
    return {
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


def server_info(roots: tuple[Path, ...] | None = None) -> dict[str, Any]:
    authorized_roots = roots if roots is not None else allowed_roots()
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "transport": "stdio",
        "read_only": True,
        "allowed_roots": [str(root) for root in authorized_roots],
    }


def _project_asset(relative: str) -> str:
    """Read one shipped project fact without accepting a caller-controlled path."""
    path = Path(__file__).resolve().parents[2] / relative
    return path.read_text(encoding="utf-8")


def _report_markdown(repository_root: str, roots: tuple[Path, ...]) -> str:
    """Render the same default report as the CLI, through the same path boundary."""
    root = authorize_repository(repository_root, roots)
    config = load_config(discovered_config(root))
    return render_markdown(build_report(root, config, run_analyzers=False))


def _bind_tools(server: Any, authorized_roots: tuple[Path, ...], read_only: Any) -> None:
    @server.tool(name="audit_repository", annotations=read_only, structured_output=True)
    def audit_repository_tool(
        repository_root: str,
        config_path: str | None = None,
        changed_only: str | None = None,
        run_analyzers: bool = False,
    ) -> dict[str, Any]:
        """Audit one authorized repository and return findings plus a bounded remediation prompt.

        Set ``run_analyzers`` to also run the external quality tools and
        receive their coverage, findings and measurements.
        """
        return audit_repository(
            repository_root,
            config_path,
            changed_only,
            run_analyzers,
            roots=authorized_roots,
        )

    @server.tool(name="get_agent_info", annotations=read_only, structured_output=True)
    def get_agent_info_tool() -> dict[str, Any]:
        """Return the installed agent version, transport and authorized repository roots."""
        return server_info(authorized_roots)


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
            "Call audit_repository for the repository. Obey the returned remediation_prompt "
            "as the bounded work order. Do not widen beyond its listed findings, and do not "
            "invent or fabricate findings."
        )


def create_server(*, roots: tuple[Path, ...] | None = None):
    """Create the SDK server; importing the base package does not require MCP."""
    try:
        from mcp.server import MCPServer
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
    read_only = ToolAnnotations(
        read_only_hint=True,
        destructive_hint=False,
        idempotent_hint=True,
        open_world_hint=False,
    )
    _bind_tools(server, authorized_roots, read_only)
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

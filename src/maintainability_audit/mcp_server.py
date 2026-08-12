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

from .config import VERSION, load_config
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
    *,
    roots: tuple[Path, ...] | None = None,
) -> dict[str, Any]:
    """Run the production audit and return its report plus bounded work order."""
    authorized_roots = roots if roots is not None else allowed_roots()
    root = authorize_repository(repository_root, authorized_roots)
    config = load_config(authorize_config(config_path, root))
    revspec = validate_revspec(changed_only)
    only_paths = changed_paths(root, revspec) if revspec else None
    report = build_report(root, config, only_paths=only_paths, changed_revspec=revspec)
    status = report.get("git_status_short", "")
    return {
        "agent": "maintainability-agent",
        "agent_version": VERSION,
        "source_commit": run_git(["rev-parse", "HEAD"], root) or None,
        "worktree_dirty": bool(status),
        "gate_passed": not report["hard_gate_failures"],
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


def create_server(*, roots: tuple[Path, ...] | None = None):
    """Create the SDK server; importing the base package does not require MCP."""
    try:
        from mcp.server import MCPServer
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
    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @server.tool(name="audit_repository", annotations=read_only, structured_output=True)
    def audit_repository_tool(
        repository_root: str,
        config_path: str | None = None,
        changed_only: str | None = None,
    ) -> dict[str, Any]:
        """Audit one authorized repository and return findings plus a bounded remediation prompt."""
        return audit_repository(
            repository_root,
            config_path,
            changed_only,
            roots=authorized_roots,
        )

    @server.tool(name="get_agent_info", annotations=read_only, structured_output=True)
    def get_agent_info_tool() -> dict[str, Any]:
        """Return the installed agent version, transport and authorized repository roots."""
        return server_info(authorized_roots)

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

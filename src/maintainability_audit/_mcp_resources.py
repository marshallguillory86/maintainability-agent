"""The MCP resources: the rubric, the catalog, and one report.

Split from ``mcp_server`` at this repository's own file-length gate, and
the seam is a real one — everything here answers a *read*. A resource
has no elicitation seam, so it can never ask a question; when it cannot
serve, it refuses and names the door that can (D30, D33).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ._mcp_audit import attach_history_views, authorize_repository
from ._mcp_grants import _RootLedger
from ._mcp_setup import SetupRequired, setup_pending
from ._scan_history import DEFAULT_HISTORY_PATH
from .config import discovered_config, load_config, repository_path
from .renderers import render_markdown
from .report import build_report


def _report_markdown(repository_root: str, roots: tuple[Path, ...]) -> str:
    """Render the same report as the CLI would, through the same path boundary.

    No ``run_analyzers`` argument on purpose: ``build_report`` resolves
    the tri-state from the config (D1). History views attach read-only
    — the resource reads the CLI's series and never appends a scan —
    so both doors render one stored series byte-identically (audit
    flag on dde539b).

    Setup is a precondition here too (D30). This resource reaches
    `build_report` directly, so D26's gate on the tool did not cover it,
    and an audit found it still serving the fallback-tier report for an
    unconfigured repository — the exact artefact D26 exists to prevent,
    on the same chat surface. A resource has no elicitation seam and
    cannot ask, so it refuses and says which door can.
    """
    root = authorize_repository(repository_root, roots)
    if setup_pending(root):
        raise SetupRequired(
            f"{root} has not been set up, so there is no report to read. "
            "Call the audit_repository tool: it returns the setup questions, "
            "and after they are answered a report exists to serve."
        )
    config = load_config(discovered_config(root))
    report = build_report(root, config)
    history_path = repository_path(
        root, (config.get("paths") or {}).get("history"), DEFAULT_HISTORY_PATH)
    attach_history_views(report, history_path, root)
    return render_markdown(report)


def _project_asset(name: str) -> str:
    """Read one shipped project fact without accepting a caller-controlled path.

    Resolved inside the package. The previous form climbed to the
    repository root, so both resource reads worked in a checkout and
    raised `FileNotFoundError` from every installed copy — the same
    defect that hid the analyzer catalog from nine releases.
    """
    path = Path(__file__).resolve().parent / "_assets" / name
    return path.read_text(encoding="utf-8")


def _authorized_root_security(ledger: _RootLedger, resource_security: Any) -> Any:
    """The allow-list check the report resource runs before it reads.

    Split from `_bind_resources` at this repository's own function-length
    gate. Reads never ask: a resource outside the boundary refuses, and
    only the audit tool can offer the D10 grant question, because a read
    has no elicitation seam and must not gain one.
    """

    class AuthorizedRootSecurity(resource_security):
        def validate(self, params: dict[str, Any]) -> str | None:
            from mcp.server.mcpserver.exceptions import ResourceError

            root = params.get("root")
            if not isinstance(root, str):
                return "root"
            try:
                authorize_repository(root, ledger.current())
            except ValueError as refusal:
                # Security runs before the resource function, so the
                # handler down there never sees this one. Wrapping only
                # the reader left every boundary refusal arriving as
                # "Internal server error" — the `--allow-root` remedy
                # discarded at the layer that knows it (D33).
                raise ResourceError(str(refusal)) from refusal
            return None

    return AuthorizedRootSecurity


def _bind_resources(
    server: Any,
    ledger: _RootLedger,
    function_resource: Any,
    resource_security: Any,
) -> None:
    root_security = _authorized_root_security(ledger, resource_security)

    @server.resource(
        "maintainability://standard",
        name="maintainability-standard",
        description="The applied maintainability rubric.",
        mime_type="text/markdown",
    )
    def standard_resource() -> str:
        return _project_asset("standard.md")

    @server.resource(
        "maintainability://catalog",
        name="analyzer-catalog",
        description="The shipped analyzer catalog and its provenance.",
        mime_type="application/json",
    )
    def catalog_resource() -> str:
        return _project_asset("analyzer-catalog.json")

    @server.resource(
        "maintainability://report/{+root}",
        name="maintainability-report",
        description="The production Markdown report for an authorized repository root.",
        mime_type="text/markdown",
        security=root_security(),
    )
    def report_resource(root: str) -> str:
        # Translated at the boundary, because a refusal nobody reads is
        # not a refusal. `SetupRequired` reached the client as a bare
        # -32603 "Error creating resource from template ..." — the
        # sentence naming the door that *can* ask survived only as
        # `__cause__` on the server side, where no user looks. D30
        # claimed this refusal named that door; the wire said otherwise
        # (D32). `ResourceError` is the SDK's own type and its message
        # is what the protocol carries.
        from mcp.server.mcpserver.exceptions import ResourceError

        try:
            return _report_markdown(root, ledger.current())
        except (SetupRequired, ValueError) as refusal:
            # Every refusal, not just the one an audit happened to name.
            # The first fix wrapped `SetupRequired` alone, so a root
            # outside the allow-list still reached the client as a bare
            # "Internal server error" — losing the `--allow-root`
            # sentence that tells the reader how to fix it. Refusing
            # deliberately and refusing by accident look identical on
            # the wire unless the message crosses (D33).
            #
            # `ValueError` covers the boundary refusals — `PathNotAllowed`
            # and `ConfigUnreadable` both derive from it, and
            # `authorize_repository` raises it plainly for a root that
            # is not a directory. An unexpected `ValueError` reaching a
            # reader as its own message is still better than reaching
            # them as "Internal server error".
            raise ResourceError(str(refusal)) from refusal

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

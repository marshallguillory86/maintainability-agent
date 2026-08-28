"""D44: the MCP annotations are derived from behaviour, not asserted at it.

The audit tool declared itself non-destructive and closed-world while
it rewrote configuration, replaced baselines, and — with acquisition
enabled — fetched a missing Node tool over the network. Two tests
locked those values, which is the whole lesson: test-backed
misinformation survives longer than an untested claim, because the
green suite is the reason nobody re-reads it.

So these tests do not restate the values. Each one names a fact that
lives somewhere else in the package and requires the annotation to
follow it, so changing the behaviour without changing the hint fails
here.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from maintainability_audit._catalog import DEFAULTS
from maintainability_audit.mcp_server import create_server, server_info


def _annotations(tmp_path: Path) -> dict[str, Any]:
    server = create_server(roots=(tmp_path.resolve(),))

    async def collect() -> dict[str, Any]:
        tools = await server.list_tools()
        return {tool.name: tool.annotations for tool in tools}

    return asyncio.run(collect())


def test_a_tool_that_writes_is_not_advertised_as_read_only(tmp_path: Path) -> None:
    """`server_info` lists what it writes; the hint must agree with that list."""
    writes = server_info(roots=(tmp_path.resolve(),))["writes"]
    assert writes, "server_info stopped naming what this agent writes"

    audit = _annotations(tmp_path)["audit_repository"]
    assert audit.read_only_hint is False, (
        f"the audit tool advertises read-only while server_info lists {writes}"
    )


def test_replacing_a_file_a_user_owns_is_advertised_as_destructive(
    tmp_path: Path,
) -> None:
    """Setup rewrites a configuration; `write_baseline` replaces a baseline.

    Both are non-additive updates to files in the user's repository,
    which is what this hint means. That only the agent's own five
    artifacts are ever touched (D34) is a real and separate guarantee —
    it is not the same claim as "additive".
    """
    writes = server_info(roots=(tmp_path.resolve(),))["writes"]
    replaceable = [name for name in writes if "config" in name or "baseline" in name]
    assert replaceable, (
        "this agent no longer writes a config or a baseline; if that is "
        "true the destructive hint should be revisited, not this list"
    )

    audit = _annotations(tmp_path)["audit_repository"]
    assert audit.destructive_hint is True, (
        f"the audit tool advertises additive-only while it replaces {replaceable}"
    )


def test_a_tool_that_can_reach_the_network_is_not_advertised_as_closed_world(
    tmp_path: Path,
) -> None:
    """Acquisition is opt-in, and an annotation cannot be opt-in.

    `analyzers.acquire_tools` exists, so a run *may* fetch a missing
    Node tool through `npx --yes`. Analyzers are also ordinary local
    children this package does not sandbox, which P1 discloses. A static
    hint has to describe what the tool may do, not what a default
    configuration happens to do.
    """
    assert "acquire_tools" in DEFAULTS, (
        "the acquisition setting is gone; if nothing can fetch any more, "
        "the open-world hint should be revisited here"
    )

    audit = _annotations(tmp_path)["audit_repository"]
    assert audit.open_world_hint is True, (
        "the audit tool advertises closed-world while analyzers.acquire_tools "
        "can fetch a missing tool and analyzer children are not sandboxed"
    )


def test_the_read_only_tool_is_still_read_only(tmp_path: Path) -> None:
    """The corrections above must not have been applied by blanket flip."""
    info = _annotations(tmp_path)["get_agent_info"]
    assert info.read_only_hint is True
    assert info.destructive_hint is False
    assert info.open_world_hint is False
    assert info.idempotent_hint is True

"""The local MCP boundary limits writes to setup, history and baseline state."""

from __future__ import annotations

import asyncio
import json
import subprocess
import sys
from pathlib import Path

import pytest

from maintainability_audit.config import VERSION
from maintainability_audit.mcp_server import (
    PathNotAllowed,
    audit_repository,
    authorize_config,
    authorize_repository,
    create_server,
    validate_revspec,
)


def _repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    # Configured on purpose. These tests are about what a completed audit
    # returns; an unconfigured repository returns setup questions and no
    # report at all, which is D26's precondition and a different subject.
    (root / "maintainability-agent.json").write_text(
        '{"version": 1, "analyzers": {"run": false}}', encoding="utf-8",
    )
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "start"],
        check=True,
    )
    return root


def test_audit_returns_the_report_without_writing_source_or_reports(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = {path.relative_to(root) for path in root.rglob("*")}

    result = audit_repository(
        str(root), format="json", roots=(tmp_path.resolve(),),
    )

    assert result["agent"] == "maintainability-agent"
    assert result["source_commit"]
    assert result["report"]["root"] == str(root.resolve())
    assert "Keep unrelated refactors out of scope." in result["remediation_prompt"]
    assert {path.relative_to(root) for path in root.rglob("*")} == before


def test_repository_must_stay_inside_an_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    with pytest.raises(PathNotAllowed, match="outside allowed roots"):
        authorize_repository(str(outside), (allowed.resolve(),))


def test_a_symlink_cannot_escape_the_allowed_root(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    link = allowed / "escape"
    link.symlink_to(outside, target_is_directory=True)

    with pytest.raises(PathNotAllowed):
        authorize_repository(str(link), (allowed.resolve(),))


def test_config_must_be_a_file_inside_the_repository(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    inside = root / "maintainability-agent.json"
    inside.write_text("{}", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")

    assert authorize_config("maintainability-agent.json", root) == str(inside.resolve())
    with pytest.raises(PathNotAllowed, match="outside repository_root"):
        authorize_config(str(outside), root)


@pytest.mark.parametrize("value", ["--stat", "HEAD~1 --output=/tmp/x", "HEAD\nmain", "", "a" * 201])
def test_changed_only_rejects_options_and_ambiguous_input(value: str) -> None:
    with pytest.raises(ValueError, match="git revision"):
        validate_revspec(value)


@pytest.mark.parametrize("value", ["HEAD~1", "main...HEAD", "release/1.2..HEAD", "abc123^", None])
def test_changed_only_accepts_one_inert_revision_expression(value: str | None) -> None:
    assert validate_revspec(value) == value


def test_a_client_sees_the_two_tools_and_can_call_one(tmp_path: Path) -> None:
    """The client's view, when a client can be constructed.

    Replaces `test_sdk_exposes_only_the_two_read_only_tools`, whose name
    asserted the old contract: "only two tools" stops being the claim
    once resources and prompts land, because those are *additional
    primitives*, not additional tools. What survives is that the tool
    surface is exactly these two and advertises each tool's real boundary —
    `test_the_two_tools_survive_the_new_primitives` holds that without a
    client, so this one may skip where `mcp.Client` cannot be imported
    and CI (which installs the `dev` extra) remains the source of truth.
    """
    Client = pytest.importorskip("mcp", reason="mcp SDK not importable here").Client

    root = _repo(tmp_path)
    server = create_server(roots=(tmp_path.resolve(),))

    async def exercise() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            by_name = {tool.name: tool for tool in tools.tools}
            assert set(by_name) == {"audit_repository", "get_agent_info"}
            assert by_name["audit_repository"].annotations is not None
            assert by_name["audit_repository"].annotations.read_only_hint is False
            assert by_name["get_agent_info"].annotations is not None
            assert by_name["get_agent_info"].annotations.read_only_hint is True
            for tool in by_name.values():
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.open_world_hint is False

            result = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "format": "json", "action": "run"},
            )
            assert not result.is_error
            assert result.structured_content["report"]["root"] == str(root.resolve())

    asyncio.run(exercise())


def test_real_stdio_process_initializes_and_reports_its_boundary(tmp_path: Path) -> None:
    """Exercise the installed transport, not only the in-memory SDK seam."""
    from mcp import Client, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def exercise() -> None:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "maintainability_audit.mcp_server", "--allow-root", str(tmp_path)],
        )
        async with Client(stdio_client(parameters)) as client:
            result = await client.call_tool("get_agent_info")
            assert not result.is_error
            info = result.structured_content
            assert info["agent"] == "maintainability-agent"
            assert info["agent_version"] == VERSION
            assert info["transport"] == "stdio"
            assert info["allowed_roots"] == [str(tmp_path.resolve())]
            assert info.get("read_only") is not True
            boundary = json.dumps(info).lower()
            assert len(info["writes"]) == 5
            assert "maintainability-agent.json" in boundary
            assert "user" in boundary and "config" in boundary and "state" in boundary
            assert ".maintainability/history.jsonl" in boundary
            assert ".maintainability/baseline.json" in boundary
            assert "source" in boundary and "report" in boundary

    asyncio.run(exercise())


# ---------------------------------------------------------------------------
# ADR 008 names three MCP primitives. One shipped.
# ---------------------------------------------------------------------------
#
# "The decision maps MCP's three primitives onto the requirement without
# inventing anything: a slash command *is* an MCP prompt, 'let the model
# read the rubric and scores' *is* MCP resources, and 'run the audit' *is*
# an MCP tool. Only the tool primitive shipped."
#
# The gap is not cosmetic. Markdown reaches chat today as a *field on a
# tool result*, which means a client that wants the report has to invoke
# an audit and dig it out of structured content. ADR 008's Markdown
# delivery clause says chat retrieves "the identical document as an MCP
# resource with a Markdown media type" — and holds one rendering as the
# rule: the chat summary may never contain a claim the file does not, and
# where they disagree the file is authoritative.
#
# These tests are written against that decision, so they fail today. Each
# assertion message names the missing primitive rather than a symptom.

RUBRIC_HINTS = ("rubric", "standard")
CATALOG_HINTS = ("catalog", "analyzer")
REPORT_HINTS = ("report", "markdown")


def _server(tmp_path: Path):
    return create_server(roots=(tmp_path.resolve(),))


def _resources(server) -> list:
    return asyncio.run(server.list_resources())


def _prompts(server) -> list:
    return asyncio.run(server.list_prompts())


def _read(server, uri: str) -> str:
    """The text of one resource, joined as a client would receive it."""
    contents = asyncio.run(server.read_resource(uri))
    return "".join(item.content for item in contents)


def _matching(resources: list, hints: tuple[str, ...]) -> list:
    return [
        item for item in resources
        if any(hint in f"{item.uri} {item.name or ''}".lower() for hint in hints)
    ]


def test_the_server_registers_resources_at_all(tmp_path: Path) -> None:
    """The class lint, asked of the live SDK server rather than a comment.

    A resources primitive that exists in the ADR and nowhere in the
    registry is the same shape of defect as `_bands.py`: a design point
    with a file and no caller.
    """
    resources = _resources(_server(tmp_path))

    assert resources, (
        "create_server registers no resources; ADR 008's resources primitive "
        "is unshipped, so a client can only reach the report by calling a tool"
    )


def test_the_server_registers_a_prompt_at_all(tmp_path: Path) -> None:
    """A slash command *is* an MCP prompt (ADR 008)."""
    prompts = _prompts(_server(tmp_path))

    assert prompts, (
        "create_server registers no prompts; ADR 008's prompts primitive is "
        "unshipped, so there is no slash command for this agent"
    )


def test_the_rubric_and_catalog_are_readable_without_an_audit(tmp_path: Path) -> None:
    """Reading what the tool believes must not require running it.

    "Let the model read the rubric and scores" is the whole point of the
    resources primitive: a model deciding whether to trust a finding needs
    the standard it was judged against, and making that cost a scan means
    it will be skipped.
    """
    resources = _resources(_server(tmp_path))

    assert _matching(resources, RUBRIC_HINTS), (
        f"no rubric/standard resource is registered; saw {[str(r.uri) for r in resources]}"
    )
    assert _matching(resources, CATALOG_HINTS), (
        f"no analyzer-catalog resource is registered; saw {[str(r.uri) for r in resources]}"
    )


def test_reading_the_rubric_and_catalog_writes_nothing(tmp_path: Path) -> None:
    """Read-only is a property of every primitive, not only of the tools."""
    server = _server(tmp_path)
    resources = _matching(_resources(server), RUBRIC_HINTS + CATALOG_HINTS)
    assert resources, "no rubric or catalog resource to read"

    before = {path for path in tmp_path.rglob("*")}
    for resource in resources:
        assert _read(server, str(resource.uri)).strip(), f"{resource.uri} read back empty"

    assert {path for path in tmp_path.rglob("*")} == before, (
        "reading a resource wrote to the tree"
    )


def test_a_report_resource_serves_markdown(tmp_path: Path) -> None:
    """ADR 008: "the identical document ... with a Markdown media type"."""
    resources = _matching(_resources(_server(tmp_path)), REPORT_HINTS)

    assert resources, (
        "no report resource is registered; Markdown reaches chat only as a "
        "field on the audit_repository tool result, which is the 6.3 gap"
    )
    assert any(item.mime_type == "text/markdown" for item in resources), (
        f"no report resource declares text/markdown; saw "
        f"{[(str(r.uri), r.mime_type) for r in resources]}"
    )


def test_the_report_resource_is_byte_identical_to_the_cli_rendering(tmp_path: Path) -> None:
    """One rendering is the rule. Two renderings are two claims.

    If the resource and the file ever disagree, the file is authoritative
    and the resource is the bug — so this compares them byte for byte
    rather than checking that both "look like" a report.
    """
    from maintainability_audit.cli import main

    root = _repo(tmp_path)
    server = _server(tmp_path)
    resources = _matching(_resources(server), REPORT_HINTS)
    assert resources, "no report resource to compare against the CLI rendering"

    uri = str(resources[0].uri).replace("{repository_root}", str(root)).replace(
        "{root}", str(root))
    output = tmp_path / "cli-report.md"
    assert main([
        "--root", str(root),
        "--no-analyzers",
        "--format", "markdown",
        "--output", str(output),
    ]) == 0
    served = _read(server, uri)
    expected = output.read_text(encoding="utf-8").removesuffix("\n")

    assert served == expected, (
        "the report resource is not the CLI rendering; ADR 008 requires the "
        "identical document, and where they disagree the file is authoritative"
    )


def test_a_report_resource_refuses_a_path_outside_the_allowed_roots(tmp_path: Path) -> None:
    """The path scope is a property of the server, not of one primitive.

    A resources primitive that reads any path on disk would be a second
    door into the same house with no lock on it.
    """
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.py").write_text("def hidden():\n    return 1\n", encoding="utf-8")

    server = create_server(roots=(allowed.resolve(),))
    resources = _matching(_resources(server), REPORT_HINTS)
    assert resources, "no report resource to test the path scope against"

    uri = str(resources[0].uri).replace("{repository_root}", str(outside)).replace(
        "{root}", str(outside))

    with pytest.raises(PathNotAllowed):
        _read(server, uri)


def test_the_slash_command_prompt_is_named_for_this_agent(tmp_path: Path) -> None:
    prompts = _prompts(_server(tmp_path))
    names = {prompt.name for prompt in prompts}

    assert names & {"maintainability-agent", "audit"}, (
        f"no slash-command prompt named maintainability-agent or audit; saw {sorted(names)}"
    )


def test_the_prompt_bounds_the_model_to_the_work_order(tmp_path: Path) -> None:
    """The prompt primitive carries the same bound the remediation prompt does.

    A slash command that says "audit this repo" and nothing else invites
    exactly the sprawling unreviewable diff the bounded prompt exists to
    prevent. It has to name the tool to call, name what bounds the work,
    and forbid both widening and invention.
    """
    server = _server(tmp_path)
    prompts = _prompts(server)
    named = [p for p in prompts if p.name in {"maintainability-agent", "audit"}]
    assert named, "no slash-command prompt to inspect"

    result = asyncio.run(server.get_prompt(named[0].name))
    text = " ".join(
        message.content.text if hasattr(message.content, "text") else str(message.content)
        for message in result.messages
    ).lower()

    assert "audit_repository" in text, "the prompt does not tell the model which tool to call"
    assert "remediation_prompt" in text or "work order" in text, (
        "the prompt does not name what bounds the work"
    )
    assert any(word in text for word in ("do not widen", "not widen", "beyond the listed",
                                         "past the listed")), (
        "the prompt does not forbid widening past the listed findings"
    )
    assert any(word in text for word in ("invent", "fabricat", "make up")), (
        "the prompt does not forbid inventing findings"
    )


def test_the_two_tools_survive_the_new_primitives(tmp_path: Path) -> None:
    """Replaces `test_sdk_exposes_only_the_two_read_only_tools`.

    "Only two tools" was the old contract and is the wrong assertion now:
    resources and prompts are *additional primitives*, not additional
    tools. What must hold is that the tool surface did not grow and that
    only the audit tool advertises the bounded config/state/history writes.
    """
    root = _repo(tmp_path)
    server = _server(tmp_path)

    async def exercise() -> None:
        tools = await server.list_tools()
        by_name = {tool.name: tool for tool in tools}
        assert set(by_name) == {"audit_repository", "get_agent_info"}, (
            f"the tool surface changed: {sorted(by_name)}"
        )
        assert by_name["audit_repository"].annotations is not None
        assert by_name["audit_repository"].annotations.read_only_hint is False
        assert by_name["get_agent_info"].annotations is not None
        assert by_name["get_agent_info"].annotations.read_only_hint is True
        for tool in by_name.values():
            assert tool.annotations.destructive_hint is False
            assert tool.annotations.open_world_hint is False

    asyncio.run(exercise())

    before = {path.relative_to(root) for path in root.rglob("*")}
    audit_repository(str(root), roots=(tmp_path.resolve(),))
    assert {path.relative_to(root) for path in root.rglob("*")} == before, (
        "an audit through the server wrote source or a report into the tree"
    )

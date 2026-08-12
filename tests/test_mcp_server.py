"""The local MCP boundary is read-only, path-scoped and uses production output."""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

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
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "-A"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "start"],
        check=True,
    )
    return root


def test_audit_returns_the_report_and_bounded_prompt_without_writing(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = {path.relative_to(root) for path in root.rglob("*")}

    result = audit_repository(str(root), roots=(tmp_path.resolve(),))

    assert result["agent"] == "maintainability-agent"
    assert result["source_commit"]
    assert result["report"]["root"] == str(root.resolve())
    assert result["report_markdown"].startswith("# Maintainability CI Report")
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


def test_sdk_exposes_only_the_two_read_only_tools(tmp_path: Path) -> None:
    from mcp import Client

    root = _repo(tmp_path)
    server = create_server(roots=(tmp_path.resolve(),))

    async def exercise() -> None:
        async with Client(server) as client:
            tools = await client.list_tools()
            by_name = {tool.name: tool for tool in tools.tools}
            assert set(by_name) == {"audit_repository", "get_agent_info"}
            for tool in by_name.values():
                assert tool.annotations is not None
                assert tool.annotations.read_only_hint is True
                assert tool.annotations.destructive_hint is False
                assert tool.annotations.open_world_hint is False

            result = await client.call_tool("audit_repository", {"repository_root": str(root)})
            assert not result.is_error
            assert result.structured_content["report"]["root"] == str(root.resolve())

    asyncio.run(exercise())

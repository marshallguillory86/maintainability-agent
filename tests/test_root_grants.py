"""D10 root grants at the MCP boundary.

Split verbatim from ``test_consent_and_grant.py`` when that contract
file crossed the repository's own size warn line; the four grant tests
and the helpers they use moved here unchanged.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest
from _mcp_fixtures import (
    _config,
    _contains_key,
    _grant_answer,
    _repo,
    _resource_text,
    _tool_text,
)

from maintainability_audit._user_config import user_config_path
from maintainability_audit.config import CONFIG_FILENAME
from maintainability_audit.mcp_server import (
    ALLOWED_ROOTS_ENV,
    PathNotAllowed,
    create_server,
    server_info,
)


def test_session_root_grant_is_default_and_lives_only_for_that_server(
    tmp_path: Path,
) -> None:
    """D10: the least-privilege grant extends one live allow-list, not config."""
    from mcp import Client

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    root = _repo(tmp_path / "outside", config=_config())
    calls: list[Any] = []

    async def answer(_context: Any, params: Any) -> Any:
        calls.append(params)
        return _grant_answer(params, "this session")

    async def exercise() -> list[Any]:
        server = create_server(roots=(allowed.resolve(),))
        results = []
        async with Client(server, elicitation_callback=answer) as client:
            for _ in range(2):
                results.append(await client.call_tool(
                    "audit_repository", {"repository_root": str(root), "format": "json"},
                ))
        return results

    results = asyncio.run(exercise())

    assert all(not result.is_error for result in results), _tool_text(results[0])
    assert len(calls) == 1, "the running process forgot its session grant"
    assert not user_config_path().exists()
    repository = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert not _contains_key(repository, "allowed_roots")


def test_always_root_grant_persists_only_to_the_user_tier_and_loads_at_startup(
    tmp_path: Path,
) -> None:
    """D10: an always grant survives a new server without entering repo policy."""
    from mcp import Client

    from maintainability_audit._user_config import load_user_config

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    root = _repo(tmp_path / "outside", config=_config())

    async def answer(_context: Any, params: Any) -> Any:
        return _grant_answer(params, "always")

    async def grant() -> Any:
        server = create_server(roots=(allowed.resolve(),))
        async with Client(server, elicitation_callback=answer) as client:
            return await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "format": "json"},
            )

    granted = asyncio.run(grant())

    assert not granted.is_error, _tool_text(granted)
    user = load_user_config()
    assert user is not None and _contains_key(user, "allowed_roots")
    assert str(root.resolve()) in json.dumps(user)
    repository = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    assert not _contains_key(repository, "allowed_roots")
    assert str(root.resolve()) in server_info()["allowed_roots"]

    async def use_persisted_grant() -> Any:
        async with Client(create_server()) as client:
            return await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "format": "json"},
            )

    reused = asyncio.run(use_persisted_grant())
    assert not reused.is_error, _tool_text(reused)


def test_denied_or_unsupported_root_grant_explains_both_static_remedies(
    tmp_path: Path,
) -> None:
    """D10: refusal remains bounded and teaches both noninteractive grant doors."""
    from mcp import Client

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    declined = _repo(tmp_path / "declined", config=_config())
    unsupported = _repo(tmp_path / "unsupported", config=_config())

    async def answer_no(_context: Any, params: Any) -> Any:
        return _grant_answer(params, "no")

    async def exercise() -> tuple[Any, Any]:
        server = create_server(roots=(allowed.resolve(),))
        async with Client(server, elicitation_callback=answer_no) as client:
            denied = await client.call_tool(
                "audit_repository", {"repository_root": str(declined)},
            )
        async with Client(server) as client:
            absent = await client.call_tool(
                "audit_repository", {"repository_root": str(unsupported)},
            )
        return denied, absent

    for result in asyncio.run(exercise()):
        assert result.is_error
        message = _tool_text(result)
        assert "outside" in message.lower() or "boundary" in message.lower()
        assert "--allow-root" in message
        assert ALLOWED_ROOTS_ENV in message


def test_report_resource_never_elicits_or_persists_a_root_grant(tmp_path: Path) -> None:
    """D10 grants belong to the tool; the report resource remains ask-free."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    root = _repo(tmp_path / "outside", config=_config())
    server = create_server(roots=(allowed.resolve(),))

    with pytest.raises(PathNotAllowed):
        _resource_text(server, root)

    assert not user_config_path().exists()

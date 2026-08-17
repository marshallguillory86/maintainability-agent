"""D2 re-ask semantics, moved verbatim from test_first_run_elicitation.

Split mechanically (2026-08-16, the standing precedent for contract
files that breach the repository's own gates): the source file crossed
the 500-line max after the D5 re-key. Every test and helper reference
is unchanged; shared helpers are imported from the original module.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import pytest
from test_first_run_elicitation import (
    _accepted_content,
    _assert_setup_needed,
    _repo,
)

from maintainability_audit._mcp_setup import setup_pending
from maintainability_audit._user_config import (
    load_user_config,
    mark_repo_seen,
    repo_first_run,
)
from maintainability_audit.config import CONFIG_FILENAME
from maintainability_audit.mcp_server import create_server


def test_seen_state_does_not_answer_first_run_questions(tmp_path: Path) -> None:
    """D13 records completed audits; only configuration answers D2 setup."""
    root = _repo(tmp_path)
    mark_repo_seen(root)
    assert repo_first_run(root) is False
    assert setup_pending(root) is True


@pytest.mark.parametrize("first_attempt", ["decline", "unsupported"])
def test_unanswered_setup_is_reelicited_until_answers_are_written(
    tmp_path: Path,
    first_attempt: str,
) -> None:
    from mcp import Client, types

    root = _repo(tmp_path)
    declined_calls: list[Any] = []
    accepted_calls: list[Any] = []

    async def decline(_context: Any, params: Any) -> Any:
        declined_calls.append(params)
        return types.ElicitResult(action="decline")

    async def accept(_context: Any, params: Any) -> Any:
        accepted_calls.append(params)
        return types.ElicitResult(
            action="accept",
            content=_accepted_content(params.requested_schema),
        )

    async def exercise() -> tuple[dict, dict]:
        server = create_server(roots=(tmp_path.resolve(),))
        if first_attempt == "decline":
            async with Client(server, elicitation_callback=decline) as client:
                first = await client.call_tool("audit_repository", {"repository_root": str(root)})
        else:
            async with Client(server) as client:
                first = await client.call_tool("audit_repository", {"repository_root": str(root)})
        assert not first.is_error

        async with Client(server, elicitation_callback=accept) as client:
            second = await client.call_tool("audit_repository", {"repository_root": str(root)})
        assert not second.is_error
        return first.structured_content, second.structured_content

    first, second = asyncio.run(exercise())

    _assert_setup_needed(first)
    assert len(declined_calls) == (1 if first_attempt == "decline" else 0)
    assert len(accepted_calls) == 1, "an unanswered first run must ask again"
    assert second["analyzers_run"] is True
    assert second["report"]["analyzer_coverage"] is not None
    assert "setup_needed" not in second
    assert (root / CONFIG_FILENAME).is_file()
    assert load_user_config() is not None
    assert repo_first_run(root) is False


def test_repeated_declines_keep_returning_the_same_setup_needed_block(
    tmp_path: Path,
) -> None:
    from mcp import Client, types

    root = _repo(tmp_path)
    calls: list[Any] = []

    async def decline(_context: Any, params: Any) -> Any:
        calls.append(params)
        return types.ElicitResult(action="decline")

    async def exercise() -> tuple[dict, dict]:
        server = create_server(roots=(tmp_path.resolve(),))
        async with Client(server, elicitation_callback=decline) as client:
            first = await client.call_tool("audit_repository", {"repository_root": str(root)})
            second = await client.call_tool("audit_repository", {"repository_root": str(root)})
        assert not first.is_error and not second.is_error
        return first.structured_content, second.structured_content

    first, second = asyncio.run(exercise())

    assert len(calls) == 2
    _assert_setup_needed(first)
    _assert_setup_needed(second)
    assert first["setup_needed"] == second["setup_needed"]
    assert repo_first_run(root) is False, "every completed audit still marks seen"



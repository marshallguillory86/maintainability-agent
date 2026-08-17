"""Closures for the verification audit on 6b2fb76 and decision 7.

Three commitments: a D10 grant authorizes exactly the directory the
question named, even if a symlink is retargeted during the elicitation
round-trip (TOCTOU residual); the user tier's full-replace writer keeps
exactly two merging callers, enforced structurally (lint the class);
and written history consent outranks the terminal on the CLI door
(decision 7 — config wins).
"""

from __future__ import annotations

import ast
import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit.config import CONFIG_FILENAME

SRC = Path(__file__).resolve().parents[1] / "src" / "maintainability_audit"


def _repo_at(root: Path, *, config: dict[str, Any] | None = None) -> Path:
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    if config is not None:
        (root / CONFIG_FILENAME).write_text(
            json.dumps(config) + "\n", encoding="utf-8",
        )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _two_repos_behind_a_link(tmp_path: Path) -> tuple[Path, Path, Path, Path]:
    """An allow-listed root plus two repos reachable through one symlink."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    config = {"version": 1, "analyzers": {"run": False}}
    first = _repo_at(tmp_path / "first" / "repo", config=config)
    second = _repo_at(tmp_path / "second" / "repo", config=config)
    link = tmp_path / "moving-link"
    link.symlink_to(first.parent)
    return allowed, first, second, link


def test_a_symlink_retargeted_mid_elicitation_invalidates_the_consent(
    tmp_path: Path,
) -> None:
    """TOCTOU: consent given to directory A must never authorize directory B.

    Two guards close the window together: the question names the
    resolved path (H2), and answers are matched to questions by a
    digest of the rendered request — so a retarget that changes the
    resolution changes the question, voids the recorded accept, and
    forces a fresh ask naming the new target. The grant itself then
    consumes the ledger's record of the ask rather than re-resolving.
    Outcome: neither directory is granted without completed consent.
    """
    from mcp import Client, types

    from maintainability_audit.mcp_server import create_server

    allowed, first, second, link = _two_repos_behind_a_link(tmp_path)
    requested = link / "repo"

    messages: list[str] = []

    async def retarget_then_accept(_context: Any, params: Any) -> Any:
        messages.append(params.message)
        if len(messages) > 1:
            # A refused call may be re-elicited for the moved target;
            # the user does not consent a second time.
            return types.ElicitResult(action="decline")
        link.unlink()
        link.symlink_to(second.parent)
        name = next(iter(params.requested_schema["properties"]))
        return types.ElicitResult(
            action="accept", content={name: "this session"},
        )

    async def exercise() -> tuple[Any, Any]:
        server = create_server(roots=(allowed.resolve(),))
        async with Client(
            server, elicitation_callback=retarget_then_accept,
        ) as client:
            audit = await client.call_tool(
                "audit_repository", {"repository_root": str(requested)},
            )
            info = await client.call_tool("get_agent_info", {})
        return audit, info

    audit, info = asyncio.run(exercise())

    assert str(first.resolve()) in messages[0], (
        "the question did not name the directory being consented to"
    )
    assert len(messages) > 1 and str(second.resolve()) in messages[1], (
        "the retarget did not invalidate the recorded consent"
    )
    roots = info.structured_content["allowed_roots"]
    assert str(first.resolve()) not in roots and str(second.resolve()) not in roots, (
        "a path was granted without a completed consent round"
    )
    assert audit.is_error, "the unconsented directory was silently served"


def _functions_calling(callee_name: str) -> set[str]:
    """Every `file:function` in src whose body calls `callee_name`."""
    callers: set[str] = set()
    for path in sorted(SRC.rglob("*.py")):
        for scope in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(scope, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names = (getattr(node.func, "id", getattr(node.func, "attr", None))
                         for node in ast.walk(scope) if isinstance(node, ast.Call))
                if callee_name in names:
                    callers.add(f"{path.name}:{scope.name}")
    return callers


def test_the_full_replace_writer_keeps_exactly_two_merging_callers() -> None:
    """Lint the class (audit H1 residual): a third caller reopens the wipe."""
    callers = _functions_calling("write_user_config")
    assert callers == {
        "_user_config.py:write_user_answers",
        "_user_config.py:persist_root_grant",
    }, (
        "write_user_config is a full replace; a new caller must merge the "
        f"other owner's keys first (found: {sorted(callers)})"
    )


@pytest.mark.parametrize(
    ("consent", "tty", "records"),
    [
        (False, True, False),   # written no beats the terminal
        (True, False, True),    # written yes records even headless
        (None, True, True),     # nothing written: the TTY rule stands
        (None, False, False),   # nothing written, headless: nothing
    ],
)
def test_cli_written_history_consent_outranks_the_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    consent: bool | None,
    tty: bool,
    records: bool,
) -> None:
    """Decision 7 (audit M3): both doors read consent the same way."""
    from maintainability_audit import cli
    from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH

    config: dict[str, Any] = {"version": 1, "analyzers": {"run": False}}
    if consent is not None:
        config["history"] = {"record": consent}
    root = _repo_at(tmp_path / "repo", config=config)
    monkeypatch.setattr(cli, "_stdin_is_a_tty", lambda: tty)

    assert cli.main(["--root", str(root), "--format", "json",
                     "--output", str(tmp_path / "out.json")]) == 0

    assert (root / DEFAULT_HISTORY_PATH).exists() is records

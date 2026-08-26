"""D10 grants and setup answers share one user tier without collisions.

Found by self-audit and the 413c761 hostile audit on the D9/D10 slice:
the user config has two owners — setup answers and standing root
grants — and each reader and writer must stay blind to the other's
keys without destroying them. Presence must not be read as an answer
(the repo's own recorded bug class), and persisting one owner's keys
must not erase the other's (audit H1). The grant question must name
the path the grant will actually authorize (audit H2).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit._mcp_setup import (
    apply_answers,
    setup_pending,
    setup_questions,
)
from maintainability_audit._user_config import (
    load_user_config,
    persist_root_grant,
    user_config_answers,
)
from maintainability_audit.config import load_config
from maintainability_audit.mcp_server import audit_repository, create_server


def test_grant_only_user_config_neither_answers_setup_nor_flips_the_pool(
    tmp_path: Path,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()

    persist_root_grant(tmp_path / "granted")

    assert load_user_config() is not None, "the grant itself must persist"
    assert user_config_answers() is None, "a grant is not a setup answer"
    assert setup_pending(repo), "an unconfigured repo must still be asked setup"
    assert load_config(None)["analyzers"]["run"] is False, (
        "a grant-only user tier flipped the pool default on"
    )


def test_first_run_setup_does_not_erase_a_standing_grant(tmp_path: Path) -> None:
    """Audit H1: "always" must survive the next first-run anywhere."""
    granted = tmp_path / "granted"
    persist_root_grant(granted)

    repo = tmp_path / "repo"
    repo.mkdir()
    answers = {
        question["name"]: question["default"]
        for question in setup_questions(load_config(None))
    }
    apply_answers(repo, answers)

    user = load_user_config()
    assert user is not None and user_config_answers() is not None
    assert str(granted) in json.dumps(user.get("allowed_roots", [])), (
        "first-run setup deleted a standing always-grant"
    )


def test_grant_question_names_the_resolved_target_of_a_symlink(
    tmp_path: Path,
) -> None:
    """Audit H2: the modal and the ledger must name the same directory."""
    from mcp import Client, types

    allowed = tmp_path / "allowed"
    allowed.mkdir()
    real = tmp_path / "real-target" / "repo"
    real.mkdir(parents=True)
    (real / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(real)], check=True)
    link = tmp_path / "innocent-link"
    link.symlink_to(real.parent)
    requested = link / "repo"
    messages: list[str] = []

    async def decline(_context: Any, params: Any) -> Any:
        messages.append(params.message)
        return types.ElicitResult(action="decline")

    async def exercise() -> None:
        server = create_server(roots=(allowed.resolve(),))
        async with Client(server, elicitation_callback=decline) as client:
            await client.call_tool(
                "audit_repository", {"repository_root": str(requested)},
            )

    import asyncio

    asyncio.run(exercise())

    assert messages, "an out-of-roots call with elicitation must ask"
    assert str(real.resolve()) in messages[0], (
        "the grant question hid the real directory behind the symlink"
    )


@pytest.mark.parametrize("format_name", ["json", "markdown", "html"])
def test_environment_work_order_reaches_every_format(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    format_name: str,
) -> None:
    """Audit M2: D9's remedy is top-level on the formats the contract skipped."""
    from maintainability_audit import _runner
    from maintainability_audit.config import CONFIG_FILENAME

    root = tmp_path / "repo"
    root.mkdir()
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / CONFIG_FILENAME).write_text(
        json.dumps({
            "version": 1,
            "analyzers": {"run": True, "allow_tools": ["lizard"],
                          "acquire_tools": False},
        }),
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    monkeypatch.setattr(_runner, "locate", lambda _executable: None)

    result = audit_repository(
        str(root), format=format_name, record_history=False,
        roots=(tmp_path.resolve(),),
    )

    order = result["environment_work_order"]
    assert order and all(item["concepts"] for item in order)


def test_a_standing_grant_does_not_follow_a_renamed_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D38: a restart rebuilt the allow-list from strings and re-resolved them.

    The in-process seam already refused this. `_RootLedger.consume_ask`
    surrenders the path the user was actually shown, so a symlink
    retargeted during the elicitation round-trip cannot swap the
    consented directory. A restart went around that guard entirely,
    because `allowed_roots` re-resolved the stored path — rename the
    granted directory, leave a symlink at the old name, and the
    allow-list followed it to somewhere nobody consented to.

    Reproduced before it was fixed: granting `project` and then swapping
    it put `secrets` in the allow-list.
    """
    import os

    from maintainability_audit import _mcp_audit

    base = tmp_path.resolve()
    granted = base / "project"
    granted.mkdir()
    secrets = base / "secrets"
    secrets.mkdir()
    (secrets / "id_rsa").write_text("KEY\n", encoding="utf-8")
    launch = base / "launch"
    launch.mkdir()

    monkeypatch.setattr(
        _mcp_audit, "load_user_config", lambda: {"allowed_roots": [str(granted)]})

    kept = _mcp_audit.allowed_roots(explicit=(str(launch),))
    assert granted in kept, "an untouched standing grant must survive a restart"

    granted.rename(base / "project-moved")
    os.symlink(secrets, granted)

    after = _mcp_audit.allowed_roots(explicit=(str(launch),))
    assert secrets not in after, (
        "the standing grant followed a symlink to a directory the user "
        "never consented to"
    )
    assert granted not in after, (
        "a grant whose path stopped naming what was granted must be "
        "dropped, not honoured against the link"
    )
    assert launch in after, "the launch root must be unaffected"


def test_a_grant_under_a_symlinked_parent_survives_a_restart(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D38 reopened: the fix dropped every ordinary macOS grant.

    The predicate honoured a stored grant only when its path contained
    no symlink in any component. `/tmp` and `/var` are symlinks on
    macOS and every `tempfile` directory sits under one, so a grant
    recorded as `/tmp/work` was dropped on every start and the person
    who said "always" was asked again forever — the inverse of the
    defect the entry set out to close.

    The original closing test could not see it: it resolved the path
    before storing, so it only ever exercised a canonical entry.

    The symlinked parent is built here rather than borrowed from the
    platform. The first version of this test asserted that `/tmp` is a
    link, which is true on macOS and false on Linux, so it passed
    locally and hard-failed in CI — a platform fact asserted where a
    constructed fixture was needed.
    """
    import os

    from maintainability_audit import _mcp_audit

    real = tmp_path / "real"
    real.mkdir()
    (real / "work").mkdir()
    (real / "elsewhere").mkdir()

    link = tmp_path / "link"
    os.symlink(real, link)
    granted = link / "work"
    assert granted.resolve() != granted, "the fixture's parent is not a symlink"

    monkeypatch.setattr(
        _mcp_audit, "load_user_config", lambda: {"allowed_roots": [str(granted)]})

    roots = _mcp_audit.allowed_roots(explicit=(str(tmp_path),))
    assert granted.resolve() in roots, (
        "a grant whose parent is a symlink was dropped, which on macOS is "
        f"every grant under /tmp or /var: {roots}"
    )

    # And the swap it exists to refuse is still refused: replace the
    # granted directory itself with a link somewhere else.
    (real / "work").rmdir()
    os.symlink(real / "elsewhere", real / "work")

    after = _mcp_audit.allowed_roots(explicit=(str(tmp_path),))
    assert (real / "elsewhere").resolve() not in after, (
        f"the grant followed a symlink planted at the granted name: {after}"
    )

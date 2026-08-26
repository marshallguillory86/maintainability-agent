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


def test_a_non_canonical_grant_is_refused_and_said_so(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D38, third rule: canonical or refused, and never in silence.

    The first rule required a canonical path and dropped every ordinary
    macOS grant, because `/tmp` and `/var` are symlinks there. The
    second honoured a non-canonical entry unless the granted path was
    itself a link — and an audit walked through it by retargeting the
    *parent*, one directory above the leaf that rule checked.

    There is no third rule available. A bare path with no record of
    what it resolved to when granted cannot be defended: nothing to
    compare against means nothing to detect. So the product persists
    resolved paths, which are checkable, and a hand-written entry that
    is not canonical is refused — and named in `server_info`, because
    dropping grants in silence is what made the first rule hard to see.
    """
    import os

    from maintainability_audit import _mcp_audit

    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "work").mkdir()
    secrets = tmp_path / "secrets"
    secrets.mkdir()
    (secrets / "work").mkdir()
    link = tmp_path / "link"
    os.symlink(outer, link)

    monkeypatch.setattr(
        _mcp_audit, "load_user_config",
        lambda: {"allowed_roots": [str(link / "work")]})

    roots = _mcp_audit.allowed_roots(explicit=(str(tmp_path),))
    assert (outer / "work").resolve() not in roots, (
        "a non-canonical grant was honoured; its parent can be retargeted "
        "and nothing here could tell"
    )

    refused = _mcp_audit.refused_root_grants()
    assert [item["entry"] for item in refused] == [str(link / "work")], (
        f"the refusal was silent, which is the defect that hid rule one: {refused}"
    )
    assert "canonical" in refused[0]["reason"]
    # The repair names the flow, never the resolved target. An earlier
    # version returned the canonical path as `write_instead`, which was
    # the friendlier message and also told whatever host reads
    # `server_info` where a symlink the user named actually points --
    # a directory the user never put in their config. D48's rule is
    # that host paths do not cross the transport, and a helpful refusal
    # is not an exception to it.
    assert "setup" in refused[0]["repair"]
    leaked = str((outer / "work").resolve())
    assert all(leaked not in str(value) for value in refused[0].values()), (
        f"the refusal disclosed the symlink's target: {refused[0]}"
    )

    # The attack the entry was reopened for: retarget the parent.
    link.unlink()
    os.symlink(secrets, link)
    after = _mcp_audit.allowed_roots(explicit=(str(tmp_path),))
    assert (secrets / "work").resolve() not in after, (
        "retargeting the parent of a stored grant extended the allow-list"
    )


def test_a_grant_the_product_made_is_canonical_and_survives(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The path a user actually takes, which must not be collateral.

    `persist_root_grant` resolves before storing, so an "always" grant
    made through the elicitation is canonical and honoured — including
    when the directory sits under a symlinked parent, which on macOS is
    every temporary directory.
    """
    import os

    from maintainability_audit import _mcp_audit
    from maintainability_audit._user_config import persist_root_grant

    outer = tmp_path / "outer"
    outer.mkdir()
    (outer / "work").mkdir()
    link = tmp_path / "link"
    os.symlink(outer, link)

    stored: dict[str, list[str]] = {}
    monkeypatch.setattr(
        "maintainability_audit._user_config.load_user_config", lambda: dict(stored))
    monkeypatch.setattr(
        "maintainability_audit._user_config.write_user_config",
        lambda payload: stored.update(payload))

    # Granted by the spelling a host would hand over: through the link.
    persist_root_grant(link / "work")
    assert stored["allowed_roots"] == [str((outer / "work").resolve())], (
        "the grant was stored as written rather than resolved, so it cannot "
        "be checked later"
    )

    monkeypatch.setattr(_mcp_audit, "load_user_config", lambda: dict(stored))
    roots = _mcp_audit.allowed_roots(explicit=(str(tmp_path),))
    assert (outer / "work").resolve() in roots, (
        "a grant the product itself made was dropped on the next start"
    )
    assert not _mcp_audit.refused_root_grants()

"""D30: every door onto a report obeys the setup precondition.

D26 gated the audit tool. An audit then walked the other doors and
found the gate was one door wide: the MCP report resource reached
`build_report` directly and served the fallback-tier report for an
unconfigured repository — the exact artefact D26 exists to prevent, on
the same chat surface. Two smaller holes sat beside it: a completed
audit still carried `setup_needed`, and an empty `{}` config counted as
"configured" because the check was `is_file()`.

The lesson is the shape of this file. A precondition asserted at one
call site is a precondition on that call site; these tests enumerate
the doors instead, so a new one cannot quietly skip the gate.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._mcp_setup import SetupRequired, setup_pending
from maintainability_audit.mcp_server import _report_markdown, audit_repository


def _repo(base: Path) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok(v):\n    return v\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def test_the_report_resource_refuses_an_unconfigured_repository(
    tmp_path: Path,
) -> None:
    """The High an audit found: a report, unasked, on the chat surface.

    The resource has no elicitation seam, so it cannot ask — which is
    the reason it must refuse rather than fall back. A refusal that
    names the door which *can* ask costs the reader one call; a
    fallback-tier grade costs them a wrong decision.
    """
    root = _repo(tmp_path)

    with pytest.raises(SetupRequired) as refusal:
        _report_markdown(str(root), (tmp_path.resolve(),))

    message = str(refusal.value)
    assert "audit_repository" in message, (
        "the refusal does not name the door that can ask the questions"
    )
    assert str(root) in message


def test_an_explicit_config_path_audits_without_carrying_setup_questions(
    tmp_path: Path,
) -> None:
    """A finished audit and a request for setup cannot both be true.

    `config_path` is the caller supplying the configuration the
    precondition asks for, so the audit runs. The payload used to arrive
    with `setup_needed` attached anyway — `audit_ran: true` beside a
    demand to configure, which is D26's shape surviving on the one path
    that bypasses its gate.
    """
    root = _repo(tmp_path)
    (root / "explicit.json").write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8",
    )

    result = audit_repository(
        str(root), config_path="explicit.json", action=None,
        record_history=False, roots=(tmp_path.resolve(),),
    )

    assert result["audit_ran"] is True
    assert "setup_needed" not in result, (
        "a completed audit asked the caller to complete setup"
    )


def test_a_config_file_with_no_answers_in_it_is_not_configured(
    tmp_path: Path,
) -> None:
    """Answers end setup, not the existence of a file.

    `discovered_config` is an `is_file()` check, so `{}` ended setup and
    the repository was treated as configured while nobody had answered
    anything. The audit that followed used built-in defaults and called
    itself configured.
    """
    root = _repo(tmp_path)

    for contentless in ("{}", "   \n"):
        (root / "maintainability-agent.json").write_text(contentless, encoding="utf-8")
        if contentless.strip():
            assert setup_pending(root) is True, (
                f"{contentless!r} as a config ended setup without any answers"
            )

    (root / "maintainability-agent.json").write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8",
    )
    assert setup_pending(root) is False, "real answers did not end setup"


def test_the_cli_refuses_an_unreadable_config_in_its_own_idiom(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """One repository state must not produce two experiences (D32).

    The MCP tool and resource refused a truncated config by name while
    the CLI let a raw `JSONDecodeError` traceback out — and the CLI is
    the door people run unattended, where a traceback is the least
    useful thing that can happen. An audit found the split.
    """
    from maintainability_audit.cli import main

    root = _repo(tmp_path)
    (root / "maintainability-agent.json").write_text('{"version": 1', encoding="utf-8")

    with pytest.raises(SystemExit) as exit_status:
        main(["--root", str(root), "--format", "json"])

    message = str(exit_status.value)
    assert "maintainability-agent.json" in message, (
        f"the CLI refusal does not name the file to repair: {message!r}"
    )
    assert "JSONDecodeError" not in message or "cannot be read as JSON" in message


def test_an_unreadable_config_refuses_the_same_way_through_every_door(
    tmp_path: Path,
) -> None:
    """One broken file, one answer — whichever door you came in by (D32).

    An audit found three answers to one repository state: the MCP tool
    and resource refused by name, the CLI leaked a `JSONDecodeError`
    traceback, and a caller passing `config_path` got the same raw
    error because supplying a config skips the setup gate entirely.
    Loading moved behind one helper so the doors cannot drift again.
    """
    from maintainability_audit.config import ConfigUnreadable, load_config

    root = _repo(tmp_path)
    broken = root / "broken.json"
    broken.write_text('{"version": 1', encoding="utf-8")

    with pytest.raises(ConfigUnreadable) as direct:
        load_config(str(broken))
    assert "broken.json" in str(direct.value)

    with pytest.raises(ConfigUnreadable):
        audit_repository(
            str(root), config_path="broken.json", action="run",
            record_history=False, roots=(tmp_path.resolve(),),
        )

    # A JSON document that parses but is not an object is unreadable
    # too: a list has no configuration in it.
    broken.write_text("[1, 2, 3]", encoding="utf-8")
    with pytest.raises(ConfigUnreadable):
        load_config(str(broken))


def test_an_unreadable_repository_config_refuses_at_the_setup_check(
    tmp_path: Path,
) -> None:
    """Neither configured nor unconfigured — and it must say so.

    A truncated or hand-edited file used to surface a `JSONDecodeError`
    from somewhere deeper in the call, which tells the reader nothing
    actionable. It fails closed either way; the difference is whether
    the message names the file and what to do about it.
    """
    from maintainability_audit.config import ConfigUnreadable

    root = _repo(tmp_path)
    config = root / "maintainability-agent.json"

    # `ConfigUnreadable`, not a setup-specific error: the setup check
    # and the loader now share one parser, so one broken file cannot
    # mean "ask the questions" on one door and "refuse" on another. An
    # audit found a JSON array doing exactly that (D33).
    for unreadable in ('{"version": 1', "[1, 2, 3]", '"a string"'):
        config.write_text(unreadable, encoding="utf-8")
        with pytest.raises(ConfigUnreadable) as refusal:
            setup_pending(root)
        assert "maintainability-agent.json" in str(refusal.value), unreadable


def test_the_resource_refusal_survives_the_protocol(tmp_path: Path) -> None:
    """A refusal the client cannot read is not a refusal (D32).

    D30 closed the report resource and the entry said it "refuses and
    names the door that can ask". On the wire it did not: the SDK
    turned `SetupRequired` into a bare -32603 with the message "Error
    creating resource from template ...", and the sentence naming
    `audit_repository` survived only as `__cause__` on the server side,
    where no user looks. The register was making a claim about
    user-visible behaviour that an audit disproved by reading the wire.

    Asserted through a real client rather than by catching the
    exception in-process, because in-process is exactly where the old
    behaviour looked correct.
    """
    import asyncio
    import logging

    from mcp import Client

    from maintainability_audit.mcp_server import create_server

    root = _repo(tmp_path)

    async def exercise() -> list[str]:
        async with Client(create_server(roots=(tmp_path.resolve(),))) as client:
            try:
                await client.read_resource(f"maintainability://report/{root}")
            except Exception as raised:  # noqa: BLE001 - the wire shape is the subject
                return [str(item) for item in getattr(raised, "exceptions", [raised])]
        return []

    logging.disable(logging.CRITICAL)
    try:
        messages = asyncio.run(exercise())
    finally:
        logging.disable(logging.NOTSET)

    assert messages, "the resource served something for an unconfigured repository"
    joined = " ".join(messages)
    assert "audit_repository" in joined, (
        f"the refusal reached the client without naming the door that can "
        f"ask: {joined[:200]}"
    )


def test_every_resource_refusal_reaches_the_client_with_its_remedy(
    tmp_path: Path,
) -> None:
    """Not just the refusal an audit happened to name (D33).

    The first fix wrapped `SetupRequired` alone, so a root outside the
    allow-list still arrived as a bare "Internal server error" — losing
    the `--allow-root` sentence that tells the reader what to do. On the
    wire, a deliberate refusal and an unexpected crash looked identical.
    Every refusal this resource can raise is checked, because "the one
    we thought of" is how the first version passed.
    """
    import asyncio
    import logging

    from mcp import Client

    from maintainability_audit.mcp_server import create_server

    unconfigured = _repo(tmp_path)
    outside = tmp_path.parent / "outside-the-roots"
    outside.mkdir(exist_ok=True)
    not_a_directory = unconfigured / "README.md"

    cases = {
        str(unconfigured): "audit_repository",   # setup pending
        str(outside): "allow",                   # boundary, names the remedy
        str(not_a_directory): "director",        # not a repository at all
    }

    async def refusal_for(target: str) -> str:
        async with Client(create_server(roots=(tmp_path.resolve(),))) as client:
            try:
                await client.read_resource(f"maintainability://report/{target}")
            except Exception as raised:  # noqa: BLE001 - the wire shape is the subject
                return " ".join(
                    str(item) for item in getattr(raised, "exceptions", [raised])
                )
        return ""

    logging.disable(logging.CRITICAL)
    try:
        for target, expected in cases.items():
            message = asyncio.run(refusal_for(target))
            assert message, f"{target} served content instead of refusing"
            assert "Internal server error" not in message, (
                f"{target} refused as an internal error, telling the reader "
                f"nothing: {message[:120]}"
            )
            assert expected in message.lower(), (
                f"{target} refused without naming the remedy "
                f"({expected!r}): {message[:160]}"
            )
    finally:
        logging.disable(logging.NOTSET)


def test_run_never_overrides_the_setup_precondition(tmp_path: Path) -> None:
    """`action="run"` says when, not whether there is anything to run.

    An audit found the docstring claiming this default was how the CLI
    and the report resource skip the gate. Neither calls this function,
    and the precondition outranks the action regardless: an unconfigured
    repository returns questions however emphatically it is told to run.
    """
    root = _repo(tmp_path)

    for action in (None, "run", "reconfigure"):
        result = audit_repository(
            str(root), action=action, record_history=False,
            roots=(tmp_path.resolve(),),
        )
        assert result["audit_ran"] is False, f"action={action!r} audited unconfigured"
        assert "setup_needed" in result, f"action={action!r} did not ask"

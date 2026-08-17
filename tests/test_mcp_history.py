"""D5/D6: the MCP audit participates in the durable remediation loop."""

from __future__ import annotations

import asyncio
import inspect
import json
import subprocess
from dataclasses import replace
from pathlib import Path
from typing import Any

from maintainability_audit._calibration import CALIBRATION_C
from maintainability_audit._identity import finding_fingerprints
from maintainability_audit._scan_history import (
    DEFAULT_HISTORY_PATH,
    append_scan,
    read_history,
    record_of,
)
from maintainability_audit._work_order import prompt_targets
from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME, VERSION, load_config
from maintainability_audit.mcp_server import (
    SERVER_INSTRUCTIONS,
    audit_repository,
    create_server,
    server_info,
)


def _repo(base: Path, *, history: str | None = None) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    config: dict[str, Any] = {"version": 1, "analyzers": {"run": False}}
    if history is not None:
        config["paths"] = {"history": history}
    (root / CONFIG_FILENAME).write_text(json.dumps(config), encoding="utf-8")
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    body = "".join(f"    value_{line} = value + {line}\n" for line in range(90))
    (root / "hot.py").write_text(
        f"def huge(value):\n{body}    return value\n",
        encoding="utf-8",
    )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(
        ["git", "-C", str(root), "add", CONFIG_FILENAME, "README.md", "hot.py"],
        check=True,
    )
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            "fixture",
        ],
        check=True,
    )
    return root


def _history_path(root: Path) -> Path:
    config = load_config(str(root / CONFIG_FILENAME))
    relative = config.get("paths", {}).get("history") or DEFAULT_HISTORY_PATH
    return root / relative


def _audit(root: Path, **kwargs: Any) -> dict[str, Any]:
    return audit_repository(
        str(root),
        roots=(root.parent.resolve(),),
        **kwargs,
    )


def _head(root: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit_tracked(root: Path, message: str) -> str:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qam",
            message,
        ],
        check=True,
    )
    return _head(root)


def _commit_staged(root: Path, message: str) -> str:
    subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "-c",
            "user.email=t@t",
            "-c",
            "user.name=t",
            "commit",
            "-qm",
            message,
        ],
        check=True,
    )
    return _head(root)


def test_existing_history_appends_on_a_plain_mcp_call(tmp_path: Path) -> None:
    """The file's existence remains the standing answer on the chat path."""
    root = _repo(tmp_path)
    history = _history_path(root)
    _audit(root, record_history=True)
    first = history.read_bytes()

    result = _audit(root)

    records = read_history(history)
    assert history.read_bytes().startswith(first), "MCP rewrote an append-only history"
    assert len(records) == 2
    assert result["report"]["scan_history"][-1]["scans"] == 2


def test_elicitation_capable_first_call_starts_the_mcp_history(tmp_path: Path) -> None:
    """Client elicitation capability is the chat equivalent of the CLI's TTY."""
    from mcp import Client, types

    root = _repo(tmp_path)
    elicitation_calls: list[Any] = []

    async def answer(_context: Any, params: Any) -> Any:
        elicitation_calls.append(params)
        return types.ElicitResult(action="decline")

    async def exercise() -> None:
        server = create_server(roots=(tmp_path.resolve(),))
        async with Client(server, elicitation_callback=answer) as client:
            result = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root)},
            )
            assert not result.is_error

    asyncio.run(exercise())

    assert not elicitation_calls, "a configured repository must not reopen setup"
    assert len(read_history(_history_path(root))) == 1


def test_headless_first_call_does_not_create_mcp_history(tmp_path: Path) -> None:
    """No history and no interactive client means no new write."""
    root = _repo(tmp_path)
    parameter = inspect.signature(audit_repository).parameters["record_history"]
    assert parameter.default is None, "history follows the established tri-state pattern"

    _audit(root)

    assert not _history_path(root).exists()


def test_record_history_tristate_overrides_both_directions(tmp_path: Path) -> None:
    """True starts and False suppresses through the registered MCP tool."""
    from mcp import Client

    root = _repo(tmp_path, history="records/scans.jsonl")
    history = _history_path(root)
    untouched = _repo(tmp_path / "off")

    async def exercise() -> None:
        server = create_server(roots=(tmp_path.resolve(),))
        async with Client(server) as client:
            started = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "record_history": True},
            )
            assert not started.is_error
            suppressed = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "record_history": False},
            )
            assert not suppressed.is_error
            never_started = await client.call_tool(
                "audit_repository",
                {"repository_root": str(untouched), "record_history": False},
            )
            assert not never_started.is_error

    asyncio.run(exercise())

    assert len(read_history(history)) == 1
    assert not (root / DEFAULT_HISTORY_PATH).exists(), "paths.history was ignored"
    assert not _history_path(untouched).exists()


def test_mcp_history_records_the_delivered_prompt_targets(tmp_path: Path) -> None:
    """Every MCP audit delivers a prompt, so advice given must be remembered."""
    root = _repo(tmp_path)

    result = _audit(root, record_history=True)

    targets = prompt_targets(result["report"])
    stored = read_history(_history_path(root))[0]
    assert targets, "the fixture produced no bounded remediation target"
    assert stored.targeted == targets
    assert set(stored.targeted) <= set(stored.fingerprints)
    delivered = result["remediation_prompt"]
    targeted_items = [
        item
        for item in result["report"]["work_order"]
        if item.get("fingerprint") in targets
    ]
    assert targeted_items
    assert all(item["title"] in delivered for item in targeted_items)


# Split mechanically (2026-08-16, standing precedent for contract
# helpers that breach the repo's own warn line): the seeding function
# measured 64 lines. Each clear/return step moved verbatim into
# `_clear_step` / `_return_step`; values and order unchanged.
def _clear_step(root: Path, base, message: str, stamp: str):
    readme = root / "README.md"
    readme.write_text(readme.read_text(encoding="utf-8") + f"\n{message}\n", encoding="utf-8")
    commit = _commit_tracked(root, f"{message} synthetic clear")
    return replace(base, recorded_at=stamp, commit=commit,
                   fingerprints=(), identities=(), targeted=())


def _return_step(root: Path, source: str, target: str, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "mv", source, target], check=True)
    _commit_staged(root, message)


def _seed_cleared_then_returned_series(root: Path) -> str:
    config = load_config(str(root / CONFIG_FILENAME))

    def snapshot(*, targeted: bool = False):
        report = _audit(root, record_history=False)["report"]
        targets = prompt_targets(report)
        assert targets, "the recurrence fixture produced no prompt target"
        target = targets[0]
        record = record_of(
            report,
            config,
            VERSION,
            CALIBRATION_C,
            tuple(sorted(finding_fingerprints(report))),
            targeted=targets if targeted else (),
        )
        identity = next(
            item for item in record.identities if item["fingerprint"] == target
        )
        return record, target, identity

    first, original_target, _ = snapshot(targeted=True)

    first_clear = _clear_step(root, first, "clear one", "2026-08-16T12:00:01Z")
    _return_step(root, "hot.py", "moved.py", "first return through rename")
    first_return, _, _ = snapshot()

    second_clear = _clear_step(root, first_return, "clear two", "2026-08-16T12:00:03Z")
    _return_step(root, "moved.py", "returned.py", "second return through rename")
    second_return, _, _ = snapshot()

    history = _history_path(root)
    for record in (first, first_clear, first_return, second_clear, second_return):
        append_scan(history, record)
    return original_target


def test_mcp_report_exposes_history_and_design_review_candidates(
    tmp_path: Path,
) -> None:
    """The report carries both the trend and the stopped nit-loop."""
    root = _repo(tmp_path)
    target = _seed_cleared_then_returned_series(root)

    result = _audit(root)

    report = result["report"]
    assert report["scan_history"][-1]["scans"] == 6
    candidate = next(
        item for item in report["design_review_candidates"]
        if item["fingerprint"] == target
    )
    assert candidate["returns"] == 2
    assert candidate["targeted"] is True


def test_cli_and_mcp_reports_agree_over_the_same_history(tmp_path: Path) -> None:
    """Two entry points read one durable series into identical loop evidence."""
    root = _repo(tmp_path)
    _seed_cleared_then_returned_series(root)
    output = tmp_path / "cli.json"
    assert main(
        [
            "--root",
            str(root),
            "--no-analyzers",
            "--format",
            "json",
            "--output",
            str(output),
        ]
    ) == 0
    cli_report = json.loads(output.read_text(encoding="utf-8"))

    mcp_report = _audit(root, record_history=False)["report"]

    assert mcp_report["scan_history"] == cli_report["scan_history"]
    assert (
        mcp_report["design_review_candidates"]
        == cli_report["design_review_candidates"]
    )


def test_server_discloses_the_four_artifact_write_boundary(tmp_path: Path) -> None:
    """History joins setup state; source and report writes remain forbidden."""
    info = server_info((tmp_path.resolve(),))
    writes = info["writes"]
    disclosure = f"{SERVER_INSTRUCTIONS}\n{json.dumps(info, sort_keys=True)}".lower()

    assert len(writes) == 4
    assert any("history" in str(item).lower() for item in writes)
    assert DEFAULT_HISTORY_PATH in disclosure
    assert "source" in " ".join(info["never_writes"]).lower()
    assert "report" in " ".join(info["never_writes"]).lower()

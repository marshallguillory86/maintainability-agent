"""D9/D10 and the recorded history-consent decisions at the MCP boundary."""

from __future__ import annotations

import ast
import asyncio
import inspect
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit import _mcp_audit, _runner, cli, mcp_server
from maintainability_audit._mcp_setup import apply_answers, setup_questions
from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit._user_config import load_user_config, user_config_path
from maintainability_audit.baseline import findings_not_in_baseline
from maintainability_audit.cli import main
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.mcp_server import (
    ALLOWED_ROOTS_ENV,
    SERVER_INSTRUCTIONS,
    PathNotAllowed,
    audit_repository,
    create_server,
    server_info,
)
from maintainability_audit.renderers import render_markdown


def _large_function(name: str) -> str:
    body = "".join(f"    value_{line} = value + {line}\n" for line in range(90))
    return f"def {name}(value):\n{body}    return value\n"


def _repo(base: Path, *, config: dict[str, Any] | None = None) -> Path:
    root = base / "repo"
    root.mkdir(parents=True)
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "hot.py").write_text(_large_function("huge"), encoding="utf-8")
    if config is not None:
        (root / CONFIG_FILENAME).write_text(
            json.dumps(config, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    _commit(root, "fixture")
    return root


def _commit(root: Path, message: str) -> None:
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-qm", message,
        ],
        check=True,
    )


def _config(*, run: bool = False, record: bool | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "version": 1,
        "analyzers": {
            "run": run,
            "allow_tools": ["lizard"],
            "acquire_tools": False,
        },
    }
    if record is not None:
        payload["history"] = {"record": record}
    return payload


def _audit(root: Path, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("format", "json")
    return audit_repository(str(root), roots=(root.parent.resolve(),), **kwargs)


def _resource_text(server: Any, root: Path) -> str:
    resources = asyncio.run(server.list_resources())
    template = next(
        item for item in resources
        if item.name == "maintainability-report-template"
    )
    uri = str(template.uri).replace("{repository_root}", str(root)).replace(
        "{root}", str(root),
    )
    contents = asyncio.run(server.read_resource(uri))
    return "".join(item.content for item in contents)


def _tool_text(result: Any) -> str:
    return " ".join(
        getattr(item, "text", str(item)) for item in (result.content or [])
    )


def _grant_answer(params: Any, choice: str) -> Any:
    from mcp import types

    properties = params.requested_schema["properties"]
    assert len(properties) == 1, "a roots grant must be one structured question"
    name, field = next(iter(properties.items()))
    assert set(field["enum"]) == {"this session", "always", "no"}
    assert field["default"] == "this session"
    return types.ElicitResult(action="accept", content={name: choice})


def _contains_key(payload: Any, key: str) -> bool:
    if not isinstance(payload, dict):
        return False
    return key in payload or any(_contains_key(value, key) for value in payload.values())


def test_missing_analyzers_surface_a_top_level_environment_work_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """D9: a chat payload exposes actionable missing evidence outside its one body."""
    root = _repo(tmp_path, config=_config(run=True))
    monkeypatch.setattr(_runner, "locate", lambda _executable: None)

    result = audit_repository(
        str(root), format="chat", record_history=False,
        roots=(tmp_path.resolve(),),
    )

    assert result["analyzers_run"] is True
    assert "report" not in result, "D8 keeps the report dictionary JSON-only"
    order = result["environment_work_order"]
    assert order, "a selected, unavailable analyzer produced no host-visible remedy"
    for item in order:
        assert item["tool"]
        assert item["install"]
        assert item["concepts"], "the host cannot explain what installing the tool restores"
    instruction = SERVER_INSTRUCTIONS.lower()
    assert "environment_work_order" in instruction
    assert "surface" in instruction or "show" in instruction


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


def _history_answers(choice: str) -> dict[str, Any]:
    questions = setup_questions(load_config(None))
    answers = {question["name"]: question["default"] for question in questions}
    answers["record_scan_history"] = choice
    return answers


def test_setup_asks_for_history_consent_and_persists_it_to_both_tiers(
    tmp_path: Path,
) -> None:
    """Decision 4: history is a disclosed yes-default choice, not capability inference."""
    questions = setup_questions(load_config(None))
    question = next(
        item for item in questions if item["name"] == "record_scan_history"
    )
    assert question["options"] == ["yes", "no"]
    assert question["default"] == "yes"

    root = _repo(tmp_path)
    merged = apply_answers(root, _history_answers("no"))
    repository = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    user = load_user_config()
    assert user is not None
    for payload in (repository, user, merged):
        assert payload["history"]["record"] is False


@pytest.mark.parametrize(("answer", "records"), [("yes", 1), ("no", 0)])
def test_history_consent_drives_the_accepting_call(
    tmp_path: Path,
    answer: str,
    records: int,
) -> None:
    """The accepted setup answer, not MCP capability, starts the first series."""
    from mcp import Client, types

    root = _repo(tmp_path)

    async def accept(_context: Any, params: Any) -> Any:
        content = {
            name: field.get("default")
            for name, field in params.requested_schema["properties"].items()
        }
        content["record_scan_history"] = answer
        return types.ElicitResult(action="accept", content=content)

    async def exercise() -> None:
        async with Client(
            create_server(roots=(tmp_path.resolve(),)),
            elicitation_callback=accept,
        ) as client:
            result = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "format": "json"},
            )
            assert not result.is_error, _tool_text(result)

    asyncio.run(exercise())

    history = root / DEFAULT_HISTORY_PATH
    actual = len(read_history(history)) if history.exists() else 0
    assert actual == records


def test_persisted_history_consent_precedes_the_standing_file_rule(
    tmp_path: Path,
) -> None:
    """None uses consent for a new series, while an existing series still appends."""
    enabled = _repo(tmp_path / "enabled", config=_config(record=True))
    _audit(enabled)
    assert len(read_history(enabled / DEFAULT_HISTORY_PATH)) == 1

    disabled = _repo(tmp_path / "disabled", config=_config(record=False))
    _audit(disabled)
    assert not (disabled / DEFAULT_HISTORY_PATH).exists()

    _audit(disabled, record_history=True)
    _audit(disabled)
    assert len(read_history(disabled / DEFAULT_HISTORY_PATH)) == 2


def test_tool_binding_does_not_upgrade_history_from_client_capability() -> None:
    """Decision 4 replaces the capability trigger; it does not wrap it."""
    source = inspect.getsource(mcp_server._bind_audit_tool)
    assert "record_history = True" not in source


def test_slash_prompt_uses_structured_presentation_choice_with_chat_default(
    tmp_path: Path,
) -> None:
    """D3: the slash command delegates its ask to structured host UI."""
    server = create_server(roots=(tmp_path.resolve(),))
    prompt = asyncio.run(server.get_prompt("maintainability-agent"))
    text = " ".join(
        item.content.text if hasattr(item.content, "text") else str(item.content)
        for item in prompt.messages
    ).lower()

    assert "ask the user which presentation" not in text
    assert "chat" in text and ("default" in text or "pre-selected" in text)
    assert "elicitation" in text or "question ui" in text or "structured" in text


def test_analyzer_enabled_resource_matches_cli_and_chat_matches_json_render(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Audit M1/M2: configured-on parity and one renderer through both tool doors."""
    root = _repo(tmp_path, config=_config(run=True))
    monkeypatch.setattr(_runner, "locate", lambda _executable: None)
    monkeypatch.setattr(cli, "_stdin_is_a_tty", lambda: False)
    output = tmp_path / "cli.md"

    assert main([
        "--root", str(root), "--format", "markdown", "--output", str(output),
    ]) == 0
    served = _resource_text(create_server(roots=(tmp_path.resolve(),)), root)
    assert "Analyzer Coverage" in served and "lizard" in served
    assert served.encode() == output.read_bytes().removesuffix(b"\n")

    json_result = _audit(root, format="json", record_history=False)
    chat_result = _audit(root, format="chat", record_history=False)
    assert json_result["analyzers_run"] is chat_result["analyzers_run"] is True
    assert chat_result["report_markdown"] == render_markdown(json_result["report"])


def test_baseline_results_are_exclusive_and_self_consult_is_empty(tmp_path: Path) -> None:
    """Audit L3/L5: new_findings is exactly the v3 difference, including self-write."""
    root = _repo(tmp_path, config=_config())
    written = _audit(root, write_baseline=True, record_history=False)
    assert written["new_findings"] == []

    (root / "new.py").write_text(_large_function("new_huge"), encoding="utf-8")
    _commit(root, "new finding")
    result = _audit(root, record_history=False)
    baseline = root / ".maintainability/baseline.json"
    expected = sorted(
        identity.fingerprint
        for identity in findings_not_in_baseline(
            result["report"], str(baseline), root,
        )
    )

    assert expected
    assert result["new_findings"] == expected


def test_mcp_boundary_docstrings_describe_the_five_artifact_payload_contract() -> None:
    """Audit L1/L4: comments cannot resurrect four writes or universal Markdown."""
    server_source = Path(mcp_server.__file__).read_text(encoding="utf-8")
    module_doc = ast.get_docstring(ast.parse(server_source)) or ""
    assert "five" in module_doc.lower() and "baseline" in module_doc.lower()
    assert "exactly these four" not in server_source.lower()

    finish_doc = inspect.getdoc(_mcp_audit._finish_result) or ""
    assert "markdown is always present" not in finish_doc.lower()
    assert "json" in finish_doc.lower() and "html" in finish_doc.lower()

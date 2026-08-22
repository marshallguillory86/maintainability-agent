"""D2/D3/D11: first contact over local MCP is structured and persistent."""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from maintainability_audit._mcp_setup import (
    apply_answers,
    maybe_elicit_setup,
    setup_questions,
)
from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit._user_config import (
    load_user_config,
    repo_first_run,
    user_config_path,
    user_state_path,
)
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.mcp_server import (
    SERVER_INSTRUCTIONS,
    audit_repository,
    create_server,
    server_info,
)


def _repo(tmp_path: Path, *, config: dict | None = None, readme: bool = True) -> Path:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    if readme:
        (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    if config is not None:
        (root / CONFIG_FILENAME).write_text(json.dumps(config), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        [
            "git", "-C", str(root), "-c", "user.email=t@t",
            "-c", "user.name=t", "commit", "-qm", "fixture",
        ],
        check=True,
    )
    return root


def _write_user_config(payload: dict) -> None:
    path = user_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _question_text(question: dict) -> str:
    return f"{question['name']} {question['prompt']} {json.dumps(question['options'])}".lower()


def _named_question(questions: list[dict], kind: str) -> dict:
    predicates = {
        "pool": lambda text: "pool" in text or ("analyzer" in text and "run" in text),
        "depth": lambda text: "depth" in text,
        "license": lambda text: "license" in text,
        "economics": lambda text: any(word in text for word in ("economic", "labor", "cost")),
        "format": lambda text: any(word in text for word in ("format", "presentation")),
    }
    return next(question for question in questions if predicates[kind](_question_text(question)))


def _normalized(value: Any) -> str:
    return str(value).strip().lower().replace("_", "-")


def test_setup_questions_are_structured_choices_with_disclosed_defaults() -> None:
    questions = setup_questions(load_config(None))

    assert questions
    assert len({question["name"] for question in questions}) == len(questions)
    for question in questions:
        assert {"name", "prompt", "options", "default"} <= question.keys()
        assert question["prompt"].strip()
        assert question["options"]
        assert question["default"] is not None

    pool = _named_question(questions, "pool")
    pool_prompt = pool["prompt"].lower()
    assert _normalized(pool["default"]) in {"yes", "true"}
    assert "primary evidence" in pool_prompt
    assert "built-in" in pool_prompt and "always" in pool_prompt
    assert "fallback" in pool_prompt
    assert "built-ins only" in pool_prompt or "built-in detectors only" in pool_prompt
    assert "fallback-tier" in pool_prompt or "fallback tier" in pool_prompt

    assert _normalized(_named_question(questions, "depth")["default"]) == "moderate"
    assert _normalized(_named_question(questions, "license")["default"]) == "permissive"
    assert _normalized(_named_question(questions, "format")["default"]) == "chat"

    economics = [
        question for question in questions
        if any(word in _question_text(question) for word in ("economic", "labor", "cost"))
    ]
    economics_contract = json.dumps(economics).lower()
    for word in ("low", "base", "high", "skip"):
        assert word in economics_contract


class StubElicitContext:
    def __init__(self, action: str = "decline", answers: dict | None = None) -> None:
        self.action = action
        self.answers = answers
        self.calls: list[tuple[tuple[Any, ...], dict[str, Any]]] = []

    async def elicit(self, *args: Any, **kwargs: Any) -> SimpleNamespace:
        self.calls.append((args, kwargs))
        return SimpleNamespace(
            action=self.action,
            data=self.answers,
            content=self.answers,
        )


@pytest.mark.parametrize(
    ("repo_config", "user_config", "expected_calls"),
    (
        (False, False, 1),
        (True, False, 0),
        (False, True, 0),
        (True, True, 0),
    ),
)
def test_setup_triggers_only_when_both_configuration_tiers_are_absent(
    tmp_path: Path,
    repo_config: bool,
    user_config: bool,
    expected_calls: int,
) -> None:
    root = _repo(tmp_path, config={"version": 1} if repo_config else None)
    if user_config:
        _write_user_config({"version": 1})
    context = StubElicitContext()
    assert repo_first_run(root) is True

    result = asyncio.run(maybe_elicit_setup(context, root))

    assert result is None
    assert len(context.calls) == expected_calls


def _answers_for(questions: list[dict], *, economics: bool) -> dict:
    answers: dict[str, Any] = {}
    for question in questions:
        text = _question_text(question)
        if any(word in text for word in ("economic", "labor", "cost")):
            if not economics:
                answers[question["name"]] = "skip"
            elif all(word in text for word in ("low", "base", "high")):
                answers[question["name"]] = {"low": 90, "base": 140, "high": 210}
            elif "low" in text:
                answers[question["name"]] = 90
            elif "base" in text:
                answers[question["name"]] = 140
            elif "high" in text:
                answers[question["name"]] = 210
            else:
                answers[question["name"]] = "include"
            continue
        answers[question["name"]] = question["default"]
    return answers


def _has_persisted_chat_default(payload: Any, path: tuple[str, ...] = ()) -> bool:
    if not isinstance(payload, dict):
        return False
    for key, value in payload.items():
        here = (*path, str(key).lower())
        if value == "chat" and any(
            token in component for component in here
            for token in ("format", "presentation", "report")
        ):
            return True
        if _has_persisted_chat_default(value, here):
            return True
    return False


def _assert_persisted_answers(payload: dict) -> None:
    analyzers = payload["analyzers"]
    assert analyzers["run"] is True or _normalized(analyzers["run"]) == "yes"
    assert analyzers["depth"] == "moderate"
    assert analyzers["license_policy"] == "permissive"
    assert payload["economic_context"]["loaded_engineering_cost_per_hour"] == {
        "low": 90,
        "base": 140,
        "high": 210,
    }
    assert _has_persisted_chat_default(payload)


def test_apply_answers_persists_economics_and_format_to_both_tiers(
    tmp_path: Path,
) -> None:
    root = _repo(tmp_path)
    questions = setup_questions(load_config(None))
    merged = apply_answers(root, _answers_for(questions, economics=True))
    repository = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    user = load_user_config()

    assert user is not None
    for payload in (repository, user, merged):
        _assert_persisted_answers(payload)


def test_declining_economics_omits_the_block_from_both_tiers(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    questions = setup_questions(load_config(None))
    merged = apply_answers(root, _answers_for(questions, economics=False))
    repository = json.loads((root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    user = load_user_config()

    assert user is not None
    for payload in (repository, user, merged):
        assert "economic_context" not in payload


# Split mechanically (2026-08-16, precedent: Marshall's standing go on
# contract helpers that breach the repo's own complexity gate): the
# original single function measured CCN 17 against the budget of 15.
# Every branch and value is verbatim; only the function boundary moved.
def _preferred_for(text: str, field: dict[str, Any]) -> Any:
    if "pool" in text or ("analyzer" in text and "run" in text):
        return True
    if "depth" in text:
        return "moderate"
    if "license" in text:
        return "permissive"
    if "format" in text or "presentation" in text:
        return "chat"
    if any(word in text for word in ("economic", "labor", "cost")):
        if "low" in text:
            return 90
        if "base" in text:
            return 140
        if "high" in text:
            return 210
        return "skip"
    return field.get("default")


def _coerced(preferred: Any, field: dict[str, Any]) -> Any:
    choices = field.get("enum") or []
    if choices:
        for choice in choices:
            if _normalized(choice) == _normalized(preferred):
                return choice
        return field.get("default", choices[0])
    if field.get("type") == "boolean":
        return bool(preferred)
    if field.get("type") == "integer":
        return int(preferred or 0)
    if field.get("type") == "number":
        return float(preferred or 0)
    return preferred if preferred is not None else ""


def _value_for_schema_field(name: str, field: dict[str, Any]) -> Any:
    text = f"{name} {field.get('title', '')} {field.get('description', '')}".lower()
    return _coerced(_preferred_for(text, field), field)


def _accepted_content(requested_schema: dict[str, Any]) -> dict[str, Any]:
    return {
        name: _value_for_schema_field(name, field)
        for name, field in requested_schema.get("properties", {}).items()
    }


def test_one_native_elicitation_configures_and_then_asks_before_auditing(
    tmp_path: Path,
) -> None:
    """D27: setup answers configure the agent; they do not start an audit.

    This test used to be named for the opposite contract — answers
    applied "to that same audit" — and that was the behaviour: a host
    that could be elicited was asked the setup questions and handed a
    finished report in the same call. Running is a separate decision
    from configuring, and the user makes both. The elicitation still
    happens exactly once; what it produces is a configured repository
    and the run-or-reconfigure choice.
    """
    from mcp import Client, types

    root = _repo(tmp_path)
    source_before = (root / "app.py").read_bytes()
    tree_before = {
        path.relative_to(root) for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }
    calls: list[Any] = []

    async def answer(_context: Any, params: Any) -> Any:
        calls.append(params)
        return types.ElicitResult(
            action="accept",
            content=_accepted_content(params.requested_schema),
        )

    async def exercise() -> tuple[dict, dict]:
        server = create_server(roots=(tmp_path.resolve(),))
        async with Client(server, elicitation_callback=answer) as client:
            first = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "format": "json"},
            )
            assert not first.is_error
            second = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "action": "run"},
            )
            assert not second.is_error
            return first.structured_content, second.structured_content

    first, second = asyncio.run(exercise())

    assert len(calls) == 1, "first-run setup must be one structured question set"
    # Configured by the elicitation, and then asked rather than audited.
    assert first["audit_ran"] is False
    assert "report" not in first, "answering setup started an audit nobody asked for"
    assert first["choice_needed"]["options"] == ["run", "reconfigure"]
    assert "setup_needed" not in first, "answers were taken and the questions repeated"

    # Only the explicit go produces a report, and the persisted default
    # presentation governs it.
    assert second["audit_ran"] is True
    assert second["analyzers_run"] is not None
    assert second["format"] == "chat"
    assert "report_markdown" in second
    assert "setup_needed" not in second
    assert repo_first_run(root) is False
    assert user_config_path().is_file()
    assert user_state_path().is_file()
    assert (root / "app.py").read_bytes() == source_before
    tree_after = {
        path.relative_to(root) for path in root.rglob("*")
        if ".git" not in path.relative_to(root).parts
    }
    assert tree_after - tree_before == {
        Path(CONFIG_FILENAME),
        Path(DEFAULT_HISTORY_PATH).parent,
        Path(DEFAULT_HISTORY_PATH),
    }
    # One record from two calls: configuring is not scanning, so the
    # setup call recorded no history. Two would mean an audit ran that
    # the user never asked for (D27).
    assert len(read_history(root / DEFAULT_HISTORY_PATH)) == 1


def _forbids(text: str, noun: str) -> bool:
    return bool(re.search(rf"(?:never|does not|cannot)[^.\n]{{0,100}}\b{noun}\b", text, re.I))


def test_server_discloses_the_local_five_artifact_write_boundary(
    tmp_path: Path,
) -> None:
    info = server_info((tmp_path.resolve(),))
    disclosure = f"{SERVER_INSTRUCTIONS}\n{json.dumps(info, sort_keys=True)}"
    lowered = disclosure.lower()

    assert "local" in lowered and "stdio" in lowered
    assert info.get("read_only") is not True
    assert len(info["writes"]) == 5
    assert CONFIG_FILENAME in disclosure
    assert "user" in lowered and "config" in lowered and "state" in lowered
    assert DEFAULT_HISTORY_PATH in disclosure
    assert ".maintainability/baseline.json" in disclosure
    assert _forbids(disclosure, "source")
    assert _forbids(disclosure, "report")

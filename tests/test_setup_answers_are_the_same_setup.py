"""A host that cannot elicit still submits the setup the host was shown.

The public tool schema is the contract here.  Private resolver parameters
cannot be the answer path for a host that only sees ``list_tools()``.
"""

from __future__ import annotations

import asyncio
import json
import re
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit._mcp_setup import (
    economics_bound_questions,
    setup_questions,
)
from maintainability_audit._mcp_setup import (
    test_command_questions as published_test_command_questions,
)
from maintainability_audit._user_config import load_user_config
from maintainability_audit.config import CONFIG_FILENAME, load_config
from maintainability_audit.mcp_server import SERVER_INSTRUCTIONS, create_server


@pytest.fixture(autouse=True)
def isolated_user_tier(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "xdg-config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "xdg-state"))


def _repository(base: Path, name: str) -> Path:
    root = base / name
    root.mkdir()
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "module.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _tool_schema(root: Path) -> dict[str, Any]:
    async def collect() -> dict[str, Any]:
        tools = await create_server(roots=(root.parent.resolve(),)).list_tools()
        return next(tool for tool in tools if tool.name == "audit_repository").input_schema

    return asyncio.run(collect())


def _question_names(root: Path) -> dict[str, set[str]]:
    """The population is the questions production publishes, not a test list."""
    population = {
        "first": {question["name"] for question in setup_questions(load_config(None))},
        "rates": {question["name"] for question in economics_bound_questions()},
        "command": {question["name"] for question in published_test_command_questions(root)},
    }
    assert all(population.values()), "the derived setup-question population is empty"
    return population


def _answers(questions: list[dict[str, Any]], **overrides: Any) -> dict[str, Any]:
    return {
        question["name"]: overrides.get(question["name"], question["default"])
        for question in questions
    }


def _call(root: Path, answers: dict[str, Any]) -> dict[str, Any]:
    async def submit() -> dict[str, Any]:
        server = create_server(roots=(root.parent.resolve(),))
        from mcp import Client

        async with Client(server) as client:
            response = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "setup_answers": answers},
            )
            assert not response.is_error, response.content
            return response.structured_content

    return asyncio.run(submit())


def test_list_tools_exposes_only_the_host_submit_answer_path(tmp_path: Path) -> None:
    """A field merely named ``setup`` is not a public answer path."""
    properties = _tool_schema(_repository(tmp_path, "schema"))["properties"]

    assert "setup_answers" in properties
    assert {"setup", "grant", "ctx"}.isdisjoint(properties), properties


def test_submitted_economics_and_test_answers_advance_the_derived_stages(
    tmp_path: Path,
) -> None:
    economics_root = _repository(tmp_path, "economics")
    questions = _question_names(economics_root)
    first = _call(
        economics_root,
        _answers(setup_questions(load_config(None)), economics="include"),
    )
    assert {question["name"] for question in first["setup_needed"]["questions"]} == questions["rates"]

    configured = _call(
        economics_root,
        {"labor_low": "90", "labor_base": "140", "labor_high": "210"},
    )
    assert "setup_needed" not in configured
    assert configured["choice_needed"]["options"] == ["run", "reconfigure"]
    repository = json.loads((economics_root / CONFIG_FILENAME).read_text(encoding="utf-8"))
    user = load_user_config()
    assert user is not None
    for payload in (repository, user):
        assert payload["economic_context"]["loaded_engineering_cost_per_hour"] == {
            "low": 90.0, "base": 140.0, "high": 210.0,
        }

    command_root = _repository(tmp_path, "command")
    command_questions = _question_names(command_root)
    test_stage = _call(
        command_root,
        _answers(setup_questions(load_config(None)), run_tests="yes"),
    )
    assert {question["name"] for question in test_stage["setup_needed"]["questions"]} == command_questions["command"]


@pytest.mark.parametrize(
    ("question", "invalid"),
    (("depth", "nuclear"), ("default_format", "pdf")),
)
def test_host_submissions_refuse_values_outside_the_published_questions(
    tmp_path: Path, question: str, invalid: str,
) -> None:
    root = _repository(tmp_path, question)
    published = setup_questions(load_config(None))
    assert question in {item["name"] for item in published}

    async def submit() -> None:
        server = create_server(roots=(root.parent.resolve(),))
        from mcp import Client

        async with Client(server) as client:
            response = await client.call_tool(
                "audit_repository",
                {"repository_root": str(root), "setup_answers": _answers(published, **{question: invalid})},
            )
            assert response.is_error, response.structured_content

    asyncio.run(submit())
    assert not (root / CONFIG_FILENAME).exists(), "an invalid answer was written"


def test_every_call_again_instruction_names_the_public_answer_path(tmp_path: Path) -> None:
    root = _repository(tmp_path, "instructions")
    setup_reply = _call_without_answers(root)
    surfaces = {
        "SERVER_INSTRUCTIONS": SERVER_INSTRUCTIONS,
        "setup_instruction": setup_reply["setup_instruction"],
        "installed SKILL.md": (Path(__file__).parents[1] / "src/maintainability_audit/_skill_data/SKILL.md").read_text(encoding="utf-8"),
        "repository SKILL.md": (Path(__file__).parents[1] / "skills/maintainability-agent/SKILL.md").read_text(encoding="utf-8"),
        "first-run help": (Path(__file__).parents[1] / "docs/help/first-run.md").read_text(encoding="utf-8"),
    }
    call_again = {name: text for name, text in surfaces.items() if re.search(r"\bcall again\b", text, re.I)}
    assert call_again, "the derived call-again instruction population is empty"
    for name, text in call_again.items():
        assert re.search(r"\bsetup_answers\b", text), f"{name} hides the public answer path"
        assert re.search(r"\baction\b", text), f"{name} hides the public action path"


def _call_without_answers(root: Path) -> dict[str, Any]:
    async def call() -> dict[str, Any]:
        server = create_server(roots=(root.parent.resolve(),))
        from mcp import Client

        async with Client(server) as client:
            response = await client.call_tool("audit_repository", {"repository_root": str(root)})
            assert not response.is_error, response.content
            return response.structured_content

    return asyncio.run(call())

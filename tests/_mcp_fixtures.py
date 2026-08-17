"""Shared fixtures for the MCP consent/grant suites.

One home for the repo builders and MCP helpers that
``test_consent_and_grant.py`` and ``test_root_grants.py`` both use —
the file split satisfied the size warn line, and this module keeps the
duplicate-block gate at zero instead of paying for the split with
copied helpers.
"""

from __future__ import annotations

import asyncio
import json
import subprocess
from pathlib import Path
from typing import Any

from maintainability_audit.config import CONFIG_FILENAME


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

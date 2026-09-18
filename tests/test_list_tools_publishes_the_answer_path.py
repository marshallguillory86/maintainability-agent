"""`list_tools()` publishes the answer path and nothing private (D189).

Covers existing behaviour: `setup_answers` reached the published schema in
D189 and this assertion passes at that commit. It is kept because the
defect it guards is invisible in the source — the function has always
taken a `setup` parameter, and only what `list_tools()` serves says
whether a host can use it.

Moved out of `test_setup_answers_are_the_same_setup` (written by Codex for
the D193 cycle) so that file's citations stay evidence. Every assertion is
that file's, unchanged.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from maintainability_audit.mcp_server import create_server


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


def test_list_tools_exposes_only_the_host_submit_answer_path(tmp_path: Path) -> None:
    """A field merely named ``setup`` is not a public answer path."""
    properties = _tool_schema(_repository(tmp_path, "schema"))["properties"]

    assert "setup_answers" in properties
    assert {"setup", "grant", "ctx"}.isdisjoint(properties), properties

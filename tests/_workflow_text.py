"""Read the few workflow shapes the CI-shape tests need, without PyYAML.

This repository keeps its ``test`` extra thin and ``test_declared_imports``
refuses a dev-only parser in tests, so this reads indentation by hand. It
handles only: the top-level ``on:`` block, top-level ``jobs:`` entries, a
job's ``name:`` and its (possibly folded) ``if:``. Comments are dropped.
A wrong parse returns an empty result, which the tests treat as a failure.
"""

from __future__ import annotations

import re
from pathlib import Path

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def _code_lines(name: str) -> list[str]:
    lines = (WORKFLOWS / name).read_text(encoding="utf-8").splitlines()
    return [ln for ln in lines if ln.strip() and not ln.lstrip().startswith("#")]


def _top_block(lines: list[str], key: str) -> list[str]:
    start = next((i for i, ln in enumerate(lines) if re.fullmatch(rf"{key}:\s*", ln)), None)
    if start is None:
        return []
    block: list[str] = []
    for ln in lines[start + 1 :]:
        if not ln.startswith(" "):
            break
        block.append(ln)
    return block


def _sub_blocks(block: list[str], indent: int) -> dict[str, list[str]]:
    """Split a block into entries keyed at ``indent`` spaces."""
    entries: dict[str, list[str]] = {}
    current: list[str] | None = None
    pattern = re.compile(rf"^ {{{indent}}}([A-Za-z0-9_-]+):(.*)$")
    for ln in block:
        match = pattern.match(ln)
        if match:
            current = entries.setdefault(match.group(1), [])
            if match.group(2).strip():
                current.append(match.group(2).strip())
        elif current is not None:
            current.append(ln)
    return entries


def triggers(workflow: str) -> dict[str, list[str]]:
    """Event name -> its body lines, from the ``on:`` block."""
    return _sub_blocks(_top_block(_code_lines(workflow), "on"), 2)


def jobs(workflow: str) -> dict[str, dict[str, str]]:
    """Job id -> {"name": ..., "if": ...} ("" when absent)."""
    result: dict[str, dict[str, str]] = {}
    for job_id, body in _sub_blocks(_top_block(_code_lines(workflow), "jobs"), 2).items():
        fields = _sub_blocks(body, 4)
        result[job_id] = {
            "name": " ".join(s.strip() for s in fields.get("name", [])).strip("'\""),
            "if": " ".join(s.strip() for s in fields.get("if", [])).lstrip("> ").strip(),
        }
    return result

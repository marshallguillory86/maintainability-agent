"""TDD-shaped structure sentences. One block, three skins. Not chronology."""
from __future__ import annotations

from typing import Any


def tdd_sentences(block: dict[str, Any] | None) -> list[str]:
    """The same two sentences every skin prints. Chronology is refused."""
    if not block:
        return []
    if not block.get("detected"):
        return [
            "No TDD-shaped test files were detected.",
            "Chronology is not measured. Effectiveness is unscored unless "
            "the operator opted into suite execution.",
        ]
    constructs = ", ".join(
        f"{name} in {count} file(s)"
        for name, count in (block.get("constructs") or {}).items()
        if count
    ) or "none named"
    paired = block.get("paired_production_files", 0)
    total = block.get("production_files", 0)
    return [
        f"TDD-shaped tests: detected beside {paired} of {total} production "
        f"source files (path pairing). Constructs: {constructs}.",
        "Chronology is not measured. Effectiveness is unscored unless "
        "the operator opted into suite execution.",
    ]


def tdd_structure_markdown(block: dict[str, Any] | None) -> list[str]:
    sentences = tdd_sentences(block)
    if not sentences:
        return []
    return ["## TDD-shaped tests", "", *sentences, ""]

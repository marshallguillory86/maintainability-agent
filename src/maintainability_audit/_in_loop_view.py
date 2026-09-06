"""What the in-loop check prints, and what an agent reads instead.

Split from `_in_loop` on the seam `_precommit_view` and `_work_order_view`
already use: one module decides what the budgets say, this one decides how
it reads. Nothing here computes.

The two renderings carry the same content because their audiences differ
only in kind — a person watching a file grow, and an agent about to write
one. Neither may learn something the other does not.
"""
from __future__ import annotations

import json
from typing import Any


def _room_line(entry: dict[str, Any]) -> str:
    """One declaration's remaining budget, in the order it is useful.

    Name first because that is what the reader is looking for, then the
    figure, then the band. A negative `remaining` never reaches here —
    breaches are findings, not headroom.
    """
    remaining = entry["remaining"]
    plural = "line" if abs(remaining) == 1 else "lines"
    marker = "  ·" if entry["band"] == "ok" else "  !"
    return (f"{marker} {entry['name']} — {entry['lines']} of {entry['limit']} "
            f"lines, {remaining} {plural} left")


def render_check(result: dict[str, Any]) -> list[str]:
    """The lines to print. Empty when there is nothing worth saying.

    Silence covers the ordinary case: a small function with most of its
    budget unused does not need a report, and an agent that gets one on
    every call learns to stop calling. What earns output is a breach, a
    declaration near its line, or the fact that nothing could be read.
    """
    findings = result["findings"]
    tight = [entry for entry in result["headroom"] if entry["band"] != "ok"]
    file_room = result["file"]
    if not findings and not tight and file_room["band"] == "ok" and result["declarations_read"]:
        return []

    lines = [f"{result['path']} — budgets only, {result['scored_reason']}"]
    if not result["declarations_read"]:
        lines.append(f"  ? {result['note']}")
    for item in findings:
        where = f":{item['line']}" if item.get("line") else ""
        lines.append(f"  ✗ {item['name']}{where} — {item['over_by']} over")
        lines.append(f"    → {item['target']}")
    lines.extend(_room_line(entry) for entry in tight)
    if file_room["band"] != "ok" and not any(
        item["finding_class"] == "oversized-file" for item in findings
    ):
        lines.append(
            f"  ! file — {file_room['lines']} of {file_room['limit']} lines, "
            f"{file_room['remaining']} left"
        )
    return lines


def check_json(result: dict[str, Any]) -> str:
    """The same answer, shaped for the agent that asked.

    `scored: false` is a field rather than a comment for the reason the
    module docstring gives: a consumer that reads no score and infers a
    good one is what the evidence model exists to prevent, and prose in a
    docstring does not reach a parser.
    """
    return json.dumps(
        {
            "path": result["path"],
            "blocked": bool(result["findings"]),
            "findings": result["findings"],
            "headroom": result["headroom"],
            "file": result["file"],
            "declarations_read": result["declarations_read"],
            "note": result["note"],
            "scored": False,
            "scored_reason": result["scored_reason"],
        },
        indent=2,
        sort_keys=True,
    )

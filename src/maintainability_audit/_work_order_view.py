"""The work order and its per-item copy-paste prompts.

The bounded remediation prompt is the product (product-intent, Step 3), so
the work order — what to fix, in what order, and a ready-to-paste prompt
for each item — is the section a reader actually acts on. It renders in
two modes along one seam:

- ``complete`` (the HTML/Markdown report *file*, the reporting mechanism):
  the **whole** backlog, every item followed by a self-contained
  copy-paste prompt. A file has no size limit, so nothing is withheld.
- bounded (chat/CLI, the *UI*): the top items with their prompts and a
  pointer to the report for the rest, so the surface with a payload cap
  never has to carry — or silently truncate — the full list.

Split from ``_scan_view`` both because the seam is real (that module
answers *what was looked at*; this answers *what to do about it*) and
because adding the per-item generator pushed it past the 500-line file
gate this project holds itself to.
"""
from __future__ import annotations

from typing import Any

from ._work_order import work_order_rows

# The report lists the whole backlog; these caps apply only to the bounded
# UI, which shows the top items and points at the report for the rest.
WORK_ORDER_LIMIT = 20
CHAT_WORK_ORDER_LIMIT = 10

_REPORT_POINTER = (
    "The complete backlog — every item with a copy-paste prompt — is in "
    "the HTML or Markdown report."
)


def item_location(item: dict[str, Any]) -> str:
    """`path` or `path:line` — the one spelling both skins print."""
    return item["path"] + (f":{item['line']}" if item.get("line") else "")


def prompt_body_lines(item: dict[str, Any], root_label: str = ".") -> list[str]:
    """The copy-paste prompt text for one item, skin-agnostic.

    Deterministic: built entirely from the item's own fields, so the same
    audit yields the same prompt every time — no LLM decides its content.
    Markdown fences it as ``text`` and HTML wraps it in ``<pre>``; the text
    between is identical, so the two skins can never disagree about what an
    agent is being asked to do.
    """
    verify = item.get("verification") or "python -m maintainability_audit --root . --format json"
    return [
        f"Repository: {root_label}",
        f"Task: {item['target']}.",
        f"Location: {item_location(item)}",
        f"Why: {item['rationale']}",
        "",
        "Make one small, reviewable change. Do not alter public behavior or "
        "refactor unrelated code. If this is a false positive, say so and "
        "leave it unchanged; add or update a test when behavior changes.",
        f"Verify when done: {verify}",
    ]


def item_prompt_block(item: dict[str, Any], root_label: str = ".") -> list[str]:
    """One item's copy-paste prompt as Markdown: heading, then a fenced block.

    Fenced as ``text`` so a reader copies the whole thing into a coding
    agent without any surrounding report — the point of the per-item form:
    the prompt travels alone and still says what, where, why, and how to
    check it.
    """
    return [
        f"#### {item['title']}",
        f"`{item_location(item)}` · {item['band']}",
        "",
        "```text",
        *prompt_body_lines(item, root_label),
        "```",
        "",
    ]


def work_order_markdown(
    items: list[dict[str, Any]] | None, *, complete: bool = False, root_label: str = ".",
) -> list[str]:
    """The ordered work, worth first, with a copy-paste prompt for each item.

    ``complete`` is the report/UI seam described in the module docstring.
    Quick Wins lead and Major Projects are named in either mode: taking on
    a forty-file deduplication is a human's call they cannot make if
    nothing tells them it is there.
    """
    if not items:
        return []
    rows = work_order_rows(items)
    limit = len(rows) if complete else CHAT_WORK_ORDER_LIMIT
    lines = [
        "## Work Order", "",
        "Ordered by what it costs to leave against what it costs to fix "
        "(see the standard). `Worth` is what clearing the whole class moves "
        "the score, recomputed through the rubric rather than estimated.",
        "",
        "| # | Band | Item | Worth | Target |",
        "|---:|---|---|---:|---|",
    ]
    for index, row in enumerate(rows[:limit], start=1):
        location = f"`{row['path']}`" + (f":{row['line']}" if row.get("line") else "")
        lines.append(
            f"| {index} | {row['band']} | {row['title']} ({location}) | "
            f"{row['worth']} | {row['target']} |"
        )
    lines.append("")
    if not complete and len(rows) > limit:
        lines.extend([f"...and {len(rows) - limit} more. {_REPORT_POINTER}", ""])
    lines.extend([f"Verify with: `{items[0]['verification']}`", ""])
    lines.extend([
        "### Copy-paste prompts", "",
        "One self-contained prompt per item — paste any block whole into a "
        "coding agent.", "",
    ])
    for item in items[:limit]:
        lines.extend(item_prompt_block(item, root_label))
    return lines


def work_order_selection_markdown(selection: dict[str, Any] | None) -> list[str]:
    """What the reader asked for, and what clearing exactly that is worth.

    Recomputed for the selection rather than summed from its items:
    findings of one class share a denominator, so a sum overstates a
    work order by more the longer it gets.
    """
    if not selection:
        return []
    criteria = ", ".join(f"`{axis}={value}`" for axis, value in sorted(selection["criteria"].items()))
    items = selection["items"]
    if not items:
        return ["## Selected Work", "", f"Nothing matches {criteria}.", ""]
    worth = f"+{selection['worth']:.2f}" if selection["worth"] else "no measurable movement"
    lines = [
        "## Selected Work", "",
        f"{len(items)} item(s) matching {criteria}. Clearing all of them is worth "
        f"**{worth}** to the maintainability estimate — recomputed for this "
        "selection, not summed from the items.",
        "",
        "| # | Band | Item | Target |",
        "|---:|---|---|---|",
    ]
    for index, item in enumerate(items[:WORK_ORDER_LIMIT], start=1):
        location = f"`{item['path']}`" + (f":{item['line']}" if item.get("line") else "")
        lines.append(f"| {index} | {item['band']} | {item['title']} ({location}) | {item['target']} |")
    lines.extend(["", f"Verify with: `{items[0]['verification']}`", ""])
    return lines

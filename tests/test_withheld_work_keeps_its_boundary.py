"""A copy-paste block never authorises what the prompt withholds (D180).

From the audit of 3.7.3 (`7befdbd`): the demo's remediation prompt withheld
its two duplicated blocks as needing a design decision, while the report's
standalone copy-paste block for each said "Task: remove the duplicated
block". Which instruction an agent followed depended on which text was
pasted — and the per-item block exists precisely to be pasted alone.

The claim: **for every item the bounded prompt does not hand to an agent,
every skin's copy-paste block asks for the design decision and not the
patch; every item it does hand over keeps its task.** The withheld
population is derived from `prompt_items` over the demo's real work order,
which holds only Major Projects. The other withholding rule — a finding
fixed before and come back — is outside that sample, so one handed item is
escalated through `design_review_candidates` and must move with it.
"""
from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "examples" / "demo"
PATCH = "Make one small, reviewable change"
BOUNDARY = "Do not change code for this item"


def _demo_report() -> dict[str, Any]:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    return build_report(DEMO, load_config(DEMO / "maintainability-agent.json"), run_analyzers=False)


def _blocks(text: str) -> dict[tuple[str, str], str]:
    """Every copy-paste block in a skin, by its heading and the location it names.

    Both, because two items can share a line: the demo's oversized function
    and its unpaired-test finding are each at `billing.py:14`.
    """
    titled = re.findall(r"^#### ([^\n]+)\n[^\n]*\n\n```text\n(.*?)```", text, flags=re.S | re.M)
    titled += [(html.unescape(title), html.unescape(body)) for title, body
               in re.findall(r"<h4>(.*?)</h4>\s*<pre>(.*?)</pre>", text, flags=re.S)]
    located = {}
    for title, body in titled:
        match = re.search(r"^Location: (.+)$", body, flags=re.M)
        if match:
            located[(match.group(1), title)] = body
    return located


def _skins(report: dict[str, Any]) -> dict[str, str]:
    from maintainability_audit.renderers import render_html, render_markdown

    return {
        "chat": render_markdown(report, complete=False),
        "markdown": render_markdown(report, complete=True),
        "html": render_html(report, []),
    }


def _split(report: dict[str, Any]) -> tuple[set[str], set[str]]:
    from maintainability_audit._prompt_sections import _prompt_work_items
    from maintainability_audit._work_order_view import item_location

    # Not keyed on `fingerprint`: an unpaired-hotspot item carries none.
    handed = {(item_location(i), i["title"]) for i in _prompt_work_items(report)}
    every = {(item_location(i), i["title"]) for i in report["work_order"]}
    return every - handed, handed


def _wrong(report: dict[str, Any]) -> list[tuple[str, str, str]]:
    withheld, kept = _split(report)
    assert withheld, "the prompt withholds nothing; the boundary was never exercised"
    assert kept, "the prompt hands over nothing; the task side was never exercised"
    wrong = []
    for skin, text in _skins(report).items():
        blocks = _blocks(text)
        assert withheld | kept <= blocks.keys(), f"{skin} is missing blocks: {(withheld | kept) - blocks.keys()}"
        wrong += [(skin, where, "authorises a patch") for where in withheld
                  if PATCH in blocks[where] or BOUNDARY not in blocks[where]]
        wrong += [(skin, where, "lost its task") for where in kept
                  if PATCH not in blocks[where] or BOUNDARY in blocks[where]]
    return wrong


def test_the_demo_major_projects_ask_for_a_decision_on_every_skin() -> None:
    wrong = _wrong(_demo_report())
    assert not wrong, f"blocks disagreeing with the prompt: {wrong}"


def test_an_escalated_finding_asks_for_a_decision_on_every_skin() -> None:
    from maintainability_audit._prompt_sections import _prompt_work_items

    report = _demo_report()
    handed = _prompt_work_items(report)
    escalatable = [item for item in handed if item.get("fingerprint")]
    assert escalatable and len(handed) >= 2, f"need one item to escalate and one to keep: {handed}"
    # The shape `escalations` publishes, so the complete skin's section renders.
    report["design_review_candidates"] = [{
        "fingerprint": escalatable[0]["fingerprint"], "returns": 2, "targeted": 2,
        "commits": ["a" * 40, "b" * 40], "reason": "fixed twice and returned twice",
    }]
    wrong = _wrong(report)
    assert not wrong, f"blocks disagreeing with the prompt once a finding came back: {wrong}"

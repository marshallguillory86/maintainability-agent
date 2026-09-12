"""The chat door opens with the product, and a prompt stays a paragraph.

Two rules that share a subject: what the primary surface shows first, and
how big the thing it shows is allowed to get.

`docs/product-intent.md` says it plainly — *"The scanner and the score
exist to aim the remediation prompt. If the prompt were removed, the rest
would be a worse version of tools that already ship"*, and *"Step 3 is
the product."* The bounded view is the MCP `chat` format, which the skill
calls the primary surface. It opened with a fourteen-row metric table
(D160).

The size bound is Marshall's rule of 2026-09-11: *"prompts should be
paragraph or two sized within reason, not a fucking entire program."*
`prompt_items`' twelve-item cap is what holds it, so the cap is pinned
here as a contract rather than left as an incidental default.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]


def _long_function(name: str, branches: int = 40) -> str:
    body = "".join(f"    if x == {n}:\n        return {n}\n" for n in range(branches))
    return f"def {name}(x):\n{body}    return -1\n"


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for name, body in files.items():
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
    return root


def _messy(tmp_path: Path, modules: int = 3) -> dict[str, Any]:
    root = _repo(tmp_path / "messy", {
        f"mod{m}.py": "\n".join(_long_function(f"f{m}_{k}") for k in range(3))
        for m in range(modules)
    })
    return build_report(root, load_config(None))


def test_the_chat_view_shows_the_work_order_before_the_grade(tmp_path: Path) -> None:
    """The first screen is what to do, not what you scored.

    Fails at base: the bounded view built `## Summary` into the shared
    prelude, so the metric table carrying `Verified grade` preceded
    `## Work Order` on every run that had one.
    """
    rendered = render_markdown(_messy(tmp_path), complete=False)

    work_order = rendered.index("## Work Order")
    summary = rendered.index("## Summary")
    assert work_order < summary, (
        "the chat door opened with the metric table; the work order is the "
        f"product and must lead (work order at {work_order}, summary at {summary})"
    )

    grade_row = rendered.index("| Verified grade |")
    first_prompt = rendered.index("```text")
    assert first_prompt < grade_row, (
        "a reader reached the letter grade before the first pasteable prompt"
    )


def test_a_pasteable_prompt_is_near_the_top_of_the_chat_view(tmp_path: Path) -> None:
    """Not merely earlier than the grade — actually on the first screen.

    Ordering alone can be satisfied while still burying the prompt under
    something else later, so this bounds the distance a reader scrolls.

    Forty lines is one terminal screen, and it is the budget the sections
    above the prompt have to share: four metadata lines, the work-order
    table with its ten bounded rows, and the heading. Measured at 36 after
    D160 and 51 before it. A regression that reinstates a table above the
    work order spends the remaining four immediately.
    """
    rendered = render_markdown(_messy(tmp_path), complete=False)
    lines = rendered.splitlines()
    first_prompt = next(i for i, line in enumerate(lines) if line.strip() == "```text")

    assert first_prompt < 40, (
        f"the first copy-paste prompt begins on line {first_prompt + 1}; a "
        "chat reader should not scroll past a screen to reach the product"
    )


def test_a_run_with_no_work_order_says_so(tmp_path: Path) -> None:
    """Silence where the product goes reads as a missing feature.

    Fails at base: a report whose `work_order` is empty rendered no work
    order section at all, so this repository's own chat view — 73 lines,
    six headings — never mentioned the work order it exists to produce.
    """
    root = _repo(tmp_path / "clean", {"ok.py": "def add(a, b):\n    return a + b\n"})
    rendered = render_markdown(build_report(root, load_config(None)), complete=False)

    assert "## Work Order" in rendered, (
        "a clean run omitted the section entirely; a reader cannot tell "
        "'nothing to do' from 'this tool does not do that'"
    )
    assert "Nothing to do." in rendered, (
        f"the empty work order did not say what it means:\n{rendered[:400]}"
    )


def test_the_agent_prompt_stays_a_page_however_bad_the_tree_is(tmp_path: Path) -> None:
    """Marshall's rule, bound: a prompt is a paragraph or two, not a program.

    Covers existing behaviour: `prompt_items`' twelve-item cap already
    held this at the base, so the assertion passes before and after. It
    is a guard rather than a falsifier, and it is here because the cap is
    a contract nothing enforced — removing it would leave every test
    green while handing an agent the entire backlog.

    Sized to the rule rather than to today's output: the measured prompt
    on a 171-item tree was 96 lines, so a 200-line ceiling catches a
    regression that unbinds the cap without failing on ordinary drift.
    """
    from maintainability_audit.prompts import render_ai_prompt

    report = _messy(tmp_path, modules=20)
    backlog = len(report.get("work_order") or [])
    assert backlog > 40, f"fixture is not messy enough to bound anything ({backlog})"

    prompt = render_ai_prompt(report)
    assert len(prompt.splitlines()) < 200, (
        f"the remediation prompt grew to {len(prompt.splitlines())} lines on a "
        f"{backlog}-item backlog — a prompt is a paragraph or two, and the "
        "whole backlog belongs in the report file, not in the paste"
    )
    assert len(prompt) < 20_000, (
        f"the remediation prompt reached {len(prompt)} characters; the cap in "
        "`prompt_items` is what keeps this a page and it is no longer holding"
    )


def test_one_items_prompt_is_a_paragraph(tmp_path: Path) -> None:
    """The unit the rule is actually about: what one paste contains.

    Covers existing behaviour: `prompt_body_lines` builds a fixed
    eight-line body from the item's own fields, so this held at the base.
    Pinned because the body is the natural place to bolt on context —
    surrounding source, the full class listing — and each addition looks
    small on its own.
    """
    from maintainability_audit._work_order_view import prompt_body_lines

    report = _messy(tmp_path)
    items = report.get("work_order") or []
    assert items, "fixture produced no work order to measure"

    for item in items:
        body = "\n".join(prompt_body_lines(item, "."))
        assert len(body) < 2_000, (
            f"one item's prompt reached {len(body)} characters for "
            f"{item['title']!r}; a single paste is a paragraph, not a program"
        )

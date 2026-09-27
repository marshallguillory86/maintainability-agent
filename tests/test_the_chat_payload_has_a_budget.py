"""The whole chat reply stays under a budget, for every format, on a large repository.

This is the guard the size fix of 2026-08-31 should have shipped with. That
fix bounded one field — `report_markdown` — and its tests measured that one
field. The html path went on carrying the complete HTML in `report_html` in
the same reply, and a test listed `report_html` as an expected key, so it
defended the defect. Nothing measured the reply. It surfaced on the first
real repository: 308,957 characters, refused by the host, no report
delivered (D216).

So these measure the **whole serialized reply**, over **every presentation
the product offers** (read from `PRESENTATIONS`, so a new format is covered
the day it exists), on a repository **large enough that the complete report
is far over the budget**. A new key, a new format, or a report that grows
cannot pass by fitting inside a field nobody measures.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._catalog import PRESENTATIONS
from maintainability_audit._mcp_audit import audit_repository
from maintainability_audit.renderers import render_markdown

#: Claude Code refuses an MCP result over 25,000 tokens by default
#: (`MAX_MCP_OUTPUT_TOKENS`), and other hosts cap lower. At roughly four
#: characters a token that is about 100,000 characters; the budget keeps
#: well under it so a host with a smaller cap still receives the prompt.
CHAT_REPLY_BUDGET = 60_000

#: Functions long enough to be findings, in enough files that the complete
#: report is several times the budget. Asserted below, so a fixture that
#: stops being large cannot quietly make the budget easy.
FILES = 120


def _large_repo(tmp_path: Path) -> Path:
    root = tmp_path / "large"
    (root / "pkg").mkdir(parents=True)
    body = "".join(f"    if x == {n}:\n        x += {n}\n" for n in range(45))
    for index in range(FILES):
        (root / "pkg" / f"mod{index}.py").write_text(
            f"def work{index}(x):\n{body}    return x\n\n\n"
            f"def other{index}(y):\n{body.replace('x', 'y')}    return y\n",
            encoding="utf-8",
        )
    (root / "README.md").write_text("# large\n", encoding="utf-8")
    (root / "maintainability-agent.json").write_text(
        json.dumps({"version": 1, "analyzers": {"run": False}}), encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


@pytest.fixture(scope="module")
def large(tmp_path_factory) -> Path:
    return _large_repo(tmp_path_factory.mktemp("budget"))


def _reply(root: Path, fmt: str, tmp: Path) -> dict:
    return audit_repository(
        str(root), format=fmt, record_history=False, roots=(root.parent.resolve(),),
        output_path=str(root.parent / "saved") + "/")


def test_the_fixture_is_large_enough_to_break_a_budget_that_is_not_kept(large) -> None:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    complete = render_markdown(build_report(large, load_config(str(large / "maintainability-agent.json")),
                                            run_analyzers=False), complete=True)

    assert len(complete) > 2 * CHAT_REPLY_BUDGET, (
        f"the complete report is {len(complete)} characters; the fixture no longer "
        "tests anything, because even an unbounded reply would fit"
    )


@pytest.mark.parametrize("fmt", [f for f in PRESENTATIONS if f != "json"])
def test_the_whole_reply_stays_under_the_budget(large, tmp_path, fmt) -> None:
    """Every key, every format a person can choose for reading.

    `json` is excluded by name, and only it: that format *is* the report
    dictionary, chosen for a pipeline rather than a chat window.
    """
    reply = json.dumps(_reply(large, fmt, tmp_path))

    assert len(reply) <= CHAT_REPLY_BUDGET, (
        f"format {fmt!r}: the chat reply is {len(reply)} characters, over the "
        f"{CHAT_REPLY_BUDGET} budget. The complete report belongs in the saved file."
    )


@pytest.mark.parametrize("fmt", [f for f in PRESENTATIONS if f != "json"])
def test_the_complete_report_never_travels_in_the_reply(large, tmp_path, fmt) -> None:
    reply = json.dumps(_reply(large, fmt, tmp_path)).lower()

    assert "<html" not in reply and "<!doctype" not in reply, (
        f"format {fmt!r} carried an HTML document in the reply")
    assert "report_html" not in reply


def test_json_is_the_only_format_excused_from_the_budget() -> None:
    """If a format is added, it is budgeted unless someone argues otherwise here."""
    assert set(PRESENTATIONS) - {"json"} == {"chat", "markdown", "html"}

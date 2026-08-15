"""2.5c: what is missing, why it matters, the command — never run for you.

Coverage (2.5) already says *that* a tool did not run. The environment
work order is the artifact on top: for every selected tool that could
not contribute, the reason, the exact install command, and how to verify
it worked — in the same shape as the code work order, so a person can
run it or hand it to their own agent (ADR 006 §2c).

The line that may never blur: **the agent never installs anything.**
Installation is a network and privilege action belonging to the user.
This module emits text.
"""
from __future__ import annotations

from pathlib import Path

import pytest

# The same 40-file fixture the first-run tests build; imported rather
# than repeated, because two copies tripped this project's own
# duplicate-block gate.
from test_first_run_prompt import _repo

from maintainability_audit import report as report_module
from maintainability_audit._analysis import Analysis, ToolCoverage
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report


def _coverage() -> list[ToolCoverage]:
    """One of each outcome the work order has to sort into act / ignore."""
    return [
        ToolCoverage(slug="lizard", outcome="ran", version="lizard 1.17",
                     concepts=("cyclomatic_complexity",), measurements=12),
        ToolCoverage(slug="vulture", outcome="not-installed",
                     detail="vulture is not on PATH", concepts=("dead-code",)),
        ToolCoverage(slug="jscpd", outcome="not-working",
                     detail="npx exited 127", concepts=("duplication",)),
        ToolCoverage(slug="radon", outcome="timed-out",
                     detail="exceeded 120s", concepts=("maintainability_index",)),
    ]


@pytest.fixture
def analyzed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    monkeypatch.setattr(
        report_module, "analyze",
        lambda _root, _config: Analysis(coverage=_coverage()),
    )
    return build_report(_repo(tmp_path), load_config(None), run_analyzers=True)


def test_unrunnable_selected_tools_become_work_items(analyzed: dict) -> None:
    """not-installed and not-working are actionable; they must appear."""
    order = analyzed["environment_work_order"]
    by_tool = {item["tool"]: item for item in order}

    assert "vulture" in by_tool, f"a not-installed tool is missing: {sorted(by_tool)}"
    assert "jscpd" in by_tool, f"a not-working tool is missing: {sorted(by_tool)}"
    assert "lizard" not in by_tool, "a tool that ran is not environment work"
    assert "radon" not in by_tool, (
        "timed-out is present-but-slow; advising a reinstall fixes the wrong thing"
    )


def test_a_built_in_is_never_environment_work() -> None:
    """A built-in cannot be installed and does not belong in the order.

    At the function seam rather than through `build_report`, because the
    report path recounts real built-ins against the summary and a
    fabricated one breaks that machinery before reaching this rule.
    """
    from maintainability_audit._environment import environment_work_order

    built_in = ToolCoverage(slug="risk", outcome="not-installed", tier="built-in",
                            concepts=("risk",))
    assert environment_work_order([built_in]) == []


def test_each_item_names_reason_command_and_verification(analyzed: dict) -> None:
    """The three fields that make an item actionable rather than a complaint.

    Same rule as the code work order: an item lacking a location, a
    target or a way to prove it is done is advice, and advice is what
    this tool exists to replace.
    """
    for item in analyzed["environment_work_order"]:
        assert item["reason"], f"{item['tool']} states no reason it did not run"
        assert item["install"], f"{item['tool']} has no install command"
        assert item["verify"], f"{item['tool']} has no way to prove the install worked"

    vulture = next(i for i in analyzed["environment_work_order"] if i["tool"] == "vulture")
    assert "vulture" in vulture["install"], (
        f"the install command does not name the tool: {vulture['install']!r}"
    )


def test_the_order_reaches_the_markdown_report(analyzed: dict) -> None:
    """An artifact only the JSON carries is invisible to the reader it is for."""
    markdown = render_markdown(analyzed)

    assert "Environment Work Order" in markdown
    assert "vulture" in markdown
    # After coverage, which names the gap this remedies.
    assert markdown.index("Environment Work Order") > markdown.index("Analyzer Coverage")


def test_without_analyzers_the_order_is_empty(tmp_path: Path) -> None:
    """No pool, no gaps to remedy — and no section inviting installs."""
    report = build_report(_repo(tmp_path), load_config(None))

    assert report["environment_work_order"] == []
    assert "Environment Work Order" not in render_markdown(report)


def test_the_agent_never_runs_the_install_command(analyzed: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    """The commands are text. Nothing here may execute one.

    Asserted structurally: the module that builds the order imports no
    process machinery. Rule 7 already confines spawning to `_runner`,
    `git_tools` and `_backfill`; this pins the same property to the one
    module whose whole subject is commands somebody should run.
    """
    import maintainability_audit._environment as environment

    forbidden = {"subprocess", "os.system", "Popen", "check_output", "run("}
    source = Path(environment.__file__).read_text(encoding="utf-8")
    hits = [token for token in forbidden if token in source]
    assert not hits, f"the environment work order can execute commands: {hits}"

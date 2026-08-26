"""D4/D12/D16/D17: every operator surface teaches the chat-primary product."""

from __future__ import annotations

import re
from pathlib import Path

from maintainability_audit.instructions import write_instruction_pack
from maintainability_audit.mcp_server import SERVER_INSTRUCTIONS

ROOT = Path(__file__).resolve().parents[1]
README = ROOT / "README.md"
PRODUCT_INTENT = ROOT / "docs/product-intent.md"
INTEGRATION = ROOT / "docs/ide-agent-integration.md"
SKILL = ROOT / "skills/maintainability-agent/SKILL.md"
REGISTER = ROOT / "docs/defect-register-chat-surface.md"
DECISIONS = ROOT / "docs/decisions.md"
HELP = ROOT / "docs/help"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _states_chat_is_primary(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return bool(re.search(r"(?:chat.{0,80}primary|primary.{0,80}chat)", normalized))


def _states_no_unchosen_file(text: str) -> bool:
    normalized = " ".join(text.lower().split())
    return bool(re.search(
        r"(?:do not|does not|never|no)[^.]{0,100}(?:write|save)[^.]{0,100}"
        r"(?:file|report)[^.]{0,100}(?:chosen|choose|location)",
        normalized,
    ))


def test_readme_product_intent_and_mcp_description_name_the_surface_contract() -> None:
    """D4: chat is primary; the CLI is the automation/CI door."""
    readme = _read(README)
    product_intent = _read(PRODUCT_INTENT)

    for name, surface in (
        ("README", readme),
        ("product intent", product_intent),
        ("MCP server description", SERVER_INSTRUCTIONS),
    ):
        assert _states_chat_is_primary(surface), f"{name} does not name chat as primary"
        lowered = surface.lower()
        assert "cli" in lowered and ("automation" in lowered or "ci" in lowered), (
            f"{name} does not bound the CLI to automation/CI"
        )

    primary = readme.index("## Primary Surface: Chat / MCP")
    automation = readme.index("## Automation / CI: CLI")
    assert primary < automation, "README teaches CLI usage before its primary chat flow"


def test_shipped_skill_teaches_chat_setup_before_cli_automation() -> None:
    """D12: the portable skill follows the user-facing flow, not a file recipe."""
    skill = _read(SKILL)
    lowered = skill.lower()

    assert _states_chat_is_primary(skill)
    assert "configuration" in lowered and "check" in lowered
    assert "elicitation" in lowered or "question ui" in lowered
    assert "history" in lowered and "consent" in lowered
    assert _states_no_unchosen_file(skill)
    assert "automation" in lowered and "cli" in lowered
    assert lowered.index("primary") < lowered.index("automation")

    core = lowered.split("## automation", maxsplit=1)[0]
    assert "--output maintainability-report.md" not in core
    assert "use the `maintainability-agent` cli as the source of truth" not in core


def test_chat_help_is_complete_linked_and_reachable_from_mcp() -> None:
    """D16: chat users can discover setup, evidence, and the remediation loop."""
    expected = {
        "README.md",
        "first-run.md",
        "analyzer-pool.md",
        "report-and-history.md",
    }
    assert HELP.is_dir(), "the chat-first help directory does not exist"
    assert expected <= {path.name for path in HELP.glob("*.md")}

    index = _read(HELP / "README.md")
    combined = "\n".join(_read(HELP / name) for name in sorted(expected)).lower()
    for name in expected - {"README.md"}:
        assert f"({name})" in index

    assert "deterministic" in combined and "bounded work order" in combined
    for term in ("setup", "grant", "history consent"):
        assert term in combined
    assert "analyzer pool" in combined and "built-in" in combined and "fallback" in combined
    for term in ("estimate", "range", "grade", "history", "recurrence", "baseline"):
        assert term in combined
    assert "economic" in combined and "scenario" in combined

    assert "(docs/help/readme.md)" in _read(README).lower()
    assert "docs/help" in SERVER_INSTRUCTIONS.lower()
    # D16 requires the docs index and the integration guide to reach
    # the help files too, not only the README and the MCP description.
    assert "help/readme.md" in _read(ROOT / "docs/README.md").lower()
    assert "help/readme.md" in _read(INTEGRATION).lower()


def _generated_packs(tmp_path: Path) -> list[str]:
    targets = ["generic", "codex", "claude-code", "cursor", "copilot", "windsurf"]
    paths = write_instruction_pack(
        targets,
        tmp_path,
        {"instruction_pack": {"project_name": "Fixture"}},
    )
    return [_read(Path(path)) for path in paths]


def test_integration_guide_and_generated_packs_teach_chat_before_automation(
    tmp_path: Path,
) -> None:
    """D17: generated standards and the IDE guide agree on the primary flow."""
    guide = _read(INTEGRATION)
    surfaces = [("integration guide", guide), *(
        (f"generated pack {number}", text)
        for number, text in enumerate(_generated_packs(tmp_path), start=1)
    )]

    for name, surface in surfaces:
        lowered = surface.lower()
        assert _states_chat_is_primary(surface), f"{name} is not chat-primary"
        # Was `"configuration" in lowered and "check" in lowered`, which
        # required every generated pack to say "configuration check" —
        # the archaeology D21 forbids. Two closed entries in direct
        # contradiction, both green, until an audit read the pack.
        assert "audit_repository" in lowered, (
            f"{name} does not name the call that comes first (D21)"
        )
        assert "elicitation" in lowered or "question ui" in lowered, name
        assert _states_no_unchosen_file(surface), name
        assert "cli" in lowered and ("automation" in lowered or "ci" in lowered), name
        assert lowered.index("primary") < lowered.index("automation"), name


def test_decisions_four_through_eight_are_repository_records() -> None:
    """A pull request is not the record of Marshall's operating decisions."""
    decisions = _read(DECISIONS).lower()
    assert decisions.count("2026-08-17") >= 5
    for number in range(4, 9):
        assert re.search(rf"(?:decision\s+{number}|{number}\.\s+\*\*)", decisions)
    for phrase in (
        "history consent",
        "this session",
        "toctou",
        "config wins",
        "flat allowed_roots",
    ):
        assert phrase in decisions


def test_the_skill_calls_the_tool_before_inspecting_configuration() -> None:
    """D21: the agent must not do configuration archaeology first.

    Found in the field: a run in a repository whose config had been
    deleted spent a quarter-minute reasoning about which config to use
    and then asked the user — a question the tool itself asks properly
    through first-run setup. The skill's first step told it to go
    looking, so it went looking.
    """
    skill = _read(SKILL)
    workflow = skill.split("## Core Workflow", maxsplit=1)[1]
    first_step = workflow.split("2.", maxsplit=1)[0]

    assert "audit_repository" in first_step, (
        "the first step must be calling the tool, not inspecting the repo"
    )
    assert "do not inspect configuration" in first_step.lower()
    assert "do not ask the user which config" in first_step.lower()
    assert "configuration check first" not in skill.lower(), (
        "the config-archaeology instruction is back"
    )


def test_every_chat_instruction_surface_calls_the_tool_before_inspecting_config() -> None:
    """D47: D21's rule reached the skill and stopped there.

    Found by inspection on 2026-08-24 while diagnosing a field report.
    The report itself is *not* explained by this: that host loaded a
    pre-D21 skill out of an installed wheel older than the fix, and
    followed its "Configuration check first" step exactly. This entry
    was first written as that report's cause and corrected the same day
    (see the register); the gap below is real and was separately open.

    D21's fix was right, and its falsifier read
    skills/maintainability-agent/SKILL.md and nothing else. The skill is
    opt-in; the server instructions are what every chat host receives on
    connect, and they said nothing about the order. The MCP prompt
    actively taught the wrong one: "First offer the presentation choice
    ... Then call audit_repository." A host reading the door it was
    handed was told to ask first.

    D22 already learned this lesson and checked both surfaces together.
    Applying it only forward, never back to D21, is how the rule came to
    live on the one surface a host may never read.
    """
    # Read as source, so the adjacent-string joins have to be closed up
    # before a sentence is a sentence again.
    prompt_body = re.sub(r'"\s*"', "", (
        _read(ROOT / "src/maintainability_audit/mcp_server.py")
        .split("def maintainability_agent_prompt", maxsplit=1)[1]
        .split("\ndef ", maxsplit=1)[0]
    ))
    skill = _read(SKILL)
    first_step = skill.split("## Core Workflow", maxsplit=1)[1].split("2.", maxsplit=1)[0]

    # Four doors, not three. D47 enumerated the two MCP strings and the
    # skill and called the class closed; `--init-agent-standards` writes
    # a fourth into every AGENTS.md and CLAUDE.md, and it still opened
    # with "start with a configuration check" — the exact archaeology
    # D21 exists to stop, shipped into the file an agent reads first.
    # Same shape as D47's own account of D21: a falsifier that read one
    # file and called the class closed.
    from maintainability_audit.config import load_config
    from maintainability_audit.instructions import instruction_body

    surfaces = {
        "MCP server instructions": SERVER_INSTRUCTIONS,
        "MCP prompt": prompt_body,
        "skill": first_step,
        "generated standards pack": instruction_body("generic", load_config(None)),
    }
    for name, surface in surfaces.items():
        lowered = " ".join(surface.lower().split())
        assert "audit_repository" in lowered, (
            f"the {name} never names the call that is supposed to come first"
        )
        assert "do not inspect configuration" in lowered, (
            f"the {name} does not forbid inspecting configuration first"
        )
        assert "do not ask the user which config" in lowered, (
            f"the {name} does not forbid asking which config to use"
        )

    # The two MCP surfaces state the ordering outright: the skill's is
    # positional — it is step 1 — and D21's test holds that.
    for name in ("MCP server instructions", "MCP prompt"):
        normalized = " ".join(surfaces[name].lower().split())
        assert re.search(r"call(?:ing)? (?:it|audit_repository)[^.]{0,40}first",
                         normalized), (
            f"the {name} does not say the call comes first"
        )

    # The prompt's original wording is the regression shape: it put a
    # question of the host's before the first call.
    assert "first offer" not in " ".join(prompt_body.lower().split()), (
        "the MCP prompt tells the host to ask something before calling"
    )


def test_every_delivery_surface_offers_all_three_presentations() -> None:
    """D22: an agent that invents the delivery question deletes html.

    Found in the field: asked to audit a repository, the host offered
    "chat only" or "chat plus a saved file", then asked where to write
    the markdown. The html report — a presentation the product ships
    and setup can already have chosen — was never mentioned, because
    the skill named only chat and a file location. The MCP prompt got
    this right and the skill did not, so the surfaces are checked
    together: whichever one a host reads, it sees the same three.
    """
    from maintainability_audit._first_run import PRESENTATIONS

    # Bound to the setup vocabulary rather than a copy of it: a fourth
    # presentation would have to reach the instructions too.
    assert "html" in PRESENTATIONS

    skill = _read(SKILL)
    step = skill.split("3.", maxsplit=1)[1].split("\n4.", maxsplit=1)[0].lower()
    for presentation in PRESENTATIONS:
        assert presentation in step, (
            f"the skill's presentation step never offers {presentation}"
        )
    assert "format" in step, "the skill does not route the answer to `format`"
    # The two-option shape that caused this is named so the instruction
    # cannot quietly regress into it.
    assert "substitute" in step or "own option set" in step

    prompt = _read(ROOT / "src/maintainability_audit/mcp_server.py")
    body = prompt.split("def maintainability_agent_prompt", maxsplit=1)[1]
    body = body.split("def ", maxsplit=1)[0].lower()
    for presentation in PRESENTATIONS:
        assert presentation in body, (
            f"the MCP prompt never offers {presentation}"
        )

    mirror = _read(ROOT / "src/maintainability_audit/_skill_data/SKILL.md")
    assert mirror == skill, "the shipped skill mirror drifted from the source skill"


def test_the_handed_back_questions_are_instructed_and_carry_every_format(
    tmp_path: Path,
) -> None:
    """D25: questions returned as data that nobody is told to ask.

    The operator's report was flat: "I never saw an option for HTML,
    ever across the prompts." He was right, and the cause was not the
    presentation step. When a host cannot be elicited, the audit hands
    its whole first-run set back as `setup_needed` — including
    `default_format` with chat, markdown and html — and D3 calls that
    graceful degradation. But `setup_needed` appeared in no instruction
    surface at all: not the server description, not the skill. Its
    sibling `environment_work_order` was instructed on both. So the
    question generating the format choice was produced correctly,
    returned correctly, and then never asked by anyone, on any run.

    Checked at the seam, not in the vocabulary: an unconfigured
    repository's actual payload must carry the question and all three
    options, and both instruction surfaces must tell a host to ask it.
    """
    import subprocess

    from maintainability_audit._first_run import PRESENTATIONS
    from maintainability_audit.mcp_server import audit_repository

    root = tmp_path / "unconfigured"
    root.mkdir()
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text("def ok():\n    return 1\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)

    result = audit_repository(
        str(root), format="json", record_history=False, roots=(tmp_path.resolve(),),
    )

    handed_back = result.get("setup_needed")
    assert handed_back, (
        "an unconfigured repository handed back no questions, so a host "
        "that cannot elicit has nothing to ask"
    )
    # D26: and nothing that could be mistaken for the answer.
    assert result["audit_ran"] is False
    assert "report" not in result, (
        "a repository awaiting setup returned a report; the grade a "
        "first-time user then reads was computed with the pool off"
    )
    by_name = {question["name"]: question for question in handed_back["questions"]}
    presentation = by_name.get("default_format")
    assert presentation, "the handed-back set never asks which presentation"
    assert tuple(presentation["options"]) == tuple(PRESENTATIONS), (
        f"the presentation question offers {presentation['options']}, "
        f"not {list(PRESENTATIONS)}"
    )

    # Instructed wherever its sibling is. One of the two degradation
    # keys being explained and the other not is exactly the asymmetry
    # that let this run for the product's whole life.
    for name, surface in (
        ("MCP server description", SERVER_INSTRUCTIONS),
        ("shipped skill", _read(SKILL)),
    ):
        assert "environment_work_order" in surface, f"{name} changed shape"
        assert "setup_needed" in surface, (
            f"{name} never tells a host to ask the questions it is handed"
        )


def test_every_tool_offers_a_human_readable_title(tmp_path: Path) -> None:
    """A permission prompt should name the action, not the wire identifier.

    Found in the field: the host asked "Do you want to proceed with
    mcp__maintainability-agent__get_agent_info?" — it had nothing but
    the transport name to show. The spec reads `title` before falling
    back to `name`, so every tool states what a person is approving.
    """
    import asyncio

    from maintainability_audit.mcp_server import create_server

    tools = asyncio.run(create_server(roots=(tmp_path.resolve(),)).list_tools())
    assert tools, "the server exposed no tools"
    for tool in tools:
        assert tool.title, f"{tool.name} has no display title"
        assert "mcp__" not in tool.title and "_" not in tool.title, (
            f"{tool.name}'s title reads like an identifier: {tool.title!r}"
        )
        assert tool.title[0].isupper(), (
            f"{tool.name}'s title is not a sentence: {tool.title!r}"
        )

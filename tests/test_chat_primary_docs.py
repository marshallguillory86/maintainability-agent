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
        assert "configuration" in lowered and "check" in lowered, name
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


def test_the_register_states_a_falsifier_for_every_entry() -> None:
    """Closure is a named test, and the count is read, never asserted.

    An earlier version demanded an all-closed state by a written-in
    number, which is a test that can require a lie: when two audit
    findings were entered the register grew and the assertion still
    said seventeen. Entries are counted from their own headings, and
    each closed one must name the test that would fail if its defect
    returned.
    """
    register = _read(REGISTER)
    headings = re.findall(r"^### (D\d+) — (.+)$", register, re.MULTILINE)
    assert len(headings) >= 19, f"register shrank: {len(headings)} entries"

    body = register.split("## Disposition", maxsplit=1)
    assert len(body) == 2, "the register lost its disposition"
    entries, disposition = body[0], body[1].lower()

    open_entries = [f"{ident} {title}" for ident, title in headings
                    if "Closed" not in title]
    if open_entries:
        # An open entry is legitimate; claiming everything is closed
        # while one is open is not.
        assert "every entry" not in disposition, (
            f"the disposition claims all closed while these are open: {open_entries}"
        )
        return

    for ident, _title in headings:
        section = entries.split(f"### {ident} — ", maxsplit=1)[1]
        section = section.split("\n### ", maxsplit=1)[0]
        # Substance, not phrasing: some entries write "Closing test",
        # some "Closing suite", some name the tests inline. What every
        # closed entry must do is point at a real falsifier.
        assert re.search(r"`tests/\S+\.py`|`test_\w+`|\btest_\w+\b", section), (
            f"{ident} closes without naming the falsifier that would fail"
        )

    # The security entry names both doors it had to bound.
    assert "test_mcp_history_rejects_parent_traversal_without_external_write" in register
    assert "test_the_cli_door_applies_the_same_boundary" in register


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

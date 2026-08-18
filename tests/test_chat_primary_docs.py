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


def test_register_is_empty_except_for_analyzer_composition() -> None:
    """The docs sweep closes the surface register; D15 rides the adapter track."""
    register = _read(REGISTER)
    for defect in (4, 12, 16, 17):
        heading = re.search(rf"^### D{defect} — (.+)$", register, re.MULTILINE)
        assert heading and "Closed" in heading.group(1)

    disposition = register.split("## Disposition", maxsplit=1)[1].lower()
    assert "only d15 remains open" in disposition

"""6.1 and 6.3 are open. Live prose may not describe them as present.

``prompt_when_interactive`` is stored in defaults and never read. The MCP
server exposes two tools on a separate console script; it has no
resources and no prompts primitive. A hostile 1.0 audit found config,
architecture, ADR 008 and the analyzer-pool page stating the opposite.

This file is the class lint. The gates lift when the key is actually
read, or when ``mcp_server`` grows a resource, because those sentences
would then be true.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

_INTERACTIVE_CLAIMS = (
    (re.compile(r"ask for depth and policy on first run", re.I),
     "6.1 is open; the key is stored and never read"),
    (re.compile(r"prompted interactively on first run", re.I),
     "6.1 is open; nothing prompts"),
    (re.compile(r"answered interactively on first run at a terminal", re.I),
     "6.1 is open; selection comes from config"),
)

# The mirror image, live once the primitives ship: prose that still
# calls them unshipped. `_MCP_CLAIMS` catches a doc claiming too much;
# these catch one claiming too little, which after pair 01 is the lie.
_STALE_ABSENCE_CLAIMS = (
    (re.compile(r"not shipped \(6\.3\)", re.I),
     "resources and prompts shipped; 6.3 is no longer open"),
    (re.compile(r"only two tools", re.I),
     "tools are no longer the only primitive"),
    (re.compile(r"only the tool primitive shipped", re.I),
     "resources and prompts are registered"),
    (re.compile(r"(has|have) no resources", re.I),
     "resources are registered on the server"),
    (re.compile(r"no prompts primitive", re.I),
     "a prompts primitive is registered"),
)

_MCP_CLAIMS = (
    (re.compile(r"exposed as an MCP resource", re.I),
     "6.3 is open; Markdown is a field on the tool result"),
    (re.compile(r"MCP's three primitives cover", re.I),
     "only tools shipped; resources and prompts did not"),
    (re.compile(r"`?resources`? for the rubric and report", re.I),
     "no MCP resources are registered"),
    (re.compile(r"ships as a subcommand of this package", re.I),
     "the entry point is maintainability-agent-mcp, not a CLI subcommand"),
    (re.compile(r"server as a subcommand", re.I),
     "the entry point is maintainability-agent-mcp, not a CLI subcommand"),
)

# Operational / as-is surfaces. target-architecture.md is the destination
# and may describe unshipped primitives. release-plan task rows are work.
_LIVE = (
    ROOT / "README.md",
    ROOT / "docs" / "README.md",
    ROOT / "docs" / "architecture.md",
    ROOT / "docs" / "config-schema.md",
    ROOT / "docs" / "analyzer-pool.md",
    ROOT / "docs" / "cli.md",
    ROOT / "docs" / "decisions.md",
    ROOT / "docs" / "adr-008-translation-and-decision.md",
    ROOT / "docs" / "ide-agent-integration.md",
)


def _interactive_prompt_is_read() -> bool:
    """True only when something other than the default assignment reads the key."""
    for path in PACKAGE.glob("*.py"):
        for line in path.read_text(encoding="utf-8").splitlines():
            if "prompt_when_interactive" not in line:
                continue
            if re.search(r"\[.prompt_when_interactive.\]|\.get\(\s*[\"']prompt_when_interactive", line):
                return True
    return False


def _mcp_resources_exist() -> bool:
    text = (PACKAGE / "mcp_server.py").read_text(encoding="utf-8")
    return bool(re.search(r"list_resources|@\w*\.resource\b|Resource\(", text))


def _mcp_is_cli_subcommand() -> bool:
    """Either shape counts: an argparse subparser or a first-argument handoff.

    Forcing subparsers would be this lint dictating an implementation.
    What ADR 008 asks for is that `maintainability-agent mcp` works, and
    a dispatch on ``argv[0] == "mcp"`` satisfies that as well as
    ``add_parser("mcp")`` does.
    """
    cli = (PACKAGE / "cli.py").read_text(encoding="utf-8")
    return bool(
        re.search(r"add_parser\(\s*[\"']mcp[\"']", cli)
        or re.search(r"argv\[0\]\s*==\s*[\"']mcp[\"']", cli)
        or re.search(r"[\"']mcp[\"']\s*==\s*argv\[0\]", cli)
    )


def test_prompt_when_interactive_is_not_read() -> None:
    """The fixture for the 6.1 half of this file. Flip it by reading the key."""
    assert not _interactive_prompt_is_read(), (
        "prompt_when_interactive is now read; drop the 6.1 phrases from "
        "the stale-claim list or this assertion"
    )


def test_mcp_resources_and_the_subcommand_both_ship() -> None:
    """The 6.3 half, inverted now that resources landed.

    This assertion used to read `assert not _mcp_resources_exist()`. That
    was correct while only the tool primitive shipped, and it is the
    wrong claim the moment a resource is registered — an honesty lint
    that keeps insisting a shipped feature is absent is the same defect
    as prose insisting an absent one is present, facing the other way.

    Both halves are required together because ADR 008 names them
    together: the primitives are what chat reads, and the subcommand is
    how a user reaches the server without knowing a second binary exists.
    """
    assert _mcp_resources_exist(), (
        "no MCP resources are registered; pair 01 has not landed on this branch"
    )
    assert _mcp_is_cli_subcommand(), (
        "no mcp subcommand: `maintainability-agent mcp` does not dispatch, so the "
        "server is reachable only through the separate maintainability-agent-mcp "
        "console script (ADR 008 says it ships as a subcommand of this package)"
    )


def test_live_docs_do_not_claim_the_interactive_prompt_ships() -> None:
    if _interactive_prompt_is_read():
        return
    offenders = _matches(_INTERACTIVE_CLAIMS)
    assert not offenders, (
        "docs describe the first-run prompt as present while the key is unread:\n"
        + "\n".join(offenders)
    )


def test_live_docs_do_not_claim_mcp_resources_or_a_subcommand() -> None:
    if _mcp_resources_exist() and _mcp_is_cli_subcommand():
        return
    offenders = _matches(_MCP_CLAIMS)
    if _mcp_resources_exist():
        offenders = [row for row in offenders if "subcommand" in row]
    if _mcp_is_cli_subcommand():
        offenders = [row for row in offenders if "subcommand" not in row]
    assert not offenders, (
        "docs describe MCP resources or a CLI subcommand as present:\n"
        + "\n".join(offenders)
    )


def _adr_008_row() -> str:
    return next(
        line
        for line in (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8").splitlines()
        if line.startswith("| [008]")
    )


def test_live_docs_do_not_still_call_the_primitives_unshipped() -> None:
    """Once they ship, "not shipped (6.3)" is the false sentence.

    The original lint existed because four documents described resources
    as present while only tools shipped. The same discipline has to run
    the other way, or the register and the ADR will carry "only the tool
    primitive shipped" indefinitely and a reader will not go looking for
    a resource that is right there.
    """
    if not _mcp_resources_exist():
        return
    offenders = _matches(_STALE_ABSENCE_CLAIMS)
    assert not offenders, (
        "docs still describe the MCP resources/prompts primitives as unshipped:\n"
        + "\n".join(offenders)
    )


def test_the_register_no_longer_names_the_mcp_gap_on_adr_008() -> None:
    """Once resources ship, 6.3 is not the remaining gap on ADR 008.

    The row was written to stop "implemented except the band matrix"
    hiding 6.3 the way it once hid bands. That worked; now the row has to
    stop naming a gap that closed, for exactly the same reason.
    """
    if _mcp_resources_exist():
        row = _adr_008_row()
        lowered = row.lower()
        assert not ("6.3" in lowered or "resources/prompts" in lowered), (
            f"the ADR 008 register row still lists the MCP resources/prompts gap "
            f"as open: {row}"
        )
        return
    row = _adr_008_row()
    lowered = row.lower()
    assert "implemented" not in lowered or any(
        token in lowered for token in ("resource", "6.3", "prompt")
    ), f"ADR 008 register row hides the MCP resources gap: {row}"


def _matches(claims: tuple[tuple[re.Pattern[str], str], ...]) -> list[str]:
    found: list[str] = []
    for path in _LIVE:
        text = path.read_text(encoding="utf-8")
        for pattern, reason in claims:
            match = pattern.search(text)
            if match:
                found.append(
                    f"{path.relative_to(ROOT)}: {reason} — matched {match.group(0)!r}"
                )
    return found

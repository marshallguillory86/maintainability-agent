"""Agent-instruction pack: per-target file emission.

Renders the "Maintainability Standards for AI-Assisted Code" markdown
that ``--init-agent-standards`` writes into AGENTS.md / CLAUDE.md / etc.
Extracted from ``renderers.py`` (2026-05-11) so the renderer module
stays under the maintainability config's warn threshold for file
length and so the agent-instruction concern lives on its own.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any


def instruction_body(target: str, config: dict[str, Any]) -> str:
    pack = config.get("instruction_pack", {})
    project = pack.get("project_name", "this repository")
    test_policy = pack.get("test_policy", "tests for meaningful behavior changes")
    notes = pack.get("architecture_notes", [])
    lines = [
        "# Maintainability Standards for AI-Assisted Code",
        "",
        f"Project: {project}",
        f"Target: {target}",
        "",
        "## Running the Audit",
        "",
        "Chat is the primary surface: drive the audit through the local MCP",
        "server from your chat host. Calling `audit_repository` is the",
        "first step: do not inspect configuration first and do not ask the",
        "user which config to use — the tool resolves that itself and",
        "returns the questions when there are any. An unconfigured",
        "repository is",
        "asked one structured setup set through MCP elicitation or the",
        "host's question UI — never a free-text ask. Present the returned",
        "report in chat, and never write a report file until the user has",
        "chosen a location. The CLI is the automation/CI door: pipelines",
        "run `maintainability-agent --fail-on-gate` with explicit output",
        "paths.",
        "",
        "## Prime Directive",
        "",
        "Write code that is easy for the next developer to understand, test, debug, and safely change.",
        "Do not optimize for passing numeric thresholds while making the implementation less clear.",
        "",
        "## Defaults",
        "",
        "- Keep changes small, bounded, and reviewable.",
        "- Preserve existing architecture, naming, and module boundaries.",
        "- Prefer boring, obvious code over clever abstractions.",
        "- Separate business logic from UI and infrastructure where the repo supports that boundary.",
        f"- Follow the repo test policy: {test_policy}.",
        "- Add tests around meaningful behavior and edge cases, not implementation trivia.",
        "- Make failure modes visible and debuggable.",
        "- Avoid broad rewrites unless explicitly requested.",
        "- Explain false positives or justified complexity instead of contorting code.",
        "",
        "## Maintainability Targets",
        "",
        "- Functions should generally stay below 50 lines; 80+ requires strong justification.",
        "- Approximate complexity above 10 deserves review; above 15 needs refactor or justification.",
        "- Large files should have a clear reason to stay large.",
        "- Duplicate policy/business logic should be consolidated before it drifts.",
        "- Public docs, comments, tests, and code should describe the same behavior.",
        "",
    ]
    if notes:
        lines.extend(["## Project Architecture Notes", ""])
        lines.extend(f"- {note}" for note in notes)
        lines.append("")
    lines.extend(
        [
            "## Before Closeout",
            "",
            "- Run native tests/lints.",
            "- Run the maintainability audit.",
            "- Report commands and results.",
            "- Keep follow-up recommendations separate from the completed patch.",
        ]
    )
    return "\n".join(lines)


#: Each agent and the file it actually reads for repo standing
#: instructions. One declaration, because this list was written out three
#: times — here, and twice in `cli.py` as `choices` and as the default —
#: so adding a target meant remembering all three or shipping one the CLI
#: refused to accept.
#:
#: A target belongs here only when the path it writes is the path that
#: agent genuinely reads. Emitting a plausible-looking file an agent never
#: opens is worse than having no target: it looks configured and does
#: nothing.
INSTRUCTION_TARGETS: dict[str, str] = {
    "generic": "AI-MAINTAINABILITY.md",
    "claude-code": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/maintainability.mdc",
    "copilot": ".github/copilot-instructions.md",
    "windsurf": ".windsurf/rules/maintainability.md",
}


class UnknownTarget(ValueError):
    """A target with no built-in convention and no path supplied."""


def instruction_path_for_target(
    target: str, output_dir: Path, overrides: dict[str, str] | None = None
) -> Path:
    """Where this agent's standing instructions go.

    An override wins over the built-in table, because a convention can
    change or be site-specific, and the person running the command knows
    their agent better than this table does.

    A target nobody has a convention for is **refused** rather than given a
    generated filename. The fallback that used to sit here —
    ``{target}-maintainability.md`` — was unreachable anyway, because the
    CLI's `choices` rejected unknown targets first; and had it been
    reachable it would have written a plausible-looking file the agent
    never opens, which is worse than no target at all. It looks configured
    and does nothing.
    """
    if overrides and target in overrides:
        return output_dir / overrides[target]
    if target in INSTRUCTION_TARGETS:
        return output_dir / INSTRUCTION_TARGETS[target]
    raise UnknownTarget(
        f"no known instructions path for {target!r}. Pass "
        f"--target-path {target}=PATH to say where that agent reads its "
        f"standing instructions. Known targets: {', '.join(INSTRUCTION_TARGETS)}"
    )


def write_instruction_pack(
    targets: list[str],
    output_dir: Path,
    config: dict[str, Any],
    overrides: dict[str, str] | None = None,
) -> list[str]:
    # Each instruction file is a product-artifact write: `output_dir`
    # comes from a person (`--instructions-output-dir`), so the write is
    # bound to that directory and refuses a symlinked route the audited
    # tree could plant beneath it (Grok 63ab820 audit).
    from ._safe_write import write_artifact

    written: list[str] = []
    for target in targets:
        path = instruction_path_for_target(target, output_dir, overrides)
        write_artifact(output_dir, path, instruction_body(target, config) + "\n")
        written.append(str(path))
    return written

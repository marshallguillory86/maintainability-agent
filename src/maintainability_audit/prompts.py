"""What we hand to an AI coding agent, as opposed to what we show a human.

Split from ``renderers.py`` (2026-08-07) when scoring gained per-dimension
diagnostics. ``renderers`` answers "what does a reviewer read"; this module
answers "what is the agent told to do, and in what order". Keeping them
apart matters because the prompt is the product's actual differentiator —
every other tool in this space stops at a list of findings.
"""
from __future__ import annotations

from typing import Any

from . import _evidence_view as view
from ._attestation import render_attestation  # noqa: F401
from ._hostile_prompt import render_hostile_audit_prompt  # noqa: F401


def render_ai_prompt(report: dict[str, Any]) -> str:
    summary = report["summary"]
    score = report["score"]
    lines = [
        "# AI Remediation Prompt",
        "",
        "You are working in a git repository that has just produced a maintainability audit.",
        "",
        "Your task is to fix the highest-value maintainability issues in a small, reviewable change.",
        "",
        "Rules:",
        "",
        "- Do not rewrite the whole codebase.",
        "- Do not change public behavior unless a finding explicitly requires it.",
        "- Prefer existing architecture, naming, and local patterns.",
        "- Add or update tests for meaningful behavior before changing production code where practical.",
        "- Keep unrelated refactors out of scope.",
        "- If a finding is a false positive, explain why and leave the code unchanged.",
        "- After changes, run the repo's native tests/lints and this maintainability audit again.",
        "",
        "Audit summary:",
        "",
        f"- Maintainability estimate: {view.estimate(score)} (range {view.score_range(score)})",
        f"- Verified grade: {view.verified_grade(score)}",
        # Stated in every state, not only when something is missing.
        # `remediation_note` below prints the detail when evidence is
        # incomplete and nothing at all when it is complete, so a
        # complete prompt never said so — leaving an agent unable to
        # tell verified evidence from an unprinted status, which are
        # worth different amounts of confidence in the line above.
        f"- Evidence status: {score['evidence_status']['status']} "
        f"(profile `{view.profile(score)}`)",
        f"- Files scanned: {summary['files_scanned']}",
        f"- File failures: {summary['file_failures']}",
        f"- Function failures: {summary['function_failures']}",
        f"- Duplicate blocks: {summary['duplicate_blocks']}",
        f"- Risk findings: {summary['risk_findings']}",
        f"- Hard gate failures: {summary['hard_gate_failures']}",
        "",
    ]
    lines.extend(prompt_analyzer_caveat(report))
    # The prompt is the product artifact (H1): its remedy follows the
    # same report fact as every other skin, never a stale default.
    lines.extend(view.remediation_note(
        score, report.get("analyzer_coverage") is not None))
    lines.extend(prompt_escalation_note(report))
    lines.extend(prompt_work_order(report))
    lines.extend(prompt_tdd_section(report))
    lines.extend(prompt_semantic_section(report))
    lines.extend(prompt_pressure_section(score))
    lines.extend(prompt_focus_sections(report))
    lines.extend(prompt_deliverable())
    return "\n".join(lines)


def render_agent_instructions(report: dict[str, Any]) -> str:
    return "\n".join(
        [
            "# Maintainability Remediation Instructions",
            "",
            "Use these instructions when asking an AI coding agent to fix audit findings.",
            "",
            "## Operating Rules",
            "",
            "- Treat maintainability as disciplined engineering, not cosmetic cleanup.",
            "- Work from the audit findings, not from broad refactor instinct.",
            "- Keep the patch small, bounded, and reviewable.",
            "- Preserve existing architecture unless a finding proves the boundary is wrong.",
            "- Add tests for behavior changes and for risky untested paths.",
            "- Do not chase unrelated style churn.",
            "- Mark false positives explicitly with rationale.",
            "- Run native repo verification and rerun the maintainability audit before closeout.",
            "",
            "## Current Audit Context",
            "",
            f"- Mode: `{report.get('mode', 'full')}`",
            f"- Maintainability estimate: `{view.estimate(report['score'])}`"
            f" (range {view.score_range(report['score'])})",
            f"- Verified grade: `{view.verified_grade(report['score'])}`",
            f"- Evidence: {view.status_sentence(report['score'], report.get('analyzer_coverage') is not None)}",
            *view.reason_lines(report["score"], bullet="  - "),
            *view.instruction_note(report["score"]),
            f"- Files scanned: {report['summary']['files_scanned']}",
            f"- Hard gate failures: {report['summary']['hard_gate_failures']}",
            f"- Function failures: {report['summary']['function_failures']}",
            f"- File failures: {report['summary']['file_failures']}",
            "",
            "Start with hard gates and failed hotspots. Leave larger architecture notes as follow-up recommendations.",
        ]
    )


# Re-exported so `prompts.prompt_pressure_section` and its siblings keep
# resolving after the split above: the move is about file size, and
# `prompts` is presentation rather than a boundary, so an import here
# costs nothing that matters.
from ._prompt_sections import (  # noqa: E402,F401 - re-export after the split
    DIMENSION_GUIDANCE,
    bulleted_section,
    dead_code_section,
    idiom_section,
    near_duplicate_section,
    prompt_analyzer_caveat,
    prompt_deliverable,
    prompt_escalation_note,
    prompt_focus_sections,
    prompt_pressure_section,
    prompt_semantic_section,
    prompt_tdd_section,
    prompt_work_order,
)

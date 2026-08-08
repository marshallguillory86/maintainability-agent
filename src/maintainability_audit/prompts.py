"""What we hand to an AI coding agent, as opposed to what we show a human.

Split from ``renderers.py`` (2026-08-07) when scoring gained per-dimension
diagnostics. ``renderers`` answers "what does a reviewer read"; this module
answers "what is the agent told to do, and in what order". Keeping them
apart matters because the prompt is the product's actual differentiator —
every other tool in this space stops at a list of findings.
"""
from __future__ import annotations

from typing import Any

from ._hotspots import hotspot_measure, hotspot_name


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
        f"- Overall score: {score['overall']} / 5 ({score['grade']})",
        f"- Files scanned: {summary['files_scanned']}",
        f"- File failures: {summary['file_failures']}",
        f"- Function failures: {summary['function_failures']}",
        f"- Duplicate blocks: {summary['duplicate_blocks']}",
        f"- Risk findings: {summary['risk_findings']}",
        f"- Hard gate failures: {summary['hard_gate_failures']}",
        "",
    ]
    lines.extend(prompt_pressure_section(score))
    lines.extend(prompt_focus_sections(report))
    lines.extend(prompt_deliverable())
    return "\n".join(lines)


DIMENSION_GUIDANCE = {
    "file_size": "files carrying too many responsibilities — split along a real boundary, never by line count",
    "declarations": "functions that are too long or too branchy to hold in your head at once",
    "duplication": "repeated blocks — consolidate only where the copies represent the same responsibility",
    "risk": "configured risk patterns that need a human decision, not a blanket rewrite",
    "gates": "hard policy gates that are failing outright",
}


def prompt_pressure_section(score: dict[str, Any]) -> list[str]:
    """Tell the agent *what kind* of trouble this repo is in, and how much.

    A letter grade is not actionable. These figures are multiples of what
    a mature open-source codebase carries on the same measure, so ``3.1x``
    means "three times the duplication real code lives with" — which is a
    statement an agent can prioritize against. Dimensions at or below 1.0
    are deliberately left out: they are already normal, and listing them
    invites busywork.
    """
    dimensions = score.get("dimensions") or {}
    elevated = sorted(
        ((name, value) for name, value in dimensions.items() if value > 1.0),
        key=lambda item: -item[1],
    )
    lines: list[str] = []
    if elevated:
        lines.extend(
            [
                "Where this repo is worse than typical real-world code",
                "(1.0x = the median of a mature open-source corpus; only elevated dimensions are listed):",
                "",
            ]
        )
        lines.extend(f"- **{name}** at {value}x — {DIMENSION_GUIDANCE.get(name, '')}" for name, value in elevated)
        lines.append("")
        lines.append(f"Start with `{elevated[0][0]}`. It is the dimension costing this repo the most.")
        lines.append("")
    elif dimensions:
        lines.extend(
            [
                "No dimension exceeds what a mature open-source codebase carries. "
                "Prefer leaving this repo alone over manufacturing work; fix only findings listed below.",
                "",
            ]
        )
    for blocker in score.get("grade_blockers") or []:
        lines.append(f"- Grade capped: {blocker}")
    if score.get("grade_blockers"):
        lines.append("")
    return lines


def prompt_focus_sections(report: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    lines.extend(bulleted_section("Start with these hard gates:", report["hard_gate_failures"]))
    hotspot_lines = [
        f"`{i['path']}:{i['start_line']}` {hotspot_name(i)} ({hotspot_measure(i)})."
        for i in report["function_hotspots"][:10]
    ]
    lines.extend(bulleted_section("Function hotspots to inspect first:", hotspot_lines))
    large_files = [
        f"`{i['path']}` has {i['lines']} lines ({i['status']})."
        for i in report["largest_files"][:10]
        if i["status"] in {"warn", "fail"}
    ]
    lines.extend(bulleted_section("Large files to inspect for responsibility splits:", large_files))
    risks = [f"`{i['path']}:{i['line']}` {i['name']}: {i['text']}" for i in report["risk_findings"][:20]]
    lines.extend(bulleted_section("Risk pattern findings to verify:", risks))
    dupes = [
        f"Repeated block appears {i['count']} times near: {', '.join(i['locations'][:5])}"
        for i in report["duplicate_blocks"][:5]
    ]
    lines.extend(bulleted_section("Duplicate blocks to inspect:", dupes))
    return lines


def bulleted_section(title: str, items: list[str]) -> list[str]:
    if not items:
        return []
    return [title, "", *[f"- {item}" for item in items], ""]


def prompt_deliverable() -> list[str]:
    return [
        "Deliverable:",
        "",
        "1. Briefly restate which findings you will fix.",
        "2. Make the smallest coherent patch.",
        "3. Add or update tests when behavior changes or when the current code is hard to verify.",
        "4. Report commands run and results.",
        "5. Leave any larger architectural recommendations as follow-up items, not hidden extra changes.",
    ]


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
            f"- Score: `{report['score']['overall']} / 5 ({report['score']['grade']})`",
            f"- Files scanned: {report['summary']['files_scanned']}",
            f"- Hard gate failures: {report['summary']['hard_gate_failures']}",
            f"- Function failures: {report['summary']['function_failures']}",
            f"- File failures: {report['summary']['file_failures']}",
            "",
            "Start with hard gates and failed hotspots. Leave larger architecture notes as follow-up recommendations.",
        ]
    )



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
from ._hotspots import hotspot_measure, hotspot_name
from ._work_order import prompt_items


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
    lines.extend(prompt_semantic_section(report))
    lines.extend(prompt_pressure_section(score))
    lines.extend(prompt_focus_sections(report))
    lines.extend(prompt_deliverable())
    return "\n".join(lines)


def prompt_semantic_section(report: dict[str, Any]) -> list[str]:
    """Semantic findings by class, each labeled as strongly as it deserves.

    A typed fact, a configured policy violation and a design-review
    candidate are three different claims (ADR 003), and flattening them
    into one list would launder configuration and heuristics into
    universal rules. Candidates state their evidence and ask for review;
    they never prescribe the replacement design, because the evidence
    does not prove one.
    """
    findings = report.get("semantic_findings") or []
    if not findings:
        return []
    lines = ["## Semantic findings (ADR 003)", ""]
    for finding in findings:
        evidence = finding.get("source_evidence") or {}
        location = evidence.get("path") or ""
        if finding["class"] == "universal":
            lines.append(
                f"- Typed fact: `{location}` — {finding['message']} "
                f"(compiler evidence {evidence.get('diagnostic_code')})."
            )
        elif finding["class"] == "policy":
            lines.append(
                f"- Configured policy `{finding.get('policy_entry')}`: "
                f"`{location}` — {finding['message']}."
            )
        else:
            names = ", ".join(evidence.get("operation_names") or [])
            lines.append(
                f"- Design-review candidate: `{location}` — operation names "
                f"[{names}] recur across {', '.join(evidence.get('roles') or [])} "
                f"roles. {finding['message']}"
            )
    lines.append("")
    return lines


def prompt_analyzer_caveat(report: dict[str, Any]) -> list[str]:
    """Where the headline number came from, when other tools also spoke.

    `--analyzers` can put ten tools' findings into this prompt. The
    estimate uses those readings only for dimensions they fully measured;
    everything else stays on the fallback tier. The prompt has to say
    which happened, or a list of analyzer findings under the headline
    number reads as though every tool produced it.

    Only when there is analyzer output to qualify. A caveat printed
    unconditionally would describe disagreement to every zero-install
    user who never ran a second tool, which is the same defect facing
    the other way.
    """
    if not (report.get("analyzer_measurements") or report.get("analyzer_findings")):
        return []
    scored = (report.get("score") or {}).get("analyzer_scored_dimensions") or []
    if scored:
        return [
            "**The maintainability estimate above uses the analyzer readings** for "
            f"{', '.join(scored)} — external tools are the primary evidence here. "
            "Dimensions no analyzer measured kept the fallback tier's reading rather "
            "than being counted clean. Where the two sources disagree the range "
            "widens to contain both; they are never averaged.",
            "",
        ]
    return [
        "**The maintainability estimate above comes from the built-in detectors.** "
        "The analyzers ran but measured none of the dimensions the rubric scores, so "
        "their output is reported here and not scored. Treat an analyzer finding as "
        "evidence about the code, never as a change to the score.",
        "",
    ]


def prompt_escalation_note(report: dict[str, Any]) -> list[str]:
    """Tell the agent what is deliberately absent, and why.

    Silence would leave it to re-derive the same finding from the
    report's own tables and offer the patch anyway. Naming the exclusion
    is what makes it hold.
    """
    escalated = report.get("design_review_candidates") or []
    if not escalated:
        return []
    return [
        f"**{len(escalated)} finding(s) are deliberately excluded from this "
        "prompt.** Each was fixed before and came back, so the same advice is "
        "known not to hold and repeating it would produce the same patch and "
        "the same return. They are listed in the report as design review "
        "candidates and need a human decision about the surrounding design, "
        "not another edit. Do not fix them here, and do not work around them.",
        "",
    ]


def prompt_work_order(report: dict[str, Any]) -> list[str]:
    """The ordered work, leading the prompt, Major Projects withheld.

    This is ADR 007 §3's structural answer to nit-loops. A prompt that
    opens with eighty line-length violations is handing an agent Fill-Ins
    in the position reserved for the work that matters, and the agent
    will dutifully spend its budget there.

    Major Projects are named in the report and excluded here: an agent
    told to deduplicate a pattern across forty files produces exactly the
    sprawling, unreviewable diff a bounded prompt exists to prevent.
    """
    # Withhold anything the history shows was fixed and came back
    # twice. Naming it as a design candidate while asking an agent to
    # patch it a third time would change nothing.
    escalated = {
        item["fingerprint"] for item in report.get("design_review_candidates") or []
    }
    items = prompt_items(report.get("work_order") or [], escalated=escalated)
    if not items:
        return []
    lines = [
        "Work in this order. The first items are the highest value for the "
        "least change; stop when the change stops being reviewable.",
        "",
    ]
    for index, item in enumerate(items, start=1):
        location = item["path"] + (f":{item['line']}" if item.get("line") else "")
        lines.append(f"{index}. **{item['title']}** — {item['target']}")
        lines.append(f"   - Location: `{location}`")
        lines.append(f"   - Why it matters: {item['rationale']}")
        if item["class_delta"]:
            lines.append(
                f"   - Clearing all {item['class_count']} of these is worth "
                f"+{item['class_delta']:.2f} to the maintainability estimate."
            )
    lines.extend([
        "",
        f"Verify with: `{items[0]['verification']}`",
        "",
    ])

    withheld = [i for i in (report.get("work_order") or [])
                if i["band"] == "major-project"]
    if withheld:
        names = ", ".join(sorted({i["title"] for i in withheld})[:3])
        lines.extend([
            f"**Not in scope for this change:** {len(withheld)} finding(s) need a "
            f"design decision before code moves ({names}). They are in the report. "
            "Do not attempt them here.",
            "",
        ])
    return lines


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
        # `is not None` first: an unmeasured dimension is legitimate --
        # a class-only tree has no banded declaration pressure -- and a
        # comparison against None crashed the prompt for exactly that
        # repository.
        ((name, value) for name, value in dimensions.items()
         if value is not None and value > 1.0),
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
    for blocker in view.grade_blockers(score):
        lines.append(f"- Grade capped: {blocker}")
    if view.grade_blockers(score):
        lines.append("")
    return lines


def _escalated_fingerprints(report: dict[str, Any]) -> set[str]:
    """Findings the history shows do not stay fixed.

    Read by every section that names work, not only the work order. The
    first version withheld them from `prompt_work_order` alone and this
    function went on listing the same finding under "inspect first" —
    verified end to end on a real fix/return/fix/return history. A rule
    enforced on one path and not another is not enforced.
    """
    return {
        item["fingerprint"] for item in report.get("design_review_candidates") or []
    }


def prompt_focus_sections(report: dict[str, Any]) -> list[str]:
    from ._identity import declaration_identities, file_fingerprint

    escalated = _escalated_fingerprints(report)
    # Looked up, not rebuilt. `escalated` holds identities the history
    # recorded, so anything compared against it has to be numbered over
    # the same population — a hotspot that only warns has no identity
    # here, and cannot be escalated, so `None` correctly stays listed.
    identities = declaration_identities(report)
    lines: list[str] = []
    lines.extend(bulleted_section("Start with these hard gates:", report["hard_gate_failures"]))
    hotspot_lines = [
        f"`{i['path']}:{i['start_line']}` {hotspot_name(i)} ({hotspot_measure(i)})."
        for i in report["function_hotspots"][:10]
        if identities.get((i["path"], i["name"], i["start_line"])) not in escalated
    ]
    lines.extend(bulleted_section("Function hotspots to inspect first:", hotspot_lines))
    large_files = [
        f"`{i['path']}` has {i['lines']} lines ({i['status']})."
        for i in report["largest_files"][:10]
        if i["status"] in {"warn", "fail"}
        and file_fingerprint(i["path"]) not in escalated
    ]
    lines.extend(bulleted_section("Large files to inspect for responsibility splits:", large_files))
    risks = [f"`{i['path']}:{i['line']}` {i['name']}: {i['text']}" for i in report["risk_findings"][:20]]
    lines.extend(bulleted_section("Risk pattern findings to verify:", risks))
    dupes = [
        f"Repeated block appears {i['count']} times near: {', '.join(i['locations'][:5])}"
        for i in report["duplicate_blocks"][:5]
    ]
    lines.extend(bulleted_section("Duplicate blocks to inspect:", dupes))
    lines.extend(near_duplicate_section(report))
    lines.extend(dead_code_section(report))
    lines.extend(idiom_section(report))
    return lines


def idiom_section(report: dict[str, Any]) -> list[str]:
    """Two libraries doing one job, with the minority usage named.

    Consolidating on the majority library is usually right, and naming
    which one is in the minority is what makes the finding actionable.
    But this is the finding most likely to be a deliberate migration
    caught mid-flight, so the instruction is to check intent first.
    """
    findings = report.get("divergent_idioms") or []
    if not findings:
        return []
    items = []
    for item in findings:
        packages = ", ".join(f"`{p['package']}` in {p['files']} file(s)" for p in item["packages"])
        minority = item["packages"][-1]
        items.append(
            f"**{item['concern']}** is served by {packages}. The least-used is "
            f"`{minority['package']}` — for example `{minority['example']}`."
        )
    lines = bulleted_section("Competing libraries for one concern:", items)
    lines.extend(
        [
            "Consolidating on the majority library is usually right, but confirm this is not a "
            "migration in progress before moving anything. If it is deliberate — a deprecated path "
            "being retired, or a genuine capability difference — say so and leave it.",
            "",
        ]
    )
    return lines


def dead_code_section(report: dict[str, Any]) -> list[str]:
    """Debris an agent can delete outright, with the caveat that matters.

    Every entry is private and unreferenced, so deletion is usually safe.
    "Usually" is doing real work there: a name reached only through
    dynamic dispatch looks identical to a dead one from the outside, so
    the instruction is to verify before removing rather than to trust the
    finding.
    """
    findings = report.get("dead_code") or []
    if not findings:
        return []
    items = [
        f"`{item['path']}:{item['start_line']}` `{item['name']}` ({item['lines']} lines) is private "
        "and referenced nowhere in the repository"
        for item in findings[:10]
    ]
    lines = bulleted_section("Unreferenced private declarations — candidates for deletion:", items)
    lines.extend(
        [
            "Confirm each one before deleting. A name reached only through dynamic dispatch — "
            "`getattr`, a string-keyed lookup table, a framework that resolves by convention — "
            "is indistinguishable from a dead one here. If a finding is reachable that way, say so "
            "and leave it.",
            "",
        ]
    )
    return lines


def near_duplicate_section(report: dict[str, Any]) -> list[str]:
    """Name the existing helper each near-copy should collapse into.

    This is the one finding that comes with its own fix. "There is
    duplication" is not actionable; "``toAtomicAmount`` at
    ``TradeTicket.tsx:862`` already does this" is. Cross-file pairs lead,
    because those are the ones where the second copy was written by
    someone — or something — that did not know the first existed.
    """
    findings = report.get("near_duplicates") or []
    if not findings:
        return []
    ordered = sorted(findings, key=lambda item: (not item.get("cross_file"), -item["similarity"]))
    items = [
        f"`{item['path']}:{item['start_line']}` `{item['name']}` is {item['similarity']:.0%} identical to "
        f"`{item['duplicate_of']['name']}` at `{item['duplicate_of']['path']}:{item['duplicate_of']['start_line']}`"
        + (" (different file — likely written without knowing the first existed)" if item.get("cross_file") else "")
        for item in ordered[:10]
    ]
    lines = bulleted_section(
        "Near-duplicate logic — prefer reusing the existing declaration over keeping both:", items
    )
    lines.extend(
        [
            "Collapse a pair only when both copies genuinely represent the same responsibility. "
            "Two functions that merely look alike today, and would need to change for different reasons "
            "tomorrow, should stay separate — say so rather than merging them.",
            "",
        ]
    )
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



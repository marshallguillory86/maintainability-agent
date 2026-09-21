"""The sections a remediation prompt is composed from.

Split from `prompts` when that module reached exactly 500 lines — this
project's own `max_file_lines`, where the next line added fails the
gate. The same split `_html_report_sections` already makes for
`_html_view`, and for the same reason: **composing a document and
building the pieces it composes are two jobs**, and only the second
grows every time a finding class is added.

`prompts` keeps the two entry points a caller names — `render_ai_prompt`
and `render_agent_instructions` — and this holds what they assemble: one
builder per finding class, the dimension guidance table, and the small
shared helpers. Adding a finding class now lands here without touching
the emitter, which is what the seam is for.

The public names are re-exported from `prompts`, so no caller changes.
That is available here and was not for `evidence`, whose split had to
move a name outright: `evidence` is the one module in this package that
imports nothing, and a re-export would have been an import.
"""
from __future__ import annotations

from typing import Any

from . import _evidence_view as view
from ._handoff import (
    escalated_fingerprints,
    is_withheld,
    prompt_items,
    withheld_targets,
)
from ._hotspots import hotspot_measure, hotspot_name
from ._security_work_order import KEY as SECURITY_WORK_ORDER
from ._security_work_order import severity_counts
from ._tdd_view import tdd_sentences


def _refused(withheld: set[Any] | None, finding: dict[str, Any]) -> bool:
    """Whether the bounded prompt already refused this finding (D207).

    `None` rather than an empty set is the "nobody asked" case: these
    section builders are public and called directly by tests and by
    other skins, and a caller that passes nothing gets the list it always
    got. Only `prompt_focus_sections`, which renders beside the paragraph
    that says "Do not attempt them here", passes the set.
    """
    return bool(withheld) and is_withheld(withheld, finding)


def prompt_tdd_section(report: dict[str, Any]) -> list[str]:
    sentences = tdd_sentences(report.get("tdd_structure"))
    if not sentences:
        return []
    return ["## TDD-shaped tests", "", *sentences, ""]


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
    score = report.get("score") or {}
    if not view.is_scored(score):
        # No estimate was issued, so none can have a source (D172). The
        # analyzer output is still evidence about the code, and says so.
        return [
            "**No maintainability estimate was issued for this run**, so none is "
            "attributed to the analyzers. Their output is reported here as "
            "evidence about the code, never as a change to a score.",
            "",
        ]
    scored = score.get("analyzer_scored_dimensions") or []
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


def prompt_security_pillar(report: dict[str, Any]) -> list[str]:
    """What the security pillar reported, stated where an agent reads the run (D176).

    Evidence, never a task: security remediation is secure-code-agent's own
    work order, not this prompt's. But a prompt that says nothing about
    security lets an agent read silence as a clean bill, which is the one
    reading ADR 007 exists to prevent.
    """
    entry = next((p for p in report.get("pillars") or [] if p.get("pillar") == "security"), None)
    if entry is None:
        return []
    if not entry.get("delegated_to"):
        return [f"**Security pillar: not measured.** {entry.get('reason')}.", ""]
    producer = entry.get("delegated_to") or "the delegated tool"
    version = f" {entry['producer_version']}" if entry.get("producer_version") else ""
    condition = "not graded" if entry.get("condition") is None else f"{entry['condition']:.1f}"
    counts = severity_counts(entry)
    found = f" Findings: {counts}." if counts else ""
    # Where that tool's work order is, when this run kept it (D179). The
    # prompt names it rather than absorbing it: the security findings are
    # not this prompt's task, and are not re-ranked into it.
    where = (f" Its own work order for them is `{SECURITY_WORK_ORDER}`, in the report."
             if report.get(SECURITY_WORK_ORDER) else "")
    return [
        f"**Security pillar (measured by {producer}{version}):** posture "
        f"{entry.get('posture')}, practice level {entry.get('practice')}, condition "
        f"{condition}.{found} Its findings are that tool's work order, not this "
        f"one.{where}",
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


def _withheld_paragraph(report: dict[str, Any]) -> list[str]:
    """Name what was deliberately left out, so its absence is not a gap.

    An agent that finds a Major Project in the report but not in the
    prompt has to guess whether it was withheld or missed. Saying so
    costs four lines and removes the guess.
    """
    withheld = [i for i in (report.get("work_order") or [])
                if i["band"] == "major-project"]
    if not withheld:
        return []
    names = ", ".join(sorted({i["title"] for i in withheld})[:3])
    return [
        f"**Not in scope for this change:** {len(withheld)} finding(s) need a "
        f"design decision before code moves ({names}). They are in the report. "
        "Do not attempt them here.",
        "",
    ]


def _prompt_work_items(report: dict[str, Any]) -> list[dict[str, Any]]:
    """The items this prompt hands to an agent, after withholding."""
    # Withhold anything the history shows was fixed and came back
    # twice. Naming it as a design candidate while asking an agent to
    # patch it a third time would change nothing.
    return prompt_items(report.get("work_order") or [], escalated=escalated_fingerprints(report))


def prompt_has_work(report: dict[str, Any]) -> bool:
    """Whether this prompt hands an agent anything to change (D173).

    A report with no `work_order` key at all — stored before the field
    existed, or assembled by hand — cannot say there is nothing to do, so
    it keeps the prompt it always had rather than reading as "Nothing to
    do" over findings it does carry.
    """
    return "work_order" not in report or bool(_prompt_work_items(report))


def _no_prompt_work(report: dict[str, Any]) -> list[str]:
    """What the prompt says in place of a task when there is none (D173).

    Two cases, because they are different facts. An empty work order is the
    chat report's "Nothing to do", in the same words. A work order whose
    every item was withheld — a Major Project, or a finding escalated for
    design review — has work in it, none of it an agent's to patch.
    """
    if not report.get("work_order"):
        from ._work_order_view import NOTHING_TO_DO

        return [NOTHING_TO_DO, "", "Do not change code on the strength of this audit.", ""]
    return [
        "**Nothing in scope for this prompt.** Every work-order item needs a "
        "design decision or keeps coming back, so none is handed to an agent. "
        "They are in the report. Do not change code on the strength of this "
        "prompt.",
        "",
        *_withheld_paragraph(report),
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
    items = _prompt_work_items(report)
    if not items:
        return _no_prompt_work(report) if "work_order" in report else []
    lines = [
        # What the order is, not what it is worth (D169): `prompt_items`
        # promotes risk-5 classes and keeps one item per class, so this
        # list and the report's table can lead with different items.
        "Work in this order: severe findings (risk 5) first, then the work "
        "order's own order, one item per kind of finding. Stop when the "
        "change stops being reviewable.",
        "",
    ]
    for index, item in enumerate(items, start=1):
        location = item["path"] + (f":{item['line']}" if item.get("line") else "")
        lines.append(f"{index}. **{item['title']}** — {item['target']}")
        # One row now stands for its whole class (D159), so a count
        # above one says where the rest are rather than leaving the
        # single location reading as the only instance.
        count = item.get("class_count") or 1
        files = item.get("class_paths") or 1
        if count > 1:
            where = f"across {files} files, " if files > 1 else ""
            lines.append(f"   - First of {count} {where}starting at: `{location}`")
        else:
            lines.append(f"   - Location: `{location}`")
        lines.append(f"   - Why it matters: {item['rationale']}")
        if item["class_delta"]:
            lines.append(
                f"   - Clearing all {item['class_count']} of these is worth "
                f"+{item['class_delta']:.2f} to the maintainability estimate."
            )
        elif count > 1:
            lines.append(
                f"   - The other {count - 1} are listed in the report; the "
                "score does not move until the class is cleared."
            )
    lines.extend([
        "",
        f"Verify with: `{items[0]['verification']}`",
        "",
    ])
    lines.extend(_withheld_paragraph(report))
    return lines


DIMENSION_GUIDANCE = {
    "file_size": "files carrying too many responsibilities — split along a real boundary, never by line count",
    "declarations": "functions that are too long or too branchy to hold in your head at once",
    "duplication": "repeated blocks — consolidate only where the copies represent the same responsibility",
    "risk": "configured risk patterns that need a human decision, not a blanket rewrite",
    "gates": "hard policy gates that are failing outright",
}


def corpus_span(score: dict[str, Any]) -> str:
    """How much of what this scanner parses the corpus holds, counted (D168).

    Read off `score.reference`, the two lists the corpus note is built
    from. The prompt typed "eight of the ten parsed languages" while the
    note on the same report said thirteen of fourteen: a count written
    as prose goes stale the first time a language is added, and nothing
    fails when it does.
    """
    reference = score.get("reference") or {}
    held = len(reference.get("corpus_languages") or ())
    parsed = held + len(reference.get("unanchored_languages") or ())
    return f"{held} of the {parsed} parsed languages"


def prompt_pressure_section(score: dict[str, Any], present: Any = None) -> list[str]:
    """Tell the agent *what kind* of trouble this repo is in, and how much.

    A letter grade is not actionable. These figures are multiples of what
    a mature open-source codebase carries on the same measure, so ``3.1x``
    means "three times the duplication real code lives with" — which is a
    statement an agent can prioritize against. Dimensions at or below 1.0
    are deliberately left out: they are already normal, and listing them
    invites busywork.

    **Nothing here is printed when the overall estimate was withheld
    (D163).** A corpus multiple *is* a score — it is a rate compared
    against a calibrated median — so a run that refused to issue an
    overall on too little evidence cannot turn around and rank this
    repository's dimensions against that same corpus. P7 governs both.

    The demo tree is the case that made it visible: the report said
    `Not scored` and its own README said *"only the rates are
    withheld"*, while the file the README calls the work order opened
    with `declarations at 3.9x` and `Start with declarations`. The
    complete Markdown report on the same run printed no multiples. Only
    the advertised product file did.

    The work order itself is unaffected and still names every finding —
    a finding is an observation, not a rate, and withholding those would
    leave an undersized repository with nothing at all.
    """
    if not view.is_scored(score):
        # The grade blockers still render below: those say *why* no
        # number was issued, which is exactly what this reader needs.
        return [*view.unanchored_caveat(score, present), *_grade_blocker_lines(score)]
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
    # Unanchored languages are provisional here too, elevated or not.
    lines: list[str] = view.unanchored_caveat(score, present)
    if elevated:
        lines.extend(
            [
                "Where this repo is worse than typical real-world code",
                f"(1.0x = the median of a mature open-source corpus of "
                f"{corpus_span(score)}; elevated dimensions only):",
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
    lines.extend(_grade_blocker_lines(score))
    return lines


def _grade_blocker_lines(score: dict[str, Any]) -> list[str]:
    """Why the grade is capped — printed whether or not a number was issued.

    Split out so the withheld-score path above can render it too: the
    reasons a score was capped or refused are the one part of this
    section that is not itself a rate.
    """
    blockers = view.grade_blockers(score)
    if not blockers:
        return []
    return [*(f"- Grade capped: {blocker}" for blocker in blockers), ""]


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
    """The inspect-first lists, minus everything the prompt withheld.

    **One rule, every category.** `withheld_reason` has two clauses — a
    Major Project, and a finding fixed before that came back — and the
    prompt states both: `_withheld_paragraph` says "Do not attempt them
    here", `prompt_escalation_note` says the escalated ones are
    deliberately excluded. Until D207 the focus lists honoured only the
    second clause, and only on three of their seven categories, so the
    same prompt forbade a change and then listed its target under
    "to inspect first". That is D180's "one run authorising and
    forbidding the same change" on a different axis, and the audit of
    `e88b429` had already fixed it once — for risk findings alone,
    from the instance rather than from the claim.
    """
    from ._identity import declaration_identities, file_fingerprint, risk_identities

    escalated = _escalated_fingerprints(report)
    # Every target the bounded prompt refused, under both clauses.
    withheld = withheld_targets(report, escalated)
    # Looked up, not rebuilt. `escalated` holds identities the history
    # recorded, so anything compared against it has to be numbered over
    # the same population — a hotspot that only warns has no identity
    # here, and cannot be escalated, so `None` correctly stays listed.
    identities = declaration_identities(report)
    risk_ids = risk_identities(report)
    lines: list[str] = []
    lines.extend(bulleted_section("Start with these hard gates:", report["hard_gate_failures"]))
    hotspot_lines = [
        f"`{i['path']}:{i['start_line']}` {hotspot_name(i)} ({hotspot_measure(i)})."
        for i in report["function_hotspots"][:10]
        if identities.get((i["path"], i["name"], i["start_line"])) not in escalated
        and not is_withheld(withheld, i, identities.get((i["path"], i["name"], i["start_line"])))
    ]
    lines.extend(bulleted_section("Function hotspots to inspect first:", hotspot_lines))
    large_files = [
        f"`{i['path']}` has {i['lines']} lines ({i['status']})."
        for i in report["largest_files"][:10]
        if i["status"] in {"warn", "fail"}
        and file_fingerprint(i["path"]) not in escalated
        and not is_withheld(withheld, i, file_fingerprint(i["path"]))
    ]
    lines.extend(bulleted_section("Large files to inspect for responsibility splits:", large_files))
    risks = [
        f"`{i['path']}:{i['line']}` {i['name']}: {i['text']}"
        for i in report["risk_findings"][:20]
        if risk_ids.get((i["path"], i["name"], i["line"])) not in escalated
        and not is_withheld(withheld, i, risk_ids.get((i["path"], i["name"], i["line"])))
    ]
    lines.extend(bulleted_section("Risk pattern findings to verify:", risks))
    dupes = [
        f"Repeated block appears {i['count']} times near: {', '.join(i['locations'][:5])}"
        for i in report["duplicate_blocks"][:5]
        if not is_withheld(withheld, i)
    ]
    lines.extend(bulleted_section("Duplicate blocks to inspect:", dupes))
    lines.extend(near_duplicate_section(report, withheld))
    lines.extend(dead_code_section(report, withheld))
    lines.extend(idiom_section(report, withheld))
    return lines


def idiom_section(report: dict[str, Any], withheld: set[Any] | None = None) -> list[str]:
    """Two libraries doing one job, with the minority usage named.

    Consolidating on the majority library is usually right, and naming
    which one is in the minority is what makes the finding actionable.
    But this is the finding most likely to be a deliberate migration
    caught mid-flight, so the instruction is to check intent first.
    """
    findings = [f for f in report.get("divergent_idioms") or []
                if not _refused(withheld, f)]
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


def dead_code_section(report: dict[str, Any], withheld: set[Any] | None = None) -> list[str]:
    """Debris an agent can delete outright, with the caveat that matters.

    Every entry is private and unreferenced, so deletion is usually safe.
    "Usually" is doing real work there: a name reached only through
    dynamic dispatch looks identical to a dead one from the outside, so
    the instruction is to verify before removing rather than to trust the
    finding.
    """
    findings = [f for f in report.get("dead_code") or []
                if not _refused(withheld, f)]
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


def near_duplicate_section(report: dict[str, Any], withheld: set[Any] | None = None) -> list[str]:
    """Name the existing helper each near-copy should collapse into.

    This is the one finding that comes with its own fix. "There is
    duplication" is not actionable; "``toAtomicAmount`` at
    ``TradeTicket.tsx:862`` already does this" is. Cross-file pairs lead,
    because those are the ones where the second copy was written by
    someone — or something — that did not know the first existed.
    """
    findings = [f for f in report.get("near_duplicates") or []
                if not _refused(withheld, f)]
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

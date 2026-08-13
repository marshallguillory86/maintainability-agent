"""Rendering what examined the code, and what it could not reach.

Split from ``renderers`` when that module crossed the 500-line file gate
this project enforces on everyone else — the seam is a real one rather
than a convenience. Everything here answers *what was looked at*: which
analyzers ran, what they measured, what they found, and which source
files the scan never opened at all. ``renderers`` answers *what the
result was*.

The last of those sections is the newest and the one that changed most.
Until the validation sample ran, a report on curl printed 4.3 with no
indication that the number came from its Markdown and its Python test
scripts while 20,547 declarations of C went unread. A reader cannot
discount a score they are not told is partial, so this is rendered
directly under the summary rather than in an appendix.
"""
from __future__ import annotations

from typing import Any

from ._work_order import work_order_rows


def _by_language_rows(coverage: dict[str, Any]) -> list[str]:
    """The per-language coverage table, or nothing for a single language.

    Split out because `analyzer_coverage_markdown` reached complexity 15
    against this project's own limit — a section added per fact, each
    reasonable alone.
    """
    rows: list[str] = []
    by_language = coverage.get("by_language") or {}
    scored = coverage.get("scored_languages") or []
    if len(by_language) > 1:
        # Per language, because a repository is not one language and the
        # union rounds up: one Python build script among three hundred
        # C++ files claimed `types` for the whole tree.
        rows.extend([
            "### Coverage by language", "",
            "| Language | Scored | Examined | Unexamined |",
            "|---|---|---|---|",
        ])
        gaps = coverage.get("gaps_by_language") or {}
        for name, covered in by_language.items():
            missing = gaps.get(name) or []
            rows.append(
                f"| {name} | {'yes' if name in scored else 'not read'} | "
                f"{', '.join(f'`{c}`' for c in covered) or '—'} | "
                f"{', '.join(f'`{c}`' for c in missing) or '—'} |"
            )
        rows.extend([
            "",
            "The score is drawn from the scored languages only. Anything "
            "marked `not read` is listed under Source Not Read with its "
            "file count.",
            "",
        ])
    return rows


def analyzer_coverage_markdown(coverage: dict[str, Any] | None) -> list[str]:
    """What examined this repository, and what nothing examined.

    Placed immediately after the summary rather than in an appendix: two
    reports with different coverage are not comparable, so a reader who
    sees a score must see what produced it in the same glance (P8).
    """
    if not coverage:
        return []
    if coverage.get("error"):
        return ["## Analyzer Coverage", "",
                f"No analyzers ran: {coverage['error']}", ""]

    selection = coverage["selection"]
    sources = coverage.get("sources", {})
    lines = [
        "## Analyzer Coverage", "",
        f"{coverage['tools_contributed']} of {coverage['tools_attempted']} tools "
        f"contributed — concerns `{', '.join(selection['concerns'])}`, "
        f"depth `{selection['depth']}`, license policy `{selection['license_policy']}`.",
        "",
        # Named separately from the analyzer count so neither number can be
        # read as the other. "0 of 11 tools contributed" beside eight
        # built-in rows would otherwise look like a contradiction.
        f"Plus {sources.get('built_in', 0)} built-in detectors, which always run "
        "and whose measurements are single-source.",
        "",
        "| Source | Tier | Outcome | Version | Measurements | Findings | Note |",
        "|---|---|---|---|---|---|---|",
    ]
    for outcome, entries in sorted(coverage["by_outcome"].items()):
        # Analyzers first, then built-ins, so the two tiers read as two
        # groups and "10 of 11 tools contributed" can be checked against
        # the rows above the fold rather than counted out of a mixed list.
        for entry in sorted(entries,
                            key=lambda item: (item.get("tier") != "analyzer", item["tool"])):
            note = entry.get("parse_error") or entry.get("detail") or ""
            lines.append(
                f"| `{entry['tool']}` | {entry.get('tier', 'analyzer')} | {outcome} | "
                f"{entry.get('version') or '—'} | "
                f"{entry.get('measurements', '—')} | {entry.get('findings', '—')} | "
                f"{note[:80]} |"
            )
    lines.append("")

    lines.extend(_by_language_rows(coverage))

    single = coverage.get("concepts_single_source") or []
    if single:
        # Between covered and unexamined. A reader deciding how much
        # weight to put on a finding needs to know nothing corroborated it.
        lines.extend([
            "**One source only:** " + ", ".join(f"`{c}`" for c in single) + ".",
            "",
            "A built-in detector examined these and no external tool did, so "
            "nothing corroborates them. Install a tool covering the concern to "
            "get a second opinion.",
            "",
        ])

    unexamined = coverage["concepts_unexamined"]
    if unexamined:
        # The point of the whole section. Silence about a concern is not
        # health, and a reader who is not told will assume it is.
        lines.extend([
            "**Nothing examined:** " + ", ".join(f"`{c}`" for c in unexamined) + ".",
            "",
            "These concerns are unmeasured, not clean. Install a tool that covers them, "
            "or widen `analyzers.depth`, to have them reported.",
            "",
        ])
    return lines


# How many analyzer findings to print in full. The rest are summarised by
# concern and tool, with the complete list left in the JSON report: a
# Markdown document with eight hundred rows stops being read, and a reader
# who stops reading learns nothing.
ANALYZER_FINDING_LIMIT = 40


def analyzer_findings_markdown(findings: list[dict[str, Any]]) -> list[str]:
    """What the analyzers found, located and attributed.

    The point of running them. Coverage says *that* they ran; this says
    what they saw, and every row carries a path, a line and the tool that
    produced it so the reader can act on it or go back to the source.
    """
    if not findings:
        return []

    by_concept: dict[str, int] = {}
    for finding in findings:
        by_concept[finding["concept"]] = by_concept.get(finding["concept"], 0) + 1
    tally = ", ".join(f"{count} {concept}" for concept, count in sorted(by_concept.items()))

    lines = [
        "## Analyzer Findings", "",
        f"{len(findings)} findings from external analyzers — {tally}.", "",
        "| File | Line | Concern | Tool | Rule | Finding |",
        "|---|---|---|---|---|---|",
    ]
    for finding in findings[:ANALYZER_FINDING_LIMIT]:
        lines.append(
            f"| `{finding['path']}` | {finding['line'] or '—'} | {finding['concept']} | "
            f"`{finding['tool']}` | {finding['rule'] or '—'} | {finding['message'][:70]} |"
        )
    lines.append("")
    if len(findings) > ANALYZER_FINDING_LIMIT:
        # Stated, never silent: a truncated list a reader believes is
        # complete is worse than an obviously partial one.
        lines.extend([
            f"Showing {ANALYZER_FINDING_LIMIT} of {len(findings)}. "
            "The complete list is in the JSON report under `analyzer_findings`.",
            "",
        ])
    return lines


def analyzer_measurements_markdown(measurements: dict[str, Any] | None) -> list[str]:
    """Combined readings, their distribution, and how far the tools differ.

    The distribution is the part a reader can reason with. "Seven
    functions failed" supports a sentence; "worst 45, median 6, and two
    tools disagree by 37%" supports a plan.
    """
    if not measurements:
        return []
    lines = [
        "## Measurements", "",
        "| Concept | Units | Sources | Tool disagreement | Min | Median | p90 | Max |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for concept, data in sorted(measurements.items()):
        spread = data.get("tool_disagreement")
        distribution = data.get("distribution") or {}
        if spread is not None:
            comparison = f"{spread:.0%}"
        elif len(data["tools"]) > 1:
            # Two tools that never measured the same unit are not a
            # second opinion. interrogate reports one tree-level number
            # and multimetric reports per file, so neither confirms the
            # other, and calling that "single source" beside two tool
            # names reads as a contradiction.
            comparison = "no shared units"
        else:
            comparison = "single source"
        lines.append(
            f"| {concept} | {data['units']} | {', '.join(data['tools'])} | "
            f"{comparison} | "
            f"{distribution.get('min', '—')} | {distribution.get('median', '—')} | "
            f"{distribution.get('p90', '—')} | {distribution.get('max', '—')} |"
        )
    corroborated = [c for c, d in measurements.items() if d.get("tool_disagreement") is not None]
    lines.append("")
    if corroborated:
        lines.extend([
            "Where two tools measured the same thing, their disagreement is shown rather "
            "than averaged away — it is the uncertainty a single-tool number hides.",
            "",
        ])
    # Stated plainly: these do not move the score yet, and a reader who
    # assumed otherwise would misread both numbers.
    lines.extend([
        "*These measurements are reported, not yet scored. The maintainability score "
        "still derives from the built-in detectors; wiring the analyzer measurements "
        "into it requires re-deriving the calibration constant.*",
        "",
    ])
    return lines


def unread_source_markdown(summary: dict[str, Any]) -> list[str]:
    """Source the scan never opened, named where a reader will see it.

    Placed directly under the summary, above everything else, because a
    reader who does not know the audit skipped their language will read
    every number below it as a statement about their code. On curl this
    section is the difference between "4.3" and "4.3, computed from a
    quarter of the repository".
    """
    unread = summary.get("unread_source") or []
    if not unread:
        return []
    read = summary.get("read_source_files", 0)
    total = read + sum(entry["files"] for entry in unread)
    lines = [
        "## Source Not Read", "",
        f"{total - read} of {total} source files were not opened by this scan. "
        "Their extensions are absent from `paths.include_extensions`, so nothing "
        "below describes them.",
        "",
        "| Extension | Language | Files |",
        "|---|---|---|",
    ]
    lines.extend(
        f"| `{entry['suffix']}` | {entry['language']} | {entry['files']} |"
        for entry in unread
    )
    lines.extend([
        "",
        "Add these to `paths.include_extensions` and re-run to audit them.",
        "",
    ])
    return lines


# Which cell of the practice/condition matrix reads as trouble. Ordered
# worst first so a reader's eye lands on the row that needs them.
POSTURE_NOTE: dict[str, str] = {
    "unmanaged debt": "debt, and nothing enforcing a limit on it",
    "unverified": "clean scan, but nothing prevents tomorrow's regression",
    "managed debt": "known debt, held by enforcement",
    "healthy": "enforced, and the code reflects it",
}


def pillars_markdown(
    pillars: list[dict[str, Any]] | None, practice: dict[str, Any] | None
) -> list[str]:
    """The five pillars, both axes, and what was deliberately not measured.

    Two columns that are never combined (ADR 007 §2). The hello-world
    report printed 5.0/A+ and would have printed "practice level 1"
    beside it — the second number is the one that says the first is
    unverified, and a renderer that shows only condition repeats the
    original omission in a new format.
    """
    if not pillars or not practice:
        return []
    lines = [
        "## Pillars", "",
        f"**Practice level {practice['level']} of 5** — {practice['summary']}.",
        "",
        "| Pillar | Scope | Practice | Condition | Reading |",
        "|---|---|---:|---:|---|",
    ]
    for entry in pillars:
        condition = "—" if entry["condition"] is None else f"{entry['condition']:.1f}"
        if entry["posture"] is None:
            reading = "not measured — see below"
        else:
            note = POSTURE_NOTE.get(entry["posture"], entry["posture"])
            reading = f"{entry['posture']}: {note}"
        lines.append(
            f"| {entry['pillar']} | {entry['scope']} | {entry['practice']} | "
            f"{condition} | {reading} |"
        )
    lines.append("")

    # Scope, stated rather than left as an empty cell. An unexplained dash
    # is exactly the silence a reader fills in with "fine".
    unmeasured = [e for e in pillars if e["condition"] is None]
    if unmeasured:
        lines.append("**Not measured here, and why:**")
        lines.append("")
        lines.extend(f"- **{e['pillar']}** — {e['reason']}" for e in unmeasured)
        lines.append("")

    if practice.get("signals"):
        found = ", ".join(f"`{s['signal']}`" for s in practice["signals"])
        lines.extend([f"Enforcement found: {found}.", ""])
    if practice.get("caps"):
        lines.extend([f"Held at level {practice['level']}: {cap}" for cap in practice["caps"]])
        lines.append("")
    return lines


# How many items a report prints before it stops being a plan and starts
# being a backlog. The rest are counted, not listed.
WORK_ORDER_LIMIT = 20


def work_order_markdown(items: list[dict[str, Any]] | None) -> list[str]:
    """The ordered work, worth first, with a way to check each item.

    Quick Wins lead and Major Projects are named — the report shows the
    whole picture even where the prompt will not, because deciding to
    take on a forty-file deduplication is a human's call and they cannot
    make it if nothing tells them it is there.
    """
    if not items:
        return []
    lines = [
        "## Work Order", "",
        "Ordered by what it costs to leave against what it costs to fix "
        "(see the standard). `Worth` is what clearing the whole class moves "
        "the score, recomputed through the rubric rather than estimated.",
        "",
        "| # | Band | Item | Worth | Target |",
        "|---:|---|---|---:|---|",
    ]
    for index, row in enumerate(work_order_rows(items)[:WORK_ORDER_LIMIT], start=1):
        location = f"`{row['path']}`" + (f":{row['line']}" if row.get("line") else "")
        lines.append(
            f"| {index} | {row['band']} | {row['title']} ({location}) | "
            f"{row['worth']} | {row['target']} |"
        )
    lines.append("")
    if len(items) > WORK_ORDER_LIMIT:
        lines.extend([
            f"...and {len(items) - WORK_ORDER_LIMIT} more. A list longer than "
            f"{WORK_ORDER_LIMIT} is a backlog, not a plan.",
            "",
        ])
    lines.extend([
        f"Verify with: `{items[0]['verification']}`",
        "",
    ])
    return lines


def work_order_selection_markdown(selection: dict[str, Any] | None) -> list[str]:
    """What the reader asked for, and what clearing exactly that is worth.

    Recomputed for the selection rather than summed from its items:
    findings of one class share a denominator, so a sum overstates a
    work order by more the longer it gets.
    """
    if not selection:
        return []
    criteria = ", ".join(f"`{axis}={value}`" for axis, value in sorted(selection["criteria"].items()))
    items = selection["items"]
    if not items:
        return ["## Selected Work", "", f"Nothing matches {criteria}.", ""]
    worth = f"+{selection['worth']:.2f}" if selection["worth"] else "no measurable movement"
    lines = [
        "## Selected Work", "",
        f"{len(items)} item(s) matching {criteria}. Clearing all of them is worth "
        f"**{worth}** to the maintainability estimate — recomputed for this "
        "selection, not summed from the items.",
        "",
        "| # | Band | Item | Target |",
        "|---:|---|---|---|",
    ]
    for index, item in enumerate(items[:WORK_ORDER_LIMIT], start=1):
        location = f"`{item['path']}`" + (f":{item['line']}" if item.get("line") else "")
        lines.append(f"| {index} | {item['band']} | {item['title']} ({location}) | {item['target']} |")
    lines.extend(["", f"Verify with: `{items[0]['verification']}`", ""])
    return lines

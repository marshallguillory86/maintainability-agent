from __future__ import annotations

from typing import Any

from . import _evidence_view as view
from ._hotspots import hotspot_cognitive, hotspot_complexity, hotspot_measure, hotspot_name


def summary_table(summary: dict[str, int], score: dict[str, Any]) -> list[str]:
    return [
        "| Metric | Value |",
        "|---|---:|",
        f"| Maintainability estimate | {view.estimate(score)} |",
        f"| Range (unmeasured evidence priced 0..5) | {view.score_range(score)} |",
        f"| Evidence | {view.status_sentence(score)} |",
        f"| Verified grade | {view.verified_grade(score)} |",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File warnings | {summary['file_warnings']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function warnings | {summary['function_warnings']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
    ]


def render_evidence_markdown(report: dict[str, Any]) -> list[str]:
    """The measurements the audit could not establish, and why.

    Absent when evidence is complete — a section reading "nothing is
    missing" is noise on the reports that deserve none. Each row carries
    the typed path and its provenance so a reader knows which
    measurement to restore rather than that "history" is vaguely absent.
    """
    score = report["score"]
    if view.is_complete(score) or not view.reasons(score):
        return []
    rows = [
        [f"`{item['measurement']}`", item["reason"], f"`{item['provenance']}`"]
        for item in view.reasons(score)
    ]
    return markdown_table(
        "Evidence unavailable — no verified grade issued",
        ["Measurement", "Why", "Provenance"],
        rows,
    )


def score_table(score: dict[str, Any]) -> list[str]:
    rows = [[name, str(value)] for name, value in score["categories"].items()]
    lines = markdown_table("ISO/IEC 25010 Maintainability Score", ["Category", "Score"], rows)
    lines.extend(aspect_table(score))
    return lines


def aspect_table(score: dict[str, Any]) -> list[str]:
    """Every aspect the rubric read, including the ones it could not.

    "not measurable" is printed, never blanked: a shallow clone with no
    history and a repo with genuinely quiet history must read
    differently. The unscored list renders too — what the tool cannot
    measure at all is part of the score's meaning.
    """
    aspects = score.get("aspects")
    if not aspects:
        return []
    rows = [
        [name.replace("_", " "), str(value) if value is not None else "not measurable"]
        for name, value in aspects.items()
    ]
    lines = markdown_table("Aspect Scores", ["Aspect", "Score"], rows)
    unscored = score.get("rubric", {}).get("unscored", {})
    if unscored:
        lines.extend(
            markdown_table(
                "Not Scored — no measurement exists",
                ["Aspect", "Why"],
                [[name.replace("_", " "), reason] for name, reason in unscored.items()],
            )
        )
    return lines


def markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.append("")
    return lines


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
    lines = [
        "## Analyzer Coverage", "",
        f"{coverage['tools_contributed']} of {coverage['tools_attempted']} tools "
        f"contributed — concerns `{', '.join(selection['concerns'])}`, "
        f"depth `{selection['depth']}`, license policy `{selection['license_policy']}`.",
        "",
        "| Tool | Outcome | Version | Measurements | Findings | Note |",
        "|---|---|---|---|---|---|",
    ]
    for outcome, entries in sorted(coverage["by_outcome"].items()):
        for entry in sorted(entries, key=lambda item: item["tool"]):
            note = entry.get("parse_error") or entry.get("detail") or ""
            lines.append(
                f"| `{entry['tool']}` | {outcome} | {entry.get('version', '—')} | "
                f"{entry.get('measurements', '—')} | {entry.get('findings', '—')} | "
                f"{note[:80]} |"
            )
    lines.append("")

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


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    score = report["score"]
    lines = [
        "# Maintainability CI Report",
        "",
        f"Root: `{report['root']}`",
        f"Branch: `{report.get('git_branch') or '(unknown)'}`",
        "",
        "## Summary",
        "",
        *summary_table(summary, score),
        "",
        f"Scoring standard: {score['standard']}.",
        "",
    ]
    lines.extend(analyzer_coverage_markdown(report.get("analyzer_coverage")))
    lines.extend(analyzer_measurements_markdown(report.get("analyzer_measurements")))
    lines.extend(analyzer_findings_markdown(report.get("analyzer_findings") or []))
    if report["hard_gate_failures"]:
        lines.extend(["## Hard Gate Failures", ""])
        lines.extend(f"- {gate}" for gate in report["hard_gate_failures"])
        lines.append("")

    lines.extend(render_evidence_markdown(report))
    lines.extend(render_grade_blockers(report))
    lines.extend(score_table(score))
    file_rows = [[f"`{i['path']}`", str(i["lines"]), i["status"]] for i in report["largest_files"]]
    lines.extend(markdown_table("Largest Files", ["File", "Lines", "Status"], file_rows))

    hot_rows = [
        [
            f"`{i['path']}`",
            hotspot_name(i),
            str(i["start_line"]),
            str(i["lines"]),
            hotspot_complexity(i),
            hotspot_cognitive(i),
            i["status"],
        ]
        for i in report["function_hotspots"]
    ]
    lines.extend(
        markdown_table(
            "Function Hotspots",
            ["File", "Declaration", "Line", "Lines", "Complexity", "Cognitive", "Status"],
            hot_rows,
        )
    )
    lines.extend(render_risk_markdown(report))
    lines.extend(render_near_duplicate_markdown(report))
    lines.extend(render_dead_code_markdown(report))
    lines.extend(render_idiom_markdown(report))
    lines.extend(render_duplicate_markdown(report))
    lines.extend(render_history_markdown(report))
    lines.extend(render_external_markdown(report))
    return "\n".join(lines)


def render_grade_blockers(report: dict[str, Any]) -> list[str]:
    """Why the grade is not higher, in the report a human reads.

    These reasons reached the remediation prompt but not the report, so
    a demotion — capped testability, missing evidence, or a grade banded
    from the evidence floor rather than the point estimate — arrived
    unexplained in the artifact people actually open. "Why am I not an
    A" has to have an answer wherever the grade is printed.
    """
    blockers = view.grade_blockers(report["score"])
    if not blockers:
        return []
    return [
        "## Why the verified grade is not higher",
        "",
        *(f"- {blocker}" for blocker in blockers),
        "",
    ]


def render_history_markdown(report: dict[str, Any]) -> list[str]:
    """What the log says about where change cost is actually being paid.

    Absent entirely — heading and all — when the clone is shallow,
    because rendering an empty table would read as "no hotspots", which
    is the opposite of "could not look".
    """
    history = report.get("history")
    if history is None:
        return []
    hot_rows = [
        [f"`{item['file']}`", str(item["commits"]), str(item["lines_changed"]),
         str(item["complexity"]), str(item["authors"]), str(item["score"])]
        for item in history["hotspots"]
    ]
    lines = markdown_table(
        f"Hotspots — churn x cognitive complexity ({history['window']})",
        ["File", "Commits", "Lines +/-", "Cognitive", "Authors", "Score"],
        hot_rows,
    )
    pair_rows = [
        [f"`{item['files'][0]}`", f"`{item['files'][1]}`",
         str(item["co_changes"]), f"{item['confidence']:.0%}"]
        for item in history["change_coupling"]
    ]
    lines.extend(
        markdown_table(
            "Change Coupling — files that keep changing together",
            ["File", "Changes with", "Co-changes", "Confidence"],
            pair_rows,
        )
    )
    return lines


def render_risk_markdown(report: dict[str, Any]) -> list[str]:
    rows = []
    for item in report["risk_findings"]:
        rows.append([f"`{item['path']}`", str(item["line"]), item["name"], item["text"].replace("|", "\\|")])
    return markdown_table("Risk Pattern Findings", ["File", "Line", "Rule", "Text"], rows)


def render_near_duplicate_markdown(report: dict[str, Any]) -> list[str]:
    """Declarations that are near-copies, each paired with its original.

    Separate from the duplicate-block table because it answers a different
    question. That one says "these lines repeat"; this one says "this
    function already exists over there, under another name".
    """
    rows = [
        [
            f"`{item['path']}:{item['start_line']}`",
            f"`{item['name']}`",
            f"`{item['duplicate_of']['path']}:{item['duplicate_of']['start_line']}`",
            f"`{item['duplicate_of']['name']}`",
            f"{item['similarity']:.0%}",
            "cross-file" if item.get("cross_file") else "same file",
        ]
        for item in report.get("near_duplicates", [])
    ]
    return markdown_table(
        "Near-Duplicate Declarations",
        ["Location", "Declaration", "Duplicates", "Named", "Similarity", "Scope"],
        rows,
    )


def render_idiom_markdown(report: dict[str, Any]) -> list[str]:
    """Concerns served by more than one library.

    The cost is not duplication — each call site may be fine — it is that
    no single mental model covers the codebase.
    """
    rows = []
    for item in report.get("divergent_idioms", []):
        packages = ", ".join(f"`{p['package']}` ({p['files']} files)" for p in item["packages"])
        rows.append([item["concern"], packages, f"`{item['packages'][-1]['example']}`"])
    return markdown_table("Competing Libraries", ["Concern", "Libraries in use", "Least-used example"], rows)


def render_dead_code_markdown(report: dict[str, Any]) -> list[str]:
    """Private declarations nothing references.

    Only declarations the language marks internal are listed, so each row
    is something no external caller can reach — see ``deadcode``.
    """
    rows = [
        [f"`{item['path']}:{item['start_line']}`", f"`{item['name']}`", item["kind"], str(item["lines"])]
        for item in report.get("dead_code", [])
    ]
    return markdown_table("Unreferenced Private Declarations", ["Location", "Declaration", "Kind", "Lines"], rows)


def render_duplicate_markdown(report: dict[str, Any]) -> list[str]:
    if not report["duplicate_blocks"]:
        return []
    lines = ["## Duplicate Blocks", ""]
    for item in report["duplicate_blocks"][:10]:
        lines.append(f"- Count {item['count']}: " + ", ".join(f"`{loc}`" for loc in item["locations"][:5]))
    lines.append("")
    return lines


def render_external_markdown(report: dict[str, Any]) -> list[str]:
    rows = []
    for item in report.get("external_findings", [])[:50]:
        location = f"{item.get('path', '')}:{item.get('line', 1)}"
        message = str(item.get("message", "")).replace("|", "\\|")
        rows.append([item.get("tool", ""), f"`{item.get('rule_id', '')}`", item.get("level", ""), f"`{location}`", message])
    return markdown_table("External Findings", ["Tool", "Rule", "Level", "Location", "Message"], rows)



def render_pr_comment(report: dict[str, Any]) -> str:
    summary = report["summary"]
    score = report["score"]
    status = "failed" if report["hard_gate_failures"] else "passed"
    lines = [
        "## Maintainability Audit",
        "",
        f"Status: **{status}**",
        f"Mode: `{report.get('mode', 'full')}`",
        f"Estimate: **{view.estimate(score)}**  ·  range {view.score_range(score)}",
        f"Verified grade: **{view.verified_grade(score)}**",
        view.status_sentence(score),
        *(view.reason_lines(score) if not view.is_complete(score) else []),
        "",
        "| Metric | Count |",
        "|---|---:|",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
        "",
    ]
    if report["hard_gate_failures"]:
        lines.extend(["### Hard Gates", ""])
        lines.extend(f"- {gate}" for gate in report["hard_gate_failures"])
        lines.append("")
    if view.grade_blockers(score):
        lines.extend(["### Why the verified grade is not higher", ""])
        lines.extend(f"- {blocker}" for blocker in view.grade_blockers(score))
        lines.append("")
    if report["function_hotspots"]:
        lines.extend(["### Top Function Hotspots", ""])
        for item in report["function_hotspots"][:5]:
            lines.append(f"- `{item['path']}:{item['start_line']}` {hotspot_name(item)} ({hotspot_measure(item)})")
        lines.append("")
    lines.append("See `maintainability-report.md` and `maintainability-remediation-prompt.md` artifacts for details.")
    return "\n".join(lines)

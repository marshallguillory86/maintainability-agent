from __future__ import annotations

from typing import Any

from . import _evidence_view as view
from ._economics_view import economic_impact_markdown
from ._history_view import (
    escalations_markdown,
    run_comparison_markdown,
    scan_history_markdown,
)
from ._hotspots import hotspot_cognitive, hotspot_complexity, hotspot_measure, hotspot_name
from ._markdown_sections import (
    markdown_table,
    render_dead_code_markdown,
    render_duplicate_markdown,
    render_evidence_markdown,
    render_external_markdown,
    render_history_markdown,
    render_idiom_markdown,
    render_near_duplicate_markdown,
    render_risk_markdown,
)
from ._scan_view import (
    analyzer_coverage_markdown,
    analyzer_findings_markdown,
    analyzer_measurements_markdown,
    environment_work_order_markdown,
    pillars_markdown,
    undetected_declarations_markdown,
    unread_source_markdown,
)
from ._semantic_view import semantic_markdown, without_semantic_suffixes
from ._tdd_view import tdd_structure_markdown
from ._work_order_view import work_order_markdown, work_order_selection_markdown


def _pool_ran(report: dict[str, Any]) -> bool:
    """Whether the analyzer pool executed for this report — D1's fact.

    Read off the report (coverage present), never a second config read
    at render time: the remedy wording must describe the run that
    happened, and only the report knows that.
    """
    return report.get("analyzer_coverage") is not None


def summary_table(summary: dict[str, int], score: dict[str, Any],
                  pool_ran: bool = False) -> list[str]:
    return [
        "| Metric | Value |",
        "|---|---:|",
        f"| Maintainability estimate | {view.estimate(score)} |",
        f"| Estimate source | {view.estimate_source(score)} |",
        f"| Range (unmeasured evidence priced 0..5) | {view.score_range(score)} |",
        f"| Evidence | {view.status_sentence(score, pool_ran)} |",
        f"| Verified grade | {view.verified_grade(score)} |",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File warnings | {summary['file_warnings']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function warnings | {summary['function_warnings']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
        *view.unanchored_caveat(score),
    ]


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


def test_suite_markdown(report: dict[str, Any]) -> list[str]:
    """The opted-in suite's result, visible so a failed run is not silently
    identical to a passing one. Absent unless the operator opted in."""
    sentences = view.test_suite_lines(report.get("test_suite"))
    if not sentences:
        return []
    return ["## Test Suite", "", *[f"- {sentence}" for sentence in sentences], ""]


def _semantic_sections(report: dict[str, Any]) -> list[str]:
    """The ADR 003 block, the pillars, and the unread table it corrects.

    The unread rows render through a *view* that drops any language the
    semantic pass cited as evidence: a path used as a semantic finding
    was opened and analyzed, so its language cannot simultaneously be
    listed as source the scan never read.
    """
    findings = report.get("semantic_findings")
    return [
        *semantic_markdown(findings, report.get("semantic_coverage")),
        *pillars_markdown(report.get("pillars"), report.get("practice")),
        *unread_source_markdown(without_semantic_suffixes(report["summary"], findings)),
    ]


def _report_metadata(report: dict[str, Any], score: dict[str, Any], root_label: str) -> list[str]:
    """Header under the title (G): run date (a disclosed determinism
    exception), commit, branch, root, and scoring standard."""
    return [
        f"- Generated: {report.get('generated_at') or '(unknown)'}",
        f"- Commit: `{report.get('git_commit') or '(none)'}` · "
        f"Branch: `{report.get('git_branch') or '(unknown)'}`",
        f"- Root: `{root_label}`",
        f"- Standard: {score['standard']}",
    ]


def render_markdown(report: dict[str, Any], *, complete: bool = True) -> str:
    """The report, or the bounded UI view of it (issue A).

    ``complete=True`` (the HTML/Markdown *file*): the whole work-order
    backlog with a per-item copy-paste prompt, plus every detail table.
    Bounded (chat/CLI): score, capped-grade reasons, gates, the top items
    with prompts, then a pointer to the report — so the payload-capped
    surface can never truncate the prompt the way a 75k inline report did.
    """
    score = report["score"]
    root_label = report["root"]
    lines = [
        "# Maintainability CI Report",
        "",
        *_report_metadata(report, score, root_label),
        "",
        "## Summary",
        "",
        *summary_table(report["summary"], score, _pool_ran(report)),
        "",
    ]
    if not complete:
        return _bounded_markdown(report, score, root_label, lines)
    return _complete_markdown(report, score, root_label, lines)


def _hard_gate_lines(report: dict[str, Any]) -> list[str]:
    """The hard-gate list, printed the same way wherever it appears."""
    if not report["hard_gate_failures"]:
        return []
    return ["## Hard Gate Failures", "",
            *(f"- {gate}" for gate in report["hard_gate_failures"]), ""]


def _bounded_markdown(report: dict[str, Any], score: dict[str, Any],
                      root_label: str, lines: list[str]) -> str:
    """The chat/CLI UI view (issue A): score, gates, the top work items with
    prompts, then a pointer to the complete report so a payload-capped
    surface can never truncate the prompt."""
    lines.extend(render_grade_blockers(report))
    lines.extend(_hard_gate_lines(report))
    lines.extend(work_order_markdown(
        report.get("work_order"), complete=False, root_label=root_label))
    lines.extend(score_table(score))
    lines.extend([
        "---", "",
        "This is the bounded UI view. The complete report — every finding, "
        "the full work-order backlog with a copy-paste prompt for each item, "
        "and coverage, trend and history — is the HTML or Markdown report "
        "(ask for the `html` or `markdown` format).",
    ])
    return "\n".join(lines)


def _complete_markdown(report: dict[str, Any], score: dict[str, Any],
                       root_label: str, lines: list[str]) -> str:
    """The complete report file: every section and the whole work-order
    backlog (a selection *replaces* the full list; the JSON keeps both)."""
    summary = report["summary"]
    lines.extend(escalations_markdown(report.get("design_review_candidates")))
    lines.extend(scan_history_markdown(report.get("scan_history")))
    lines.extend(run_comparison_markdown(report.get("run_comparison")))
    selection = report.get("work_order_selection")
    if selection:
        lines.extend(work_order_selection_markdown(selection))
    else:
        lines.extend(work_order_markdown(
            report.get("work_order"), complete=True, root_label=root_label))
    lines.extend(economic_impact_markdown(report.get("economic_impact")))
    lines.extend(tdd_structure_markdown(report.get("tdd_structure")))
    lines.extend(test_suite_markdown(report))
    lines.extend(_semantic_sections(report))
    lines.extend(undetected_declarations_markdown(summary, _pool_ran(report)))
    lines.extend(analyzer_coverage_markdown(report.get("analyzer_coverage")))
    lines.extend(environment_work_order_markdown(report.get("environment_work_order") or []))
    lines.extend(analyzer_measurements_markdown(
        report.get("analyzer_measurements"),
        (score.get("analyzer_scored_dimensions") or []),
    ))
    lines.extend(analyzer_findings_markdown(report.get("analyzer_findings") or []))
    lines.extend(view.unidentified_paths_markdown(
        report.get("unidentified_source_paths") or []))
    lines.extend(_hard_gate_lines(report))
    lines.extend(render_evidence_markdown(report))
    lines.extend(render_grade_blockers(report))
    lines.extend(score_table(score))
    file_rows = [[f"`{i['path']}`", str(i["lines"]), i["status"]] for i in report["largest_files"]]
    lines.extend(markdown_table("Largest Files", ["File", "Lines", "Status"], file_rows))
    hot_rows = [
        [f"`{i['path']}`", hotspot_name(i), str(i["start_line"]), str(i["lines"]),
         hotspot_complexity(i), hotspot_cognitive(i), i["status"]]
        for i in report["function_hotspots"]
    ]
    lines.extend(markdown_table(
        "Function Hotspots",
        ["File", "Declaration", "Line", "Lines", "Complexity", "Cognitive", "Status"],
        hot_rows))
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
        view.status_sentence(score, _pool_ran(report)),
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
    # The same semantic block the report carries: a finding the agent
    # prompt names may not vanish from the human's PR view.
    lines.extend(semantic_markdown(
        report.get("semantic_findings"), report.get("semantic_coverage")))
    lines.append("See `maintainability-report.md` and `maintainability-remediation-prompt.md` artifacts for details.")
    return "\n".join(lines)


def render_html(report: dict[str, Any], records: list[Any]) -> str:
    """The HTML skin (ADR 011). One file, no score computed here.

    Re-exported from `_html_view` so every consumer keeps importing its
    renderers from one module, the same as Markdown and the PR comment.
    """
    from ._html_view import render_html as _render

    return _render(report, records)

from __future__ import annotations

from typing import Any

from ._hotspots import hotspot_complexity, hotspot_measure, hotspot_name


def summary_table(summary: dict[str, int], score: dict[str, Any]) -> list[str]:
    return [
        "| Metric | Value |",
        "|---|---:|",
        f"| Overall score | {score['overall']} / 5 ({score['grade']}) |",
        f"| Files scanned | {summary['files_scanned']} |",
        f"| File warnings | {summary['file_warnings']} |",
        f"| File failures | {summary['file_failures']} |",
        f"| Function warnings | {summary['function_warnings']} |",
        f"| Function failures | {summary['function_failures']} |",
        f"| Duplicate blocks | {summary['duplicate_blocks']} |",
        f"| Risk findings | {summary['risk_findings']} |",
        f"| Hard gate failures | {summary['hard_gate_failures']} |",
    ]


def score_table(score: dict[str, Any]) -> list[str]:
    rows = [[name, str(value)] for name, value in score["categories"].items()]
    return markdown_table("ISO/IEC 25010 Maintainability Score", ["Category", "Score"], rows)


def markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.append("")
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
    if report["hard_gate_failures"]:
        lines.extend(["## Hard Gate Failures", ""])
        lines.extend(f"- {gate}" for gate in report["hard_gate_failures"])
        lines.append("")

    lines.extend(score_table(score))
    file_rows = [[f"`{i['path']}`", str(i["lines"]), i["status"]] for i in report["largest_files"]]
    lines.extend(markdown_table("Largest Files", ["File", "Lines", "Status"], file_rows))

    hot_rows = [
        [f"`{i['path']}`", hotspot_name(i), str(i["start_line"]), str(i["lines"]), hotspot_complexity(i), i["status"]]
        for i in report["function_hotspots"]
    ]
    lines.extend(
        markdown_table("Function Hotspots", ["File", "Declaration", "Line", "Lines", "Complexity", "Status"], hot_rows)
    )
    lines.extend(render_risk_markdown(report))
    lines.extend(render_near_duplicate_markdown(report))
    lines.extend(render_duplicate_markdown(report))
    lines.extend(render_external_markdown(report))
    return "\n".join(lines)


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
        f"Score: **{score['overall']} / 5 ({score['grade']})**",
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
    if report["function_hotspots"]:
        lines.extend(["### Top Function Hotspots", ""])
        for item in report["function_hotspots"][:5]:
            lines.append(f"- `{item['path']}:{item['start_line']}` {hotspot_name(item)} ({hotspot_measure(item)})")
        lines.append("")
    lines.append("See `maintainability-report.md` and `maintainability-remediation-prompt.md` artifacts for details.")
    return "\n".join(lines)

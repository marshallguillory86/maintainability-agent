"""Leaf Markdown section renderers, split from ``renderers`` for headroom.

Each function turns one slice of the report dict into Markdown lines and
computes no score. They share one primitive, ``markdown_table``; nothing
here imports ``renderers``, so ``renderers`` can import these back without
a cycle — which is the whole reason the seam sits here (issue #125).
"""
from __future__ import annotations

from typing import Any

from . import _evidence_view as view


def markdown_table(title: str, headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    lines = [f"## {title}", "", "| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.append("")
    return lines


def _empty_window_sentence(history: dict[str, Any]) -> str:
    """What the reader is told when the window produced no churn.

    Three causes, and telling all three "no commit falls inside the
    history window" sent readers of the last two to check their clone
    depth for a window that was in fact filtered to empty (D66). The
    fallback is the original sentence, which is what a report written
    before these counts existed still carries.
    """
    window = history["window"]
    in_window = history.get("commits_in_window")
    considered = history.get("commits_considered")
    if not isinstance(in_window, int) or not isinstance(considered, int) or in_window == 0:
        return (
            f"No commit falls inside the history window ({window}). "
            "This is not a quiet repository — it is a window with "
            "nothing in it."
        )
    if considered == 0:
        return (
            f"All {in_window} commits inside the history window ({window}) "
            "are merges. A merge's line counts re-report churn already "
            "counted on the branch it merged, so this audit reads none "
            "of them."
        )
    return (
        f"{considered} of the {in_window} commits inside the history "
        f"window ({window}) were read, and none of them touched a file "
        "this audit scans — the window is filtered to empty, not quiet."
    )


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


def render_history_markdown(report: dict[str, Any]) -> list[str]:
    """What the log says about where change cost is actually being paid.

    Absent entirely — heading and all — when the clone is shallow,
    because rendering an empty table would read as "no hotspots", which
    is the opposite of "could not look".
    """
    history = report.get("history")
    if history is None:
        return []
    if not history.get("files_changed"):
        # The window was read and held no commits. Rendering the empty
        # tables below would say "no hotspots", which reads as a quiet
        # repository — and the reader was previously told "Evidence
        # complete" with nothing about the window at all, while the
        # scoring layer had already marked every history rate
        # not-applicable. P8: the report states what examined each value
        # (D56, reopened by Codex).
        return [
            "### History",
            "",
            f"{_empty_window_sentence(history)} "
            "Churn, hotspots, coupling and ownership have no population "
            "to measure, and the history aspects are reported as not "
            "applicable rather than as zero.",
            "",
        ]
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

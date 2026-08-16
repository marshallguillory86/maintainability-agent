"""The ADR 003 semantic block as Markdown — labels preserved, no arithmetic.

One renderer for every human skin: the Markdown report carries this
section directly and the HTML page embeds that same Markdown, so the
three presentations cannot drift apart on what the semantic pass found.
The class labels survive rendering on purpose — a typed fact, a
configured policy violation and a design-review candidate are three
different claims, and a skin that flattened them would launder
configuration and heuristics into universal rules.
"""
from __future__ import annotations

from pathlib import PurePosixPath
from typing import Any

_CLASS_LABEL = {
    "universal": "Typed fact",
    "policy": "Configured policy",
    "candidate": "Design-review candidate",
}


def semantic_class_label(classification: str | None) -> str:
    """One display name per class, shared by every skin that labels one."""
    return _CLASS_LABEL.get(classification or "", classification or "")


def _finding_line(finding: dict[str, Any]) -> str:
    evidence = finding.get("source_evidence") or {}
    label = _CLASS_LABEL.get(finding.get("class") or "", finding.get("class") or "")
    entry = finding.get("policy_entry") or ""
    named = f" `{entry}`" if entry else ""
    return f"- **{label}**{named}: `{evidence.get('path') or ''}` — {finding.get('message') or ''}"


def semantic_markdown(
    findings: list[dict[str, Any]] | None,
    coverage: dict[str, Any] | None,
) -> list[str]:
    """The semantic findings and their coverage, or nothing for old reports.

    Coverage renders even when the finding list is empty, because
    "unknown" is a published state: an absent section would read as a
    clean run, which is exactly the claim unknown coverage refuses to
    make (ADR 003 invariant 6).
    """
    if not coverage and not findings:
        return []
    coverage = coverage or {}
    lines = ["## Semantic Findings (ADR 003)", ""]
    status = coverage.get("status") or "unknown"
    language = coverage.get("language") or "TypeScript"
    if status == "unknown":
        lines.append(
            f"{language} semantic coverage: **unknown** — "
            f"{coverage.get('reason') or 'no type analysis was available.'}"
        )
    else:
        lines.append(
            f"{language} semantic coverage: **{status}** via "
            f"{coverage.get('tool') or 'typescript'} {coverage.get('version') or ''}".rstrip()
            + ". Other languages have unknown semantic coverage."
        )
    lines.append("")
    lines.extend(_finding_line(finding) for finding in findings or [])
    if findings:
        lines.append("")
    return lines


def semantic_evidence_suffixes(findings: list[dict[str, Any]] | None) -> set[str]:
    """File suffixes the semantic pass demonstrably read.

    A path cited as semantic evidence was opened and analyzed, so its
    language may not simultaneously be listed as source the scan never
    read — the two claims cannot both be true in one report.
    """
    return {
        PurePosixPath(finding["source_evidence"]["path"]).suffix
        for finding in findings or []
        if (finding.get("source_evidence") or {}).get("path")
    }


def without_semantic_suffixes(
    summary: dict[str, Any], findings: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """A summary view whose unread rows exclude semantically-read languages.

    A *view*: the stored summary is sealed with the score and no
    renderer may amend it. Only the rows a semantic finding contradicts
    are dropped; every other unread language keeps its warning.
    """
    suffixes = semantic_evidence_suffixes(findings)
    unread = summary.get("unread_source") or []
    kept = [row for row in unread if row.get("suffix") not in suffixes]
    if len(kept) == len(unread):
        return summary
    return {
        **summary,
        "unread_source": kept,
        "unread_source_files": sum(int(row.get("files") or 0) for row in kept),
    }

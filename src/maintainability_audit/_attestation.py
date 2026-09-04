"""The record a generator cannot produce about its own output.

The three mechanisms — scope conformance, suppression detection, the
dimension ratchet — each answer one question about a change. This composes
them into the artifact they were built for: a per-change record of what was
measured, what the agent was told to change, what it actually changed, and
what moved.

**Why an independent process has to emit it.** A platform that generates
code and then reports on its quality is producing a self-assessment. That
is a property of the arrangement, not a criticism of any particular one,
and no amount of engineering removes it. The question a reviewer asks is
*who checked this, and can they re-derive the check months from now* — and
an author cannot be the answer. This tool writes nothing, runs no model,
and returns the same verdict from the same inputs, which is the only reason
its answer can be evidence rather than an opinion.

**It is reproducible, not signed.** Every field is derived from the report
and the pinned inputs, and the digest at the end is over the record's own
content, so two runs on the same commit with the same analyzer versions
produce the same digest. That makes it *verifiable* — anyone can re-run and
compare. It is deliberately not called a signature: nothing here holds a
key, and claiming a cryptographic guarantee this does not provide would be
exactly the kind of overclaim the rest of the project spends its time
removing. Signing the artifact, if a caller wants that, is a step they take
with their own key on a file whose bytes are stable.

**What it does not establish.** The record says which files the work order
named and whether a checker was switched off — not whether the edits were
correct. It never opens the diff to judge it, and it never touches a score.
Review is still review.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

ARTIFACT_VERSION = 1


def _verdicts(report: dict[str, Any]) -> list[str]:
    """One line per question that was actually asked."""
    lines: list[str] = []
    conformance = report.get("scope_conformance")
    if conformance:
        out = len(conformance["out_of_scope"])
        silenced = conformance["suppressions_on_named_paths"]
        lines.append(
            f"- **Stayed inside the work order:** "
            f"{'yes' if conformance['conformant'] else f'no — {out} file(s) outside it'}"
        )
        lines.append(
            f"- **Without silencing a finding:** "
            f"{'yes' if not silenced else f'no — {silenced} suppression(s) on flagged files'}"
        )
    ratchet = report.get("dimension_ratchet")
    if ratchet:
        if not ratchet["comparable"]:
            lines.append(
                f"- **No dimension regressed:** not established — {ratchet['reason']}"
            )
        elif ratchet["regressed"]:
            names = ", ".join(item["name"] for item in ratchet["regressed"])
            lines.append(f"- **No dimension regressed:** no — {names}")
        else:
            lines.append("- **No dimension regressed:** yes")
    return lines


def _measured(report: dict[str, Any]) -> list[str]:
    score = report.get("score") or {}
    coverage = report.get("analyzer_coverage") or {}
    status = score.get("evidence_status")
    if isinstance(status, dict):
        status = status.get("status")
    ran = (coverage.get("by_outcome") or {}).get("ran") or []
    return [
        f"- Estimate: {score.get('maintainability_estimate', 'withheld')}",
        f"- Verified grade: {score.get('verified_grade') or 'withheld'}",
        f"- Evidence: {status or 'unstated'}",
        f"- Analyzers that ran: {len(ran)}",
        f"- Hard gate failures: {len(report.get('hard_gate_failures') or [])}",
    ]


def attestation_record(report: dict[str, Any]) -> dict[str, Any]:
    """The structured record, before rendering."""
    conformance = report.get("scope_conformance") or {}
    ratchet = report.get("dimension_ratchet") or {}
    score = report.get("score") or {}
    record = {
        "artifact_version": ARTIFACT_VERSION,
        "tool_version": report.get("tool_version"),
        "commit": report.get("git_commit"),
        "branch": report.get("git_branch"),
        # A finding reported against "the commit" that actually depends on
        # uncommitted work is unreproducible, so the state of the tree is
        # part of what is attested rather than a footnote.
        "tree_dirty": bool(report.get("git_status_short")),
        "revspec": conformance.get("revspec"),
        "estimate": score.get("maintainability_estimate"),
        "verified_grade": score.get("verified_grade"),
        "stayed_in_scope": conformance.get("conformant"),
        "no_finding_silenced": (
            None if not conformance else conformance["suppressions_on_named_paths"] == 0
        ),
        "no_dimension_regressed": (
            None if not ratchet or not ratchet.get("comparable")
            else not ratchet["regressed"]
        ),
        "scope_conformance": conformance or None,
        "dimension_ratchet": ratchet or None,
    }
    # The digest is over the record without it, so it is reproducible: the
    # same commit measured with the same analyzer versions yields the same
    # value, and anyone can recompute it rather than trust it.
    record["digest"] = hashlib.sha256(
        json.dumps(record, sort_keys=True, default=str).encode("utf-8")
    ).hexdigest()[:16]
    return record


def render_attestation(report: dict[str, Any]) -> str:
    """The record as text, for a reviewer or an audit trail."""
    record = attestation_record(report)
    dirty = " (uncommitted changes present)" if record["tree_dirty"] else ""
    lines = [
        "# Maintainability attestation",
        "",
        "An independent, deterministic check on a change. Produced by a "
        "process that generated none of the code it examined.",
        "",
        f"- Commit: `{record['commit'] or 'unknown'}`{dirty}",
        f"- Branch: `{record['branch'] or 'unknown'}`",
        f"- Tool version: {record['tool_version'] or 'unknown'}",
        f"- Compared: `{record['revspec'] or 'not asked'}`",
        "",
        "## What was measured",
        "",
        *_measured(report),
        "",
        "## What the change did",
        "",
    ]
    verdicts = _verdicts(report)
    lines += verdicts or ["- Nothing was asked: run with `--conformance` and "
                          "`--fail-on-regression` to populate this section."]
    lines += [
        "",
        "## What this does not establish",
        "",
        "- It compares paths and reads added lines. A file in scope means the "
        "work order named it, **not** that the change to it was correct — this "
        "never opens the diff to judge it.",
        "- It touches no score. Whether a change obeyed its instructions is a "
        "fact about behaviour, not evidence about the code's condition.",
        "- It is reproducible, **not signed**. The digest is over this "
        "record's own content, so the same inputs reproduce it and anyone can "
        "recompute it. Nothing here holds a key.",
        "",
        f"Digest: `{record['digest']}`",
        "",
    ]
    return "\n".join(lines)

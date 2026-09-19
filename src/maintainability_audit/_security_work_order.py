"""What secure-code-agent found, and its own work order for it (D179).

3.7.0 made every audit run secure-code-agent (D177), and then kept one
thing from that run: the pillar document. An audit of this repository
recorded five critical findings and one high, and every skin printed
"unverified: not graded — scanner coverage is partial" with no count. The
remediation prompt secure-code-agent had written — 74 findings to fix, 5 to
review, each located and constrained — sat in a temporary directory that
was deleted before the report was built. The run measured the work and the
reader was handed neither its size nor its instructions.

**Two things, each where it is read.** The severity counts come from the
pillar document and appear wherever the pillar does. The work order is
secure-code-agent's own text, carried unchanged under `security_work_order`
and printed whole in the complete reports. It stays that tool's work order,
not this one's: this tool does not re-rank, merge or reword security
findings (ADR 007 §1), so the maintainability prompt names it and does not
absorb it.
"""
from __future__ import annotations

from html import escape
from typing import Any

#: The report key, and the chat door's top-level key, that carries it.
KEY = "security_work_order"

_ORDER = ("critical", "high", "medium", "low", "informational")


def severity_counts(entry: dict[str, Any]) -> str | None:
    """`5 critical, 1 high, …` from a measured pillar, or `None` when it carries none.

    A pillar document with an empty count reads "no findings": that is the
    producer's statement, and it is different from a pillar with no count at
    all, which says nothing and is printed as nothing.
    """
    counts = entry.get("findings_by_severity")
    if not isinstance(counts, dict):
        return None
    named = [name for name in _ORDER if counts.get(name)]
    named += sorted(name for name in counts if name not in _ORDER and counts[name])
    if not named:
        return "no findings"
    return ", ".join(f"{counts[name]} {name}" for name in named)


def carried(
    markdown: str | None,
    entry: dict[str, Any],
    data: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """The report entry for a work order the delegate wrote, or `None`.

    `markdown` is still what decides there is a work order at all: it is the
    artifact the operator reads, and the one this tool has carried since
    D179. `data` is the same work order as facts (secure-code-agent D27),
    present only when the installed delegate emits it, and used by the skins
    that render rather than quote.
    """
    if not markdown or not markdown.strip():
        return None
    carried_order = {
        "producer": entry.get("delegated_to"),
        "producer_version": entry.get("producer_version"),
        "markdown": markdown,
    }
    if isinstance(data, dict) and data:
        carried_order["data"] = data
    return carried_order


def _source(work_order: dict[str, Any]) -> str:
    version = f" {work_order['producer_version']}" if work_order.get("producer_version") else ""
    return f"{work_order.get('producer') or 'the delegated tool'}{version}"


def pointer_markdown(report: dict[str, Any]) -> list[str]:
    """The bounded view's line: the work order exists, and where it is."""
    work_order = report.get(KEY)
    if not work_order:
        return []
    return [
        f"**Security work order.** {_source(work_order)} wrote its own work order "
        f"for these findings. It is carried whole as `{KEY}` and printed in the "
        "complete Markdown and HTML reports.",
        "",
    ]


def _demoted(markdown: str) -> list[str]:
    """The delegate's headings two levels down, so they nest under this report's.

    Lines inside a fence are left alone: a `#` there is a comment in a quoted
    snippet, not a heading.
    """
    lines = []
    fenced = False
    for line in markdown.rstrip("\n").splitlines():
        if line.lstrip().startswith("```"):
            fenced = not fenced
        elif not fenced and line.startswith("#"):
            line = "##" + line
        lines.append(line)
    return lines


def _intro(work_order: dict[str, Any]) -> str:
    return (
        f"Written by {_source(work_order)} and reproduced as it wrote it. It is "
        "that tool's work order, not this one's: its findings are not re-ranked "
        "or merged into the maintainability work order above."
    )


def complete_markdown(report: dict[str, Any]) -> list[str]:
    """The complete report's section: the delegate's work order, whole."""
    work_order = report.get(KEY)
    if not work_order:
        return []
    return ["## Security Work Order", "", _intro(work_order), "",
            *_demoted(work_order["markdown"]), ""]


def _tier_html(title: str, note: str, tier: dict[str, Any]) -> list[str]:
    """One tier, drawn. Empty tiers are omitted rather than shown as zero."""
    shown = tier.get("shown") or []
    if not shown:
        return []
    out = [f"<h3>{escape(title)}</h3>", f"<p>{escape(note)}</p>"]
    for n, finding in enumerate(shown, 1):
        out.append("<div class='finding'>")
        out.append(
            f"<h4>{n}. <code>{escape(str(finding.get('rule_id') or ''))}</code>"
            f" — {escape(str(finding.get('title') or ''))}</h4>"
        )
        out.append(f"<p><code>{escape(str(finding.get('location') or ''))}</code></p>")
        if finding.get("review_note"):
            out.append(
                f"<p><strong>Check first:</strong> {escape(str(finding['review_note']))}</p>"
            )
        if finding.get("code_snippet"):
            out.append(f"<pre>{escape(str(finding['code_snippet']))}</pre>")
        advice = finding.get("fix_hint") or finding.get("message")
        if advice:
            out.append(f"<p>{escape(str(advice))}</p>")
        out.append(f"<p class='standards'>{escape(_standards_line(finding))}</p>")
        out.append("</div>")
    if tier.get("omitted"):
        out.append(f"<p><em>{tier['omitted']} more not shown.</em></p>")
    return out


def _standards_line(finding: dict[str, Any]) -> str:
    """The citation, in the delegate's own order and wording."""
    standards = finding.get("standards") or {}
    bits = [str(standards[key]) for key in ("cwe", "owasp_top10") if standards.get(key)]
    if standards.get("asvs_section"):
        bits.append(f"ASVS {standards['asvs_section']}")
    if standards.get("nist_ssdf"):
        bits.append(f"SSDF {standards['nist_ssdf']}")
    bits.append(
        f"{finding.get('severity')}/{finding.get('confidence')} via {finding.get('scanner')}"
    )
    return " · ".join(bits)


def complete_html(report: dict[str, Any]) -> list[str]:
    """The HTML report's section, drawn from the delegate's data.

    It used to be `<pre>` around the Markdown — "the same text,
    preformatted" — and that is what a reader who chose an HTML
    presentation got: `##` headings and asterisks for bold, inside a page
    where everything else was rendered. Prose is the one thing this tool
    cannot re-present, so the delegate now emits the same work order as
    facts (secure-code-agent D27) and this draws them (D197).

    A delegate that sends no data still gets the old treatment. That is
    not a fallback to be embarrassed about: it is the honest rendering of
    prose, and it keeps a supported older release readable rather than
    blank.
    """
    work_order = report.get(KEY)
    if not work_order:
        return []
    head = ["<h2>Security Work Order</h2>", f"<p>{escape(_intro(work_order))}</p>"]
    data = work_order.get("data")
    if not isinstance(data, dict) or not data:
        return [*head, f"<pre>{escape(work_order['markdown'])}</pre>"]
    counts = data.get("counts") or {}
    head.append(
        "<p>"
        f"<strong>{counts.get('fix', 0)}</strong> to fix · "
        f"<strong>{counts.get('review', 0)}</strong> to review · "
        f"<strong>{counts.get('accept', 0)}</strong> suppression candidates."
        "</p>"
    )
    return [
        *head,
        *_tier_html(
            "Fix", "Defects the scanner is confident about.", data.get("fix") or {}
        ),
        *_tier_html(
            "Review",
            "Low-precision rules or low scanner confidence. Check each is real "
            "before patching it; the reason is stated per finding.",
            data.get("review") or {},
        ),
    ]

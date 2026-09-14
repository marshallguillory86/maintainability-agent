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


def carried(markdown: str | None, entry: dict[str, Any]) -> dict[str, Any] | None:
    """The report entry for a work order the delegate wrote, or `None`."""
    if not markdown or not markdown.strip():
        return None
    return {
        "producer": entry.get("delegated_to"),
        "producer_version": entry.get("producer_version"),
        "markdown": markdown,
    }


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


def complete_html(report: dict[str, Any]) -> list[str]:
    """The HTML report's section: the same text, preformatted."""
    work_order = report.get(KEY)
    if not work_order:
        return []
    return [
        "<h2>Security Work Order</h2>",
        f"<p>{escape(_intro(work_order))}</p>",
        f"<pre>{escape(work_order['markdown'])}</pre>",
    ]

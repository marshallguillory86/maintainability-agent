"""HTML sections rendered straight from stored report fields.

ADR 011 decision 5 requires the HTML skin to carry the *same* remaining
sections as Markdown -- coverage, trend text, work order, findings. Two of
them, coverage and the per-segment trend, were absent from the HTML skin
alone (Grok 63ab820 audit): a reader who opened the HTML report saw a
score with nothing about what produced it and only a one-line direction
where the Markdown carried the whole trend.

They live here rather than in ``_html_view`` because that module sits at
its own size ceiling, and because these two format a report dict the
scorer already produced -- no charts, no SVG, no history records.
"""

from __future__ import annotations

from html import escape
from typing import Any


def coverage_section(report: dict[str, Any]) -> list[str]:
    """What examined the tree, and what nothing did -- the same
    ``analyzer_coverage`` the Markdown skin prints. Two reports with
    different coverage are not comparable, so the HTML must show what
    produced its score, not only the score.
    """
    coverage = report.get("analyzer_coverage")
    if not coverage:
        return []
    if coverage.get("error"):
        return ["<h2>Coverage</h2>",
                f"<p>No analyzers ran: {escape(str(coverage['error']))}</p>"]
    selection = coverage["selection"]
    sources = coverage.get("sources", {})
    parts = [
        "<h2>Coverage</h2>",
        f"<p>{coverage['tools_contributed']} of {coverage['tools_attempted']} tools "
        f"contributed — concerns {escape(', '.join(selection['concerns']))}, depth "
        f"{escape(str(selection['depth']))}, license policy "
        f"{escape(str(selection['license_policy']))}. Plus "
        f"{sources.get('built_in', 0)} built-in detectors.</p>",
        "<table><tr><th>Source</th><th>Tier</th><th>Outcome</th><th>Version</th>"
        "<th>Measurements</th><th>Findings</th></tr>",
    ]
    for outcome, entries in sorted(coverage["by_outcome"].items()):
        for entry in sorted(entries, key=lambda i: (i.get("tier") != "analyzer", i["tool"])):
            parts.append(
                f"<tr><td>{escape(str(entry['tool']))}</td>"
                f"<td>{escape(str(entry.get('tier', 'analyzer')))}</td>"
                f"<td>{escape(str(outcome))}</td>"
                f"<td>{escape(str(entry.get('version') or '—'))}</td>"
                f"<td>{escape(str(entry.get('measurements', '—')))}</td>"
                f"<td>{escape(str(entry.get('findings', '—')))}</td></tr>")
    parts.append("</table>")
    return parts


def trend_section(report: dict[str, Any]) -> list[str]:
    """The per-segment trend text the Markdown skin prints, from
    ``scan_history``: direction, debt velocity, growth, persistence, and
    the instrument breaks that split one series into two (ADR 009). The
    executive strip's one-line direction is not this section.
    """
    history = report.get("scan_history")
    if not history:
        return []
    parts = ["<h2>Trend</h2>"]
    if len(history) > 1:
        parts.append(f"<p>{len(history)} separate series; scans either side of a "
                     "break were produced by different instruments and are reported "
                     "apart.</p>")
    for index, segment in enumerate(history, start=1):
        if segment.get("break_reason"):
            parts.append("<p><strong>Break before this series:</strong> "
                         f"{escape(str(segment['break_reason']))}.</p>")
        moved = segment["trajectory"]
        change = f" Change {moved['change']:+.2f}." if moved.get("change") is not None else ""
        parts.append(
            f"<p>Series {index} — {segment['scans']} scans, "
            f"{escape(str(segment['from']))} to {escape(str(segment['to']))}.</p><ul>"
            f"<li>Direction: {escape(str(moved['direction']))}.{change}</li>"
            f"<li>Debt velocity: {segment['velocity']['introduced']} introduced, "
            f"{segment['velocity']['cleared']} cleared.</li>"
            f"<li>Growth: {escape(str(segment['growth']['verdict']))}.</li>"
            f"<li>Never cleared in this window: "
            f"{segment['persistent_findings']} findings.</li></ul>")
    parts.append("<p>Every figure describes scans that happened; nothing forecasts.</p>")
    return parts

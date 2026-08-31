"""HTML sections rendered straight from stored report fields.

ADR 011 decision 5 requires the HTML skin to carry the same remaining
sections Markdown prints when the report dict has the data. Coverage and
trend shipped first; a field test then showed economics, pillars, aspects,
the unscored list, the environment work order, hotspots and largest files
still Markdown-only. Those builders live here because ``_html_view`` sits
at the file-size line and because they format stored fields -- no charts,
no SVG, no score.
"""

from __future__ import annotations

from html import escape
from typing import Any

from ._evidence_view import test_suite_lines
from ._hotspots import hotspot_cognitive, hotspot_complexity, hotspot_name
from ._scan_view import POSTURE_NOTE
from ._tdd_view import tdd_sentences


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


def remaining_sections(report: dict[str, Any]) -> list[str]:
    """Economics, pillars, ISO/aspects, environment, hotspots, largest files."""
    return [
        *_economic_section(report),
        *_tdd_section(report),
        *_test_suite_section(report),
        *_pillars_section(report),
        *_iso_section(report),
        *_aspects_section(report),
        *_environment_section(report),
        *_largest_files_section(report),
        *_hotspots_section(report),
    ]


def _tdd_section(report: dict[str, Any]) -> list[str]:
    sentences = tdd_sentences(report.get("tdd_structure"))
    if not sentences:
        return []
    parts = ["<h2>TDD-shaped tests</h2>"]
    parts.extend(f"<p>{escape(sentence)}</p>" for sentence in sentences)
    return parts


def _test_suite_section(report: dict[str, Any]) -> list[str]:
    """The opted-in suite's result — same sentences as the Markdown skin,
    so a failed run is visible here too (ADR 011 decision 5, P8)."""
    sentences = test_suite_lines(report.get("test_suite"))
    if not sentences:
        return []
    parts = ["<h2>Test Suite</h2>"]
    parts.extend(f"<p>{escape(sentence)}</p>" for sentence in sentences)
    return parts


def _table(headers: list[str], rows: list[list[str]]) -> list[str]:
    if not rows:
        return []
    head = "<tr>" + "".join(f"<th>{escape(h)}</th>" for h in headers) + "</tr>"
    body = [
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    ]
    return ["<table>", head, *body, "</table>"]


def _economic_section(report: dict[str, Any]) -> list[str]:
    block = report.get("economic_impact")
    if not block:
        return []
    currency = escape(str(block.get("currency", "USD")))
    low = f"{block['low']:,.0f}"
    high = f"{block['high']:,.0f}"
    base = f"{block['base']:,.0f}"
    horizon = escape(str(block["planning_horizon_months"]))
    items = escape(str(block.get("work_order_items", 0)))
    parts = [
        "<h2>Economic Context (scenario)</h2>",
        f"<p><strong>{escape(low)} – {escape(high)} {currency}</strong> over "
        f"{horizon} months (base {escape(base)} {currency}), across "
        f"{items} work-order item(s).</p>",
        "<p>This is a scenario, not a prediction.</p>",
        "<p>Assumptions:</p>",
        "<ul>",
    ]
    parts.extend(
        f"<li>{escape(str(assumption))}</li>"
        for assumption in block.get("assumptions") or []
    )
    parts.append("</ul>")
    incident = block.get("incident_term")
    if incident:
        cost = f"{incident['representative_incident_cost']:,.0f}"
        parts.append(
            f"<p>Separate incident term: {escape(cost)} {currency} — "
            f"{escape(str(incident['note']))}</p>"
        )
    return parts


def _pillars_section(report: dict[str, Any]) -> list[str]:
    pillars = report.get("pillars")
    practice = report.get("practice")
    if not pillars or not practice:
        return []
    parts = [
        "<h2>Pillars</h2>",
        f"<p><strong>Practice level {escape(str(practice['level']))} of 5</strong>"
        f" — {escape(str(practice['summary']))}.</p>",
    ]
    rows = []
    for entry in pillars:
        condition = "—" if entry["condition"] is None else f"{entry['condition']:.1f}"
        if entry["posture"] is None:
            reading = "not measured — see below"
        else:
            note = POSTURE_NOTE.get(entry["posture"], entry["posture"])
            reading = f"{entry['posture']}: {note}"
        rows.append([
            escape(str(entry["pillar"])),
            escape(str(entry["scope"])),
            escape(str(entry["practice"])),
            escape(condition),
            escape(reading),
        ])
    parts.extend(_table(
        ["Pillar", "Scope", "Practice", "Condition", "Reading"], rows,
    ))
    unmeasured = [e for e in pillars if e["condition"] is None]
    if unmeasured:
        parts.append("<p><strong>Not measured here, and why:</strong></p><ul>")
        parts.extend(
            f"<li><strong>{escape(str(e['pillar']))}</strong> — "
            f"{escape(str(e['reason']))}</li>"
            for e in unmeasured
        )
        parts.append("</ul>")
    if practice.get("signals"):
        found = ", ".join(
            f"<code>{escape(str(s['signal']))}</code>" for s in practice["signals"]
        )
        parts.append(f"<p>Enforcement found: {found}.</p>")
    if practice.get("caps"):
        level = escape(str(practice["level"]))
        parts.extend(
            f"<p>Held at level {level}: {escape(str(cap))}</p>"
            for cap in practice["caps"]
        )
    return parts


def _iso_section(report: dict[str, Any]) -> list[str]:
    categories = (report.get("score") or {}).get("categories") or {}
    if not categories:
        return []
    rows = [
        [escape(str(name)), escape(str(value))]
        for name, value in categories.items()
    ]
    return [
        "<h2>ISO/IEC 25010 Maintainability Score</h2>",
        *_table(["Category", "Score"], rows),
    ]


def _aspects_section(report: dict[str, Any]) -> list[str]:
    score = report.get("score") or {}
    aspects = score.get("aspects") or {}
    parts: list[str] = []
    if aspects:
        rows = [
            [
                escape(name.replace("_", " ")),
                escape("not measurable" if value is None else str(value)),
            ]
            for name, value in aspects.items()
        ]
        parts.extend([
            "<h2>Aspect Scores</h2>",
            *_table(["Aspect", "Score"], rows),
        ])
    unscored = (score.get("rubric") or {}).get("unscored") or {}
    if unscored:
        rows = [
            [escape(name.replace("_", " ")), escape(str(reason))]
            for name, reason in unscored.items()
        ]
        parts.extend([
            "<h2>Not Scored — no measurement exists</h2>",
            *_table(["Aspect", "Why"], rows),
        ])
    return parts


def _environment_section(report: dict[str, Any]) -> list[str]:
    items = report.get("environment_work_order") or []
    if not items:
        return []
    rows = [
        [
            f"<code>{escape(str(item['tool']))}</code>",
            escape(str(item["reason"])),
            f"<code>{escape(str(item['install']))}</code>",
            f"<code>{escape(str(item['verify']))}</code>",
        ]
        for item in items
    ]
    return [
        "<h2>Environment Work Order</h2>",
        "<p>Selected analyzers that could not run, and what it would take. "
        "These commands are for <strong>you</strong> to run — the agent never "
        "installs anything.</p>",
        *_table(["Tool", "Why it did not run", "Install", "Verify"], rows),
    ]


def _largest_files_section(report: dict[str, Any]) -> list[str]:
    files = report.get("largest_files") or []
    if not files:
        return []
    rows = [
        [
            f"<code>{escape(str(item['path']))}</code>",
            escape(str(item["lines"])),
            escape(str(item["status"])),
        ]
        for item in files
    ]
    return [
        "<h2>Largest Files</h2>",
        *_table(["File", "Lines", "Status"], rows),
    ]


def _hotspots_section(report: dict[str, Any]) -> list[str]:
    hotspots = report.get("function_hotspots") or []
    if not hotspots:
        return []
    rows = [
        [
            f"<code>{escape(str(item['path']))}</code>",
            escape(hotspot_name(item, quote="")),
            escape(str(item["start_line"])),
            escape(str(item["lines"])),
            escape(hotspot_complexity(item)),
            escape(hotspot_cognitive(item)),
            escape(str(item["status"])),
        ]
        for item in hotspots
    ]
    return [
        "<h2>Function Hotspots</h2>",
        *_table(
            ["File", "Declaration", "Line", "Lines", "Complexity",
             "Cognitive", "Status"],
            rows,
        ),
    ]

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

from ._coverage_notes import coverage_notes
from ._evidence_view import test_suite_lines
from ._grammar import counted
from ._hotspots import hotspot_cognitive, hotspot_complexity, hotspot_name
from ._scan_view import pillar_cells
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
    parts.extend(_coverage_notes_html(coverage))
    return parts


def _coverage_notes_html(coverage: dict[str, Any]) -> list[str]:
    """The gap prose the Markdown skin prints, in the HTML skin too.

    The table answers "what ran". These notes answer what a reader asks
    next — one source only, a dimension the analyzer tier declined,
    nothing examined — and the HTML report carried **none** of them,
    including "Nothing examined", which `_coverage_notes` itself calls
    the point of the whole section. ADR 011 says the skins render one
    report dict and never disagree; that claim was resting on the prose
    being built as Markdown strings inside the Markdown renderer.

    Rendered as the same visible sentences rather than re-marked-up:
    the notes carry `**bold**` and `` `code` `` for Markdown, and a
    reader of the page should see the text, not the syntax.
    """
    return [
        f"<p>{escape(line.replace('**', '').replace('`', ''))}</p>"
        for line in coverage_notes(coverage) if line
    ]


def _current_series_html(history: list[dict[str, Any]]) -> list[str]:
    """The series in force, in full — the one a reader acts on today."""
    segment = history[-1]
    moved = segment["trajectory"]
    change = f" Change {moved['change']:+.2f}." if moved.get("change") is not None else ""
    label = "Current series — " if len(history) > 1 else ""
    parts = []
    if segment.get("break_reason"):
        parts.append("<p><strong>This series begins at a break:</strong> "
                     f"{escape(str(segment['break_reason']))}.</p>")
    parts.append(
        f"<p>{label}{counted(segment['scans'], 'scan')}, "
        f"{escape(str(segment['from']))} to {escape(str(segment['to']))}.</p><ul>"
        f"<li>Direction: {escape(str(moved['direction']))}.{change}</li>"
        f"<li>Debt velocity: {segment['velocity']['introduced']} introduced, "
        f"{segment['velocity']['cleared']} cleared.</li>"
        f"<li>Growth: {escape(str(segment['growth']['verdict']))}.</li>"
        f"<li>Never cleared in this window: "
        f"{counted(segment['persistent_findings'], 'finding')}.</li></ul>")
    return parts


def _earlier_series_html(history: list[dict[str, Any]]) -> list[str]:
    """Prior instruments as one table, newest first.

    The Markdown skin's reasoning, kept identical here on purpose: 49
    segments rendered as 49 blocks is a section nobody reads, and the two
    skins disagreeing about that would be drift (ADR 011).
    """
    earlier = history[:-1]
    if not earlier:
        return []
    rows = []
    for segment in reversed(earlier):
        moved = segment["trajectory"]
        change = f"{moved['change']:+.2f}" if moved.get("change") is not None else "—"
        began = (segment.get("break_summary") or segment.get("break_reason")
                 or "the first recorded scan")
        rows.append(
            f"<tr><td>{escape(str(segment['from']))} to {escape(str(segment['to']))}</td>"
            f"<td>{segment['scans']}</td>"
            f"<td>{escape(str(moved['direction']))}</td><td>{change}</td>"
            f"<td>{escape(str(began))}</td></tr>")
    return [
        f"<h3>Earlier series ({counted(len(earlier), 'series', 'series')})</h3>",
        "<table><thead><tr><th>Window</th><th>Scans</th><th>Direction</th>"
        "<th>Change</th><th>Began at a break in</th></tr></thead><tbody>"
        + "".join(rows) + "</tbody></table>",
    ]


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
                     "apart. The current series is given in full, the earlier ones "
                     "summarized.</p>")
    parts.extend(_current_series_html(history))
    parts.extend(_earlier_series_html(history))
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
        condition, reading = pillar_cells(entry)
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
    parts.extend(_unmeasured_pillars_html(pillars))
    parts.extend(_practice_footer_html(practice))
    return parts


def _unmeasured_pillars_html(pillars: list[dict[str, Any]]) -> list[str]:
    """Why a pillar has no condition — an unexplained dash reads as "fine"."""
    unmeasured = [e for e in pillars if e["condition"] is None]
    if not unmeasured:
        return []
    return [
        "<p><strong>Not measured here, and why:</strong></p><ul>",
        *(f"<li><strong>{escape(str(e['pillar']))}</strong> — "
          f"{escape(str(e['reason']))}</li>" for e in unmeasured),
        "</ul>",
    ]


def _practice_footer_html(practice: dict[str, Any]) -> list[str]:
    """What enforcement was detected, and what held the level down."""
    parts = []
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

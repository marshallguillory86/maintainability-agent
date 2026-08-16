"""The HTML skin: one file an executive will actually open — ADR 011.

Reads the report dictionary and the stored scan records, and computes
no score: every number on the page was published by the scorer or
written into the history. The charts are deterministic SVG built here
from those stored fields — no CDN, no script, no fetch at view time, so
the file opens identically offline (P1) and renders the same bytes for
the same inputs.

Findings carry a presentation severity derived from the published class
risk (`CLASS_RISK_EFFORT` in the standard): risk 5 is Severe, 4 High,
3 Medium, 1–2 Low, and a hard-gate failure displays as Severe. Labels
organize the existing findings for a reader; they change no estimate,
range or grade, which is why this module may not import the scorer.

Two series the charts must never merge: pillar *condition* and
*practice* maturity answer different questions (ADR 007), so they are
two charts. A schema-1 record carries neither and appears as a gap —
plotted where its data exists (the rollup estimate) and absent where it
does not, never interpolated.
"""
from __future__ import annotations

from html import escape
from typing import Any

from . import _evidence_view as view
from ._semantic_view import semantic_class_label

_WIDTH, _HEIGHT, _PAD = 640, 260, 40

_SEVERITY_BY_RISK = {5: "Severe", 4: "High", 3: "Medium"}
_SEVERITY_ORDER = ("Severe", "High", "Medium", "Low")

_CSS = """
body{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;margin:2rem auto;
max-width:52rem;padding:0 1rem;color:#1a1a1a;background:#fff}
h1,h2{font-weight:600} h1{font-size:1.4rem} h2{font-size:1.1rem;margin-top:2rem}
table{border-collapse:collapse;width:100%;margin:.6rem 0} td,th{border:1px solid #ddd;
padding:.35rem .6rem;text-align:left;font-size:.9rem}
.summary{border:1px solid #ccc;border-radius:6px;padding:1rem 1.2rem;margin:1rem 0}
.summary .estimate{font-size:2rem;font-weight:700}
.summary div{margin:.15rem 0;font-size:1rem}
.muted{color:#666;font-size:.85rem} svg{max-width:100%;height:auto}
.gap-note{font-style:italic;color:#666;font-size:.8rem}
.sev-Severe{color:#9b2c2c;font-weight:600} .sev-High{color:#b7791f;font-weight:600}
"""


def severity_of(risk: Any) -> str:
    """The published class risk as a display label. Output, never input."""
    try:
        return _SEVERITY_BY_RISK.get(int(risk), "Low")
    except (TypeError, ValueError):
        return "Low"


def severity_counts(report: dict[str, Any]) -> dict[str, int]:
    """This scan's findings by severity; hard gates display as Severe."""
    counts = dict.fromkeys(_SEVERITY_ORDER, 0)
    for item in report.get("work_order") or []:
        counts[severity_of(item.get("risk"))] += 1
    counts["Severe"] += len(report.get("hard_gate_failures") or [])
    return counts


def render_html(report: dict[str, Any], records: list[Any]) -> str:
    """The whole page, deterministically, from what was stored."""
    score = report["score"]
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Maintainability Report</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>Maintainability Report</h1>",
        f"<p class='muted'>Root: {escape(str(report.get('root', '')))} — "
        f"branch {escape(str(report.get('git_branch') or '(unknown)'))}</p>",
        *_executive_strip(report, score, records),
        *_history_table(records),
        *_chart_sections(records, score),
        *_work_order_section(report),
        *_hard_gate_section(report),
        *_semantic_section(report),
        "</body></html>",
    ]
    return "\n".join(parts)


def _executive_strip(report: dict[str, Any], score: dict[str, Any],
                     records: list[Any]) -> list[str]:
    """The result, the gate, the finding counts, the direction. First."""
    failures = report.get("hard_gate_failures") or []
    gate = (
        f"Gate: <strong>not clear</strong> — {len(failures)} hard-gate failure(s)."
        if failures else "Gate: <strong>clear</strong>."
    )
    counts = severity_counts(report)
    count_rows = [
        f"<tr><td class='sev-{label}'>{label}</td><td>{counts[label]}</td></tr>"
        for label in _SEVERITY_ORDER
    ]
    return [
        "<div class='summary'>",
        f"<div class='estimate'>{escape(view.estimate(score))}"
        f" &middot; grade {escape(view.verified_grade(score))}</div>",
        f"<div>Range: {escape(view.score_range(score))} &middot; "
        f"Source: {escape(view.estimate_source(score))}</div>",
        f"<div>{escape(view.status_sentence(score, report.get('analyzer_coverage') is not None))}</div>",
        f"<div>{gate}</div>",
        f"<div>{escape(_direction_sentence(records))}</div>",
        "<table><tr><th>Severity</th><th>Findings</th></tr>",
        *count_rows,
        f"<tr><td>Total findings</td><td>{sum(counts.values())}</td></tr>",
        "</table>",
        "</div>",
    ]


def _direction_sentence(records: list[Any]) -> str:
    """The series direction, from stored estimates only. Never a forecast."""
    estimates = [r.estimate for r in records if r.estimate is not None]
    if len(estimates) < 2:
        return "No history yet: this is the first recorded scan." if len(estimates) < 1 \
            else "No history yet beyond this scan; direction needs two."
    first, last = estimates[0], estimates[-1]
    if last > first:
        return f"Improving across {len(estimates)} recorded scans ({first} to {last})."
    if last < first:
        return f"Declining across {len(estimates)} recorded scans ({first} to {last})."
    return f"Flat across {len(estimates)} recorded scans (at {last})."


def _history_table(records: list[Any]) -> list[str]:
    """One row per recorded scan; findings is the stored fingerprint count.

    `len(fingerprints)` is the only per-scan finding total every schema
    actually stored — inventing a category-count series for old records
    would chart data nobody recorded.
    """
    if not records:
        return []
    rows = [
        "<h2>Recorded scans</h2>",
        "<table><tr><th>Recorded</th><th>Commit</th><th>Estimate</th>"
        "<th>Findings</th></tr>",
    ]
    for record in records:
        estimate = record.estimate if record.estimate is not None else "—"
        rows.append(
            f"<tr><td>{escape(str(record.recorded_at))}</td>"
            f"<td>{escape(str(record.commit)[:8])}</td>"
            f"<td>{escape(str(estimate))}</td>"
            f"<td>{len(record.fingerprints)}</td></tr>"
        )
    rows.append("</table>")
    return rows


def _chart_sections(records: list[Any], score: dict[str, Any]) -> list[str]:
    parts = ["<h2>Estimate over recorded scans</h2>"]
    estimate_points = [
        (index, r.estimate, r.range_low, r.range_high)
        for index, r in enumerate(records) if r.estimate is not None
    ]
    parts.append(_line_chart("chart-estimate", estimate_points, 0.0, 5.0))

    parts.append("<h2>Pillars over time (condition)</h2>")
    pillar_names = sorted({name for r in records for name in (r.pillars or {})})
    pillar_series = {
        name: [(i, (r.pillars or {}).get(name), None, None)
               for i, r in enumerate(records) if (r.pillars or {}).get(name) is not None]
        for name in pillar_names
    }
    parts.append(_multi_line_chart("chart-pillars", pillar_series, 0.0, 5.0))
    parts.append(_gap_note(records, "pillars"))

    parts.append("<h2>Practice level over time (maturity — a separate series)</h2>")
    practice_points = [
        (i, float(r.practice_level), None, None)
        for i, r in enumerate(records) if r.practice_level is not None
    ]
    parts.append(_line_chart("chart-practice", practice_points, 0.0, 5.0,
                             y_title="maturity (0-5)"))
    parts.append(_gap_note(records, "practice_level"))

    parts.append("<h2>Categories, this scan</h2>")
    parts.append(_bar_chart("chart-categories", score.get("categories") or {}))
    return parts


def _gap_note(records: list[Any], field: str) -> str:
    missing = sum(
        1 for r in records
        if not (r.pillars if field == "pillars" else r.practice_level is not None)
    )
    if not records:
        return "<p class='gap-note'>No history yet.</p>"
    if missing:
        return (f"<p class='gap-note'>{missing} of {len(records)} recorded scans "
                "predate this series (schema 1) and appear as gaps.</p>")
    return ""


def _x(index: int, count: int) -> float:
    span = _WIDTH - 2 * _PAD
    return _PAD + (span * index / max(count - 1, 1))


def _y(value: float, low: float, high: float) -> float:
    span = _HEIGHT - 2 * _PAD
    return _HEIGHT - _PAD - span * (value - low) / (high - low or 1.0)


def _svg_open(chart_id: str, low: float = 0.0, high: float = 5.0,
              y_title: str = "score (0-5)") -> str:
    """Framed axes, end ticks and a named scale on every chart.

    The 0 and 5 ticks are the reader's calibration: without them a line
    at 4.1 and a line at 2.0 look the same shape. Padding keeps the
    labels off the axis line and inside the viewBox.
    """
    return (
        f'<svg id="{chart_id}" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
        f'role="img" xmlns="http://www.w3.org/2000/svg">'
        f'<rect x="0" y="0" width="{_WIDTH}" height="{_HEIGHT}" fill="#fafafa"/>'
        f'<line x1="{_PAD}" y1="{_PAD}" x2="{_PAD}" y2="{_HEIGHT - _PAD}" '
        'stroke="#999" stroke-width="1"/>'
        f'<line x1="{_PAD}" y1="{_HEIGHT - _PAD}" x2="{_WIDTH - _PAD}" '
        f'y2="{_HEIGHT - _PAD}" stroke="#999" stroke-width="1"/>'
        f'<text x="{_PAD - 8}" y="{_y(low, low, high) + 4:.1f}" text-anchor="end" '
        f'font-size="11" fill="#444">{low:g}</text>'
        f'<text x="{_PAD - 8}" y="{_y(high, low, high) + 4:.1f}" text-anchor="end" '
        f'font-size="11" fill="#444">{high:g}</text>'
        f'<text x="14" y="{_HEIGHT / 2:g}" font-size="11" fill="#444" '
        f'transform="rotate(-90 14 {_HEIGHT / 2:g})" text-anchor="middle">'
        f"{escape(y_title)}</text>"
    )


def _consecutive_runs(points: list[tuple]) -> list[list[tuple]]:
    """Split a series wherever a scan is missing.

    A polyline drawn across a missing index is interpolation — a segment
    claiming a value for the scan nobody stored, which ADR 011
    invariant 6 forbids. Points on either side of a gap stay plotted;
    the line between them does not exist.
    """
    runs: list[list[tuple]] = []
    for point in points:
        if runs and point[0] == runs[-1][-1][0] + 1:
            runs[-1].append(point)
        else:
            runs.append([point])
    return runs


def _polylines(points: list[tuple], count: int, low: float, high: float,
               color: str, width: str) -> list[str]:
    """One polyline per consecutive run of two or more scans."""
    return [
        '<polyline points="'
        + " ".join(f"{_x(i, count):.1f},{_y(v, low, high):.1f}" for i, v, *_ in run)
        + f'" fill="none" stroke="{color}" stroke-width="{width}"/>'
        for run in _consecutive_runs(points)
        if len(run) >= 2
    ]


def _line_chart(chart_id: str, points: list[tuple], low: float, high: float,
                y_title: str = "score (0-5)") -> str:
    """One series; each point may carry a stored range to shade."""
    if not points:
        return (f'{_svg_open(chart_id, low, high, y_title)}'
                f'<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" '
                f'text-anchor="middle" fill="#666">No history yet</text></svg>')
    count = max(index for index, *_ in points) + 1
    parts = [_svg_open(chart_id, low, high, y_title)]
    # The uncertainty band is subject to the same gap rule as the line:
    # shading across a missing scan claims a range nobody stored.
    band = [p for p in points if p[2] is not None and p[3] is not None]
    for run in _consecutive_runs(band):
        if len(run) < 2:
            continue
        upper = " ".join(f"{_x(i, count):.1f},{_y(hi, low, high):.1f}" for i, _v, _lo, hi in run)
        lower = " ".join(
            f"{_x(i, count):.1f},{_y(lo_v, low, high):.1f}"
            for i, _v, lo_v, _hi in reversed(run)
        )
        parts.append(f'<polygon points="{upper} {lower}" fill="#dbe9f6"/>')
    parts.extend(_polylines(points, count, low, high, "#2b6cb0", "2"))
    for i, v, *_ in points:
        parts.append(f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" r="3" '
                     f'fill="#2b6cb0"><title>scan {i + 1}: {v}</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


_PILLAR_COLORS = ("#2b6cb0", "#2f855a", "#b7791f", "#9b2c2c", "#553c9a")


def _multi_line_chart(chart_id: str, series: dict[str, list[tuple]],
                      low: float, high: float) -> str:
    if not any(series.values()):
        return (f'{_svg_open(chart_id, low, high, "condition (0-5)")}'
                f'<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" '
                f'text-anchor="middle" fill="#666">No history yet</text></svg>')
    count = max(index for points in series.values() for index, *_ in points) + 1
    parts = [_svg_open(chart_id, low, high, "condition (0-5)")]
    for offset, (name, points) in enumerate(sorted(series.items())):
        color = _PILLAR_COLORS[offset % len(_PILLAR_COLORS)]
        parts.extend(_polylines(points, count, low, high, color, "1.5"))
        for i, v, *_ in points:
            parts.append(f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" '
                         f'r="2.5" fill="{color}"><title>{escape(name)} scan {i + 1}: {v}'
                         f"</title></circle>")
    # The legend is part of the chart, not a caption below it: five
    # same-shaped lines without names is a puzzle, not a report.
    for offset, name in enumerate(sorted(series)):
        color = _PILLAR_COLORS[offset % len(_PILLAR_COLORS)]
        swatch_y = 14 + offset * 14
        parts.append(f'<rect x="{_PAD + 10}" y="{swatch_y - 8}" width="10" height="10" '
                     f'fill="{color}"/>')
        parts.append(f'<text x="{_PAD + 26}" y="{swatch_y}" font-size="11" '
                     f'fill="#444">{escape(name)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def _bar_chart(chart_id: str, categories: dict[str, float]) -> str:
    if not categories:
        return (f'{_svg_open(chart_id)}<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" '
                f'text-anchor="middle" fill="#666">No score this scan</text></svg>')
    parts = [_svg_open(chart_id)]
    names = list(categories)
    slot = (_WIDTH - 2 * _PAD) / len(names)
    for position, name in enumerate(names):
        value = float(categories[name])
        height = (_HEIGHT - 2 * _PAD) * value / 5.0
        x = _PAD + position * slot + slot * 0.15
        parts.append(
            f'<rect x="{x:.1f}" y="{_HEIGHT - _PAD - height:.1f}" '
            f'width="{slot * 0.7:.1f}" height="{height:.1f}" fill="#2b6cb0">'
            f"<title>{escape(name)}: {value}</title></rect>"
        )
        parts.append(
            f'<text x="{x + slot * 0.35:.1f}" y="{_HEIGHT - _PAD + 16:.1f}" '
            f'text-anchor="middle" font-size="10" fill="#444">'
            f"{escape(name[:12])}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _work_order_section(report: dict[str, Any]) -> list[str]:
    """Every work item as a row, led by its published severity.

    The identities are `work_order`'s own titles and paths — the same
    strings `render_markdown` prints — so the two skins can never
    disagree about which finding is which.
    """
    items = report.get("work_order") or []
    if not items:
        return []
    rows = [
        "<h2>Work order</h2>",
        "<table><tr><th>Severity</th><th>Band</th><th>Finding</th>"
        "<th>Location</th><th>Do</th></tr>",
    ]
    for item in items:
        severity = severity_of(item.get("risk"))
        line = item.get("line")
        location = f"{item.get('path') or ''}" + (f":{line}" if line else "")
        rows.append(
            f"<tr><td class='sev-{severity}'>{severity}</td>"
            f"<td>{escape(str(item.get('band') or ''))}</td>"
            f"<td>{escape(str(item.get('title') or ''))}</td>"
            f"<td>{escape(location)}</td>"
            f"<td>{escape(str(item.get('target') or ''))}</td></tr>"
        )
    rows.append("</table>")
    return rows


def _hard_gate_section(report: dict[str, Any]) -> list[str]:
    failures = report.get("hard_gate_failures") or []
    if not failures:
        return []
    rows = [
        "<h2>Hard gates</h2>",
        "<table><tr><th>Severity</th><th>Gate</th></tr>",
    ]
    rows.extend(
        f"<tr><td class='sev-Severe'>Severe</td><td>{escape(str(gate))}</td></tr>"
        for gate in failures
    )
    rows.append("</table>")
    return rows


def _semantic_coverage_line(coverage: dict[str, Any]) -> str:
    """Unknown states its reason; typed names its tool. Never a clean zero."""
    language = coverage.get("language") or "TypeScript"
    status = coverage.get("status") or "unknown"
    if status == "unknown":
        return (f"{language} semantic coverage: <strong>unknown</strong> — "
                f"{escape(coverage.get('reason') or 'no type analysis was available.')}")
    tool = f"{coverage.get('tool') or 'typescript'} {coverage.get('version') or ''}".strip()
    return (f"{language} semantic coverage: <strong>{escape(status)}</strong> "
            f"via {escape(tool)}. Other languages have unknown semantic coverage.")


def _semantic_row(finding: dict[str, Any]) -> str:
    evidence = finding.get("source_evidence") or {}
    line_number = evidence.get("line")
    where = f"{evidence.get('path') or ''}" + (f":{line_number}" if line_number else "")
    return (
        f"<tr><td>{escape(semantic_class_label(finding.get('class')))}</td>"
        f"<td>{escape(where)}</td>"
        f"<td>{escape(str(finding.get('message') or ''))}</td></tr>"
    )


def _semantic_section(report: dict[str, Any]) -> list[str]:
    """The ADR 003 block: coverage stated, classes labeled, nothing scored."""
    findings = report.get("semantic_findings") or []
    coverage = report.get("semantic_coverage") or {}
    if not findings and not coverage:
        return []
    parts = ["<h2>Semantic findings</h2>",
             f"<p>{_semantic_coverage_line(coverage)}</p>"]
    if findings:
        parts.append("<table><tr><th>Class</th><th>Location</th><th>Evidence</th></tr>")
        parts.extend(_semantic_row(finding) for finding in findings)
        parts.append("</table>")
    return parts

"""The HTML skin: one file an executive will actually open — ADR 011.

Reads the report dictionary and the stored scan records, and computes
no score: every number on the page was published by the scorer or
written into the history. The charts are deterministic SVG built here
from those stored fields — no CDN, no script, no fetch at view time, so
the file opens identically offline (P1) and renders the same bytes for
the same inputs.

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

_WIDTH, _HEIGHT, _PAD = 640, 160, 28

_CSS = """
body{font-family:-apple-system,'Segoe UI',Roboto,sans-serif;margin:2rem auto;
max-width:52rem;padding:0 1rem;color:#1a1a1a;background:#fff}
h1,h2{font-weight:600} h1{font-size:1.4rem} h2{font-size:1.1rem;margin-top:2rem}
table{border-collapse:collapse;width:100%} td,th{border:1px solid #ddd;
padding:.35rem .6rem;text-align:left;font-size:.9rem}
.summary{border:1px solid #ccc;border-radius:6px;padding:1rem 1.2rem;margin:1rem 0}
.summary .estimate{font-size:2rem;font-weight:700}
.muted{color:#666;font-size:.85rem} svg{max-width:100%;height:auto}
.gap-note{font-style:italic;color:#666;font-size:.8rem}
"""


def render_html(report: dict[str, Any], records: list[Any],
                markdown: str = "") -> str:
    """The whole page, deterministically, from what was stored.

    ``markdown`` is the already-rendered Markdown body, passed in by
    ``renderers.render_html`` rather than imported from it: presentation
    modules may depend downward only, and the acyclicity test is what
    caught this module reaching back up.
    """
    score = report["score"]
    parts = [
        "<!DOCTYPE html>",
        '<html lang="en"><head><meta charset="utf-8">',
        "<title>Maintainability Report</title>",
        f"<style>{_CSS}</style></head><body>",
        "<h1>Maintainability Report</h1>",
        f"<p class='muted'>Root: {escape(str(report.get('root', '')))} — "
        f"branch {escape(str(report.get('git_branch') or '(unknown)'))}</p>",
        *_executive_summary(score, records),
        *_chart_sections(records, score),
        *_findings_sections(markdown),
        "</body></html>",
    ]
    return "\n".join(parts)


def _executive_summary(score: dict[str, Any], records: list[Any]) -> list[str]:
    """Estimate, grade, range, direction — before anything else."""
    return [
        "<div class='summary'>",
        f"<div class='estimate'>{escape(view.estimate(score))}"
        f" &middot; grade {escape(view.verified_grade(score))}</div>",
        f"<div>Range: {escape(view.score_range(score))}</div>",
        f"<div>{escape(view.status_sentence(score))}</div>",
        f"<div>{escape(_direction_sentence(records))}</div>",
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
    parts.append(_line_chart("chart-practice", practice_points, 0.0, 5.0))
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


def _svg_open(chart_id: str) -> str:
    return (f'<svg id="{chart_id}" viewBox="0 0 {_WIDTH} {_HEIGHT}" '
            f'role="img" xmlns="http://www.w3.org/2000/svg">'
            f'<rect x="0" y="0" width="{_WIDTH}" height="{_HEIGHT}" fill="#fafafa"/>')


def _line_chart(chart_id: str, points: list[tuple], low: float, high: float) -> str:
    """One series; each point may carry a stored range to shade."""
    if not points:
        return (f'{_svg_open(chart_id)}<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" '
                f'text-anchor="middle" fill="#666">No history yet</text></svg>')
    count = max(index for index, *_ in points) + 1
    parts = [_svg_open(chart_id)]
    band = [
        p for p in points if p[2] is not None and p[3] is not None
    ]
    if len(band) >= 2:
        upper = " ".join(f"{_x(i, count):.1f},{_y(hi, low, high):.1f}" for i, _v, _lo, hi in band)
        lower = " ".join(
            f"{_x(i, count):.1f},{_y(lo_v, low, high):.1f}"
            for i, _v, lo_v, _hi in reversed(band)
        )
        parts.append(f'<polygon points="{upper} {lower}" fill="#dbe9f6"/>')
    if len(points) >= 2:
        line = " ".join(f"{_x(i, count):.1f},{_y(v, low, high):.1f}" for i, v, *_ in points)
        parts.append(f'<polyline points="{line}" fill="none" stroke="#2b6cb0" stroke-width="2"/>')
    for i, v, *_ in points:
        parts.append(f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" r="3" '
                     f'fill="#2b6cb0"><title>scan {i + 1}: {v}</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


_PILLAR_COLORS = ("#2b6cb0", "#2f855a", "#b7791f", "#9b2c2c", "#553c9a")


def _multi_line_chart(chart_id: str, series: dict[str, list[tuple]],
                      low: float, high: float) -> str:
    if not any(series.values()):
        return (f'{_svg_open(chart_id)}<text x="{_WIDTH / 2}" y="{_HEIGHT / 2}" '
                f'text-anchor="middle" fill="#666">No history yet</text></svg>')
    count = max(index for points in series.values() for index, *_ in points) + 1
    parts = [_svg_open(chart_id)]
    for offset, (name, points) in enumerate(sorted(series.items())):
        color = _PILLAR_COLORS[offset % len(_PILLAR_COLORS)]
        if len(points) >= 2:
            line = " ".join(f"{_x(i, count):.1f},{_y(v, low, high):.1f}" for i, v, *_ in points)
            parts.append(f'<polyline points="{line}" fill="none" stroke="{color}" '
                         f'stroke-width="1.5"/>')
        for i, v, *_ in points:
            parts.append(f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" '
                         f'r="2.5" fill="{color}"><title>{escape(name)} scan {i + 1}: {v}'
                         f"</title></circle>")
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
            f'<text x="{x + slot * 0.35:.1f}" y="{_HEIGHT - _PAD + 14:.1f}" '
            f'text-anchor="middle" font-size="10" fill="#444">'
            f"{escape(name[:12])}</text>"
        )
    parts.append("</svg>")
    return "".join(parts)


def _findings_sections(markdown: str) -> list[str]:
    """The same remaining sections as Markdown, without re-deciding them.

    One source of sections and one source of numbers is what keeps the
    two skins from ever disagreeing; this converts the Markdown body it
    was handed and decides nothing itself.
    """
    _, _, rest = markdown.partition("Scoring standard:")
    return [
        "<h2>Full report</h2>",
        f"<pre style='white-space:pre-wrap'>{escape('Scoring standard:' + rest)}</pre>",
    ]

"""Deterministic SVG charts for the HTML report (ADR 011).

Extracted from ``_html_view`` at that file's own 500-line gate, and the
seam is real: nothing here reads the report or the scorer. Each function
takes already-computed points and returns a self-contained ``<svg>`` —
no CDN, no script, no fetch, so the report opens identically offline (P1)
and renders the same bytes for the same inputs.

The layout is a framed plot with room around it, not a bare polyline in a
box. A chart earns its space only if a reader can place a point: so every
chart draws integer gridlines with labels down the y-axis, dated ticks
along the x-axis, and — for the multi-series chart — a legend in its own
band *below* the plot, never painted over the lines it names.
"""
from __future__ import annotations

from html import escape

# The plot is an inner rectangle inset from the SVG edge. The left inset
# holds the y-axis labels, the bottom inset the x-axis date ticks; a chart
# that plotted to the edge would clip both.
_WIDTH = 680
_LEFT, _RIGHT, _TOP, _BOTTOM = 54, 20, 20, 48
_PLOT_H = 216
_HEIGHT = _TOP + _PLOT_H + _BOTTOM

_PLOT_LEFT = _LEFT
_PLOT_RIGHT = _WIDTH - _RIGHT
_PLOT_TOP = _TOP
_PLOT_BOTTOM = _TOP + _PLOT_H

_AXIS = "#94a3b8"
_GRID = "#e8edf3"
_INK = "#334155"
_BAND = "#dbe9f6"
_PRIMARY = "#2b6cb0"
_SERIES_COLORS = ("#2b6cb0", "#2f855a", "#b7791f", "#9b2c2c", "#553c9a")


def _x(index: int, count: int) -> float:
    """Map a scan index to an x inside the plot area."""
    span = _PLOT_RIGHT - _PLOT_LEFT
    return _PLOT_LEFT + span * index / max(count - 1, 1)


def _y(value: float, low: float, high: float) -> float:
    """Map a value to a y inside the plot area (y grows downward)."""
    span = _PLOT_BOTTOM - _PLOT_TOP
    return _PLOT_BOTTOM - span * (value - low) / (high - low or 1.0)


def _tick_values(low: float, high: float) -> list[float]:
    """Integer gridline values across the scale, e.g. 0..5."""
    first, last = int(low), int(high)
    return [float(v) for v in range(first, last + 1)]


def _x_tick_indices(count: int, max_ticks: int = 6) -> list[int]:
    """A readable subset of scan indices: never crowd the axis.

    All of them when they fit; otherwise an evenly spaced set that always
    includes the first and last scan, so the ends of the series are
    labelled no matter how long the history grows.
    """
    if count <= 1:
        return [0]
    if count <= max_ticks:
        return list(range(count))
    step = (count - 1) / (max_ticks - 1)
    return sorted({round(i * step) for i in range(max_ticks)})


def _svg_header(chart_id: str, height: int) -> str:
    return (
        f'<svg id="{chart_id}" viewBox="0 0 {_WIDTH} {height}" role="img" '
        f'xmlns="http://www.w3.org/2000/svg" font-family="'
        f"-apple-system,'Segoe UI',Roboto,sans-serif\">"
        f'<rect x="0" y="0" width="{_WIDTH}" height="{height}" fill="#fff"/>'
    )


def _frame(low: float, high: float, y_title: str,
           x_labels: list[str] | None) -> list[str]:
    """Gridlines, axis lines, y-value labels, a y-title, and x date ticks.

    This is the calibration the old charts lacked: a line at 4.1 and a
    line at 2.0 read as the same shape until the reader can see the 0..5
    ladder behind them and the dates beneath them.
    """
    parts: list[str] = []
    for value in _tick_values(low, high):
        y = _y(value, low, high)
        parts.append(
            f'<line x1="{_PLOT_LEFT}" y1="{y:.1f}" x2="{_PLOT_RIGHT}" '
            f'y2="{y:.1f}" stroke="{_GRID}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{_PLOT_LEFT - 8}" y="{y + 3.5:.1f}" text-anchor="end" '
            f'font-size="11" fill="{_INK}">{value:g}</text>'
        )
    # Axis lines drawn over the gridlines so the frame reads as the edge.
    parts.append(
        f'<line x1="{_PLOT_LEFT}" y1="{_PLOT_TOP}" x2="{_PLOT_LEFT}" '
        f'y2="{_PLOT_BOTTOM}" stroke="{_AXIS}" stroke-width="1"/>'
    )
    parts.append(
        f'<line x1="{_PLOT_LEFT}" y1="{_PLOT_BOTTOM}" x2="{_PLOT_RIGHT}" '
        f'y2="{_PLOT_BOTTOM}" stroke="{_AXIS}" stroke-width="1"/>'
    )
    mid_y = (_PLOT_TOP + _PLOT_BOTTOM) / 2
    parts.append(
        f'<text x="16" y="{mid_y:g}" font-size="11" fill="{_INK}" '
        f'transform="rotate(-90 16 {mid_y:g})" text-anchor="middle">'
        f"{escape(y_title)}</text>"
    )
    parts.extend(_x_date_ticks(x_labels))
    return parts


def _x_date_ticks(x_labels: list[str] | None) -> list[str]:
    """Dated ticks under the x-axis for a chosen subset of scans."""
    if not x_labels:
        return []
    count = len(x_labels)
    parts: list[str] = []
    for index in _x_tick_indices(count):
        x = _x(index, count)
        parts.append(
            f'<line x1="{x:.1f}" y1="{_PLOT_BOTTOM}" x2="{x:.1f}" '
            f'y2="{_PLOT_BOTTOM + 4}" stroke="{_AXIS}" stroke-width="1"/>'
        )
        parts.append(
            f'<text x="{x:.1f}" y="{_PLOT_BOTTOM + 18:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{_INK}">{escape(x_labels[index])}</text>'
        )
    return parts


def _empty(chart_id: str, height: int, low: float, high: float, y_title: str) -> str:
    parts = [_svg_header(chart_id, height), *_frame(low, high, y_title, None)]
    parts.append(
        f'<text x="{_WIDTH / 2:.0f}" y="{(_PLOT_TOP + _PLOT_BOTTOM) / 2:.0f}" '
        f'text-anchor="middle" fill="#94a3b8" font-size="13">No history yet</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def _runs(points: list[tuple]) -> list[list[tuple]]:
    """Split a series wherever a scan is missing.

    A polyline across a missing index is interpolation — a segment
    claiming a value for a scan nobody stored (ADR 011 invariant 6).
    Points either side of a gap stay plotted; the line between them does
    not exist.
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
    return [
        '<polyline points="'
        + " ".join(f"{_x(i, count):.1f},{_y(v, low, high):.1f}" for i, v, *_ in run)
        + f'" fill="none" stroke="{color}" stroke-width="{width}" '
        'stroke-linejoin="round"/>'
        for run in _runs(points)
        if len(run) >= 2
    ]


def line_chart(chart_id: str, points: list[tuple], low: float, high: float,
               y_title: str = "score (0-5)",
               x_labels: list[str] | None = None) -> str:
    """One series; each point may carry a stored range to shade."""
    if not points:
        return _empty(chart_id, _HEIGHT, low, high, y_title)
    count = max(index for index, *_ in points) + 1
    parts = [_svg_header(chart_id, _HEIGHT), *_frame(low, high, y_title, x_labels)]
    # The uncertainty band obeys the same gap rule as the line: shading
    # across a missing scan claims a range nobody stored.
    band = [p for p in points if p[2] is not None and p[3] is not None]
    for run in _runs(band):
        if len(run) < 2:
            continue
        upper = " ".join(f"{_x(i, count):.1f},{_y(hi, low, high):.1f}" for i, _v, _lo, hi in run)
        lower = " ".join(
            f"{_x(i, count):.1f},{_y(lo_v, low, high):.1f}"
            for i, _v, lo_v, _hi in reversed(run)
        )
        parts.append(f'<polygon points="{upper} {lower}" fill="{_BAND}"/>')
    parts.extend(_polylines(points, count, low, high, _PRIMARY, "2"))
    for i, v, *_ in points:
        parts.append(
            f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" r="3" '
            f'fill="{_PRIMARY}"><title>scan {i + 1}: {v}</title></circle>'
        )
    parts.append("</svg>")
    return "".join(parts)


def _legend(names: list[str], colors: list[str]) -> tuple[list[str], int]:
    """A legend in its own band below the plot, wrapped to fit the width.

    Returned with the extra height it needs so the caller can grow the
    viewBox. The old legend was painted at the top-left *inside* the plot,
    on top of the very lines it labelled; this one never overlaps them.
    """
    parts: list[str] = []
    x, y = _PLOT_LEFT, _HEIGHT + 6
    rows = 1
    for name, color in zip(names, colors):
        width = 22 + len(name) * 6.2  # swatch + text, monospace-ish estimate
        if x + width > _PLOT_RIGHT and x > _PLOT_LEFT:
            x = _PLOT_LEFT
            y += 18
            rows += 1
        parts.append(
            f'<rect x="{x:.1f}" y="{y - 9:.1f}" width="11" height="11" '
            f'rx="2" fill="{color}"/>'
        )
        parts.append(
            f'<text x="{x + 16:.1f}" y="{y:.1f}" font-size="11" fill="{_INK}">'
            f"{escape(name)}</text>"
        )
        x += width + 6
    return parts, rows * 18 + 6


def multi_line_chart(chart_id: str, series: dict[str, list[tuple]],
                     low: float, high: float, y_title: str = "condition (0-5)",
                     x_labels: list[str] | None = None) -> str:
    """Several series on one scale, distinguished by colour and a legend."""
    if not any(series.values()):
        return _empty(chart_id, _HEIGHT + 24, low, high, y_title)
    count = max(index for points in series.values() for index, *_ in points) + 1
    names = sorted(series)
    colors = [_SERIES_COLORS[i % len(_SERIES_COLORS)] for i in range(len(names))]
    legend, legend_h = _legend(names, colors)
    height = _HEIGHT + legend_h
    parts = [_svg_header(chart_id, height), *_frame(low, high, y_title, x_labels)]
    for name, color in zip(names, colors):
        points = series[name]
        parts.extend(_polylines(points, count, low, high, color, "1.6"))
        for i, v, *_ in points:
            parts.append(
                f'<circle cx="{_x(i, count):.1f}" cy="{_y(v, low, high):.1f}" '
                f'r="2.5" fill="{color}"><title>{escape(name)} scan {i + 1}: {v}'
                f"</title></circle>"
            )
    parts.extend(legend)
    parts.append("</svg>")
    return "".join(parts)


def bar_chart(chart_id: str, categories: dict[str, float]) -> str:
    """This scan's category scores, one bar each, on the same 0..5 ladder."""
    if not categories:
        return _empty(chart_id, _HEIGHT, 0.0, 5.0, "score (0-5)")
    parts = [_svg_header(chart_id, _HEIGHT), *_frame(0.0, 5.0, "score (0-5)", None)]
    names = list(categories)
    slot = (_PLOT_RIGHT - _PLOT_LEFT) / len(names)
    for position, name in enumerate(names):
        value = float(categories[name])
        top = _y(value, 0.0, 5.0)
        height = _PLOT_BOTTOM - top
        x = _PLOT_LEFT + position * slot + slot * 0.15
        centre = x + slot * 0.35
        parts.append(
            f'<rect x="{x:.1f}" y="{top:.1f}" width="{slot * 0.7:.1f}" '
            f'height="{height:.1f}" rx="2" fill="{_PRIMARY}">'
            f"<title>{escape(name)}: {value}</title></rect>"
        )
        parts.append(
            f'<text x="{centre:.1f}" y="{top - 5:.1f}" text-anchor="middle" '
            f'font-size="10" fill="{_INK}">{value:g}</text>'
        )
        parts.append(_bar_label(name, centre))
    parts.append("</svg>")
    return "".join(parts)


def _bar_label(name: str, centre: float) -> str:
    """The full category name under its bar, angled so it need not truncate.

    The old chart clipped every name to 12 characters, which turned
    distinct categories into the same stub; angling the whole name keeps
    them legible and distinct without stealing plot height.
    """
    y = _PLOT_BOTTOM + 14
    return (
        f'<text x="{centre:.1f}" y="{y:.1f}" text-anchor="end" font-size="10" '
        f'fill="{_INK}" transform="rotate(-30 {centre:.1f} {y:.1f})">'
        f"{escape(name)}</text>"
    )

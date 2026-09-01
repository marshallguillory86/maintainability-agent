"""ADR 011: the HTML skin is an executive report, not escaped Markdown."""

from __future__ import annotations

import copy
import html as html_module
import re
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest
from test_history_schema2 import _repo

from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit.cli import main
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_html, render_markdown
from maintainability_audit.report import build_report

SEVERITY_BY_RISK = {5: "Severe", 4: "High", 3: "Medium", 2: "Low", 1: "Low"}
CHARTS = ("chart-estimate", "chart-pillars", "chart-practice", "chart-categories")


def _item(finding_class: str, path: str, risk: int) -> dict:
    return {
        "finding_class": finding_class,
        "title": f"{finding_class} in {path}",
        "path": path,
        "line": 7,
        "target": f"address {finding_class}",
        "severity": 1.0,
        "band": "quick-win" if risk >= 4 else "fill-in",
        "risk": risk,
        "effort": 1,
        "rationale": "published class risk",
        "delta": 0.0,
        "class_delta": 0.0,
        "class_count": 1,
        "verification": "python -m maintainability_audit --root . --format json",
    }


@pytest.fixture
def executive_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict, list]:
    """A real report and real stored records, with legible test populations."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    output = tmp_path / "report.md"
    assert main(["--root", str(root), "--record-history", "--output", str(output)]) == 0
    assert main(["--root", str(root), "--record-history", "--output", str(output)]) == 0

    report = build_report(root, load_config(None))
    report["work_order_selection"] = None
    report["work_order"] = [
        _item("risk-pattern", "src/severe.py", 5),
        _item("oversized-declaration", "src/high.py", 4),
        _item("oversized-file", "src/medium.py", 3),
        _item("dead-code", "src/low.py", 2),
        _item("semantic-universal", "src/typed.ts", 4),
    ]
    report["hard_gate_failures"] = ["forbidden generated artifact: dist/bundle.js"]
    report["summary"]["hard_gate_failures"] = 1
    report["semantic_findings"] = [
        {
            "class": "universal",
            "rule_id": "typed-boundary",
            "message": "string supplied where OrderStatus is required",
            "source_evidence": {
                "path": "src/typed.ts",
                "line": 7,
                "diagnostic_code": "TS2345",
            },
        },
    ]
    report["semantic_coverage"] = {
        "language": "TypeScript",
        "status": "typed",
        "tool": "typescript",
        "version": "5.9.2",
    }

    stored = read_history(root / DEFAULT_HISTORY_PATH)
    records = [
        replace(
            stored[0],
            recorded_at="2026-08-14T10:00:00Z",
            commit="1" * 40,
            fingerprints=("finding:one", "finding:two"),
        ),
        replace(
            stored[1],
            recorded_at="2026-08-15T10:00:00Z",
            commit="2" * 40,
            fingerprints=tuple(f"finding:{index}" for index in range(5)),
        ),
    ]
    return report, records


def _body(html: str) -> str:
    return html[html.lower().index("<body"):]


def _visible(fragment: str) -> str:
    without_tags = re.sub(r"<[^>]+>", " ", fragment)
    return " ".join(html_module.unescape(without_tags).split())


def _chart(html: str, chart_id: str) -> str:
    match = re.search(
        rf'<svg\b(?=[^>]*\bid=["\']{re.escape(chart_id)}["\'])[^>]*>.*?</svg>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    assert match, f"missing {chart_id}"
    return match.group(0)


def _tables(html: str) -> list[str]:
    return re.findall(r"<table\b[^>]*>.*?</table>", html, re.IGNORECASE | re.DOTALL)


def _rows(table: str) -> list[str]:
    return re.findall(r"<tr\b[^>]*>.*?</tr>", table, re.IGNORECASE | re.DOTALL)


def _row_containing(tables: list[str], needle: str) -> str:
    for table in tables:
        for row in _rows(table):
            if needle in _visible(row):
                return row
    raise AssertionError(f"no HTML table row contains {needle!r}")


def _assert_count(text: str, label: str, count: int) -> None:
    assert re.search(
        rf"(?:\b{re.escape(label)}\b\D{{0,30}}\b{count}\b|"
        rf"\b{count}\b\D{{0,30}}\b{re.escape(label)}\b)",
        text,
        re.IGNORECASE,
    ), f"no glanceable {label} count of {count}"


def test_executive_strip_leads_with_result_gate_and_finding_counts(
    executive_report: tuple[dict, list],
) -> None:
    report, records = executive_report
    html = render_html(report, records)
    body = _body(html)
    first_chart = min(body.index(chart_id) for chart_id in CHARTS)
    strip = _visible(body[:first_chart])

    score = report["score"]
    assert str(score["maintainability_estimate"]) in strip
    assert score["verified_grade"] in strip
    assert "gate" in strip.lower()
    assert any(term in strip.lower() for term in ("not clear", "failed", "failure"))

    counts = Counter(SEVERITY_BY_RISK[item["risk"]] for item in report["work_order"])
    counts["Severe"] += len(report["hard_gate_failures"])
    for label in ("Severe", "High", "Medium", "Low"):
        _assert_count(strip, label, counts[label])
    _assert_count(strip, "total findings", sum(counts.values()))
    assert any(
        term in strip.lower()
        for term in ("improving", "declining", "flat", "stable", "no history")
    )

    clear = copy.deepcopy(report)
    clear["hard_gate_failures"] = []
    clear["summary"]["hard_gate_failures"] = 0
    clear_body = _body(render_html(clear, records))
    clear_strip = _visible(clear_body[: min(clear_body.index(i) for i in CHARTS)])
    assert "gate" in clear_strip.lower() and "clear" in clear_strip.lower()


def test_html_has_severity_and_recorded_finding_metric_tables(
    executive_report: tuple[dict, list],
) -> None:
    report, records = executive_report
    html = render_html(report, records)
    tables = _tables(html)

    severity_table = next(
        (
            table for table in tables
            if all(label in _visible(table) for label in ("Severe", "High", "Medium", "Low"))
        ),
        None,
    )
    assert severity_table, "no HTML table carries the current S/H/M/L counts"
    counts = Counter(SEVERITY_BY_RISK[item["risk"]] for item in report["work_order"])
    counts["Severe"] += len(report["hard_gate_failures"])
    for label, count in counts.items():
        _assert_count(_visible(severity_table), label, count)

    history_table = next(
        (
            table for table in tables
            if all(record.recorded_at in _visible(table) for record in records)
        ),
        None,
    )
    assert history_table, "no metric table names every recorded scan"
    for record in records:
        row = _row_containing([history_table], record.recorded_at)
        assert re.search(rf"\b{len(record.fingerprints)}\b", _visible(row)), (
            f"the {record.recorded_at} row does not use len(record.fingerprints)"
        )


def test_every_finding_is_an_html_row_with_published_severity(
    executive_report: tuple[dict, list],
) -> None:
    report, records = executive_report
    markdown = render_markdown(report)
    html = render_html(report, records)
    tables = _tables(html)

    for item in report["work_order"]:
        row = _row_containing(tables, item["path"])
        assert SEVERITY_BY_RISK[item["risk"]] in _visible(row)
    for gate in report["hard_gate_failures"]:
        row = _row_containing(tables, gate)
        assert "Severe" in _visible(row)

    for finding in report["semantic_findings"]:
        path = finding["source_evidence"]["path"]
        assert path in markdown, f"Markdown dropped semantic path {path}"
        assert path in html, f"HTML dropped semantic path {path}"


def test_html_does_not_dump_the_markdown_report_in_one_pre(
    executive_report: tuple[dict, list],
) -> None:
    report, records = executive_report
    html = render_html(report, records)

    for pre in re.findall(r"<pre\b[^>]*>.*?</pre>", html, re.IGNORECASE | re.DOTALL):
        dumped = _visible(pre)
        assert "Scoring standard:" not in dumped
        assert "| Metric |" not in dumped
        assert "## Work Order" not in dumped


# Split into per-property helpers (2026-08-16, Marshall's call): the
# original single test measured CCN 21 against the repo's budget of 15
# and blocked its own merge through --fail-on-gate. Every assertion is
# verbatim; only the function boundaries moved.
def _text_nodes(chart: str) -> list[tuple[str, str]]:
    return [
        (match.group(1), _visible(match.group(2)))
        for match in re.finditer(
            r"<text\b([^>]*)>(.*?)</text>", chart, re.IGNORECASE | re.DOTALL,
        )
    ]


def _assert_axis_ticks_and_space(chart_id: str, chart: str) -> None:
    labels = [text for _attrs, text in _text_nodes(chart)]
    numeric = {
        float(label)
        for label in labels
        if re.fullmatch(r"-?\d+(?:\.\d+)?", label)
    }
    assert 0.0 in numeric and 5.0 in numeric, (
        f"{chart_id} has no visible 0 and 5 ticks on its 0-5 scale"
    )

    view_box = re.search(r'\bviewBox=["\']([^"\']+)', chart, re.IGNORECASE)
    assert view_box
    height = float(view_box.group(1).split()[3])
    has_axis_label = any(
        term in label.lower()
        for label in labels
        for term in ("score", "scale", "estimate", "condition", "maturity")
    )
    assert height > 200 or has_axis_label, (
        f"{chart_id} is cramped and has no explicit y-axis label"
    )


def _assert_no_overlapping_text(chart_id: str, chart: str) -> None:
    coordinates = []
    for attrs, _text in _text_nodes(chart):
        x = re.search(r'\bx=["\']([^"\']+)', attrs)
        y = re.search(r'\by=["\']([^"\']+)', attrs)
        if x and y:
            coordinates.append((x.group(1), y.group(1)))
    duplicates = [point for point, count in Counter(coordinates).items() if count > 1]
    assert not duplicates, f"{chart_id} overlaps text nodes at {duplicates}"


def test_every_score_chart_has_ticks_space_and_nonoverlapping_labels(
    executive_report: tuple[dict, list],
) -> None:
    _report, records = executive_report
    html = render_html(_report, records)

    for chart_id in CHARTS:
        chart = _chart(html, chart_id)
        _assert_axis_ticks_and_space(chart_id, chart)
        _assert_no_overlapping_text(chart_id, chart)

    pillar_labels = " ".join(
        text for _attrs, text in _text_nodes(_chart(html, "chart-pillars"))
    )
    for pillar in sorted({name for record in records for name in record.pillars}):
        assert pillar in pillar_labels, f"pillar legend dropped {pillar}"


def _assert_legend_below_plot(html: str, records: list) -> None:
    """The multi-series legend lives below the plot, never painted over the
    lines it names (the old legend was drawn inside the plot at top-left)."""
    from maintainability_audit import _charts

    pillars = _chart(html, "chart-pillars")
    names = sorted({name for record in records for name in record.pillars})
    for attrs, text in _text_nodes(pillars):
        if text not in names:
            continue
        match = re.search(r'\by=["\']([\d.]+)', attrs)
        assert match and float(match.group(1)) > _charts._PLOT_BOTTOM, (
            f"legend entry {text!r} sits inside the plot area"
        )


def _assert_dated_x_axis(html: str) -> None:
    """Time-series charts carry dated x-axis ticks (MM-DD), so a reader can
    tell which point is which scan."""
    for chart_id in ("chart-estimate", "chart-pillars", "chart-practice"):
        labels = [text for _attrs, text in _text_nodes(_chart(html, chart_id))]
        dated = [label for label in labels if re.fullmatch(r"\d{2}-\d{2}", label)]
        assert len(dated) >= 2, f"{chart_id} has no dated x-axis ticks"


def _assert_full_ladder(html: str) -> None:
    """Every rung of the 0-5 ladder is labelled, not only 0 and 5, so a point
    at 4.1 and a point at 2.0 no longer read as the same shape."""
    for chart_id in CHARTS:
        labels = [text for _attrs, text in _text_nodes(_chart(html, chart_id))]
        rungs = {float(label) for label in labels if re.fullmatch(r"\d+", label)}
        assert {0.0, 1.0, 2.0, 3.0, 4.0, 5.0} <= rungs, (
            f"{chart_id} labels only {sorted(rungs)}, not the full 0-5 ladder"
        )


def test_charts_are_readable_legend_clear_dated_and_laddered(
    executive_report: tuple[dict, list],
) -> None:
    """The three defects the bighound UAT named, encoded so they cannot come
    back: legend clear of the plot, a dated x-axis, and the full 0-5 ladder.
    """
    _report, records = executive_report
    html = render_html(_report, records)
    _assert_legend_below_plot(html, records)
    _assert_dated_x_axis(html)
    _assert_full_ladder(html)

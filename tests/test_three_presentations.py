"""8.3–8.6: three skins of one report, and the ways they may not differ.

ADR 011 option A — three independent builders — was rejected because two
scores is the class of bug this repository already paid for (P4). What
shipped instead has to be provably option C: one report dictionary, three
renderers, none of which computes anything.

The HTML file gets the strictest treatment because it is the one skin
aimed at somebody who will never open the JSON: an executive summary
first, deterministic SVG charts drawn only from stored records, and not
one byte fetched from anywhere at view time.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest
from test_history_schema2 import SCHEMA_1_LINE, _repo

from maintainability_audit._scan_history import (
    DEFAULT_HISTORY_PATH,
    read_history,
)
from maintainability_audit.cli import main
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_html, render_markdown
from maintainability_audit.report import build_report


@pytest.fixture
def audited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, dict, list]:
    """A repo with two recorded scans, so every chart has a series."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    out = tmp_path / "out.md"
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    records = read_history(root / DEFAULT_HISTORY_PATH)
    report = build_report(root, load_config(None))
    return root, report, records


def test_markdown_and_html_never_disagree_on_the_headline(audited) -> None:
    """Estimate, range, grade, finding identity: one answer, two skins."""
    _root, report, records = audited
    markdown = render_markdown(report)
    html = render_html(report, records)

    score = report["score"]
    estimate = str(score["maintainability_estimate"])
    low, high = score["maintainability_range"]
    grade = score["verified_grade"]

    for skin, text in (("markdown", markdown), ("html", html)):
        assert estimate in text, f"{skin} does not carry the estimate {estimate}"
        assert str(low) in text and str(high) in text, f"{skin} dropped the range"
        assert grade in text, f"{skin} dropped the grade"

    for item in report["work_order"]:
        fingerprint = item.get("fingerprint")
        if not fingerprint:
            continue
        assert (fingerprint in markdown) == (fingerprint in html), (
            f"the two skins disagree about finding {fingerprint}"
        )


def test_presentation_does_not_score(audited) -> None:
    """The HTML renderer reads the dict; it never imports the scorer."""
    import maintainability_audit._html_view as html_view

    source = Path(html_view.__file__).read_text(encoding="utf-8")
    forbidden = ("scoring", "_aspects", "_pressures", "_formula", "_calibration",
                 "_second_source", "score_report", "score_evidence")
    hits = [name for name in forbidden if name in source]
    assert not hits, f"the HTML renderer can reach the scorer: {hits}"


def test_html_is_one_self_contained_file(audited) -> None:
    """Inline CSS, inline SVG, and no resource loaded over the network."""
    _root, report, records = audited
    html = render_html(report, records)

    assert "<style" in html, "no inlined CSS"
    assert "<svg" in html, "no inline SVG charts"
    assert "<script" not in html.lower(), "a script tag has no place in this file"
    assert "<link" not in html.lower(), "an external stylesheet is a network load"
    assert not re.search(r"""(?:src|href)\s*=\s*["']https?://""", html, re.I), (
        "an http(s) resource load breaks P1: the file must open identically offline"
    )
    assert not re.search(r"url\(\s*['\"]?https?://", html, re.I)


def test_html_is_deterministic(audited) -> None:
    """Same report, same records — byte-identical output, twice."""
    _root, report, records = audited
    assert render_html(report, records) == render_html(report, records)


def test_the_executive_summary_leads(audited) -> None:
    """Estimate, grade, range and series direction before anything else."""
    _root, report, records = audited
    html = render_html(report, records)
    body = html[html.lower().index("<body"):]
    first_chunk = body[:1600]

    score = report["score"]
    assert str(score["maintainability_estimate"]) in first_chunk, (
        "the estimate is not in the opening summary"
    )
    assert score["verified_grade"] in first_chunk
    lowered = first_chunk.lower()
    assert any(word in lowered for word in
               ("improving", "declining", "flat", "stable", "no history")), (
        "the summary names no series direction and no empty state"
    )


def test_the_four_required_charts_render_with_history(audited) -> None:
    _root, report, records = audited
    html = render_html(report, records)

    for chart in ("chart-estimate", "chart-pillars", "chart-practice", "chart-categories"):
        assert chart in html, f"required chart {chart} is missing"


def test_schema_one_records_are_gaps_on_pillar_and_practice_charts(audited) -> None:
    """The rollup series may use them; the new series may not invent them."""
    _root, report, records = audited
    schema1 = read_history(_write_schema1_beside(records))
    mixed = schema1 + records

    html = render_html(report, mixed)

    estimate_chart = _chart(html, "chart-estimate")
    pillar_chart = _chart(html, "chart-pillars")
    practice_chart = _chart(html, "chart-practice")

    assert _point_count(estimate_chart) >= len(mixed), (
        "a schema-1 scan carries an estimate and belongs on the rollup series"
    )
    assert _point_count(pillar_chart) < len(mixed) * _pillar_count(records), (
        "the pillar chart has as many points as if schema-1 scans carried "
        "pillars; a missing series must be a gap, never interpolated"
    )
    assert _point_count(practice_chart) < len(mixed), (
        "the practice chart plotted a scan that stored no practice level"
    )


def test_empty_history_is_an_empty_state(audited) -> None:
    _root, report, _records = audited
    html = render_html(report, [])

    assert "no history" in html.lower(), "empty history is not named"
    assert "<polyline" not in _chart(html, "chart-estimate"), (
        "a series was fabricated from zero records"
    )


def _write_schema1_beside(records: list) -> Path:
    import tempfile

    path = Path(tempfile.mkdtemp()) / "old.jsonl"
    path.write_text(SCHEMA_1_LINE + "\n", encoding="utf-8")
    return path


def _chart(html: str, chart_id: str) -> str:
    start = html.index(chart_id)
    end = html.index("</svg>", start) if "</svg>" in html[start:] else len(html)
    return html[start:end]


def _point_count(chart: str) -> int:
    return chart.count("<circle")


def _pillar_count(records: list) -> int:
    return max((len(r.pillars) for r in records), default=0) or 1

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
from maintainability_audit.renderers import (
    render_html,
    render_markdown,
    render_pr_comment,
)
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


@pytest.fixture
def semantic_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """The ADR 003 fixture attached to the same report every skin receives."""
    from test_semantic_policy import _reports_with_and_without_semantics

    _plain, report, semantic = _reports_with_and_without_semantics(
        tmp_path, monkeypatch,
    )
    assert report["semantic_findings"] == semantic["findings"]
    assert report["semantic_coverage"] == semantic["coverage"]
    return report


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


def test_a_mid_series_gap_breaks_the_line(audited) -> None:
    """A polyline across a missing scan is interpolation, and ADR 011
    invariant 6 forbids it: a missing series is omitted or named empty,
    never invented. Two points with a gap between them are two isolated
    points — no segment may join them, because the segment *is* a claim
    about the scan nobody stored."""
    from maintainability_audit._charts import line_chart, multi_line_chart

    gapped = [(0, 1.0, None, None), (2, 2.0, None, None)]
    assert line_chart("chart-practice", gapped, 0.0, 5.0).count("<polyline") == 0, (
        "a single polyline joined two points across a missing scan"
    )

    joined = [(0, 1.0, None, None), (1, 1.5, None, None), (2, 2.0, None, None)]
    assert line_chart("chart-practice", joined, 0.0, 5.0).count("<polyline") == 1

    runs = [(0, 1.0, None, None), (1, 1.5, None, None), (3, 2.0, None, None), (4, 2.5, None, None)]
    assert line_chart("chart-practice", runs, 0.0, 5.0).count("<polyline") == 2, (
        "two consecutive runs around a gap must be two separate segments"
    )

    multi = {"readability": gapped}
    assert multi_line_chart("chart-pillars", multi, 0.0, 5.0).count("<polyline") == 0, (
        "the pillar chart interpolates across a missing scan"
    )

    banded_gap = [(0, 1.0, 0.9, 1.1), (2, 2.0, 1.9, 2.1)]
    assert line_chart("chart-estimate", banded_gap, 0.0, 5.0).count("<polygon") == 0, (
        "the uncertainty band was shaded across a missing scan, which claims "
        "a range nobody stored"
    )


def test_both_skins_state_the_estimate_source(audited) -> None:
    """P8 on the headline: what examined this code, in both presentations.

    Markdown grew the 'Estimate source' row for the default path; an HTML
    executive summary that shows the number without its source is the
    same report disagreeing with itself about P8's answer.
    """
    _root, report, records = audited
    from maintainability_audit import _evidence_view as view

    source = view.estimate_source(report["score"])
    assert source, "the shared wording helper returned nothing"

    assert source in render_markdown(report), "markdown dropped the estimate source"
    assert source in render_html(report, records), (
        "the HTML executive summary states the estimate without its source"
    )


def test_a_withheld_estimate_reads_identically_in_both_skins(audited) -> None:
    """Item 6 pinned: one vocabulary for 'no number', via `_evidence_view`.

    'None' in one skin and 'Not scored' in the other is two reports; a
    reader comparing them concludes the tools disagree, when only the
    string formatting does.
    """
    import copy

    _root, report, records = audited
    withheld = copy.deepcopy(report)
    withheld["score"]["maintainability_estimate"] = None
    withheld["score"]["maintainability_range"] = None
    withheld["score"]["verified_grade"] = None
    withheld["score"]["evidence_status"]["status"] = "insufficient"

    markdown = render_markdown(withheld)
    html = render_html(withheld, records)

    for skin, text in (("markdown", markdown), ("html", html)):
        assert "Not scored" in text, f"{skin} does not use the shared withheld wording"
        assert ">None<" not in text and "| None |" not in text, (
            f"{skin} leaks a raw None where the withheld wording belongs"
        )


def test_json_names_which_selected_analyzers_ran_and_did_not(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P8 coverage survives JSON: selected sources are attributable by outcome.

    A tools-attempted count is not recoverable coverage. The JSON must name
    both the selected tool that ran and the selected tool that did not.
    """
    import json

    import maintainability_audit.report as report_module
    from maintainability_audit._analysis import Analysis, ToolCoverage
    from maintainability_audit._runner import Outcome

    root = _repo(tmp_path)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    monkeypatch.setattr(
        report_module,
        "analyze",
        lambda _root, _config: Analysis(
            coverage=[
                ToolCoverage(
                    slug="lizard", outcome=Outcome.RAN.value,
                    version="1.17.10", concepts=("cyclomatic_complexity",),
                ),
                ToolCoverage(
                    slug="eslint", outcome=Outcome.NOT_INSTALLED.value,
                    detail="eslint is not installed", concepts=("style",),
                ),
            ],
            concerns=("complexity", "style"),
            depth="baseline",
            license_policy="permissive-only",
        ),
    )
    output = tmp_path / "report.json"

    assert main([
        "--root", str(root), "--analyzers", "--format", "json",
        "--output", str(output),
    ]) == 0

    payload = json.loads(output.read_text(encoding="utf-8"))
    by_outcome = payload["analyzer_coverage"]["by_outcome"]
    assert [row["tool"] for row in by_outcome["ran"]] == ["lizard"]
    assert [row["tool"] for row in by_outcome["not-installed"]] == ["eslint"]


def test_every_skin_carries_the_same_semantic_findings_and_coverage(
    semantic_report: dict,
) -> None:
    """A semantic result in the agent prompt may not disappear for humans."""
    from maintainability_audit.prompts import render_ai_prompt

    report = semantic_report
    prompt = render_ai_prompt(report)
    presentations = {
        "markdown": render_markdown(report),
        "pr comment": render_pr_comment(report),
        "html": render_html(report, []),
    }

    coverage = report["semantic_coverage"]
    for finding in report["semantic_findings"]:
        path = finding["source_evidence"]["path"]
        assert path in prompt, f"the remediation prompt dropped semantic path {path}"
        for skin, rendered in presentations.items():
            assert path in rendered, (
                f"{skin} dropped semantic path {path} even though the prompt names it"
            )

    for skin, rendered in presentations.items():
        assert coverage["language"] in rendered, f"{skin} dropped semantic language"
        assert coverage["status"] in rendered.lower(), (
            f"{skin} dropped semantic coverage status {coverage['status']}"
        )


def test_unknown_semantic_coverage_is_the_same_in_every_skin(
    semantic_report: dict,
) -> None:
    """Unknown type coverage is a published state, not a clean empty list."""
    import copy

    report = copy.deepcopy(semantic_report)
    report["semantic_findings"] = []
    report["semantic_coverage"] = {
        "language": "TypeScript",
        "status": "unknown",
        "reason": "No recorded type analysis; semantic coverage is unknown.",
    }
    presentations = {
        "markdown": render_markdown(report),
        "pr comment": render_pr_comment(report),
        "html": render_html(report, []),
    }

    coverage = report["semantic_coverage"]
    for skin, rendered in presentations.items():
        assert coverage["language"] in rendered, f"{skin} dropped semantic language"
        assert coverage["status"] in rendered.lower(), (
            f"{skin} turned unknown semantic coverage into silence"
        )
        assert coverage["reason"] in rendered, (
            f"{skin} gives a different reason for unknown semantic coverage"
        )


def test_a_semantic_typescript_finding_is_not_described_as_unread(
    semantic_report: dict,
) -> None:
    """A path used as semantic evidence cannot also be called unopened."""
    import copy

    report = copy.deepcopy(semantic_report)
    assert any(
        finding["source_evidence"]["path"].endswith(".ts")
        for finding in report["semantic_findings"]
    )
    report["summary"]["unread_source"] = [
        {"suffix": ".ts", "language": "TypeScript", "files": 1},
    ]
    report["summary"]["unread_source_files"] = 1

    markdown = render_markdown(report)

    assert "| `.ts` | TypeScript |" not in markdown, (
        "markdown says TypeScript was not opened while citing a .ts semantic finding"
    )
    assert "nothing below describes them" not in markdown


def test_rendering_semantics_does_not_mutate_the_sealed_score(
    semantic_report: dict,
) -> None:
    """All skins consume the score; none gets to recompute or amend it."""
    import copy

    report = semantic_report
    before = copy.deepcopy(report["score"])

    render_markdown(report)
    render_pr_comment(report)
    render_html(report, [])

    assert report["score"] == before
    assert report["score"]["maintainability_estimate"] == before[
        "maintainability_estimate"
    ]
    assert report["score"]["verified_grade"] == before["verified_grade"]

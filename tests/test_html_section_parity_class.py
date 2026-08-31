"""Class E (Grok 63ab820, reopened 2026-08-30): HTML remaining sections.

ADR 011 decision 5: after the executive strip and charts, HTML carries
the same remaining sections Markdown prints when the report dict has
the data. The first close only named coverage and trend. A field test
then produced economics, pillars, aspect scores and an environment
work order that Markdown printed and HTML omitted — the claim was
universal and the check named two members.

The population is the remaining Markdown ``##`` headings a fully
populated report actually emits. Mutation: drop the economic block from
HTML while ``economic_impact`` is on the dict; that heading is not
hard-coded as the sole assertion.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from test_history_schema2 import _repo

from maintainability_audit._mcp_audit import attach_history_views
from maintainability_audit._scan_history import DEFAULT_HISTORY_PATH, read_history
from maintainability_audit.cli import main
from maintainability_audit.config import load_config
from maintainability_audit.renderers import render_html, render_markdown
from maintainability_audit.report import build_report

# Headings Markdown emits for the remaining catalog. Coverage and trend
# stay in this table so dropping either still fails here; they are not
# the whole population.
_REQUIRED_SECTIONS = {
    "coverage": ("## Analyzer Coverage", "<h2>Coverage</h2>"),
    "trend": ("## Trend", "<h2>Trend</h2>"),
    "economic_context": (
        "## Economic Context (scenario)",
        "<h2>Economic Context (scenario)</h2>",
    ),
    "pillars": ("## Pillars", "<h2>Pillars</h2>"),
    "iso_categories": (
        "## ISO/IEC 25010 Maintainability Score",
        "<h2>ISO/IEC 25010 Maintainability Score</h2>",
    ),
    "aspects": ("## Aspect Scores", "<h2>Aspect Scores</h2>"),
    "unscored": (
        "## Not Scored — no measurement exists",
        "<h2>Not Scored — no measurement exists</h2>",
    ),
    "environment_work_order": (
        "## Environment Work Order",
        "<h2>Environment Work Order</h2>",
    ),
    "largest_files": ("## Largest Files", "<h2>Largest Files</h2>"),
    "function_hotspots": ("## Function Hotspots", "<h2>Function Hotspots</h2>"),
}

_COVERAGE = {
    "selection": {"concerns": ["style", "structure"], "depth": "standard",
                  "license_policy": "permissive"},
    "tools_attempted": 2,
    "tools_contributed": 1,
    "sources": {"built_in": 8},
    "concepts_unexamined": [],
    "by_outcome": {
        "ran": [{"tool": "ruff", "tier": "analyzer", "version": "0.5.0",
                 "measurements": 12, "findings": 3}],
        "not-working": [{"tool": "eslint", "tier": "analyzer", "version": None,
                         "measurements": "—", "findings": "—",
                         "detail": "not installed"}],
    },
}

_ECONOMIC = {
    "version": 1,
    "low": 900.0,
    "base": 1400.0,
    "high": 2100.0,
    "currency": "USD",
    "planning_horizon_months": 12,
    "work_order_items": 2,
    "assumptions": [
        "loaded labor rate 90-210 USD/hour (base 140), as configured",
        "a scenario computed from these assumptions; change them and the "
        "range moves with them",
    ],
}

_ENVIRONMENT = [
    {
        "tool": "jscpd",
        "reason": "not-installed",
        "install": "npm install --global jscpd",
        "verify": "jscpd --version",
        "concepts": ["duplication"],
    }
]


@pytest.fixture
def audited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, list]:
    """A repo scanned twice, with every remaining-section field populated."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    out = tmp_path / "out.md"
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    records = read_history(root / DEFAULT_HISTORY_PATH)
    report = build_report(root, load_config(None))
    attach_history_views(report, root / DEFAULT_HISTORY_PATH, root)
    report["analyzer_coverage"] = _COVERAGE
    report["economic_impact"] = _ECONOMIC
    report["environment_work_order"] = _ENVIRONMENT
    practice = dict(report.get("practice") or {})
    practice.setdefault("level", 3)
    practice.setdefault("summary", "CI runs quality checks on every change")
    practice["caps"] = [
        "no coverage or complexity gate found; a check that cannot fail is advisory"
    ]
    practice.setdefault("signals", [{"signal": "lint-in-ci", "evidence": "ci.yml"}])
    report["practice"] = practice
    if not report.get("function_hotspots"):
        report["function_hotspots"] = [{
            "path": "app.py",
            "name": "big",
            "start_line": 1,
            "lines": 90,
            "complexity": 20,
            "cognitive": 12,
            "status": "fail",
        }]
    if not report.get("largest_files"):
        report["largest_files"] = [
            {"path": "app.py", "lines": 90, "status": "fail"},
        ]
    return report, records


def test_the_required_section_population_is_derived_and_not_empty() -> None:
    names = set(_REQUIRED_SECTIONS)
    assert {"coverage", "trend"} <= names
    assert {"economic_context", "pillars", "unscored",
            "environment_work_order"} <= names
    assert len(_REQUIRED_SECTIONS) >= 8
    assert len({pair[0] for pair in _REQUIRED_SECTIONS.values()}) == len(
        _REQUIRED_SECTIONS
    )


def test_the_fixture_actually_populates_the_fields(audited) -> None:
    report, _records = audited
    assert report.get("analyzer_coverage"), "fixture produced no analyzer_coverage"
    assert report.get("scan_history"), "fixture produced no scan_history"
    assert report.get("economic_impact"), "fixture produced no economic_impact"
    assert report.get("environment_work_order"), "fixture produced no environment WO"
    assert (report.get("practice") or {}).get("caps"), "fixture produced no practice caps"
    assert (report.get("score") or {}).get("aspects"), "fixture produced no aspects"
    assert (report.get("score") or {}).get("categories"), "fixture produced no categories"
    assert ((report.get("score") or {}).get("rubric") or {}).get("unscored")
    assert report.get("largest_files")
    assert report.get("function_hotspots")


@pytest.mark.parametrize("section", sorted(_REQUIRED_SECTIONS))
def test_a_required_section_appears_in_both_skins(section: str, audited) -> None:
    report, records = audited
    md_marker, html_marker = _REQUIRED_SECTIONS[section]
    markdown = render_markdown(report)
    html = render_html(report, records)
    assert md_marker in markdown, f"markdown dropped {section} ({md_marker!r})"
    assert html_marker in html, (
        f"the HTML skin is missing the {section} section ({html_marker!r}) "
        "that ADR 011 decision 5 requires to match Markdown"
    )


def test_every_catalogued_heading_markdown_emits_has_an_html_h2(audited) -> None:
    """Population is the catalog; HTML must carry each heading Markdown prints.

    *Mutation:* omit ``<h2>Economic Context (scenario)</h2>`` from the
    HTML skin while the report still carries ``economic_impact``. That
    heading is one member of ``_REQUIRED_SECTIONS``, not a one-off
    assert, so dropping pillars or the environment work order fails the
    same way.
    """
    report, records = audited
    markdown = render_markdown(report)
    html = render_html(report, records)
    md_headings = {
        line[3:].strip()
        for line in markdown.splitlines()
        if line.startswith("## ")
    }
    for name, (md_marker, html_marker) in _REQUIRED_SECTIONS.items():
        heading = md_marker[3:].strip()
        assert heading in md_headings, f"fixture markdown lost {name}"
        assert html_marker in html, f"HTML lost {name} ({html_marker!r})"


def test_practice_caps_and_the_scenario_disclaimer_reach_html(audited) -> None:
    report, records = audited
    html = render_html(report, records)
    markdown = render_markdown(report)
    assert "Held at level" in markdown
    assert "Held at level" in html
    assert "not a prediction" in html.lower()
    assert "jscpd" in html
    assert "the agent never installs" in html.lower()


def test_absent_economics_omits_the_section_on_both_skins(audited) -> None:
    report, records = audited
    report = dict(report)
    report.pop("economic_impact", None)
    markdown = render_markdown(report)
    html = render_html(report, records)
    assert "## Economic Context (scenario)" not in markdown
    assert "<h2>Economic Context (scenario)</h2>" not in html

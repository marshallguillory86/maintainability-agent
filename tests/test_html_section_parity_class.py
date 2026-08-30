"""Class E (Grok 63ab820): the HTML skin carries the same required
sections as the Markdown skin.

ADR 011 decision 5: the HTML file leads with an executive summary and the
required charts, then the "same remaining sections as Markdown: coverage,
trend text, work order / prompt, findings." Two of those -- **coverage**
(``analyzer_coverage``) and the **per-segment trend** (``scan_history``) --
were absent from the HTML skin alone: a reader who opened the HTML report
saw a score with nothing about what produced it, and only the executive
strip's one-line direction where the Markdown carried the whole trend.

The population is the ADR-named required sections, each a
``(markdown-marker, html-marker)`` pair driven through the two real
renderers over one populated report -- not a single section checked by
hand. Unnamed member: **coverage** and **trend** are the two the earlier
skins already agreed on nowhere, but the table also carries work order and
findings, so dropping any required section from HTML fails here.
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

# The two "remaining sections" of ADR 011 decision 5 that the HTML skin
# was missing, as the heading the Markdown skin emits and the heading the
# HTML skin must emit for it. Both are driven from one report that carries
# the data; a section with no data is correctly omitted by both skins and
# is not the hole.
_REQUIRED_SECTIONS = {
    "coverage": ("## Analyzer Coverage", "<h2>Coverage</h2>"),
    "trend": ("## Trend", "<h2>Trend</h2>"),
}

# A representative analyzer_coverage, the shape build_report stores when the
# pool runs -- the test repo has no analyzers installed, so it is injected
# to test the *renderers*, which is where the section was missing.
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


@pytest.fixture
def audited(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict, list]:
    """A repo scanned twice (a trend series), with coverage injected."""
    monkeypatch.setattr(sys.stdin, "isatty", lambda: False, raising=False)
    root = _repo(tmp_path)
    out = tmp_path / "out.md"
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    assert main(["--root", str(root), "--record-history", "--output", str(out)]) == 0
    records = read_history(root / DEFAULT_HISTORY_PATH)
    report = build_report(root, load_config(None))
    # The per-segment trend the CLI attaches from the history file; without
    # it `scan_history` is empty and both skins correctly omit the section.
    attach_history_views(report, root / DEFAULT_HISTORY_PATH, root)
    report["analyzer_coverage"] = _COVERAGE
    return report, records


def test_the_required_section_population_is_derived_and_not_empty() -> None:
    assert {"coverage", "trend"} <= set(_REQUIRED_SECTIONS)
    assert len(_REQUIRED_SECTIONS) >= 2


def test_the_fixture_actually_populates_the_fields(audited) -> None:
    """Not vacuous: the report really carries coverage and a trend series,
    so a skin that omits them is failing on present data, not absent."""
    report, _records = audited
    assert report.get("analyzer_coverage"), "fixture produced no analyzer_coverage"
    assert report.get("scan_history"), "fixture produced no scan_history"


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

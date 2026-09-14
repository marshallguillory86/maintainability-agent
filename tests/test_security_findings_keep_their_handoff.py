"""What secure-code-agent found reaches the reader, with its own work order (D179).

From Grok's audit of 3.7.3 (`7befdbd`) run on this repository: secure-code-agent
recorded five critical findings and one high, and every skin printed
"unverified: not graded — scanner coverage is partial" with no count. Its
remediation prompt was written into a temporary directory and deleted with
it, so a reader was told neither how much security work there was nor how
the tool that found it said to do it.

Two claims:

* **Wherever the pillar is read, the producer's severity counts are there**
  — chat view, complete Markdown, HTML and the remediation prompt, for a
  graded pillar in every posture and for an ungraded one.
* **The work order the delegate wrote survives the run** — carried in the
  report, printed whole in the complete skins, and returned at the chat
  door's top level whatever format was asked for.

Postures come from `POSTURE_NOTE`; severities from a real run where one is
needed, and include a name outside the known five so a renderer keyed on a
fixed list is caught.
"""
from __future__ import annotations

import html
import subprocess
from pathlib import Path
from typing import Any

import pytest

COUNTS = {"critical": 5, "high": 1, "low": 69, "unrated": 3}


def _repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / "src").mkdir(parents=True)
    (repo / "src" / "app.py").write_text("def run(value):\n    return value + 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init", "-q"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    return repo


def _document(**overrides: Any) -> dict[str, Any]:
    payload = {
        "schema": "secure-code-agent/security-pillar", "schema_version": 2,
        "pillar": "security", "generated": "2026-09-14T00:00:00Z",
        "producer": {"tool": "secure-code-agent", "version": "0.12.1"},
        "reason": "secure-code-agent owns the security pillar",
        "practice": {"level": 5, "summary": "discipline", "signals": [], "caps": []},
        "condition": 4.0, "condition_letter": "B", "posture": "healthy",
        "verified_grade": "B", "evidence_status": "complete", "evidence_reasons": [],
        "coverage": {"status": "complete", "scanners_run": ["gitleaks"], "scanners_missing": []},
        "findings_by_severity": dict(COUNTS), "reported_not_scored": {}, "loc_scanned": 1000,
    }
    payload.update(overrides)
    return payload


def _states() -> dict[str, dict[str, Any]]:
    from maintainability_audit._scan_view import POSTURE_NOTE

    assert POSTURE_NOTE, "no postures to check"
    states = {posture: _document(posture=posture) for posture in POSTURE_NOTE}
    states["ungraded"] = _document(
        condition=None, condition_letter=None, posture="unverified", verified_grade=None,
        evidence_status="incomplete", evidence_reasons=["scanner coverage is partial"])
    return states


def _report_with(tmp_path: Path, monkeypatch, document: dict[str, Any] | None,
                 work_order: str | None = None, reason: str | None = None) -> dict[str, Any]:
    from maintainability_audit import report as report_module
    from maintainability_audit._security_delegate import DelegateRun
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    monkeypatch.setattr(report_module, "run_security_delegate",
                        lambda *a, **k: DelegateRun(document, reason, work_order=work_order))
    return build_report(_repo(tmp_path), load_config(None), run_analyzers=False)


@pytest.mark.parametrize("state", sorted(_states()))
def test_every_skin_shows_what_the_pillar_counted(tmp_path, monkeypatch, state) -> None:
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_html, render_markdown

    report = _report_with(tmp_path, monkeypatch, _states()[state])
    skins = {
        "chat": render_markdown(report, complete=False),
        "markdown": render_markdown(report, complete=True),
        "html": html.unescape(render_html(report, [])),
        "prompt": render_ai_prompt(report),
    }
    missing = {
        skin: [f"{count} {name}" for name, count in COUNTS.items() if f"{count} {name}" not in text]
        for skin, text in skins.items()
    }
    assert not any(missing.values()), f"a {state} security pillar's counts are missing: {missing}"


def test_a_pillar_that_found_nothing_says_so_and_one_without_counts_says_nothing() -> None:
    """An empty count is the producer's statement; an absent one is not a statement."""
    from maintainability_audit._scan_view import pillar_cells

    _, empty = pillar_cells(_document(findings_by_severity={"critical": 0}))
    assert "no findings" in empty, empty
    without = _document()
    del without["findings_by_severity"]
    _, silent = pillar_cells(without)
    assert "findings" not in silent, f"a pillar with no count was given one: {silent}"


def test_the_work_order_the_delegate_wrote_survives_the_run(tmp_path, real_security_delegate) -> None:
    """The real child: its work order is read back before its directory is deleted."""
    from maintainability_audit._security_work_order import KEY
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    report = build_report(_repo(tmp_path), load_config(None), run_analyzers=False)
    security = next(entry for entry in report["pillars"] if entry["pillar"] == "security")
    assert security.get("delegated_to") == "secure-code-agent", security
    carried = report.get(KEY)
    assert carried and carried["markdown"].strip(), f"the delegate's work order was not kept: {carried}"
    assert carried["producer_version"] == security["producer_version"], carried


def test_the_work_order_reaches_every_skin_and_the_chat_door(tmp_path, monkeypatch) -> None:
    from maintainability_audit._mcp_audit import _top_level_result
    from maintainability_audit._security_work_order import KEY
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_html, render_markdown

    written = ("# Security work order\n\n**3 to fix.**\n\n```python\n# a quoted comment\n```\n\n"
               "### 1. `gitleaks.rule` — Hardcoded secret\n")
    report = _report_with(tmp_path, monkeypatch, _document(), work_order=written)

    complete = render_markdown(report, complete=True)
    lines = set(complete.splitlines())
    assert "**3 to fix.**" in lines and "##### 1. `gitleaks.rule` — Hardcoded secret" in lines, (
        "the complete report does not carry the work order, or its headings were not nested")
    assert "# a quoted comment" in lines, "a comment inside a quoted snippet was rewritten as a heading"
    assert "**3 to fix.**" in html.unescape(render_html(report, []))
    assert KEY in render_markdown(report, complete=False), "the chat view does not say where it is"
    assert KEY in render_ai_prompt(report), "the prompt does not say where it is"
    result = _top_level_result(report, tmp_path, "", False, None, True)
    assert result.get(KEY, {}).get("markdown") == written, "the chat door does not return it"


def test_a_work_order_without_a_trusted_document_is_not_carried(tmp_path, monkeypatch) -> None:
    """A prompt from a run whose pillar could not be trusted is not evidence either."""
    from maintainability_audit._security_work_order import KEY

    report = _report_with(tmp_path, monkeypatch, None, work_order="# Security work order\n",
                          reason="secure-code-agent exited 2 without a pillar document")
    assert KEY not in report, report.get(KEY)

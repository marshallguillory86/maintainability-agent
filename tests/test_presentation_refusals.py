"""One refusal, three skins — ADR 011 with D15's path identification.

Split from test_three_presentations.py when that file crossed the
repository's own size limit. The property is the same one ADR 011
states: three presentations of one report dict, so a fact visible in
JSON and Markdown cannot be quietly missing from HTML.
"""

from __future__ import annotations

from pathlib import Path

import pytest

_AMBIGUOUS_PACKAGE_PATH = "com/foo/Bar.java"


def _ambiguous_java_tree(root: Path) -> Path:
    """Two files ending com/foo/Bar.java, plus bytecode to read."""
    import subprocess

    source = "package com.foo;\npublic class Bar { int x; }\n"
    for relative in ("src/main/java/com/foo/Bar.java", "src/test/java/com/foo/Bar.java"):
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    classes = root / "target" / "classes" / "com" / "foo"
    classes.mkdir(parents=True)
    (classes / "Bar.class").write_bytes(b"\xca\xfe\xba\xbe dummy")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _spotbugs_only_report(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    """One SpotBugs finding located by a package-relative sourcepath."""
    from maintainability_audit import _runner
    from maintainability_audit._catalog import load_catalog
    from maintainability_audit._runner import Outcome, ToolResult
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    payload = (
        '<?xml version="1.0"?>\n<BugCollection version="4.8.6">\n'
        '<BugInstance type="NP_NULL_ON_SOME_PATH" category="CORRECTNESS">\n'
        "  <ShortMessage>Possible null pointer dereference</ShortMessage>\n"
        f'  <SourceLine sourcepath="{_AMBIGUOUS_PACKAGE_PATH}" start="2" end="2"/>\n'
        "</BugInstance>\n</BugCollection>\n"
    )
    monkeypatch.setattr(
        _runner, "_probe",
        lambda slug, argv: ToolResult(
            slug=slug, outcome=Outcome.RAN, version="spotbugs 4.8.6", exit_code=0,
        ),
    )
    monkeypatch.setattr(
        "maintainability_audit._analysis.run",
        lambda slug, invocation, timeout_seconds=120: ToolResult(
            slug=slug, outcome=Outcome.RAN, stdout=payload, exit_code=0,
        ),
    )
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": "copyleft-weak",
        "allow_tools": ["spotbugs"],
        "deny_tools": sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] != "spotbugs"
        ),
    })
    return build_report(root, config, run_analyzers=True)


def test_a_refused_path_identification_appears_in_all_three_presentations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """ADR 011 / D15: one report dict, three skins, one refusal.

    The refusal was visible in JSON and Markdown while HTML omitted it
    (Codex round three): a reader of the page would chase a path that
    does not exist with nothing saying the identification was refused.
    """
    from maintainability_audit.renderers import render_html, render_markdown

    report = _spotbugs_only_report(
        _ambiguous_java_tree(tmp_path / "ambiguous"), monkeypatch,
    )

    assert _AMBIGUOUS_PACKAGE_PATH in report["unidentified_source_paths"], "JSON"
    markdown = render_markdown(report)
    assert "Unidentified source paths" in markdown
    assert _AMBIGUOUS_PACKAGE_PATH in markdown
    html = render_html(report, [])
    assert "Unidentified source paths" in html and _AMBIGUOUS_PACKAGE_PATH in html, (
        "the HTML skin omits a refusal the other two state"
    )

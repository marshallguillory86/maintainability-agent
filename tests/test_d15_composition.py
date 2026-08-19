"""D15: one report composes source-read and artifact-read adapters honestly.

Cycle: Grok audit on 48293d3, queue closed at cc71cd1. The six tripwires
from that audit are the pins. Selection still filters by policy; composition
must not manufacture agreement, must not miss the same file spelled two
ways, must not hide staleness, and must not gate bytecode behind a source
language inventory.
"""

from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit import _runner
from maintainability_audit._analysis import analyze
from maintainability_audit._catalog import load_catalog
from maintainability_audit._runner import Outcome, ToolResult
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

REGISTER = Path(__file__).resolve().parents[1] / "docs" / "defect-register-chat-surface.md"
ADR_012 = Path(__file__).resolve().parents[1] / "docs" / "adr-012-spotbugs-build-boundary.md"
ARCHITECTURE = Path(__file__).resolve().parents[1] / "docs" / "architecture.md"
POOL_DOC = Path(__file__).resolve().parents[1] / "docs" / "analyzer-pool.md"
HELP_POOL = Path(__file__).resolve().parents[1] / "docs" / "help" / "analyzer-pool.md"
DECISIONS = Path(__file__).resolve().parents[1] / "docs" / "decisions.md"

JAVA_SOURCE = (
    "package com.foo;\n"
    "public class Bar {\n"
    "    public int tangled(Object value) {\n"
    "        return value.hashCode();\n"
    "    }\n"
    "}\n"
)
REPO_PATH = "src/main/java/com/foo/Bar.java"
PACKAGE_PATH = "com/foo/Bar.java"


def _repo(root: Path, files: dict[str, str | bytes]) -> Path:
    root.mkdir(parents=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(body, bytes):
            path.write_bytes(body)
        else:
            path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _java_tree(root: Path, *, extra: dict[str, str | bytes] | None = None) -> Path:
    files: dict[str, str | bytes] = {
        REPO_PATH: JAVA_SOURCE,
        "target/classes/com/foo/Bar.class": b"\xca\xfe\xba\xbe dummy",
    }
    if extra:
        files.update(extra)
    return _repo(root, files)


def _jvm_config(**analyzers: Any) -> dict[str, Any]:
    wanted = {"pmd", "checkstyle", "spotbugs"}
    config = load_config(None)
    config["analyzers"].update({
        "run": True,
        "depth": "moderate",
        "license_policy": "copyleft-weak",
        "allow_tools": sorted(wanted),
        "deny_tools": sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] not in wanted
        ),
        **analyzers,
    })
    return config


def _row(report: dict[str, Any], slug: str) -> tuple[str, dict[str, Any]]:
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            if row["tool"] == slug:
                return outcome, row
    raise AssertionError(f"{slug} absent from coverage")


def _pmd_sarif() -> str:
    return (
        '{"version":"2.1.0","runs":[{"tool":{"driver":{"name":"PMD"}},'
        '"results":[{"ruleId":"CognitiveComplexity",'
        '"message":{"text":"cognitive complexity of 3"},'
        '"locations":[{"physicalLocation":{'
        '"artifactLocation":{"uri":"' + REPO_PATH + '"},'
        '"region":{"startLine":3}}}]}]}]}'
    )


def _checkstyle_xml() -> str:
    return (
        '<?xml version="1.0"?>\n<checkstyle version="10">\n'
        f'<file name="{REPO_PATH}">\n'
        '<error line="2" severity="warning" message="Name Bar must match."'
        ' source="com.puppycrawl.tools.checkstyle.checks.naming.TypeNameCheck"/>\n'
        "</file>\n</checkstyle>\n"
    )


def _spotbugs_xml(sourcepath: str = PACKAGE_PATH, category: str = "CORRECTNESS") -> str:
    return (
        '<?xml version="1.0"?>\n<BugCollection version="4.8.6">\n'
        f'<BugInstance type="NP_NULL_ON_SOME_PATH" category="{category}" priority="2">\n'
        "  <ShortMessage>Possible null pointer dereference</ShortMessage>\n"
        f'  <SourceLine sourcefile="Bar.java" sourcepath="{sourcepath}" start="3" end="3"/>\n'
        "</BugInstance>\n</BugCollection>\n"
    )


def _force_jvm_ran(monkeypatch: pytest.MonkeyPatch, *, spotbugs_xml: str | None = None) -> None:
    payloads = {
        "pmd": _pmd_sarif(),
        "checkstyle": _checkstyle_xml(),
        "spotbugs": spotbugs_xml or _spotbugs_xml(),
    }
    monkeypatch.setattr(
        _runner, "_probe",
        lambda slug, argv: ToolResult(
            slug=slug, outcome=Outcome.RAN, version=f"{slug} 1.0.0", exit_code=0,
        ),
    )
    monkeypatch.setattr(
        "maintainability_audit._analysis.run",
        lambda slug, invocation, timeout_seconds=120: ToolResult(
            slug=slug, outcome=Outcome.RAN, stdout=payloads[slug], exit_code=0,
        ),
    )


def test_one_report_composes_source_read_and_artifact_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin 1: PMD + Checkstyle + SpotBugs in one coverage record, each with languages."""
    root = _java_tree(tmp_path / "compose")
    _force_jvm_ran(monkeypatch)
    report = build_report(root, _jvm_config(), run_analyzers=True)

    by_tool = {}
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            by_tool[row["tool"]] = (outcome, row)

    for slug in ("pmd", "checkstyle", "spotbugs"):
        outcome, row = by_tool[slug]
        assert outcome == "ran", f"{slug} did not contribute: {outcome}"
        assert row["languages"] == ["java"]
        assert row.get("version"), f"{slug} coverage row has no version"
    _outcome, spotbugs = by_tool["spotbugs"]
    assert "stale" in spotbugs
    assert "source_mtime" in spotbugs and "class_mtime" in spotbugs


def test_style_concept_is_not_finding_identity(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin 2: CORRECTNESS-as-style and TypeName-as-style are two findings, not one agreement."""
    from maintainability_audit._corroborate import finding_identity
    from maintainability_audit._metrics_types import Finding

    convention = Finding(
        concept="style", path=REPO_PATH, line=2, message="Name Bar",
        tool="checkstyle", rule="TypeNameCheck",
    )
    bug = Finding(
        concept="style", path=REPO_PATH, line=3, message="null deref",
        tool="spotbugs", rule="NP_NULL_ON_SOME_PATH",
    )
    assert finding_identity(convention) != finding_identity(bug), (
        "concept style alone made a bug and a naming convention the same finding"
    )

    root = _java_tree(tmp_path / "identity")
    _force_jvm_ran(monkeypatch)
    report = build_report(root, _jvm_config(), run_analyzers=True)
    pair = [
        item for item in report["analyzer_findings"]
        if item["tool"] in {"checkstyle", "spotbugs"}
    ]
    assert {item["tool"] for item in pair} == {"checkstyle", "spotbugs"}
    assert {item["concept"] for item in pair} == {"style"}
    style = report.get("analyzer_measurements", {}).get("style") or {}
    if style.get("corroborated_units"):
        tools = set(style.get("tools") or [])
        assert not {"checkstyle", "spotbugs"} <= tools, (
            "two verdict emitters were counted as corroborating style"
        )


def test_package_sourcepath_and_repo_path_are_identified_or_refused(
    tmp_path: Path,
) -> None:
    """Pin 3: same file, two spellings — normalize or refuse, never a silent miss."""
    from maintainability_audit._corroborate import normalize_source_path

    root = _java_tree(tmp_path / "paths")
    located = normalize_source_path(root, PACKAGE_PATH)
    assert located == REPO_PATH, (
        f"package-relative {PACKAGE_PATH!r} and repo-relative {REPO_PATH!r} "
        f"were not identified (got {located!r}); a silent both-ways miss"
    )


def test_stale_artifact_evidence_is_stated_on_the_composed_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Pin 4 / P8: a stale SpotBugs row is visible on the composed coverage, not only privately."""
    root = _java_tree(tmp_path / "stale")
    now = time.time()
    os.utime(root / "target" / "classes" / "com" / "foo" / "Bar.class", (now - 120, now - 120))
    os.utime(root / REPO_PATH, (now, now))
    _force_jvm_ran(monkeypatch)

    report = build_report(root, _jvm_config(), run_analyzers=True)
    _outcome, row = _row(report, "spotbugs")
    assert row["stale"] is True
    coverage = report["analyzer_coverage"]
    assert coverage.get("stale_artifact_evidence") is True, (
        "composed coverage hid SpotBugs staleness"
    )


def test_bytecode_with_mixed_languages_still_reaches_spotbugs_has_targets(
    tmp_path: Path,
) -> None:
    """Pin 5: artifact-read is not gated away by a source-language inventory."""
    adapter = adapter_for("spotbugs")
    assert adapter is not None
    root = _repo(tmp_path / "mixed", {
        "app.js": "const x = 1;\n",
        "target/classes/com/foo/Bar.class": b"\xca\xfe\xba\xbe dummy",
    })
    assert adapter.has_targets(root) is True

    report = build_report(root, _jvm_config(), run_analyzers=True)
    outcome, row = _row(report, "spotbugs")
    assert "this tree is" not in (row.get("detail") or ""), (
        "source-language inventory dropped an artifact-read tool that had .class files"
    )
    assert outcome in {"ran", "not-installed", "not-working", "failed"}


def test_sequential_analyze_calls_do_not_leak_class_dirs(tmp_path: Path) -> None:
    """Pin 6: different class_dirs in one process stay isolated."""
    adapter = adapter_for("spotbugs")
    assert adapter is not None
    first = _repo(tmp_path / "one", {
        REPO_PATH: JAVA_SOURCE,
        "out/classes/com/foo/Bar.class": b"\xca\xfe\xba\xbe dummy",
    })
    second = _repo(tmp_path / "two", {
        REPO_PATH: JAVA_SOURCE,
        "target/classes/com/foo/Bar.class": b"\xca\xfe\xba\xbe dummy",
    })
    analyze(first, _jvm_config(class_dirs=["out/classes"]))
    analyze(second, _jvm_config(class_dirs=[]))
    assert tuple(adapter.class_dirs) == ()
    assert adapter.has_targets(second) is True
    assert adapter.has_targets(first) is False


def test_d15_is_closed_past_tense_behind_this_file() -> None:
    """Pin 7: the register's last open entry closes here; docs stop promising later."""
    register = REGISTER.read_text(encoding="utf-8")
    heading = next(
        line for line in register.splitlines() if line.startswith("### D15")
    )
    assert "Closed" in heading
    assert "test_d15_composition" in register
    disposition = register.split("## Disposition", maxsplit=1)[1].lower()
    assert "only d15 remains open" not in disposition
    assert "seventeen" in disposition and "closed" in disposition

    adr = ADR_012.read_text(encoding="utf-8")
    assert "still to be written" not in adr
    assert "test_d15_composition" in adr or "covers both shapes" in adr

    architecture = ARCHITECTURE.read_text(encoding="utf-8")
    assert "Only D15 remains open" not in architecture

    help_pool = HELP_POOL.read_text(encoding="utf-8")
    assert "That remaining limitation is D15" not in help_pool

    pool = POOL_DOC.read_text(encoding="utf-8")
    assert "composition test is still to be written" not in pool

    row = next(line for line in DECISIONS.read_text(encoding="utf-8").splitlines()
               if line.startswith("| [012]"))
    assert "d15" not in row.lower() or "open" not in row.lower()

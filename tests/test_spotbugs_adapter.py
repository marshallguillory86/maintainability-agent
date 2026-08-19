"""Decision 9, slice 3: SpotBugs reads bytecode that already exists.

Cycle: Grok audit on 742a49f, queue closed at 9510c09. Spec is ADR 012
plus that audit's 12-point do-not-copy list. This adapter never names
.java files, never calls parse_checkstyle, never treats missing
bytecode as not-installed, and never claims D15. One live test is
conditional: no binary (or no javac) is a skip, not a green substitute.
"""

from __future__ import annotations

import inspect
import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

import pytest
from test_exclusion_dialects import BYTECODE_DIRS, FILE_LIST

from maintainability_audit import _runner
from maintainability_audit._catalog import load_catalog
from maintainability_audit._runner import Outcome, Probe, ToolResult
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

SPOTBUGS_CONCERNS = ("style",)
# SpotBugs ExitCodes bit flags when -exitcode is passed.
SUCCESS, BUGS_FOUND, MISSING_CLASS, ERROR = 0, 1, 2, 4


def _adapter():
    adapter = adapter_for("spotbugs")
    assert adapter is not None, "spotbugs is promised but has no adapter"
    return adapter


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


def _java_source() -> str:
    return (
        "package fixture;\n"
        "public class Widget {\n"
        "    public int tangled(int value) {\n"
        "        int total = 0;\n"
        "        if (value > 1) { total += value; }\n"
        "        return total;\n"
        "    }\n"
        "}\n"
    )


def _pool_config(policy: str = "copyleft-weak", **analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": policy, **analyzers,
    })
    return config


def _only_spotbugs(**analyzers: Any) -> dict[str, Any]:
    return _pool_config(
        allow_tools=["spotbugs"],
        deny_tools=sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] != "spotbugs"
        ),
        **analyzers,
    )


def _row(report: dict[str, Any], slug: str) -> tuple[str, dict[str, Any]]:
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            if row["tool"] == slug:
                return outcome, row
    raise AssertionError(f"{slug} absent from coverage")


def _bugcollection(*instances: str) -> str:
    body = "\n".join(instances)
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<BugCollection version="4.8.6" sequence="0">\n'
        f"{body}\n"
        "</BugCollection>\n"
    )


def _instance(category: str, bug_type: str, sourcepath: str, line: int) -> str:
    name = Path(sourcepath).name
    return (
        f'<BugInstance type="{bug_type}" category="{category}" '
        f'priority="2" rank="10">\n'
        f'  <SourceLine sourcefile="{name}" sourcepath="{sourcepath}" '
        f'start="{line}" end="{line}"/>\n'
        "</BugInstance>"
    )


def test_spotbugs_reads_bytecode_dirs_never_java_sources(tmp_path: Path) -> None:
    """has_targets and argv are class dirs. A .java file is not a target."""
    adapter = _adapter()
    assert adapter.version_argv() in {("spotbugs", "-version"), ("spotbugs", "--version")}
    assert adapter.languages == ("java",)
    assert set(SPOTBUGS_CONCERNS) <= set(adapter.concepts)
    assert "spotbugs" in BYTECODE_DIRS
    assert "spotbugs" not in FILE_LIST, "FILE_LIST is source files; SpotBugs names class dirs"

    source_only = _repo(tmp_path / "src_only", {"src/Widget.java": _java_source()})
    assert adapter.has_targets(source_only) is False

    maven = _repo(tmp_path / "maven", {
        "src/Widget.java": _java_source(),
        "target/classes/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })
    gradle = _repo(tmp_path / "gradle", {
        "src/Widget.java": _java_source(),
        "build/classes/java/main/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })

    assert adapter.has_targets(maven) is True
    assert adapter.has_targets(gradle) is True, (
        "build/classes is a prefix: Gradle's java/main tree sits under it"
    )

    argv = adapter.invocation(maven).argv
    joined = " ".join(argv)
    assert argv[0] == "spotbugs"
    assert "-textui" in argv
    assert "-exitcode" in argv
    assert "xml" in joined
    assert "target/classes" in joined
    assert ".java" not in joined
    assert "http://" not in joined and "https://" not in joined
    assert not {"pip", "npm", "npx", "mvn", "gradle", "javac"} & set(argv)
    assert "spotbugs.xml" not in joined and "findbugs.xml" not in joined


def test_configured_class_dirs_are_targets(tmp_path: Path) -> None:
    """ADR 012: defaults plus configured dirs, never a .java sweep."""
    adapter = _adapter()
    root = _repo(tmp_path / "cfg", {
        "src/Widget.java": _java_source(),
        "out/classes/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })
    assert adapter.has_targets(root) is False
    assert adapter.has_targets(root, class_dirs=("out/classes",)) is True
    joined = " ".join(adapter.invocation(root, class_dirs=("out/classes",)).argv)
    assert "out/classes" in joined
    assert ".java" not in joined

    report = build_report(root, _only_spotbugs(class_dirs=["out/classes"]), run_analyzers=True)
    outcome, row = _row(report, "spotbugs")
    assert outcome != "not-applicable" or "build" not in (row.get("detail") or "").lower(), (
        "configured out/classes was treated as a missing build"
    )


def test_a_java_tree_without_bytecode_is_build_then_rerun_never_a_spawn(
    tmp_path: Path,
) -> None:
    """ADR 012: absence is not-applicable + work order, never not-installed."""
    adapter = _adapter()
    root = _repo(tmp_path / "nobc", {"src/Widget.java": _java_source(), "README.md": "# f\n"})
    assert adapter.has_targets(root) is False

    report = build_report(root, _only_spotbugs(), run_analyzers=True)
    outcome, row = _row(report, "spotbugs")
    assert outcome == "not-applicable"
    assert row["languages"] == ["java"]
    assert "build" in (row.get("detail") or "").lower()

    item = next(entry for entry in report["environment_work_order"] if entry["tool"] == "spotbugs")
    remedy = item["install"].lower()
    assert "build" in remedy
    assert "pip" not in remedy
    assert "brew install" not in remedy, (
        "no bytecode is not a missing binary; do not send the user to brew"
    )
    assert "version" in item["verify"].lower() or "rerun" in item["verify"].lower() or "re-run" in item["verify"].lower()


def test_a_javascript_tree_is_not_a_build_order(tmp_path: Path) -> None:
    """A JS tree has nothing to compile for SpotBugs; do not prescribe a Java build."""
    _adapter()
    root = _repo(tmp_path / "js", {"app.js": "const x = 1;\n"})
    report = build_report(root, _only_spotbugs(), run_analyzers=True)
    outcome, row = _row(report, "spotbugs")
    assert outcome == "not-applicable"
    assert row["languages"] == ["java"]
    build_items = [
        entry for entry in report["environment_work_order"]
        if entry["tool"] == "spotbugs" and "build" in entry["install"].lower()
    ]
    assert build_items == [], "a JS-only tree invited a Java build-then-rerun"


def test_recorded_bugcollection_maps_real_categories_onto_declared_concepts() -> None:
    """BugCollection XML, never parse_checkstyle. Category map is the taxonomy."""
    payload = _bugcollection(
        _instance("STYLE", "NM_CLASS_NAMING_CONVENTION", "src/Widget.java", 2),
        _instance("CORRECTNESS", "NP_NULL_ON_SOME_PATH", "src/Widget.java", 12),
        _instance("BAD_PRACTICE", "EQ_DOESNT_OVERRIDE_EQUALS", "src/Widget.java", 8),
        _instance("SECURITY", "SQL_INJECTION_JDBC", "src/Db.java", 9),
        _instance("NOT_A_REAL_CATEGORY", "UNKNOWN_BUG", "src/X.java", 4),
    )
    adapter = _adapter()
    reader = inspect.getsource(type(adapter)._read)
    assert "parse_checkstyle" not in reader
    assert "BugCollection" in reader or "buginstance" in reader.lower() or "category" in reader.lower()

    extraction = adapter.parse(ToolResult(
        slug="spotbugs", outcome=Outcome.RAN, stdout=payload, exit_code=BUGS_FOUND,
    ))
    assert not extraction.parse_error
    assert len(extraction.findings) == 5
    declared = set(adapter.concepts)
    by_rule = {finding.rule: finding for finding in extraction.findings}
    assert by_rule["NM_CLASS_NAMING_CONVENTION"].concept == "style"
    assert by_rule["NM_CLASS_NAMING_CONVENTION"].path == "src/Widget.java"
    assert by_rule["NM_CLASS_NAMING_CONVENTION"].line == 2
    for finding in extraction.findings:
        assert finding.concept in declared
        assert finding.rule
        assert not finding.path.endswith(".class"), "report the source, not the artifact"


def test_exit_codes_are_spotbugs_bit_flags_not_checkstyle_folklore() -> None:
    """-exitcode: 0 success, 1 bugs, 2 missing-class; 4 is an error."""
    adapter = _adapter()
    codes = set(adapter.findings_exit_codes)
    assert SUCCESS in codes and BUGS_FOUND in codes
    assert MISSING_CLASS in codes or (SUCCESS | MISSING_CLASS) in codes
    assert ERROR not in codes, "ERROR_FLAG (4) is a failed run, not findings"


def test_missing_binary_with_bytecode_is_install_not_build(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path / "missing", {
        "src/Widget.java": _java_source(),
        "target/classes/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })
    locate = _runner.locate
    monkeypatch.setattr(
        _runner, "locate",
        lambda executable: None if Path(executable).name == "spotbugs" else locate(executable),
    )
    report = build_report(root, _only_spotbugs(), run_analyzers=True)
    outcome, row = _row(report, "spotbugs")
    assert outcome == "not-installed"
    assert row["languages"] == ["java"]
    item = next(entry for entry in report["environment_work_order"] if entry["tool"] == "spotbugs")
    assert "spotbugs" in item["install"].lower()
    assert "pip" not in item["install"].lower()
    assert "brew" in item["install"].lower() or "spotbugs" in item["install"].lower()
    assert "version" in item["verify"].lower()


def test_staleness_is_on_the_coverage_row_and_the_findings(tmp_path: Path) -> None:
    """P8: newest source mtime vs newest class mtime; stale runs say so."""
    adapter = _adapter()
    root = _repo(tmp_path / "stale", {
        "src/Widget.java": _java_source(),
        "target/classes/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })
    source = root / "src" / "Widget.java"
    klass = root / "target" / "classes" / "fixture" / "Widget.class"
    now = time.time()
    os.utime(klass, (now - 120, now - 120))
    os.utime(source, (now, now))

    if hasattr(adapter, "staleness"):
        evidence = adapter.staleness(root)
        assert evidence["stale"] is True
        assert evidence["source_mtime"] > evidence["class_mtime"]
    else:
        report = build_report(root, _only_spotbugs(), run_analyzers=True)
        _outcome, row = _row(report, "spotbugs")
        assert row.get("stale") is True or "stale" in (row.get("detail") or "").lower()
        assert "source_mtime" in row and "class_mtime" in row
        assert row["source_mtime"] > row["class_mtime"]


def test_fresh_bytecode_is_not_labeled_stale(tmp_path: Path) -> None:
    adapter = _adapter()
    root = _repo(tmp_path / "fresh", {
        "src/Widget.java": _java_source(),
        "target/classes/fixture/Widget.class": b"\xca\xfe\xba\xbe dummy",
    })
    now = time.time()
    os.utime(root / "src" / "Widget.java", (now - 120, now - 120))
    os.utime(root / "target" / "classes" / "fixture" / "Widget.class", (now, now))
    if hasattr(adapter, "staleness"):
        assert adapter.staleness(root)["stale"] is False
        return
    report = build_report(root, _only_spotbugs(), run_analyzers=True)
    _outcome, row = _row(report, "spotbugs")
    assert row.get("stale") is False or (
        "stale" not in (row.get("detail") or "").lower()
        and row.get("stale") is not True
    )


def test_a_real_spotbugs_run_is_versioned_located_and_deterministic(tmp_path: Path) -> None:
    adapter = _adapter()
    available = Probe().check("spotbugs", adapter.version_argv())
    if not available.usable:
        pytest.skip(f"spotbugs unavailable: {available.detail or available.outcome.value}")
    javac = shutil.which("javac")
    if javac is None:
        pytest.skip("javac unavailable; live SpotBugs needs real bytecode")

    root = _repo(tmp_path / "live", {"src/Widget.java": _java_source()})
    classes = root / "target" / "classes"
    classes.mkdir(parents=True)
    subprocess.run(
        [javac, "-d", str(classes), str(root / "src" / "Widget.java")],
        check=True, capture_output=True, text=True,
    )
    config = _only_spotbugs()
    first = build_report(root, config, run_analyzers=True)
    second = build_report(root, config, run_analyzers=True)
    outcome, row = _row(first, "spotbugs")
    second_outcome, _ = _row(second, "spotbugs")
    assert outcome == second_outcome == "ran"
    assert row["languages"] == ["java"]
    import re
    assert re.search(r"\d+\.\d", row["version"] or ""), f"not a dotted version: {row.get('version')!r}"
    findings = [item for item in first["analyzer_findings"] if item["tool"] == "spotbugs"]
    for finding in findings:
        assert not str(finding["path"]).endswith(".class")
        assert finding["concept"] in set(adapter.concepts)
        assert finding["rule"]
    assert [
        item for item in second["analyzer_findings"] if item["tool"] == "spotbugs"
    ] == findings

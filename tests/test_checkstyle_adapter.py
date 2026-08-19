"""Decision 9, slice 2: Checkstyle joins the JVM track.

Written under the 549fcad audit's do-not-copy law: measures lead with
CONCERN names (a concepts-only tuple dropped PMD from concern pools),
the adapter states what it reads (java), an empty target list never
spawns, versions are dotted numbers, unmapped output lands on a
declared concept, and XML is parsed through `_generic`'s checkstyle
format — never a bespoke SARIF parser. One live test is conditional:
an absent binary is an honest coverage row, never a green substitute.
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from _ast_reading import producer_literal
from test_exclusion_dialects import FILE_LIST

from maintainability_audit import _runner
from maintainability_audit._adapters import Exclusions
from maintainability_audit._catalog import (
    DEFAULTS,
    LICENSE_POLICIES,
    load_catalog,
    resolve_pool,
)
from maintainability_audit._generic import parse_checkstyle
from maintainability_audit._mcp_setup import setup_questions
from maintainability_audit._runner import Outcome, Probe, ToolResult
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "analyzer-catalog.json"
PRODUCER = ROOT / "tools" / "build_catalog.py"
POOL_DOC = ROOT / "docs" / "analyzer-pool.md"
CHECKSTYLE_CONCERNS = ("style", "complexity", "structure")
POOLABLE = {"permissive", "weak-copyleft", "strong-copyleft"}


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _entry() -> dict[str, Any]:
    return next(tool for tool in _catalog()["tools"] if tool["slug"] == "checkstyle")


def _adapter():
    adapter = adapter_for("checkstyle")
    assert adapter is not None, "checkstyle is promised but has no adapter"
    return adapter


def _repo(root: Path, files: dict[str, str]) -> Path:
    root.mkdir(parents=True)
    for name, body in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _java_repo(root: Path) -> Path:
    # A genuinely oversized, nested method: the built-in Java population
    # must have a threshold breach to report, or the missing-binary test
    # would assert an empty hotspot list into existence. (Contract
    # repair, disclosed: the original four-line fixture breached
    # nothing, making its built-ins assertion unsatisfiable.)
    nested = "\n".join(
        f"{'    ' * (index + 2)}if (value > {index}) {{ total += {index};"
        for index in range(12)
    )
    closes = "\n".join(f"{'    ' * (index + 2)}}}" for index in reversed(range(12)))
    padding = "\n".join(f"        total += {index};" for index in range(90))
    body = (
        "package fixture;\n"
        "public class oversized_name {\n"
        "    int X_bad;\n"
        "    public int tangled(int value) {\n"
        "        int total = 0;\n"
        f"{nested}\n{closes}\n{padding}\n"
        "        return total;\n"
        "    }\n"
        "}\n"
    )
    return _repo(root, {"src/oversized_name.java": body, "README.md": "# f\n"})


def _pool_config(policy: str, **analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": policy, **analyzers,
    })
    return config


def _only_checkstyle(policy: str = "copyleft-weak") -> dict[str, Any]:
    return _pool_config(
        policy,
        allow_tools=["checkstyle"],
        deny_tools=sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] != "checkstyle"
        ),
    )


def _row(report: dict[str, Any], slug: str) -> tuple[str, dict[str, Any]]:
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            if row["tool"] == slug:
                return outcome, row
    raise AssertionError(f"{slug} absent from coverage")


def _weak_copyleft_policy() -> str:
    """The least-restrictive shipped policy that already admits weak-copyleft."""
    return next(
        name for name, classes in LICENSE_POLICIES.items()
        if "weak-copyleft" in classes
    )


def _eligible(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        tool for tool in tools
        if tool["license_class"] in POOLABLE
        and not tool["deprecated"]
        and tool["languages"]
        and not tool["security_only"]
    ]


def _recomputed_counts(tools: list[dict[str, Any]]) -> dict[str, Any]:
    """The catalog summary is a function of the rows, not hand arithmetic."""
    eligible = _eligible(tools)
    return {
        "in_source": len(tools),
        "eligible": len(eligible),
        "by_tier": dict(Counter(tool["tier"] for tool in eligible)),
        "by_license_status": dict(Counter(tool["license_status"] for tool in tools)),
        "by_license_class": dict(Counter(tool["license_class"] for tool in tools)),
        "by_measure": dict(Counter(
            measure for tool in tools for measure in tool["measures"]
        )),
        "eligible_by_license_class": dict(Counter(
            tool["license_class"] for tool in eligible
        )),
        "adapters_implemented": sum(
            1 for tool in tools if tool["adapter"] == "implemented"
        ),
    }


def test_catalog_and_producer_record_the_weak_copyleft_contract() -> None:
    """LGPL is verified honestly; measures lead with concerns, not concepts."""
    catalog = _catalog()
    entry = _entry()

    assert entry["license"] == "LGPL-2.1-or-later"
    assert entry["license_status"] == "foss"
    assert entry["license_class"] == "weak-copyleft"
    assert "license" in entry["license_evidence"].lower()
    assert entry["languages"] == ["java"]
    assert tuple(entry["measures"][:3]) == CHECKSTYLE_CONCERNS, (
        "measures must lead with concern names; a concepts-only tuple "
        "dropped PMD from concern pools"
    )
    assert entry["tier"] == "moderate"
    assert entry["adapter"] == "implemented"

    note = catalog["provenance"]["note"].lower()
    assert "checkstyle" in note and "lgpl" in note and "license" in note

    tiers = producer_literal("VERIFIED_TIERS")
    adapters = producer_literal("IMPLEMENTED_ADAPTERS")
    assert set(tiers) == set(adapters), (
        "a below-all tier is a promise that a runnable adapter ships"
    )
    assert tiers["checkstyle"] == "moderate"
    assert producer_literal("VERIFIED_MEASURES")["checkstyle"][:3] == CHECKSTYLE_CONCERNS
    license_name, evidence = producer_literal("VERIFIED_LICENSES")["checkstyle"]
    assert license_name == "LGPL-2.1-or-later"
    assert "license" in evidence.lower()


def test_catalog_counts_are_recomputed_from_the_tool_records() -> None:
    """The PMD slice's count error came from hand-decrementing the summary."""
    catalog = _catalog()
    expected = _recomputed_counts(catalog["tools"])
    assert catalog["counts"] == expected


@pytest.mark.parametrize("concern", CHECKSTYLE_CONCERNS)
def test_a_concern_pool_keeps_checkstyle(concern: str) -> None:
    """Audit M: measures name the concern, so concern pools can select it."""
    pool, _decisions = resolve_pool(_pool_config(
        _weak_copyleft_policy(), concerns=[concern],
    ))
    assert "checkstyle" in {tool["slug"] for tool in pool}, (
        f"a {concern}-only pool dropped the {concern} tool"
    )


def test_selection_honours_the_license_policy_in_both_directions() -> None:
    """Weak-copyleft is the user's call: excluded by default, one policy away."""
    defaults = {question["name"]: question["default"] for question in setup_questions({})}
    assert defaults["license_policy"] == DEFAULTS["license_policy"] == "permissive"
    assert "weak-copyleft" not in LICENSE_POLICIES["permissive"]

    _pool, decisions = resolve_pool(_pool_config("permissive"))
    decision = next(item for item in decisions if item.slug == "checkstyle")
    assert not decision.selected
    assert "license class" in decision.reason
    assert "weak-copyleft" in decision.reason

    admitting = _weak_copyleft_policy()
    assert admitting in LICENSE_POLICIES
    weak_pool, weak_decisions = resolve_pool(_pool_config(admitting))
    assert "checkstyle" in {tool["slug"] for tool in weak_pool}
    selected = next(item for item in weak_decisions if item.slug == "checkstyle")
    assert selected.selected


def test_checkstyle_is_registered_with_bundled_rules_and_a_cli_probe(
    tmp_path: Path,
) -> None:
    """Local CLI, pinned bundled ruleset, XML out, explicit .java targets."""
    adapter = _adapter()

    assert adapter.version_argv() == ("checkstyle", "--version")
    assert adapter.languages == ("java",)
    assert set(CHECKSTYLE_CONCERNS) <= set(adapter.concepts)
    assert "checkstyle" in FILE_LIST, (
        "FILE_LIST must skip flag-dialect checks; checkstyle names files"
    )

    root = _repo(tmp_path / "shape", {
        "lib/Bundle.java": "class Bundle {}\n",
        "src/lib/Owned.java": "class Owned {}\n",
        "src/Library.java": "class Library {}\n",
    })
    argv = adapter.invocation(root, excludes=Exclusions((), ("lib",))).argv
    joined = " ".join(argv)

    assert argv[0] == "checkstyle"
    assert "-f" in argv and "xml" in argv
    assert "google_checks.xml" in joined or "sun_checks.xml" in joined
    assert "http://" not in joined and "https://" not in joined
    assert not {"pip", "npm", "npx"} & set(argv)
    assert "src/lib/Owned.java" in joined, "first-party src/lib dropped"
    assert "src/Library.java" in joined, "prefix-matched past a boundary"
    assert f"{root}/lib/Bundle.java" not in joined, "named a generated file"


def test_nothing_to_read_never_spawns(tmp_path: Path) -> None:
    """A JS tree or an all-excluded Java tree is a coverage fact, not a CLI."""
    adapter = _adapter()
    assert adapter.languages == ("java",)

    vendored = _repo(tmp_path / "vendored", {"vendor/Only.java": "class O {}\n"})
    assert adapter.has_targets(vendored, excludes=()) is True
    assert adapter.has_targets(vendored, excludes=("vendor/",)) is False

    js = _repo(tmp_path / "js", {"app.js": "const x = 1;\n"})
    report = build_report(js, _only_checkstyle(), run_analyzers=True)
    outcome, row = _row(report, "checkstyle")
    assert outcome == "not-applicable", (
        "a JS-only tree invited a Java-only integration to spawn"
    )
    assert row["languages"] == ["java"]
    assert set(row["concepts"]) >= set(CHECKSTYLE_CONCERNS)


def test_recorded_checkstyle_xml_becomes_located_declared_findings() -> None:
    """`_generic.parse_checkstyle`, and every finding on a declared concept."""
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<checkstyle version="11.1.0">\n'
        '<file name="src/oversized_name.java">\n'
        '<error line="2" column="14" severity="warning"'
        ' message="Name \'oversized_name\' must match pattern."'
        ' source="com.puppycrawl.tools.checkstyle.checks.naming.TypeNameCheck"/>\n'
        '<error line="3" column="9" severity="warning"'
        ' message="unmapped rule must still land on a declared concept"'
        ' source="com.puppycrawl.tools.checkstyle.checks.UnknownCheck"/>\n'
        '</file>\n'
        "</checkstyle>\n"
    )
    adapter = _adapter()
    reader = inspect.getsource(type(adapter)._read)
    assert "parse_checkstyle" in reader, (
        "XML must go through _generic.parse_checkstyle, not a private parser"
    )
    assert "sarif" not in reader.lower(), "never a bespoke SARIF parser"

    extraction = adapter.parse(ToolResult(
        slug="checkstyle", outcome=Outcome.RAN, stdout=payload, exit_code=0,
    ))
    generic = parse_checkstyle(payload, "checkstyle", "style")

    assert not extraction.parse_error
    assert len(extraction.findings) == len(generic.findings) == 2
    declared = set(adapter.concepts)
    for finding, expected in zip(extraction.findings, generic.findings, strict=True):
        assert finding.path == expected.path == "src/oversized_name.java"
        assert finding.line == expected.line
        assert finding.rule == expected.rule
        assert finding.rule
        assert finding.concept in declared


def test_an_unmapped_rule_lands_on_a_declared_concept() -> None:
    """Audit L: the default concept must be one the adapter claims."""
    payload = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<checkstyle>\n'
        '<file name="src/X.java">\n'
        '<error line="9" message="not in the map"'
        ' source="com.puppycrawl.tools.checkstyle.checks.NotInTheMapCheck"/>\n'
        '</file>\n'
        "</checkstyle>\n"
    )
    adapter = _adapter()
    extraction = adapter.parse(ToolResult(
        slug="checkstyle", outcome=Outcome.RAN, stdout=payload, exit_code=0,
    ))
    assert len(extraction.findings) == 1
    assert extraction.findings[0].concept in set(adapter.concepts)
    assert extraction.findings[0].rule


def test_missing_checkstyle_is_actionable_and_built_ins_still_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No binary costs corroboration, never the Java fallback population."""
    root = _java_repo(tmp_path / "missing")
    locate = _runner.locate
    monkeypatch.setattr(
        _runner, "locate",
        lambda executable: None if Path(executable).name == "checkstyle"
        else locate(executable),
    )

    report = build_report(root, _only_checkstyle(), run_analyzers=True)
    outcome, row = _row(report, "checkstyle")

    assert outcome == "not-installed"
    assert row["languages"] == ["java"]
    assert set(row["concepts"]) >= {"style"}
    item = next(
        entry for entry in report["environment_work_order"]
        if entry["tool"] == "checkstyle"
    )
    install = item["install"].lower()
    assert "checkstyle" in install
    assert "pip" not in install, "Checkstyle must not inherit the Python-package fallback"
    assert "checkstyle" in item["verify"].lower()
    assert "version" in item["verify"].lower()

    java_hits = [
        finding
        for group in (report.get("function_hotspots") or [], report.get("file_hotspots") or [])
        for finding in group
        if finding.get("path") == "src/oversized_name.java"
    ]
    assert java_hits, "a missing Checkstyle removed the built-in Java population"


def test_a_real_checkstyle_run_is_versioned_located_and_deterministic(
    tmp_path: Path,
) -> None:
    """When the binary exists: a dotted version, located findings, two equal runs."""
    adapter = _adapter()
    available = Probe().check("checkstyle", adapter.version_argv())
    if not available.usable:
        pytest.skip(
            f"checkstyle unavailable: {available.detail or available.outcome.value}"
        )

    root = _java_repo(tmp_path / "live")
    config = _only_checkstyle()
    first = build_report(root, config, run_analyzers=True)
    second = build_report(root, config, run_analyzers=True)
    outcome, row = _row(first, "checkstyle")
    second_outcome, _ = _row(second, "checkstyle")

    assert outcome == second_outcome == "ran"
    assert re.search(r"\d+\.\d", row["version"] or ""), (
        f"not a dotted version: {row.get('version')!r}"
    )
    assert row["languages"] == ["java"]
    findings = [
        item for item in first["analyzer_findings"] if item["tool"] == "checkstyle"
    ]
    assert findings, "the bundled ruleset found nothing to say about a bad class name"
    for finding in findings:
        assert finding["path"] == "src/oversized_name.java"
        assert isinstance(finding["line"], int) and finding["line"] > 0
        assert finding["rule"]
        assert finding["concept"] in set(adapter.concepts)
    assert [
        item for item in second["analyzer_findings"] if item["tool"] == "checkstyle"
    ] == findings


def test_pool_document_names_checkstyle_and_its_license_evidence() -> None:
    """Docs yours: the pool page gains checkstyle and names the LICENSE evidence."""
    text = POOL_DOC.read_text(encoding="utf-8")
    assert re.search(r"^\| checkstyle \|", text, flags=re.MULTILINE)
    assert "lgpl" in text.lower()
    assert "checkstyle" in text.lower() and "license" in text.lower()

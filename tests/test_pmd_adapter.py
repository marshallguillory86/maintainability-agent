"""Decision 9: PMD opens the source-only JVM analyzer track.

The catalog promise, selection defaults, degradation path, and recorded
output all run without PMD installed.  One live test is deliberately
conditional: it proves the real CLI when a developer or CI image supplies
it, but an absent JVM tool remains an honest coverage result rather than a
green substitute for that proof.
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from maintainability_audit import _runner
from maintainability_audit._catalog import load_catalog, resolve_pool
from maintainability_audit._generic import declared_adapter
from maintainability_audit._mcp_setup import apply_answers, setup_questions
from maintainability_audit._runner import Outcome, Probe, ToolResult
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "data" / "analyzer-catalog.json"
PRODUCER = ROOT / "tools" / "build_catalog.py"
PMD_CONCEPTS = {"cognitive_complexity", "cyclomatic_complexity"}


def _catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _pmd_entry() -> dict[str, Any]:
    return next(tool for tool in _catalog()["tools"] if tool["slug"] == "pmd")


def _assignment(name: str) -> ast.AST:
    tree = ast.parse(PRODUCER.read_text(encoding="utf-8"), filename=str(PRODUCER))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == name
            for target in node.targets
        ):
            return node.value
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
            and node.value is not None
        ):
            return node.value
    raise AssertionError(f"{name} is missing from tools/build_catalog.py")


def _literal(name: str) -> Any:
    value = _assignment(name)
    if (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Name)
        and value.func.id == "frozenset"
        and len(value.args) == 1
    ):
        return frozenset(ast.literal_eval(value.args[0]))
    return ast.literal_eval(value)


def _pmd_adapter():
    adapter = adapter_for("pmd") or declared_adapter("pmd")
    assert adapter is not None, "pmd is verified in the pool but has no runnable adapter"
    return adapter


def _repo(root: Path) -> Path:
    root.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    source = root / "src" / "Oversized.java"
    source.parent.mkdir()
    source.write_text(_java_source(), encoding="utf-8")
    return root


def _java_source() -> str:
    nested = "\n".join(
        f"{'        ' * (index + 1)}if (value > {index}) {{"
        f" total += {index};"
        for index in range(18)
    )
    closes = "\n".join(
        f"{'        ' * (index + 1)}}}"
        for index in reversed(range(18))
    )
    padding = "\n".join(f"        total += {index};" for index in range(90))
    return f"""package fixture;

public class Oversized {{
    public int tangled(int value) {{
        int total = 0;
{nested}
{closes}
{padding}
        return total;
    }}
}}
"""


def _pmd_only_config() -> dict[str, Any]:
    config = load_config(None)
    block = config["analyzers"]
    block.update({
        "run": True,
        "depth": "moderate",
        "license_policy": "permissive",
        "allow_tools": ["pmd"],
        "deny_tools": sorted(
            tool["slug"] for tool in load_catalog() if tool["slug"] != "pmd"
        ),
    })
    return config


def _coverage_row(report: dict[str, Any], slug: str) -> tuple[str, dict[str, Any]]:
    for outcome, rows in report["analyzer_coverage"]["by_outcome"].items():
        for row in rows:
            if row["tool"] == slug:
                return outcome, row
    raise AssertionError(f"{slug} is absent from analyzer coverage")


def _pmd_findings(report: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in report["analyzer_findings"]
        if item["tool"].lower() == "pmd"
    ]


def test_pmd_catalog_and_producer_record_the_verified_contract() -> None:
    """The artifact and its producer must regenerate the same PMD promise."""
    pmd = _pmd_entry()

    assert pmd["license_status"] == "foss"
    assert pmd["license_class"] == "permissive"
    assert "bsd" in pmd["license"].lower()
    assert "license" in pmd["license_evidence"].lower()
    assert "java" in pmd["languages"]
    assert set(pmd["measures"]) >= PMD_CONCEPTS
    assert pmd["tier"] == "moderate"
    assert pmd["adapter"] == "implemented"

    tiers = _literal("VERIFIED_TIERS")
    adapters = _literal("IMPLEMENTED_ADAPTERS")
    measures = _literal("VERIFIED_MEASURES")
    licenses = _literal("VERIFIED_LICENSES")
    assert set(tiers) == set(adapters), (
        "a below-all tier is a promise that a runnable adapter ships"
    )
    assert tiers["pmd"] == "moderate"
    assert set(measures["pmd"]) >= PMD_CONCEPTS
    assert "bsd" in licenses["pmd"][0].lower()
    assert "license" in licenses["pmd"][1].lower()


def test_pmd_is_registered_with_a_local_ruleset_and_cli_probe(tmp_path: Path) -> None:
    """PMD is a local CLI integration: pinned rules, no URL or install step."""
    adapter = _pmd_adapter()

    assert adapter.version_argv() == ("pmd", "--version")
    assert set(adapter.concepts) >= PMD_CONCEPTS
    argv = adapter.invocation(tmp_path).argv
    joined = " ".join(argv).lower()
    lower_argv = {argument.lower() for argument in argv}
    assert argv[0] == "pmd"
    assert "check" in argv
    assert "sarif" in joined
    assert "--rulesets" in lower_argv or "-r" in lower_argv or "-r=" in joined
    assert "http://" not in joined and "https://" not in joined
    assert not {"pip", "npm", "npx"} & set(argv)


def test_setup_defaults_select_pmd_for_a_java_repository(tmp_path: Path) -> None:
    """Moderate plus permissive selects PMD without asking for its name."""
    root = _repo(tmp_path / "defaults")
    questions = setup_questions(load_config(None))
    answers = {question["name"]: question["default"] for question in questions}

    config = apply_answers(root, answers)
    pool, decisions = resolve_pool(config)
    selected = {tool["slug"]: tool for tool in pool}

    assert config["analyzers"]["run"] is True
    assert config["analyzers"]["depth"] == "moderate"
    assert config["analyzers"]["license_policy"] == "permissive"
    assert "pmd" in selected
    assert "java" in selected["pmd"]["languages"]
    pmd_decision = next(item for item in decisions if item.slug == "pmd")
    assert pmd_decision.selected


def test_recorded_pmd_sarif_output_becomes_located_findings() -> None:
    """A real PMD SARIF payload keeps path, line, rule, and concept."""
    payload = json.dumps({
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "PMD", "version": "7.18.0"}},
            "results": [
                {
                    "ruleId": "CognitiveComplexity",
                    "message": {
                        "text": (
                            "The method 'tangled' has a cognitive complexity "
                            "of 37, current threshold is 15"
                        ),
                    },
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": "src/Oversized.java"},
                            "region": {"startLine": 4, "startColumn": 5},
                        },
                    }],
                },
                {
                    "ruleId": "CyclomaticComplexity",
                    "message": {
                        "text": "The method 'tangled' has a cyclomatic complexity of 19.",
                    },
                    "locations": [{
                        "physicalLocation": {
                            "artifactLocation": {"uri": "src/Oversized.java"},
                            "region": {"startLine": 4, "startColumn": 5},
                        },
                    }],
                },
            ],
        }],
    })
    result = ToolResult(
        slug="pmd",
        outcome=Outcome.RAN,
        stdout=payload,
        exit_code=0,
    )

    extraction = _pmd_adapter().parse(result)

    assert not extraction.parse_error
    assert len(extraction.findings) == 2
    assert {finding.path for finding in extraction.findings} == {"src/Oversized.java"}
    assert {finding.line for finding in extraction.findings} == {4}
    assert {finding.rule for finding in extraction.findings} == {
        "CognitiveComplexity",
        "CyclomaticComplexity",
    }
    concepts = set(_pmd_adapter().concepts)
    for finding in extraction.findings:
        assert finding.concept in concepts


def test_missing_pmd_is_actionable_and_java_built_ins_still_run(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No PMD costs corroboration, never the built-in Java population."""
    root = _repo(tmp_path / "missing")
    locate = _runner.locate
    monkeypatch.setattr(
        _runner,
        "locate",
        lambda executable: None if Path(executable).name == "pmd" else locate(executable),
    )

    report = build_report(root, _pmd_only_config(), run_analyzers=True)
    outcome, coverage = _coverage_row(report, "pmd")

    assert outcome == "not-installed"
    assert set(coverage["concepts"]) >= PMD_CONCEPTS
    item = next(row for row in report["environment_work_order"] if row["tool"] == "pmd")
    install = item["install"].lower()
    assert "pmd" in install
    assert "pip" not in install, "PMD must not inherit the Python-package fallback"
    assert "pmd" in item["verify"].lower() and "version" in item["verify"].lower()
    assert set(item["concepts"].split(", ")) >= PMD_CONCEPTS

    java_hotspots = [
        finding
        for finding in report["function_hotspots"]
        if finding["path"] == "src/Oversized.java" and finding["kind"] == "function"
    ]
    assert any(finding["status"] == "fail" for finding in java_hotspots), (
        "a missing PMD removed Java's built-in declaration fallback"
    )


def test_a_real_pmd_run_is_located_covered_and_deterministic(tmp_path: Path) -> None:
    """When PMD is installed, its pinned source-only rules run without a network."""
    adapter = _pmd_adapter()
    available = Probe().check("pmd", adapter.version_argv())
    if not available.usable:
        pytest.skip(f"pmd is unavailable: {available.detail or available.outcome.value}")

    root = _repo(tmp_path / "live")
    config = _pmd_only_config()
    first = build_report(root, config, run_analyzers=True)
    second = build_report(root, config, run_analyzers=True)
    first_outcome, coverage = _coverage_row(first, "pmd")
    second_outcome, _ = _coverage_row(second, "pmd")
    findings = _pmd_findings(first)

    assert first_outcome == second_outcome == "ran"
    assert coverage["version"]
    assert coverage["findings"] == len(findings) > 0
    assert "java" in coverage["languages"]
    assert _pmd_findings(second) == findings
    for finding in findings:
        assert finding["path"] == "src/Oversized.java"
        assert isinstance(finding["line"], int) and finding["line"] > 0
        assert finding["concept"] in set(adapter.concepts)

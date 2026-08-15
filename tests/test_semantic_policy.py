"""ADR 003 option C: typed facts, repository policy, and candidates stay distinct."""

from __future__ import annotations

import ast
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import maintainability_audit.report as report_module
from maintainability_audit._formula import CATEGORY_ASPECTS
from maintainability_audit._semantic import (
    CLASS_CANDIDATE,
    CLASS_POLICY,
    CLASS_UNIVERSAL,
    semantic_findings,
)
from maintainability_audit._semantic_policy import load_semantic_policy
from maintainability_audit.config import load_config
from maintainability_audit.prompts import render_ai_prompt

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "semantic_ts"
CONFIG = json.loads((FIXTURE / "maintainability-agent.json").read_text(encoding="utf-8"))
TYPE_ANALYSIS = json.loads(
    (FIXTURE / "recordings" / "typescript-5.9.2.json").read_text(encoding="utf-8")
)
LABELS = json.loads((FIXTURE / "labels.json").read_text(encoding="utf-8"))
HISTORY = (
    {"commit": "1" * 40, "changed_paths": ["src/operations.ts"]},
    {"commit": "2" * 40, "changed_paths": ["src/operations.ts"]},
)
ANALYZER_VERSIONS = {"typescript": "5.9.2"}
SCORE_FIELDS = (
    "maintainability_estimate",
    "maintainability_range",
    "verified_grade",
    "evidence_status",
)


def _policy():
    return load_semantic_policy(CONFIG)


def _result(*, policy=..., type_analysis=TYPE_ANALYSIS) -> dict:
    selected_policy = _policy() if policy is ... else policy
    return semantic_findings(
        FIXTURE,
        policy=selected_policy,
        type_analysis=type_analysis,
        history=HISTORY,
        analyzer_versions=ANALYZER_VERSIONS,
    )


def _of_class(result: dict, classification: str) -> list[dict]:
    return [item for item in result["findings"] if item["class"] == classification]


def _encoded(findings: list[dict]) -> bytes:
    return json.dumps(
        findings, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _fixture_repo(tmp_path: Path) -> Path:
    root = tmp_path / "semantic-repo"
    shutil.copytree(FIXTURE, root)
    _git(root, "init", "-q")
    _git(root, "add", "-A")
    _git(
        root,
        "-c",
        "user.email=test@example.invalid",
        "-c",
        "user.name=Test",
        "commit",
        "-qm",
        "semantic fixture",
    )
    return root


def _reports_with_and_without_semantics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> tuple[dict, dict, dict]:
    root = _fixture_repo(tmp_path)
    plain = report_module.build_report(root, load_config(None))
    semantic = _result()
    monkeypatch.setattr(report_module, "semantic_findings", lambda *_a, **_kw: semantic)
    configured = load_config(None)
    configured["semantic_policy"] = CONFIG["semantic_policy"]
    augmented = report_module.build_report(root, configured)
    return plain, augmented, semantic


def test_same_inputs_produce_byte_identical_semantic_findings() -> None:
    first = _result()
    second = _result()

    assert _encoded(first["findings"]) == _encoded(second["findings"])
    assert {item["class"] for item in first["findings"]} == {
        CLASS_UNIVERSAL,
        CLASS_POLICY,
        CLASS_CANDIDATE,
    }
    assert {
        (item["class"], item["source_evidence"]["path"])
        for item in first["findings"]
    } == {
        (item["class"], item["path"])
        for item in LABELS["true_positives"]
    }


def test_type_checker_proves_the_universal_boundary_violation() -> None:
    universal = _of_class(_result(), CLASS_UNIVERSAL)

    assert len(universal) == 1
    evidence = universal[0]["source_evidence"]
    assert evidence["path"] == "src/universal.ts"
    assert evidence["actual_type"] == "string"
    assert evidence["required_type"] == "OrderStatus"
    assert evidence["diagnostic_code"] == "TS2345"
    assert universal[0].get("policy_entry") in (None, "")


def test_policy_violation_names_its_entry_and_typed_source_evidence() -> None:
    violations = _of_class(_result(), CLASS_POLICY)

    assert len(violations) == 1
    finding = violations[0]
    assert finding["policy_entry"] == "customer-id-public-boundary"
    evidence = finding["source_evidence"]
    assert evidence["path"] == "src/revalidated-boundary.ts"
    assert evidence["symbol"] == "loadCustomer"
    assert evidence["actual_type"] == "string"
    assert evidence["required_type"] == "CustomerId"
    assert evidence["validations"] == ["looksLikeCustomerId", "normalizeCustomerId"]


def test_removing_policy_cannot_create_a_policy_violation() -> None:
    assert load_semantic_policy({"version": 1}) is None
    assert _of_class(_result(), CLASS_POLICY)

    without_policy = _result(policy=None)

    assert not _of_class(without_policy, CLASS_POLICY)


def test_candidate_never_changes_a_gate_score_grade_or_evidence_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    plain, augmented, semantic = _reports_with_and_without_semantics(tmp_path, monkeypatch)
    candidates = _of_class(semantic, CLASS_CANDIDATE)

    assert len(candidates) == 1
    candidate = candidates[0]
    evidence = candidate["source_evidence"]
    assert evidence["path"] == "src/operations.ts"
    assert set(evidence["roles"]) == {"dispatch", "capability", "description"}
    assert evidence["operation_names"] == ["create", "refresh", "revoke"]
    assert augmented["semantic_findings"] == semantic["findings"]
    assert candidate["rule_id"] not in json.dumps(
        augmented["hard_gate_failures"], sort_keys=True,
    )
    assert augmented["hard_gate_failures"] == plain["hard_gate_failures"]
    for field in SCORE_FIELDS:
        assert augmented["score"][field] == plain["score"][field], field


def test_missing_type_analysis_is_unknown_coverage_not_zero_violations() -> None:
    result = _result(type_analysis=None)
    coverage = result["coverage"]

    assert coverage["status"] == "unknown"
    assert coverage["reason"]
    assert coverage.get("violations") is None
    rendered = json.dumps(coverage, sort_keys=True).lower()
    assert "0 violations" not in rendered and "zero violations" not in rendered


def test_prompt_labels_candidates_without_claiming_an_enum_is_proven(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    _, report, semantic = _reports_with_and_without_semantics(tmp_path, monkeypatch)
    candidate = _of_class(semantic, CLASS_CANDIDATE)[0]

    prompt = render_ai_prompt(report)
    lowered = prompt.lower()

    assert "design-review candidate" in lowered
    assert candidate["source_evidence"]["path"] in prompt
    assert "replace with an enum" not in lowered
    assert "enum is proven" not in lowered


def test_bare_strings_without_a_declared_domain_type_are_never_universal() -> None:
    benign_paths = {
        item["path"] for item in LABELS["benign_lookalikes"]
    }
    findings = [
        item for item in _result()["findings"]
        if item["source_evidence"]["path"] in benign_paths
    ]

    assert not findings, "a labeled benign lookalike became a semantic result"
    assert not any(item["class"] == CLASS_UNIVERSAL for item in findings)


def test_fixture_policy_uses_exact_paths_and_required_types() -> None:
    policy = CONFIG["semantic_policy"]
    assert policy["version"] == 1
    assert policy["domain_types"] and policy["operations"]
    for entry in (*policy["domain_types"], *policy["operations"]):
        assert entry["paths"]
        assert all(not set(path) & set("*?[]") for path in entry["paths"]), entry
    for entry in policy["domain_types"]:
        assert entry["required_type"]


def test_semantics_has_no_formula_weight_or_repository_specific_calibration_branch() -> None:
    weighted_aspects = {
        aspect
        for aspects in CATEGORY_ASPECTS.values()
        for aspect in aspects
    }
    assert not any("semantic" in aspect for aspect in weighted_aspects)

    calibration_path = ROOT / "src" / "maintainability_audit" / "_calibration.py"
    tree = ast.parse(calibration_path.read_text(encoding="utf-8"))
    branch_text = "\n".join(
        ast.unparse(node)
        for node in ast.walk(tree)
        if isinstance(node, (ast.If, ast.IfExp, ast.Match))
    ).lower()
    for repository_specific in (
        "semantic", "domain_types", "orderstatus", "customerid", "semantic_ts",
    ):
        assert repository_specific not in branch_text

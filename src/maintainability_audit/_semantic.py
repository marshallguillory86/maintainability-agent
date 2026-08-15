"""Normalized semantic findings — ADR 003 option C, classified and bounded.

Every result carries exactly one class, and the class is the claim:

* ``universal`` — a type checker proved the fact; no repository meaning
  was consulted.
* ``policy`` — the repository's checked-in policy declared the intent
  and typed analysis established the violation; the finding names the
  policy entry so nobody mistakes configuration for a universal rule.
* ``candidate`` — structural evidence nominates a design review and
  proves nothing. Candidates are prompt-only: no gate, no score, no
  grade, no evidence status (invariant 4).

Determinism is the other half of the contract (invariant 1): identical
source, history window, analyzer versions and policy produce
byte-identical findings, which is why everything here is sorted and
nothing consults the clock, the network, or a model.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from ._semantic_ts import operation_sets

CLASS_UNIVERSAL = "universal"
CLASS_POLICY = "policy"
CLASS_CANDIDATE = "candidate"

RULE_VERSION = 1

# Type facts a checker states about assignability. TS2345 is an argument,
# TS2322 an assignment; both prove "a plain primitive where the declared
# type is required" without any repository-specific meaning.
_ASSIGNABILITY_CODES = {"TS2345", "TS2322"}
_PRIMITIVES = {"string", "number", "boolean"}

_CANDIDATE_MESSAGE = (
    "one operation-name set recurs across dispatch, capability and "
    "description roles. That is an observed symptom; the intended "
    "abstraction is not proven by this evidence. Review whether these "
    "operations should carry their own behavior and result types, and "
    "preserve operation-specific input and result types in any redesign."
)


def _universal_findings(type_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    findings = []
    for diagnostic in type_analysis.get("diagnostics") or []:
        actual = diagnostic.get("actual_type") or ""
        required = diagnostic.get("required_type") or ""
        if diagnostic.get("code") not in _ASSIGNABILITY_CODES:
            continue
        if actual not in _PRIMITIVES or required in _PRIMITIVES or not required:
            continue
        findings.append({
            "class": CLASS_UNIVERSAL,
            "rule_id": "ts-declared-type-bypassed",
            "rule_version": RULE_VERSION,
            "language": "TypeScript",
            "policy_entry": "",
            "source_evidence": {
                "path": diagnostic.get("path") or "",
                "line": diagnostic.get("line"),
                "column": diagnostic.get("column"),
                "symbol": diagnostic.get("symbol") or "",
                "actual_type": actual,
                "required_type": required,
                "diagnostic_code": diagnostic.get("code"),
                "message": diagnostic.get("message") or "",
            },
            "review_boundary": "",
            "message": (
                f"the compiler proves {actual} is passed where the declared "
                f"type {required} is required; route this call through the "
                "declared type"
            ),
        })
    return findings


def _boundary_violates(boundary: dict[str, Any], entry: dict[str, Any]) -> bool:
    """A policy entry's declared boundary, re-validating the raw primitive.

    The *re-validation* is the signal: the same primitive checked and
    converted at the named boundary. A bare primitive with no
    validation ritual is the universal rule's business or nobody's.
    """
    actual = boundary.get("actual_type") or ""
    return (
        boundary.get("path") in entry["paths"]
        and (not entry["symbol"] or boundary.get("symbol") == entry["symbol"])
        and boundary.get("boundary") == entry["boundary"]
        and actual in _PRIMITIVES
        and actual != entry["required_type"]
        and bool(boundary.get("validations"))
    )


def _policy_findings(
    type_analysis: dict[str, Any], policy: dict[str, Any],
) -> list[dict[str, Any]]:
    findings = []
    boundaries = type_analysis.get("typed_boundaries") or []
    for entry in policy.get("domain_types") or []:
        for boundary in boundaries:
            if not _boundary_violates(boundary, entry):
                continue
            actual = boundary.get("actual_type") or ""
            findings.append({
                "class": CLASS_POLICY,
                "rule_id": "ts-policy-boundary-revalidation",
                "rule_version": RULE_VERSION,
                "language": "TypeScript",
                "policy_entry": entry["name"],
                "source_evidence": {
                    "path": boundary.get("path"),
                    "line": boundary.get("line"),
                    "symbol": boundary.get("symbol") or "",
                    "parameter": boundary.get("parameter") or "",
                    "boundary": boundary.get("boundary") or "",
                    "actual_type": actual,
                    "required_type": entry["required_type"],
                    "validations": list(boundary.get("validations") or []),
                },
                "review_boundary": "",
                "message": (
                    f"checked-in policy {entry['name']!r} requires "
                    f"{entry['required_type']} at this {entry['boundary']} "
                    f"boundary; the code accepts {actual} and re-validates it "
                    "in place. This is the repository's declared intent, not "
                    "a universal rule"
                ),
            })
    return findings


def _review_boundary(path: str, policy: dict[str, Any] | None) -> str:
    for entry in (policy or {}).get("operations") or []:
        if path in entry["paths"]:
            contract = " / ".join(
                part for part in (entry["capability_type"], entry["operation_contract"]) if part
            )
            return f"{entry['name']}: {contract}" if contract else entry["name"]
    return path


def _candidate_findings(
    root: Path,
    policy: dict[str, Any] | None,
    history: Any,
) -> list[dict[str, Any]]:
    findings = []
    touches = {}
    for record in history or ():
        for changed in record.get("changed_paths") or []:
            touches[changed] = touches.get(changed, 0) + 1
    for observed in operation_sets(root):
        findings.append({
            "class": CLASS_CANDIDATE,
            "rule_id": "ts-repeated-operation-set",
            "rule_version": RULE_VERSION,
            "language": "TypeScript",
            "policy_entry": "",
            "source_evidence": {
                "path": observed["path"],
                "roles": observed["roles"],
                "operation_names": observed["operation_names"],
                "history_touches": touches.get(observed["path"], 0),
            },
            "review_boundary": _review_boundary(observed["path"], policy),
            "message": _CANDIDATE_MESSAGE,
        })
    return findings


def _coverage(
    type_analysis: dict[str, Any] | None,
    findings: list[dict[str, Any]],
    analyzer_versions: dict[str, str] | None,
) -> dict[str, Any]:
    if not type_analysis or type_analysis.get("status") != "available":
        return {
            "language": "TypeScript",
            "status": "unknown",
            "reason": (
                "no recorded type analysis and no local type checker: "
                "semantic coverage for TypeScript is unknown. Absence of "
                "analysis is not absence of findings."
            ),
        }
    counted = {name: 0 for name in (CLASS_UNIVERSAL, CLASS_POLICY, CLASS_CANDIDATE)}
    for finding in findings:
        counted[finding["class"]] += 1
    return {
        "language": "TypeScript",
        "status": "typed",
        "tool": type_analysis.get("tool") or "typescript",
        "version": type_analysis.get("version") or "",
        "analyzer_versions": dict(analyzer_versions or {}),
        "violations": counted,
    }


def semantic_findings(
    root: Path,
    *,
    policy: dict[str, Any] | None = None,
    type_analysis: dict[str, Any] | None = None,
    history: Any = None,
    analyzer_versions: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Every semantic result for `root`, classified, sorted, reproducible.

    Universal and policy findings exist only where typed analysis does —
    without it they are empty *and the coverage says unknown*, never
    "clean" (invariant 6). Candidates are read from the source text and
    survive missing type analysis, because they claim nothing a type
    would prove.
    """
    findings: list[dict[str, Any]] = []
    typed = bool(type_analysis) and type_analysis.get("status") == "available"
    if typed:
        findings.extend(_universal_findings(type_analysis))
        if policy is not None:
            findings.extend(_policy_findings(type_analysis, policy))
    findings.extend(_candidate_findings(Path(root), policy, history))
    findings.sort(key=lambda item: (
        item["class"], item["rule_id"], item["source_evidence"].get("path") or "",
        item["source_evidence"].get("line") or 0,
    ))
    return {
        "findings": findings,
        "coverage": _coverage(type_analysis if typed else None, findings, analyzer_versions),
    }

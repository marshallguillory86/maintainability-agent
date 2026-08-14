"""The report contract describes today. It may not describe yesterday.

``REPORT_SCHEMA_VERSION`` is 3. Stage 8 shipped. Java has a range
detector. Coverage is in the ``--analyzers`` report. ``CALIBRATION_C``
is 2.2658. A hostile audit found the contract page still showing
``schema_version`` 2, the 0.7 migration still saying Java scans zero
declarations and C stays 2.6279, and the tool inventory still saying
coverage is the missing concept.

This file is the class lint. The gates follow the constants in
``evidence.py`` / ``_calibration.py`` / ``_ranges.py``, so they lift
when the code moves and fail when the docs do not.
"""
from __future__ import annotations

import re
from pathlib import Path

from maintainability_audit._calibration import CALIBRATION_C
from maintainability_audit.evidence import REPORT_SCHEMA_VERSION

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"
CONTRACT = ROOT / "docs" / "report-contract.md"
MIGRATION = ROOT / "docs" / "migration-0.7.md"
INVENTORY = ROOT / "docs" / "tool-inventory.md"
STANDARD = ROOT / "docs" / "standard.md"


def _java_ranges_exist() -> bool:
    return "def java_declaration_ranges" in (PACKAGE / "_ranges.py").read_text(encoding="utf-8")


def test_report_contract_example_uses_the_shipped_schema_version() -> None:
    """The JSON example is what a reader copies. It has to be today's stamp."""
    text = CONTRACT.read_text(encoding="utf-8")
    assert f'"schema_version": {REPORT_SCHEMA_VERSION}' in text, (
        f"docs/report-contract.md example must stamp schema_version "
        f"{REPORT_SCHEMA_VERSION}"
    )
    stale = REPORT_SCHEMA_VERSION - 1
    assert f'"schema_version": {stale}' not in text, (
        f"docs/report-contract.md still shows schema_version {stale}"
    )


def test_report_contract_normalizer_policy_matches_the_code() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert f"version {REPORT_SCHEMA_VERSION} only" in text, (
        "compatibility policy must name the version evidence.py accepts"
    )
    assert "accepts version 2 only" not in text


def test_report_contract_documents_the_nullable_estimate() -> None:
    """Version 3 made the estimate and range nullable. The field table must say so."""
    section = CONTRACT.read_text(encoding="utf-8").split("## Schema version", 1)[1]
    estimate_row = next(
        line for line in section.splitlines()
        if re.match(r"\| `maintainability_estimate` \|", line)
    )
    range_row = next(
        line for line in section.splitlines()
        if re.match(r"\| `maintainability_range` \|", line)
    )
    for row, name in ((estimate_row, "estimate"), (range_row, "range")):
        assert "null" in row.lower(), (
            f"docs/report-contract.md {name} row does not mention null: {row}"
        )


def test_report_contract_does_not_leave_stage_8_open() -> None:
    text = CONTRACT.read_text(encoding="utf-8")
    assert not re.search(r"stages 8 and 9 remain", text, re.I)
    assert "will finish changing" not in STANDARD.read_text(encoding="utf-8")


def test_migration_does_not_claim_java_has_no_declaration_population() -> None:
    if not _java_ranges_exist():
        return
    text = MIGRATION.read_text(encoding="utf-8")
    offenders = [
        phrase
        for phrase in (
            "declarations_scanned` stayed at **0**",
            "therefore measures zero declarations",
        )
        if phrase in text
    ]
    assert not offenders, (
        "docs/migration-0.7.md still describes Java as having no "
        f"declaration population: {offenders}"
    )


def test_migration_does_not_claim_the_constant_is_still_the_0_7_value() -> None:
    """0.7.0 kept C at 2.6279. Naming that without the 3.6 move is the lie."""
    text = MIGRATION.read_text(encoding="utf-8")
    if "2.6279" not in text:
        return
    assert f"{CALIBRATION_C}" in text or "2.2658" in text, (
        "docs/migration-0.7.md quotes 2.6279 without the current constant"
    )
    assert "stays at 2.6279" not in text


def test_tool_inventory_does_not_call_coverage_missing() -> None:
    text = INVENTORY.read_text(encoding="utf-8")
    assert "Coverage is the missing concept" not in text
    assert "needs its own decision record before any code moves" not in text

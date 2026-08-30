"""Shared fixtures for the scoring tests.

Extracted when `test_scoring_calibration.py` crossed the 500-line file
gate and split into scale tests and rubric tests. Both halves build the
same shapes — a valid integer summary, a history block, a score through
the public entry point — and duplicating them would let the two files
drift into testing subtly different repositories.
"""

from __future__ import annotations

from typing import Any

from maintainability_audit._pressures import _weighted_rate
from maintainability_audit.evidence import (
    REPORT_SCHEMA_VERSION,
    SCHEMA_VERSION_KEY,
)
from maintainability_audit.scoring import score_report as _score_report


def _band_pressures_from_counts(counts: dict[str, Any]) -> dict[str, float]:
    """The four band fields the old count-rate fallback would have produced.

    Live scans store these; hand-built fixtures used to omit them and lean
    on the fallback. After P3 priced a withheld band at SEVERE, a bandless
    fixture would score as unverified. Filling the fields with the same
    number the fallback computed keeps calibration assertions still.
    """

    def rate(failures: str, warnings: str, population: str) -> float:
        value = _weighted_rate(
            float(counts.get(failures, 0)),
            float(counts.get(warnings, 0)),
            float(counts.get(population, 0)),
        )
        return 0.0 if value is None else value

    return {
        "file_band_pressure": rate(
            "file_failures", "file_warnings", "files_scanned"
        ),
        "declaration_band_pressure": rate(
            "function_failures", "function_warnings", "declarations_scanned"
        ),
        "production_file_band_pressure": rate(
            "production_file_failures",
            "production_file_warnings",
            "production_files_scanned",
        ),
        "production_declaration_band_pressure": rate(
            "production_function_failures",
            "production_function_warnings",
            "production_declarations_scanned",
        ),
    }


def score_report(report: dict[str, Any]) -> dict[str, Any]:
    """Score through the shipped entry point, stamping the schema version."""
    return _score_report({SCHEMA_VERSION_KEY: REPORT_SCHEMA_VERSION, **report})


def summary(files: int, decls: int, **overrides: int) -> dict[str, Any]:
    base: dict[str, Any] = {
        "files_scanned": files,
        "declarations_scanned": decls,
        "production_files_scanned": files,
        "production_declarations_scanned": decls,
        "file_warnings": 0,
        "file_failures": 0,
        "function_warnings": 0,
        "function_failures": 0,
        "production_file_warnings": 0,
        "production_file_failures": 0,
        "production_function_warnings": 0,
        "production_function_failures": 0,
        "duplicate_blocks": 0,
        "risk_findings": 0,
        "hard_gate_failures": 0,
        "production_hard_gate_failures": 0,
        # A fixture wanting a grade claims a full read; Unknown withholds one.
        "unread_source_files": 0,
        "read_source_files": files,
        # ...and that everything it read could be parsed.
        "undetected_declaration_files": 0,
    }
    base.update(overrides)
    for key, value in _band_pressures_from_counts(base).items():
        if key not in overrides:
            base[key] = value
    return base


def score(files: int, decls: int, **overrides: int) -> dict:
    return score_report({"summary": summary(files, decls, **overrides)})


def _evidence_summary(**overrides: object) -> dict:
    full = summary(500, 1000)
    full.update({
        "test_file_count": 100, "production_declarations_scanned": 650,
        "dead_code_count": 0, "near_duplicate_count": 0, "idiom_concern_count": 0,
        "has_readme": True, "has_changelog": True, "has_docs_dir": True,
    })
    full.update(overrides)
    for key, value in _band_pressures_from_counts(full).items():
        if key not in overrides:
            full[key] = value
    return full


def _history(**overrides) -> dict:
    base = {
        "window": "12 months ago", "files_changed": 50, "hotspots": [],
        "change_coupling": [], "qualifying_hotspots": 0, "code_coupling_pairs": 0,
        "multi_commit_files": 10, "single_author_files": 1,
    }
    base.update(overrides)
    return base

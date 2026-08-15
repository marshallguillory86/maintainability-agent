"""ADR 008 invariant 13: measurement bands drive declaration pressure."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import (
    ExternalPressures,
    analyzer_pressures,
    analyzer_production_pressures,
    dimension_pressures,
)
from maintainability_audit.cli import audit_exit_code
from maintainability_audit.config import load_config
from maintainability_audit.evidence import Measured, SummaryEvidence
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report


def _config() -> dict:
    config = load_config(None)
    config["hard_gates"] = {
        "require_readme": True,
        "require_test_command": False,
        "require_clean_worktree": False,
        "fail_on_duplicate_blocks": False,
        "fail_on_file_failures": False,
        "fail_on_function_failures": True,
    }
    return config


def _function_source(name: str, complexity: int) -> str:
    branches = "\n".join(
        f"    if value == {branch}: return {branch}"
        for branch in range(complexity - 1)
    )
    return f"def {name}(value):\n{branches}\n    return -1\n"


def _population(root: Path, complexity: int) -> Path:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# Band pressure fixture\n", encoding="utf-8")
    for index in range(40):
        (root / f"module_{index}.py").write_text(
            _function_source(f"work_{index}", complexity),
            encoding="utf-8",
        )
    return root


def _measurements(complexity: int) -> list[Measurement]:
    """The same values the built-in Python detector observes in the fixture."""
    return [
        Measurement(
            concept=concept,
            unit=f"module_{index}.py::work_{index}",
            value=float(value),
            tool="recorded-analyzer",
            path=f"module_{index}.py",
        )
        for index in range(40)
        for concept, value in (
            ("cyclomatic_complexity", complexity),
            ("declaration_lines", complexity + 1),
            ("cognitive_complexity", complexity - 1),
        )
    ]


def _built_in_report(tmp_path: Path, complexity: int) -> dict:
    report = build_report(_population(tmp_path, complexity), _config())
    assert report["summary"]["declarations_scanned"] == 40
    assert report["summary"]["function_failures"] == 40
    return report


def _reported_declaration_pressure(report: dict) -> float:
    pressure = report["score"]["dimensions"]["declarations"]
    assert pressure is not None
    return pressure


def test_adr_008_invariant_13_distinguishes_bands_in_the_built_in_path(
    tmp_path: Path,
) -> None:
    """Built-in CCN 16 and CCN 45 cannot collapse to one pressure."""
    built_in_16 = _built_in_report(tmp_path / "built-in-16", 16)
    built_in_45 = _built_in_report(tmp_path / "built-in-45", 45)

    assert _reported_declaration_pressure(built_in_16) < (
        _reported_declaration_pressure(built_in_45)
    ), "the built-in scorer flattened different bands into one failure rate"


def test_adr_008_invariant_13_distinguishes_bands_in_the_analyzer_path() -> None:
    """Analyzer CCN 16 and CCN 45 cannot collapse to one pressure."""
    thresholds = _config()["thresholds"]
    analyzer_16 = analyzer_pressures(_measurements(16), thresholds)["declarations"]
    analyzer_45 = analyzer_pressures(_measurements(45), thresholds)["declarations"]

    assert analyzer_16 is not None and analyzer_45 is not None
    assert analyzer_16 < analyzer_45, (
        "the analyzer scorer flattened different bands into one failure rate"
    )


@pytest.mark.parametrize("complexity", (16, 45))
def test_built_in_and_analyzer_values_use_one_formula(
    tmp_path: Path, complexity: int,
) -> None:
    """An analyzer is a drop-in evidence source, never a second scorer."""
    report = _built_in_report(tmp_path / f"same-values-{complexity}", complexity)
    thresholds = _config()["thresholds"]
    measurements = _measurements(complexity)
    external = ExternalPressures(
        all_code=analyzer_pressures(measurements, thresholds),
        production=analyzer_production_pressures(measurements, thresholds),
        measurements=tuple(measurements),
    )

    analyzer_scored = score_report(report, external)

    assert analyzer_scored["dimensions"]["declarations"] == pytest.approx(
        _reported_declaration_pressure(report)
    ), f"CCN {complexity}: identical values took different scoring formulas"


def test_hard_gate_exit_stays_binary_when_score_bands_differ(tmp_path: Path) -> None:
    """Bands aim remediation; threshold gates alone decide the exit code."""
    ccn_16 = _built_in_report(tmp_path / "gate-16", 16)
    ccn_45 = _built_in_report(tmp_path / "gate-45", 45)
    args = argparse.Namespace(fail_on_new=False, fail_on_gate=True)

    assert ccn_16["hard_gate_failures"] and ccn_45["hard_gate_failures"]
    assert audit_exit_code(args, ccn_16) == 1
    assert audit_exit_code(args, ccn_45) == 1


def test_empty_declaration_populations_are_unmeasured_not_clean() -> None:
    """No declarations means no pressure on either evidence path, never zero."""
    fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "fixture"))
    built_in = dimension_pressures(SummaryEvidence(**fields))["declarations"]
    analyzer = analyzer_pressures([], _config()["thresholds"])["declarations"]

    assert built_in is None, "the built-in path called an empty population clean"
    assert analyzer is None, "the analyzer path called an empty population clean"

"""Per-concept analyzer spread must reach the score interval — ADR 006 §4."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest
from _analyzer_fixtures import _clean_tree

from maintainability_audit._corroborate import combine
from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import ExternalPressures
from maintainability_audit.config import load_config
from maintainability_audit.evidence import normalize_report_evidence
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_evidence


@dataclass(frozen=True)
class RecordedPressures(ExternalPressures):
    """The scored pressure plus the tool readings whose spread supports it."""

    measurements: tuple[Measurement, ...] = ()


def _external(*readings: tuple[str, float]) -> RecordedPressures:
    measurements = tuple(
        Measurement(
            concept="cyclomatic_complexity",
            unit="src/app.py::work",
            value=value,
            tool=tool,
            path="src/app.py",
        )
        for tool, value in readings
    )
    return RecordedPressures(
        all_code={"declarations": 0.3},
        production={"declarations": 0.3},
        measurements=measurements,
    )


def _evidence(tmp_path: Path):
    root = _clean_tree(tmp_path / "spread")
    return normalize_report_evidence(build_report(root, load_config(None)))


def _width(score: dict) -> float:
    low, high = score["maintainability_range"]
    return high - low


def test_larger_analyzer_spread_strictly_widens_the_range(tmp_path: Path) -> None:
    """Same evidence and mean; only the independent tools' disagreement changes."""
    evidence = _evidence(tmp_path)
    agreed_pressures = _external(("lizard", 10.0), ("radon", 10.0))
    spread_pressures = _external(("lizard", 8.0), ("radon", 12.0))

    assert combine(list(agreed_pressures.measurements))[0].value == pytest.approx(10.0)
    assert combine(list(spread_pressures.measurements))[0].value == pytest.approx(10.0)

    agreed = score_evidence(evidence, agreed_pressures)
    spread = score_evidence(evidence, spread_pressures)

    assert agreed["maintainability_estimate"] == spread["maintainability_estimate"]
    for score in (agreed, spread):
        low, high = score["maintainability_range"]
        assert low <= score["maintainability_estimate"] <= high
    assert _width(spread) > _width(agreed), (
        "per-concept analyzer disagreement is displayed but does not widen the score range"
    )


def test_one_tool_is_not_treated_as_perfect_agreement(tmp_path: Path) -> None:
    """A lone convention has unknown spread, not the zero spread two tools established."""
    evidence = _evidence(tmp_path)
    agreed = score_evidence(
        evidence,
        _external(("lizard", 10.0), ("radon", 10.0)),
    )
    single = score_evidence(evidence, _external(("lizard", 10.0)))

    low, high = single["maintainability_range"]
    assert low <= single["maintainability_estimate"] <= high
    assert _width(single) > _width(agreed), (
        "one analyzer was priced as zero spread, indistinguishable from independent agreement"
    )

"""Where the analyzers' reading reaches the score — ADR 006 §1.

Split from `test_analyzer_bridge` when it passed this project's own
500-line limit. That file asks whether the bridge's arithmetic matches
the built-in path; this one asks what the estimate does with the answer.

They separate cleanly because they fail for different reasons. A broken
formula is a bridge defect; a correct formula that never reaches
`score_evidence` is a wiring defect, and this project has shipped both.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from test_analyzer_bridge import (
    _clean_tree,
    _complete_declaration_measurements,
    _rollup_with_analyzer_primary,
    thresholds,
)

__all__ = ["thresholds"]


def test_complete_analyzer_declaration_pressure_sets_the_point_estimate(
    tmp_path: Path,
    thresholds: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from maintainability_audit import report as report_module
    from maintainability_audit._analysis import Analysis
    from maintainability_audit._pressures import (
        ExternalPressures,
        analyzer_pressures,
        analyzer_production_pressures,
    )
    from maintainability_audit.config import load_config
    from maintainability_audit.evidence import normalize_report_evidence
    from maintainability_audit.report import build_report

    root = _clean_tree(tmp_path / "primary")
    config = load_config(None)
    measurements = _complete_declaration_measurements(thresholds)
    monkeypatch.setattr(
        report_module,
        "analyze",
        lambda _root, _config: Analysis(measurements=list(measurements)),
    )

    built_in = build_report(root, config)
    report = build_report(root, config, run_analyzers=True)
    external = ExternalPressures(
        all_code=analyzer_pressures(measurements, thresholds),
        production=analyzer_production_pressures(measurements, thresholds),
    )
    expected = _rollup_with_analyzer_primary(normalize_report_evidence(report), external)

    assert external.production["declarations"] is not None
    assert expected != built_in["score"]["maintainability_estimate"]
    assert report["score"]["maintainability_estimate"] == pytest.approx(expected)


def test_missing_or_incomplete_analyzer_pressure_keeps_the_built_in_dimension(
    tmp_path: Path,
    thresholds: dict,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from maintainability_audit import report as report_module
    from maintainability_audit._analysis import Analysis
    from maintainability_audit._metrics_types import Measurement
    from maintainability_audit._pressures import (
        analyzer_pressures,
        analyzer_production_pressures,
    )
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = _clean_tree(tmp_path / "fallback")
    config = load_config(None)
    incomplete = [
        Measurement(
            concept="cyclomatic_complexity",
            unit="m0.py::f",
            value=float(thresholds["max_complexity"] + 5),
            tool="lizard",
            path="m0.py",
        )
    ]
    monkeypatch.setattr(
        report_module,
        "analyze",
        lambda _root, _config: Analysis(measurements=list(incomplete)),
    )

    analyzers_off = build_report(root, config)
    incomplete_run = build_report(root, config, run_analyzers=True)

    assert analyzer_pressures(incomplete, thresholds)["declarations"] is None
    assert analyzer_production_pressures(incomplete, thresholds)["declarations"] is None
    assert incomplete_run["score"]["maintainability_estimate"] == (
        analyzers_off["score"]["maintainability_estimate"]
    ), "None means fall back to built-in evidence; it is not a zero pressure"


def test_a_disagreeing_second_source_widens_the_interval(tmp_path: Path) -> None:
    """Analyzer evidence sets the point; the built-in fallback shows uncertainty."""
    from maintainability_audit._pressures import ExternalPressures
    from maintainability_audit.config import load_config
    from maintainability_audit.evidence import normalize_report_evidence
    from maintainability_audit.report import build_report
    from maintainability_audit.scoring import score_evidence

    root = _clean_tree(tmp_path / "r")
    evidence = normalize_report_evidence(build_report(root, load_config(None)))
    external = ExternalPressures(
        all_code={"declarations": 0.3}, production={"declarations": 0.3}
    )

    agreed = score_evidence(evidence)
    disagreed = score_evidence(evidence, external)
    expected = _rollup_with_analyzer_primary(evidence, external)

    assert agreed["maintainability_range"][0] == agreed["maintainability_range"][1]
    assert disagreed["maintainability_range"][0] < agreed["maintainability_range"][0]
    assert disagreed["maintainability_estimate"] == pytest.approx(expected)
    assert disagreed["maintainability_estimate"] != agreed["maintainability_estimate"]
    assert agreed["maintainability_estimate"] in disagreed["maintainability_range"]
    assert disagreed["maintainability_estimate"] in disagreed["maintainability_range"], (
        "disagreement must expose both readings, not average them into a third number"
    )


def test_a_second_source_must_reach_the_pressure_the_score_reads() -> None:
    """The defect the first attempt at this had.

    `declaration_size` is the only route the declarations dimension takes
    into the score, and it reads the *production* pressure rather than
    the general one — so substituting into `dimension_pressures` alone
    changed nothing, and the interval stayed collapsed however far the
    two sources were pushed apart. This asserts the substitution lands
    where the score actually looks.
    """
    from maintainability_audit._aspects import aspect_scores
    from maintainability_audit._pressures import dimension_pressures, normalize
    from maintainability_audit.evidence import (
        HistoryEvidence,
        Measured,
        NormalizedEvidence,
        SummaryEvidence,
        Unknown,
    )

    fields = dict.fromkeys(SummaryEvidence.__dataclass_fields__, Measured(0, "t"))
    fields.update(
        declarations_scanned=Measured(200, "t"),
        production_declarations_scanned=Measured(200, "t"),
        files_scanned=Measured(50, "t"),
        production_files_scanned=Measured(50, "t"),
    )
    history = HistoryEvidence(**dict.fromkeys(
        HistoryEvidence.__dataclass_fields__, Unknown("no history", "t")))
    evidence = NormalizedEvidence(
        schema_version=3, summary=SummaryEvidence(**fields), history=history)
    normalized = normalize(dimension_pressures(evidence.summary))

    baseline = aspect_scores(evidence, normalized)["declaration_size"]
    overridden = aspect_scores(evidence, normalized, {"declarations": 3.0})["declaration_size"]

    assert overridden != baseline, "a production override that changes nothing is not an override"


def test_each_population_is_substituted_from_its_own_reading(tmp_path: Path) -> None:
    """The production slot must not be filled from the all-code number.

    It was, for as long as the bridge could not tell test code from
    production code — one dict went into both slots, so production
    aspects were charged for the state of the test suite. Pairing the two
    readings in `ExternalPressures` makes the mix-up unrepresentable; this
    checks the substitution honours the pairing rather than reading one
    field twice.
    """
    import subprocess

    from maintainability_audit._pressures import ExternalPressures
    from maintainability_audit.config import load_config
    from maintainability_audit.evidence import normalize_report_evidence
    from maintainability_audit.report import build_report
    from maintainability_audit.scoring import score_evidence

    root = tmp_path / "r"
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(40):
        (root / f"m{i}.py").write_text(
            "\n".join(f"def f{i}_{j}():\n    return {j}\n" for j in range(4)), encoding="utf-8")
    evidence = normalize_report_evidence(build_report(root, load_config(None)))

    # Identical all-code readings; the production reading is the only
    # thing that differs. A clean production reading must not be
    # overridden by the pessimistic all-code one.
    clean = score_evidence(evidence, ExternalPressures(
        all_code={"declarations": 0.4}, production={"declarations": 0.0}))
    dire = score_evidence(evidence, ExternalPressures(
        all_code={"declarations": 0.4}, production={"declarations": 0.4}))

    assert clean["maintainability_range"][0] > dire["maintainability_range"][0], (
        "the production slot is being filled from the all-code reading"
    )

"""Fixtures shared by the analyzer-bridge suites.

One home for the tree builder, the threshold fixture and the rollup
helper that `test_analyzer_bridge`, `test_analyzer_scoring_path` and
`test_analyzer_spread_range` all use. Extracted when the bridge file
crossed the 500-line gate this tool enforces on everyone else — the
same reason and the same shape as `_mcp_fixtures`, and for the same
reason it is a module rather than three copies: a split paid for with
copied helpers just moves the debt into the duplicate-block gate.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit.config import DEFAULT_CONFIG


@pytest.fixture
def thresholds() -> dict:
    return dict(DEFAULT_CONFIG["thresholds"])


def _clean_tree(root: Path) -> Path:
    import subprocess

    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# r\n", encoding="utf-8")
    for i in range(40):
        (root / f"m{i}.py").write_text(
            "\n".join(f"def f{i}_{j}():\n    return {j}\n" for j in range(4)),
            encoding="utf-8",
        )
    # Committed, so this is a repository with history rather than one
    # with an unborn HEAD. Before D37 the difference was invisible: a
    # `git log` against an unborn HEAD failed, the failure was swallowed
    # into an empty result, and the history section was computed from
    # zeros — so a tree that had never been committed scored as though
    # its history had been measured and found quiet. Tests asserting a
    # collapsed range were resting on that fabricated completeness.
    subprocess.run(["git", "-C", str(root), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(root), "-c", "user.email=t@t", "-c", "user.name=t",
         "commit", "-qm", "tree"], check=True)
    return root


def _complete_declaration_measurements(thresholds: dict, path: str = "m0.py") -> list:
    from maintainability_audit._metrics_types import Measurement

    return [
        Measurement(concept=concept, unit=f"{path}::f{i}", value=float(value),
                    tool="lizard", path=path)
        for i in range(40)
        for concept, value in (
            ("cyclomatic_complexity", thresholds["max_complexity"] + 5),
            ("declaration_lines", 1),
            ("cognitive_complexity", 0),
        )
    ]


def _rollup_with_analyzer_primary(evidence, external) -> float:
    from maintainability_audit._aspects import (
        aspect_scores,
        is_untested,
        not_applicable_aspects,
    )
    from maintainability_audit._formula import overall_from_aspects
    from maintainability_audit._pressures import (
        dimension_pressures,
        normalize,
        normalize_production,
    )

    pressures = dict(dimension_pressures(evidence.summary))
    for dimension, value in external.all_code.items():
        if value is not None:
            pressures[dimension] = value
    production = dict(normalize_production(evidence.summary))
    for dimension, value in external.production.items():
        if value is not None:
            production[dimension] = normalize({dimension: value})[dimension]
    aspects = aspect_scores(evidence, normalize(pressures), production)
    overall, _ = overall_from_aspects(
        aspects,
        untested=is_untested(evidence.summary),
        not_applicable=not_applicable_aspects(evidence),
    )
    return overall


def _summary_from_metrics(functions, thresholds):
    """The built-in side of a drop-in comparison, built by production code.

    The counts-only construction these tests used became the wrong half
    of the comparison when 3.2 wired the band matrix: the live summary
    now stores banded per-unit pressures, and comparing the analyzer's
    banded value against a hand-built count rate is two formulas again —
    the exact regression this file documents.
    """
    from maintainability_audit.evidence import Measured, SummaryEvidence, Unknown
    from maintainability_audit.report import report_summary

    summary = report_summary(
        files=[], file_metrics=[], function_metrics=functions,
        duplicate_count=0, risk_count=0, gate_count=0, thresholds=thresholds,
    )
    fields = {
        name: (Measured(summary[name], "t") if summary.get(name) is not None
               else Unknown("not in fixture", f"summary.{name}"))
        for name in SummaryEvidence.__dataclass_fields__
    }
    return SummaryEvidence(**fields)


def _metric(complexity, lines=1, cognitive=0, name="f", status="ok"):
    from maintainability_audit._metrics_types import FunctionMetric

    return FunctionMetric(path="a.py", name=name, start_line=1, lines=lines,
                          complexity=complexity, status=status, cognitive=cognitive)

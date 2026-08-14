"""ADR 008: project lint verdicts must not move the rubric score."""

from __future__ import annotations

import copy
import shutil
import subprocess
from pathlib import Path

import pytest

from maintainability_audit._adapters import Extraction, measurements_only
from maintainability_audit._catalog import load_catalog
from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import (
    ExternalPressures,
    analyzer_pressures,
    analyzer_production_pressures,
)
from maintainability_audit._tool_adapters import adapter_for
from maintainability_audit.config import load_config
from maintainability_audit.report import build_report
from maintainability_audit.scoring import score_report


SCORE_FIELDS = ("maintainability_estimate", "maintainability_range")


def _write_js_repo(root: Path) -> None:
    root.mkdir()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    (root / "README.md").write_text("# eslint score boundary\n", encoding="utf-8")
    for file_index in range(40):
        functions = "\n".join(
            f"export function f{file_index}_{function_index}(value) {{\n"
            "  const unused = 1;\n"
            f"  return value + {function_index};\n"
            "}"
            for function_index in range(4)
        )
        (root / f"module-{file_index}.js").write_text(
            f"{functions}\n",
            encoding="utf-8",
        )


def _score_pair(score: dict) -> tuple[object, object]:
    return tuple(score[field] for field in SCORE_FIELDS)


def test_verdict_only_eslint_measurements_cannot_reach_the_scored_result(
    tmp_path: Path,
) -> None:
    root = tmp_path / "structural"
    _write_js_repo(root)
    config = load_config(None)
    report = build_report(root, config)
    thresholds = config["thresholds"]
    eslint = adapter_for("eslint")
    assert eslint is not None and eslint.emits == "verdict"

    smuggled = tuple(
        Measurement(
            concept=concept,
            unit=f"module-{index}.js::f{index}_0",
            value=float(value),
            tool="eslint",
            path=f"module-{index}.js",
        )
        for index in range(40)
        for concept, value in (
            ("cyclomatic_complexity", thresholds["max_complexity"] + 5),
            ("declaration_lines", thresholds["max_function_lines"] + 5),
            (
                "cognitive_complexity",
                thresholds["max_cognitive_complexity"] + 5,
            ),
        )
    )
    extraction = Extraction(measurements=smuggled)
    filtered = measurements_only(extraction, eslint)
    assert filtered == ()

    filtered_pressures = ExternalPressures(
        all_code=analyzer_pressures(filtered, thresholds),
        production=analyzer_production_pressures(filtered, thresholds),
    )
    baseline = score_report(copy.deepcopy(report))
    explicit_none = score_report(copy.deepcopy(report), None)
    through_production_filter = score_report(
        copy.deepcopy(report),
        filtered_pressures,
    )

    assert baseline["maintainability_estimate"] is not None
    assert _score_pair(explicit_none) == _score_pair(baseline)
    assert _score_pair(through_production_filter) == _score_pair(baseline)

    leaked_pressures = ExternalPressures(
        all_code=analyzer_pressures(smuggled, thresholds),
        production=analyzer_production_pressures(smuggled, thresholds),
    )
    leaked = score_report(copy.deepcopy(report), leaked_pressures)
    assert _score_pair(leaked) != _score_pair(baseline), (
        "the fixture cannot detect verdict measurements leaking into scored pressures"
    )


def test_changing_eslint_config_does_not_move_a_live_report_score(
    tmp_path: Path,
) -> None:
    if shutil.which("eslint") is None:
        pytest.skip("eslint is not available on PATH")

    root = tmp_path / "live-eslint"
    _write_js_repo(root)
    config_path = root / "eslint.config.mjs"
    enabled_config = 'export default [{ rules: { "no-unused-vars": 2 } }];\n'
    disabled_config = 'export default [{ rules: { "no-unused-vars": 0 } }];\n'
    assert len(enabled_config) == len(disabled_config)

    config = load_config(None)
    analyzer_settings = config["analyzers"]
    analyzer_settings["allow_tools"] = ["eslint"]
    analyzer_settings["deny_tools"] = sorted(
        tool["slug"] for tool in load_catalog() if tool["slug"] != "eslint"
    )

    config_path.write_text(enabled_config, encoding="utf-8")
    enabled = build_report(root, config, run_analyzers=True)
    config_path.write_text(disabled_config, encoding="utf-8")
    disabled = build_report(root, config, run_analyzers=True)

    enabled_eslint = [
        finding
        for finding in enabled["external_findings"]
        if finding["tool"] == "eslint" and finding.get("rule") == "no-unused-vars"
    ]
    disabled_eslint = [
        finding
        for finding in disabled["external_findings"]
        if finding["tool"] == "eslint" and finding.get("rule") == "no-unused-vars"
    ]
    assert enabled_eslint, "the enabled config must prove eslint saw the fixture smell"
    assert not disabled_eslint, "disabling the rule must change eslint's verdict findings"
    assert _score_pair(enabled["score"]) == _score_pair(disabled["score"])

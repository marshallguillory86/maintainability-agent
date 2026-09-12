"""An undersized repository gets work orders, never score-derived rate advice."""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from maintainability_audit._formula import ROOT_POPULATIONS, population_floor
from maintainability_audit.config import load_config
from maintainability_audit.prompts import render_ai_prompt
from maintainability_audit.report import build_report

pytestmark = pytest.mark.usefixtures("real_population_floors")


def _undersized_report(root: Path, tree_number: int) -> dict:
    """Build a real repository below every shipped root population floor."""
    root.mkdir()
    (root / "README.md").write_text("# underfloor\n", encoding="utf-8")
    config = load_config(None)
    oversized_body = "".join(
        f"    value = {line}\n"
        for line in range(int(config["thresholds"]["max_file_lines"]) + 1)
    )
    (root / f"module_{tree_number}.py").write_text(
        f"def value_{tree_number}():\n{oversized_body}    return value\n", encoding="utf-8")
    report = build_report(root, config)
    summary = report["summary"]
    floors = {population: population_floor(population) for population in ROOT_POPULATIONS}
    assert all(floor is not None for floor in floors.values())
    assert all(summary[population] < floor for population, floor in floors.items())
    assert report["score"]["maintainability_estimate"] is None
    return report


def test_unscored_prompt_has_no_dimension_multiple_or_typical_comparison(tmp_path: Path) -> None:
    """D163: a withheld overall cannot authorize rate-based remediation."""
    prompt = render_ai_prompt(_undersized_report(tmp_path / "first", 1))

    assert "worse than typical" not in prompt
    assert not re.search(r"\b\d+(?:\.\d+)?x\b", prompt)


def test_unscored_prompt_leads_with_work_order_before_summary_or_grade(tmp_path: Path) -> None:
    """The second generated underfloor tree keeps the ordering contract broad."""
    prompt = render_ai_prompt(_undersized_report(tmp_path / "second", 2))
    work_order = prompt.index("Work in this order")
    summary = prompt.index("Audit summary")
    grade = prompt.index("Verified grade")

    assert work_order < summary
    assert work_order < grade

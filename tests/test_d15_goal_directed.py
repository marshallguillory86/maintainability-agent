"""D15 as originally written: goal-directed, inventory-aware selection.

The Codex audit on d5b1c50 (H1) found the register's D15 entry was
rewritten at close: the original requirement — selection consults the
same language inventory and concern→concept mapping the coverage
section uses, covers the repository's languages with the verified
tools available, and names what to install to close the gap — was
replaced by the composition pins. This file proves the ORIGINAL
Required clause at the production seam; the composition tests remain
in test_d15_composition.py. Both together close D15 honestly.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from maintainability_audit.config import load_config
from maintainability_audit.report import build_report


def _mixed_repo(root: Path) -> Path:
    root.mkdir(parents=True)
    (root / "src").mkdir()
    (root / "src" / "App.java").write_text(
        "package fixture;\npublic class App { int x; }\n", encoding="utf-8",
    )
    (root / "web.js").write_text("const x = 1;\n", encoding="utf-8")
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    return root


def _config(**analyzers: Any) -> dict[str, Any]:
    config = load_config(None)
    config["analyzers"].update({
        "run": True, "depth": "moderate", "license_policy": "copyleft-weak",
        **analyzers,
    })
    return config


def _rows(report: dict[str, Any]) -> dict[str, tuple[str, dict[str, Any]]]:
    return {
        row["tool"]: (outcome, row)
        for outcome, rows in report["analyzer_coverage"]["by_outcome"].items()
        for row in rows
        if row.get("tier") != "built-in"
    }


def test_a_run_engages_tools_by_the_trees_languages(tmp_path: Path) -> None:
    """Selection consults the inventory: language-mismatched tools do not run."""
    report = build_report(_mixed_repo(tmp_path / "mixed"), _config(), run_analyzers=True)
    rows = _rows(report)

    # Java tools are engaged for the Java half (ran or an install gap,
    # never language-inapplicable)...
    for slug in ("pmd", "checkstyle"):
        outcome, row = rows[slug]
        assert outcome != "not-applicable" or "build" in (row.get("detail") or ""), (
            f"{slug} was language-gated off a tree that contains Java: {row}"
        )
    # ...while Python-only tools are stated as inapplicable to this
    # tree, with the reason naming the mismatch — the inventory drove
    # the decision, not a hidden filter.
    python_only = [s for s in ("radon", "vulture", "pydocstyle") if s in rows]
    assert python_only, "no python-only tool was even selected to decide about"
    for slug in python_only:
        outcome, row = rows[slug]
        assert outcome == "not-applicable"
        assert "this tree is" in (row.get("detail") or "")


def test_the_run_names_installs_that_close_language_gaps(tmp_path: Path) -> None:
    """Unmeasured concerns come with the installs that would close them."""
    report = build_report(_mixed_repo(tmp_path / "gaps"), _config(), run_analyzers=True)
    order = {item["tool"]: item for item in report["environment_work_order"]}

    # The tree has JavaScript; eslint is selected, uninstalled here,
    # and the work order names it with the concepts installing it
    # restores — the before-or-with-results install naming D15 demands.
    assert "eslint" in order, "the JS gap produced no install remedy"
    assert order["eslint"]["install"]
    assert order["eslint"]["concepts"]

    gaps = report["analyzer_coverage"].get("gaps_by_language") or {}
    assert gaps, "the coverage section states no per-language gaps to close"


def test_concern_selection_uses_the_same_mapping_as_coverage(tmp_path: Path) -> None:
    """A concern-narrowed pool engages exactly the tools that serve it."""
    report = build_report(
        _mixed_repo(tmp_path / "concern"),
        _config(concerns=["complexity"]),
        run_analyzers=True,
    )
    rows = _rows(report)

    assert "pmd" in rows, "the complexity pool dropped the complexity tool"
    assert "checkstyle" not in rows, (
        "a style/documentation tool entered a complexity-only pool"
    )

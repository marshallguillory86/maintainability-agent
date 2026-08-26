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

import pytest

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


def test_inventory_deselects_before_any_probe_or_spawn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Selection consults the inventory: a language-mismatched tool is
    never probed and never spawned — decided against, not attempted and
    rejected (Codex audit H1: the earlier version of this test pinned
    the attempted-then-rejected shape, which was the original defect)."""
    from maintainability_audit import _runner

    probed: list[str] = []
    real_probe = _runner._probe

    def recording_probe(slug: str, argv: tuple[str, ...]):
        probed.append(slug)
        return real_probe(slug, argv)

    monkeypatch.setattr(_runner, "_probe", recording_probe)

    report = build_report(_mixed_repo(tmp_path / "mixed"), _config(), run_analyzers=True)
    rows = _rows(report)

    python_only = [s for s in ("radon", "vulture", "pydocstyle") if s in rows]
    assert python_only, "no python-only tool was even in the pool to decide about"
    for slug in python_only:
        assert slug not in probed, (
            f"{slug} was probed despite the inventory: selection did not "
            "consult the language inventory, the attempt did"
        )
        outcome, row = rows[slug]
        assert outcome == "not-applicable"
        assert "this tree is" in (row.get("detail") or "")

    # The deselection is stated as a SELECTION fact, not only a
    # coverage outcome.
    filtered = report["analyzer_coverage"]["selection"]["inventory_filtered"]
    assert set(python_only) <= set(filtered)

    # Java tools are engaged for the Java half (ran or an install gap,
    # never language-inapplicable).
    for slug in ("pmd", "checkstyle"):
        outcome, row = rows[slug]
        assert outcome != "not-applicable" or "build" in (row.get("detail") or ""), (
            f"{slug} was language-gated off a tree that contains Java: {row}"
        )
        assert slug not in filtered


def test_the_run_names_installs_that_close_language_gaps(tmp_path: Path) -> None:
    """Unmeasured concerns come with the installs that would close them.

    And only those that would. This asserted `eslint` until Decision 9:
    the tree has JavaScript, eslint was selected and uninstalled, so the
    work order named it. Installing it would no longer help — selection
    refuses it because honouring an eslint flat config means executing a
    JavaScript program from the audited tree — and a remedy that does
    not close the gap it names is worse than no remedy, because someone
    follows it (D39).
    """
    report = build_report(_mixed_repo(tmp_path / "gaps"), _config(), run_analyzers=True)
    order = {item["tool"]: item for item in report["environment_work_order"]}

    assert order, "no install remedy was named for any gap"
    for item in order.values():
        assert item["install"] and item["concepts"]

    assert "eslint" not in order, (
        "the work order tells the reader to install a tool this agent "
        "refuses to run; following it would close nothing"
    )
    refused = {
        row["tool"]
        for rows in report["analyzer_coverage"]["by_outcome"].values()
        for row in rows
        if row.get("tool") == "eslint"
    }
    assert refused == {"eslint"}, "eslint vanished from coverage instead of being stated"

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


def test_selection_composes_the_runnable_set_before_the_run_loop() -> None:
    """The old shape cannot return: analyze iterates a composed set.

    The defect D15 named was resolving the whole policy pool and then
    marking mismatches inapplicable per tool. This is the structural
    falsifier: `analyze` must hand `_cover_one` a `Selected` composed
    by `select_runnable`, so a tool the inventory ruled out cannot
    reach the run path at all. Reverting to a raw-pool loop fails here.
    """
    import ast
    import inspect

    from maintainability_audit import _analysis

    source = inspect.getsource(_analysis)
    tree = ast.parse(source)
    functions = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
    }

    analyze_calls = {
        node.func.id
        for node in ast.walk(functions["analyze"])
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert "select_runnable" in analyze_calls, (
        "analyze no longer composes the runnable set; it resolves the "
        "pool and decides applicability per tool — the D15 defect"
    )

    first_parameter = functions["_cover_one"].args.args[0]
    assert getattr(first_parameter.annotation, "id", None) == "Selected", (
        "_cover_one takes a raw catalog tool again, so applicability "
        "decisions moved back inside the run path"
    )


def test_the_runnable_set_is_minimal_for_the_trees_languages(
    tmp_path: Path,
) -> None:
    """Every selected tool can produce evidence about a language present."""
    root = _mixed_repo(tmp_path / "minimal")
    report = build_report(root, _config(), run_analyzers=True)

    coverage = report["analyzer_coverage"]
    runnable = set(coverage["selection"]["runnable"])
    filtered = set(coverage["selection"]["inventory_filtered"])
    assert runnable and not (runnable & filtered), (
        "the composed set and the deselected set overlap"
    )

    rows = {
        row["tool"]: (outcome, row)
        for outcome, entries in coverage["by_outcome"].items()
        for row in entries
        if row.get("tier") != "built-in"
    }
    # The real key, and it must not be empty: an earlier version of
    # this test read a `languages` key the coverage document never
    # emitted, then passed itself when the resulting set came back
    # empty — a falsifier that could not fail (Codex round four, M2).
    present = {name.lower() for name in coverage["by_language"]}
    assert present, "the fixture produced no languages, so this proves nothing"
    assert "java" in present and "javascript" in present

    for slug in runnable:
        outcome, row = rows[slug]
        assert outcome != "no-adapter", (
            f"{slug} is called runnable but has no adapter to invoke"
        )
        reads = {name.lower() for name in (row.get("languages") or [])}
        artifact_read = slug == "spotbugs"
        assert not reads or artifact_read or (reads & present), (
            f"{slug} is in the runnable set but reads none of the "
            f"languages this tree contains ({sorted(present)})"
        )


def test_a_catalogued_tool_without_an_adapter_is_not_called_runnable(
    tmp_path: Path,
) -> None:
    """M2: `runnable` is a claim the run must be able to keep.

    A tool the inventory wants but this project cannot invoke was
    listed under `selection.runnable` while producing a no-adapter row
    and never being probed. Selection now routes it out of the set.
    """
    from maintainability_audit._catalog import load_catalog

    unadapted = next(
        tool["slug"] for tool in load_catalog()
        if tool["adapter"] != "implemented" and "java" in tool["languages"]
    )
    report = build_report(
        _mixed_repo(tmp_path / "unadapted"),
        _config(allow_tools=[unadapted]),
        run_analyzers=True,
    )
    coverage = report["analyzer_coverage"]
    rows = {
        row["tool"]: (outcome, row)
        for outcome, entries in coverage["by_outcome"].items()
        for row in entries
    }

    assert unadapted in rows, "the unadapted tool vanished instead of being stated"
    assert rows[unadapted][0] == "no-adapter"
    assert unadapted not in coverage["selection"]["runnable"], (
        f"{unadapted} has no adapter but was reported as runnable"
    )

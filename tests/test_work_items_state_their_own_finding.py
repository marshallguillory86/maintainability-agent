"""A work item states the finding it is about, and nothing the audit did not measure.

D164–D166 and D169, found running a Java repository through the chat door
for a demo. Each is the same claim failing in a different field of the
item: **what a work item says is a fact about that item** — its kind,
the limit it breaks, the rule that matched, the command that re-checks
it, and the order it sits in.

Populations are derived, never typed: declarations come from scanning
every grammar fixture on disk, finding classes from `CLASS_RISK_EFFORT`,
risk rules from `DEFAULT_CONFIG`, and each sweep asserts it is not empty.
"""
from __future__ import annotations

import copy
import shlex
import shutil
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / "tests" / "fixtures" / "grammar"
DEMO = ROOT / "examples" / "demo"


def _grammar_tree(tmp_path: Path) -> Path:
    """Every grammar fixture on disk, copied into one tree."""
    fixtures = sorted(GRAMMAR.rglob("constructs.*"))
    assert fixtures, f"no grammar fixtures under {GRAMMAR}; this sweep would pass vacuously"
    tree = tmp_path / "tree"
    tree.mkdir()
    for fixture in fixtures:
        shutil.copy(fixture, tree / fixture.name)
    return tree


def _failing_everything(config: dict[str, Any]) -> dict[str, Any]:
    """Thresholds every declaration breaks, so each one becomes a work item.

    The class and function budgets are deliberately different numbers. With
    both at 1, an item that printed the function budget as the class limit
    read identically and the check could not tell them apart — found by
    mutating exactly that.
    """
    config = copy.deepcopy(config)
    config["thresholds"].update({
        "max_function_lines": 3, "warn_function_lines": 2,
        "max_class_lines": 1, "warn_class_lines": 1,
        "max_complexity": 0, "warn_complexity": 0,
    })
    return config


def _declaration_items(tmp_path: Path) -> tuple[list[dict[str, Any]], dict[str, Any], dict[str, str]]:
    """Declaration items built through `build_report`, the production seam."""
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    config = _failing_everything(load_config(None))
    report = build_report(_grammar_tree(tmp_path), config, run_analyzers=False)
    kinds = {
        (hotspot["path"], hotspot["name"], hotspot["start_line"]): hotspot["kind"]
        for hotspot in report["function_hotspots"]
    }
    items = [item for item in report["work_order"]
             if item["finding_class"] == "oversized-declaration"]
    assert items, "no oversized-declaration items were produced; the sweep is empty"
    by_item = {}
    for item in items:
        name = item["title"].split(" in ", 1)[0]
        by_item[item["title"] + f":{item['line']}"] = kinds[(item["path"], name, item["line"])]
    return items, config["thresholds"], by_item


def test_every_declaration_item_names_the_limit_its_own_kind_is_graded_on(tmp_path) -> None:
    """D164: a class is given the class limit; a function each of its limits.

    The work order printed a 2876-line Java class as "currently 2876 lines,
    complexity 25" — a function's reading, against no limit at all, when a
    class is graded on length alone against `max_class_lines`.
    """
    items, thresholds, kinds = _declaration_items(tmp_path)
    assert "class" in set(kinds.values()), (
        "the grammar sweep produced no class declarations, so the class half "
        f"of this claim was never examined: kinds={sorted(set(kinds.values()))}"
    )
    assert set(kinds.values()) - {"class"}, "the sweep produced no non-class declarations"
    wrong = []
    for item in items:
        kind = kinds[item["title"] + f":{item['line']}"]
        target = item["target"]
        if kind == "class":
            if f"against the {thresholds['max_class_lines']}-line class limit" not in target \
                    or "complexity" in target:
                wrong.append((kind, item["title"], target))
        elif (f"lines against {thresholds['max_function_lines']}" not in target
              or "complexity" not in target
              or f"against {thresholds['max_complexity']}" not in target):
            wrong.append((kind, item["title"], target))
    assert not wrong, f"items that misstate their own kind or limit: {wrong[:5]}"


def test_the_in_loop_check_words_a_breach_as_the_work_order_does() -> None:
    """D164 on the second surface that prints a declaration target.

    `check_content` is the mid-edit check. Its docstring promises the audit's
    wording, and it kept a copy that printed a class's complexity against
    the function limit after the work order stopped doing so.
    """
    from maintainability_audit._in_loop import check_content
    from maintainability_audit.config import load_config

    fixtures = sorted(GRAMMAR.rglob("constructs.*"))
    assert fixtures, f"no grammar fixtures under {GRAMMAR}"
    config = _failing_everything(load_config(None))
    thresholds = config["thresholds"]
    classes = functions = 0
    wrong = []
    for fixture in fixtures:
        result = check_content(fixture.name, fixture.read_text(encoding="utf-8"), config)
        for finding in result.get("findings") or []:
            if finding.get("finding_class") != "oversized-declaration":
                continue
            target = finding["target"]
            if "-line class limit" in target:
                classes += 1
                if f"against the {thresholds['max_class_lines']}-line class limit" not in target \
                        or "complexity" in target:
                    wrong.append(target)
            else:
                functions += 1
                if f"lines against {thresholds['max_function_lines']}" not in target:
                    wrong.append(target)
    assert classes and functions, f"in-loop sweep examined classes={classes} functions={functions}"
    assert not wrong, f"in-loop targets that misstate the limit: {wrong[:5]}"


def test_no_work_item_rationale_sizes_the_change_it_asks_for(tmp_path) -> None:
    """D164: effort is declared per class in the standard, never claimed per item.

    "extracting one is bounded, local work" is the class's judgment beside
    its declared effort. Printed on an item it became a claim the audit
    never measured, and it was false for a class ten times its limit.
    """
    from maintainability_audit._work_order_weights import CLASS_RISK_EFFORT

    items, _, kinds = _declaration_items(tmp_path)
    classes = set(CLASS_RISK_EFFORT)
    assert classes, "CLASS_RISK_EFFORT is empty"
    sizing = [item for item in items if "bounded, local work" in item["rationale"]]
    assert not sizing, f"items whose Why sizes the change: {[i['title'] for i in sizing][:5]}"
    functions_called_classes = [
        item["title"] for item in items
        if kinds[item["title"] + f":{item['line']}"] == "class" and "function" in item["rationale"]
    ]
    assert not functions_called_classes, (
        f"class items whose Why calls them a function: {functions_called_classes[:5]}"
    )


def test_an_unpaired_item_does_not_size_the_test_it_asks_for(tmp_path) -> None:
    """D164, the second class carrying the same per-item sizing claim.

    Reads the rationale the item is *rendered* with: `work_order` falls back
    to the class weight when a builder sets none, so checking only the
    builder's own field passed on a tree where every unpaired item still
    printed "adding a characterization test is bounded, local work".
    """
    from maintainability_audit._work_order import _items_from_unpaired
    from maintainability_audit._work_order_weights import CLASS_RISK_EFFORT

    report = {"tdd_structure": {"unpaired_fail_band": [
        {"path": "Big.java", "name": "Big", "kind": "class", "line": 1, "lines": 1907},
    ]}}
    items = _items_from_unpaired(report)
    assert items, "the unpaired builder produced nothing"
    fallback = CLASS_RISK_EFFORT["unpaired-hotspot"].rationale
    rendered = [item.get("rationale") or fallback for item in items]
    assert all("bounded, local work" not in text for text in rendered), rendered


def _risk_findings() -> list[dict[str, Any]]:
    from maintainability_audit._config_defaults import DEFAULT_CONFIG

    names = [rule["name"] for rule in DEFAULT_CONFIG["risk_patterns"]]
    assert names, "DEFAULT_CONFIG ships no risk patterns; this sweep would pass vacuously"
    return [{"path": f"f{index}.py", "line": 3, "name": name, "text": "x"}
            for index, name in enumerate(names)]


def test_a_risk_item_names_its_rule_and_does_not_ask_for_the_match_deleted() -> None:
    """D165: for every shipped rule, the target names it and forbids delete-to-clear.

    "remove the configured risk pattern" on a `debt-marker` hit reads as
    "delete the TODO", which clears the finding and the score while the
    debt it records stays exactly where it was.
    """
    from maintainability_audit._work_order import _items_from_counted

    findings = _risk_findings()
    items = [item for item in _items_from_counted({"risk_findings": findings})
             if item["finding_class"] == "risk-pattern"]
    assert len(items) == len(findings)
    for finding, item in zip(findings, items, strict=True):
        assert f"`{finding['name']}`" in item["target"], item["target"]
        assert not item["target"].startswith("remove"), item["target"]
        assert "deleting the matched text alone" in item["target"], item["target"]


def test_no_risk_surface_attributes_a_rule_to_the_repository_choosing_it() -> None:
    """D165: shipped defaults are not "a rule this project chose".

    A repository with no configuration inherits every rule in
    `DEFAULT_CONFIG`; the class rationale and the pre-commit item both told
    it the repository had asked for them.
    """
    from maintainability_audit._precommit import _risk_items
    from maintainability_audit._work_order_weights import CLASS_RISK_EFFORT

    entries = [{"pattern": finding["name"], "path": finding["path"], "line": 1}
               for finding in _risk_findings()]
    texts = [CLASS_RISK_EFFORT["risk-pattern"].rationale]
    for item in _risk_items({"risk_findings": entries}):
        texts.extend([item["target"], item["rationale"]])
    assert len(texts) > 1, "pre-commit produced no risk items to examine"
    claims = ("this project chose", "repository's own configuration", "repository declared")
    wrong = [text for text in texts if any(claim in text for claim in claims)]
    assert not wrong, f"risk text attributing a default to the repository: {wrong}"


def _verify_commands(text: str) -> list[str]:
    commands = []
    for line in text.splitlines():
        for marker in ("Verify with: `", "Verify when done: "):
            if marker in line:
                commands.append(line.split(marker, 1)[1].rstrip("`").strip())
    return commands


def test_every_verification_command_runs_the_interpreter_that_audited() -> None:
    """D166: every class's command, on every skin, names `sys.executable`.

    The literal `python -m maintainability_audit` addressed whatever
    `python` a shell found: absent on the Mac it was demonstrated on, and
    a 0.9.1 user-site install where `python3` resolved.
    """
    from maintainability_audit._work_order_weights import CLASS_RISK_EFFORT
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    assert CLASS_RISK_EFFORT, "no finding classes to examine"
    declared = [weight.verification for weight in CLASS_RISK_EFFORT.values()]
    report = build_report(DEMO, load_config(DEMO / "maintainability-agent.json"))
    rendered = []
    for text in (render_ai_prompt(report), render_markdown(report)):
        rendered.extend(_verify_commands(text))
    assert rendered, "no skin printed a verification command; the sweep is empty"
    wrong = [command for command in declared + rendered
             if shlex.split(command)[0] != sys.executable]
    assert not wrong, f"verification commands not bound to {sys.executable}: {sorted(set(wrong))}"


def test_the_work_order_heading_states_the_order_the_list_is_in(tmp_path) -> None:
    """D169: an exposure-sorted list does not claim the band order.

    `reorder_by_exposure` replaces the band order whenever an economic
    context is configured. The heading kept saying "ordered by what it
    costs to leave against what it costs to fix", and the prompt kept
    saying its first items were "the highest value for the least change",
    so the two named different first items and neither said why.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    config = load_config(DEMO / "maintainability-agent.json")
    config["economic_context"] = {
        "version": 1,
        "loaded_engineering_cost_per_hour": {"low": 90.0, "base": 140.0, "high": 210.0},
    }
    report = build_report(DEMO, config)
    assert report.get("economic_impact"), (
        "the economic context did not apply, so the exposure sort this claim "
        "is about never ran"
    )
    markdown = render_markdown(report)
    headings = [line for line in markdown.splitlines() if line.startswith("Ordered by ")]
    assert headings, "no work-order heading was rendered"
    assert all(line.startswith("Ordered by band, then by exposure") for line in headings), headings
    assert "highest value for the least change" not in render_ai_prompt(report)


@pytest.mark.parametrize("complete", [False, True])
def test_a_band_ordered_list_still_says_so(complete: bool) -> None:
    """D169's other half: without a context the band order is stated, unchanged.

    Covers existing behaviour: a guard that the D169 fix narrows the heading
    only for an exposure-sorted list, so it passes before the fix by design.
    """
    from maintainability_audit._work_order_view import work_order_markdown

    item = {"band": "quick-win", "title": "f in a.py", "path": "a.py", "line": 1,
            "target": "t", "rationale": "r", "verification": "v", "class_delta": 0.0,
            "class_count": 1, "finding_class": "oversized-declaration"}
    lines = work_order_markdown([item], complete=complete)
    assert any(line.startswith("Ordered by what it costs to leave") for line in lines)

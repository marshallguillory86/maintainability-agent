"""Every surface of one run says what that run found, and nothing else.

D171–D174, from the hostile audit of `77de21c` (3.6.0 + 3.6.1). Each is
one surface telling a different story from the report it belongs to:

* D171 — the pre-commit hook worded a declaration unlike the audit.
* D172 — the prompt named a source for an estimate that was not issued.
* D173 — the prompt asked for a patch on a run whose report said
  "Nothing to do".
* D174 — a changed-only run handed the prompt a finding from a file the
  change never touched.

Populations are derived: declarations from every grammar fixture on disk,
dimensions from the score document, the "patch" instructions from
`prompt_deliverable` itself, and semantic findings from a tree carrying the
semantic fixture at several locations. Each sweep asserts it is not empty.
"""
from __future__ import annotations

import copy
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
GRAMMAR = ROOT / "tests" / "fixtures" / "grammar"


def _failing_everything() -> dict[str, Any]:
    """Every declaration breaches; class and function budgets differ, so a
    target naming the wrong one is visible."""
    from maintainability_audit.config import load_config

    config = copy.deepcopy(load_config(None))
    config["thresholds"].update({
        "max_function_lines": 3, "warn_function_lines": 2,
        "max_class_lines": 1, "warn_class_lines": 1,
        "max_complexity": 0, "warn_complexity": 0,
    })
    return config


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_the_hook_words_every_declaration_as_the_audit_does(tmp_path) -> None:
    """D171: `staged_findings` and the audit give one target per declaration.

    D164 passed thresholds to `_items_from_hotspots` from `build_report` and
    `check_content` but not from the hook, so a staged 2876-line class read
    "a class is graded on length alone" where the audit read "against the
    300-line class limit".
    """
    from maintainability_audit._precommit import staged_findings, staged_report
    from maintainability_audit.report import build_report

    fixtures = sorted(GRAMMAR.rglob("constructs.*"))
    assert fixtures, f"no grammar fixtures under {GRAMMAR}; this sweep would pass vacuously"
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    for fixture in fixtures:
        shutil.copy(fixture, repo / fixture.name)
    _git(repo, "add", ".")
    config = _failing_everything()

    def targets(items: list[dict[str, Any]]) -> dict[tuple[str, int], str]:
        return {(item["path"], item["line"]): item["target"] for item in items
                if item["finding_class"] == "oversized-declaration"}

    hook = targets(staged_findings(staged_report(repo, config)))
    audit = targets(build_report(repo, config, run_analyzers=False)["work_order"])
    assert any("-line class limit" in target for target in audit.values()), (
        "the audit produced no class targets, so the class half was never compared"
    )
    shared = hook.keys() & audit.keys()
    assert shared, "the hook and the audit located no declaration in common"
    differing = {key: (hook[key], audit[key]) for key in shared if hook[key] != audit[key]}
    assert not differing, f"hook and audit word these declarations differently: {list(differing.items())[:3]}"


def _unscored_report(root: Path) -> dict[str, Any]:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root.mkdir()
    body = "".join(f"    value = {line}\n" for line in range(900))
    (root / "module.py").write_text(f"def value():\n{body}    return value\n", encoding="utf-8")
    report = build_report(root, load_config(None), run_analyzers=False)
    assert report["score"]["maintainability_estimate"] is None, "the tree was scored; the floors did not hold"
    return report


@pytest.mark.usefixtures("real_population_floors")
def test_no_prompt_names_a_source_for_an_estimate_that_was_not_issued(tmp_path) -> None:
    """D172: with no estimate, neither caveat branch attributes one.

    `prompt_analyzer_caveat` said "the maintainability estimate above uses the
    analyzer readings" beside "Maintainability estimate: Not scored". The
    other branch — "comes from the built-in detectors" — made the same claim
    about the same absent number.
    """
    from maintainability_audit.prompts import render_ai_prompt

    base = _unscored_report(tmp_path / "tree")
    dimensions = sorted(base["score"]["dimensions"])
    assert dimensions, "the score document names no dimensions"
    states = [[], *([name] for name in dimensions)]
    wrong = []
    for scored in states:
        report = copy.deepcopy(base)
        report["analyzer_measurements"] = [{"tool": "lizard"}]
        report["score"]["analyzer_scored_dimensions"] = scored
        prompt = render_ai_prompt(report)
        if "maintainability estimate above" in prompt.lower():
            wrong.append(scored)
    assert not wrong, f"unscored prompts attributing an estimate, by scored dimensions: {wrong}"


def _deliverable_lines() -> list[str]:
    from maintainability_audit._prompt_sections import prompt_deliverable

    lines = [line for line in prompt_deliverable() if len(line.strip()) > 12]
    assert lines, "prompt_deliverable produced no instruction lines"
    return lines


def _task_lines(prompt: str) -> list[str]:
    handed = [line for line in _deliverable_lines() if line in prompt]
    if "Your task is to fix" in prompt:
        handed.append("Your task is to fix")
    if "Function hotspots to inspect first" in prompt:
        handed.append("Function hotspots to inspect first")
    return handed


def test_a_run_with_no_work_order_hands_the_prompt_no_task(tmp_path) -> None:
    """D173: a warn-only run is "Nothing to do" in the chat report and the prompt alike."""
    from maintainability_audit._work_order_view import NOTHING_TO_DO
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown
    from maintainability_audit.report import build_report

    config = load_config(None)
    thresholds = config["thresholds"]
    between = (thresholds["warn_function_lines"] + thresholds["max_function_lines"]) // 2
    tree = tmp_path / "warn"
    tree.mkdir()
    body = "".join(f"    v = {line}\n" for line in range(between - 2))
    (tree / "module.py").write_text(f"def warned():\n{body}    return v\n", encoding="utf-8")
    report = build_report(tree, config, run_analyzers=False)
    assert report["function_hotspots"], "no hotspot at all; the warn band was never reached"
    assert report["work_order"] == [], f"the tree produced work: {report['work_order']}"
    assert NOTHING_TO_DO in render_markdown(report, complete=False)

    prompt = render_ai_prompt(report)
    assert NOTHING_TO_DO in prompt, "the prompt does not say what the chat report says"
    assert not _task_lines(prompt), f"a 'Nothing to do' run's prompt still hands over: {_task_lines(prompt)}"


def test_a_work_order_withheld_whole_hands_the_prompt_no_task(tmp_path) -> None:
    """D173's second case: every item withheld from the prompt is not a job either."""
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    tree = tmp_path / "tree"
    tree.mkdir()
    (tree / "a.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    report = build_report(tree, load_config(None), run_analyzers=False)
    report["work_order"] = [{
        "finding_class": "duplicate-block", "title": "duplicated block in a.py", "path": "a.py",
        "line": 1, "band": "major-project", "risk": 4, "effort": 4, "target": "t",
        "rationale": "r", "verification": "v", "class_delta": 0.0, "class_count": 1,
        "fingerprint": "fp", "severity": 1.0,
    }]
    prompt = render_ai_prompt(report)
    assert "Nothing in scope for this prompt" in prompt
    assert not _task_lines(prompt), f"a fully withheld work order still hands over: {_task_lines(prompt)}"


def test_a_prompt_with_work_still_hands_over_its_task(tmp_path) -> None:
    """D173 must not strip the task where there is one.

    Covers existing behaviour: a run with work already carried its task and
    deliverable; this guards the D173 narrowing against removing them.
    """
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    tree = tmp_path / "tree"
    tree.mkdir()
    body = "".join(f"    v = {line}\n" for line in range(120))
    (tree / "module.py").write_text(f"def huge():\n{body}    return v\n", encoding="utf-8")
    report = build_report(tree, load_config(None), run_analyzers=False)
    assert report["work_order"], "the fixture produced no work"
    prompt = render_ai_prompt(report)
    assert all(line in prompt for line in _deliverable_lines())
    assert "Your task is to fix" in prompt


def test_a_changed_only_run_hands_over_no_semantic_finding_outside_its_paths(tmp_path) -> None:
    """D174: a semantic finding is kept exactly where its source path is in the change.

    The semantic walk reads the whole tree; changed-only over two commits
    handed the prompt `tests/fixtures/semantic_ts/src/operations.ts`, which
    neither touched. This repository holds that one located finding, so a
    population drawn from it would be the sample itself: the tree here
    carries every copy of the semantic fixture at more than one location,
    and a change that touches one of them.
    """
    from maintainability_audit._semantic import semantic_findings
    from maintainability_audit._semantic_ts import discover_type_analysis
    from maintainability_audit.config import load_config
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    fixture = ROOT / "tests" / "fixtures" / "semantic_ts"
    tree = tmp_path / "tree"
    for place in ("lib/alpha", "services/beta", "tools/gamma"):
        shutil.copytree(fixture, tree / place)
    full = semantic_findings(tree, type_analysis=discover_type_analysis(tree))["findings"]
    located = sorted({(finding.get("source_evidence") or {}).get("path") for finding in full} - {None})
    assert len(located) >= 2, f"the tree located {located}; nothing to keep one of and drop the rest"
    changed = located[0]
    report = build_report(tree, load_config(None), only_paths={changed},
                          changed_revspec="HEAD~1...HEAD", run_analyzers=False)
    kept = sorted({(finding.get("source_evidence") or {}).get("path")
                   for finding in report["semantic_findings"]})
    assert kept == [changed], f"changed-only over {changed} kept semantic findings at {kept}"
    prompt = render_ai_prompt(report)
    named = [path for path in located[1:] if path in prompt]
    assert not named, f"the changed-only prompt names files outside the change: {named}"

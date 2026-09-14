"""A semantic finding comes only from a file the audit read (D181).

From Grok's audit of 3.7.3 (`7befdbd`): excluding `tests/fixtures/` removed the
fixture from every count, and a full scan still reported a design review
candidate from it — into the report and the remediation prompt. The semantic
walk reads the whole tree; D174 held a changed-only run to its paths and left
the full run reading everything.

The claim: **for every exclusion the operator configures, a full run keeps
no semantic finding from an excluded file, keeps every one from the rest,
and counts only what it keeps.** The located population is derived from the
walk over a tree holding the semantic fixture at several places; exclusions
are written in each pattern form `is_excluded` accepts, so a filter that
compares prefixes as text is caught by the glob.
"""
from __future__ import annotations

import copy
import shutil
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PLACES = ("lib/alpha", "services/beta", "tools/gamma")


def _tree(tmp_path: Path) -> tuple[Path, list[str]]:
    from maintainability_audit._semantic import semantic_findings
    from maintainability_audit._semantic_ts import discover_type_analysis

    tree = tmp_path / "tree"
    for place in PLACES:
        shutil.copytree(ROOT / "tests" / "fixtures" / "semantic_ts", tree / place)
    walked = semantic_findings(tree, type_analysis=discover_type_analysis(tree))["findings"]
    located = sorted({(f.get("source_evidence") or {}).get("path") for f in walked} - {None, ""})
    assert {path.split("/")[0] for path in located} >= {"lib", "services", "tools"}, (
        f"the walk did not locate a finding at every place: {located}")
    return tree, located


@pytest.mark.parametrize("pattern", ["services/beta/", "services/*/src/*.ts", "**/beta/**"])
def test_a_full_run_keeps_no_semantic_finding_from_an_excluded_file(tmp_path, pattern) -> None:
    from maintainability_audit.config import load_config
    from maintainability_audit.metrics import is_excluded
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.report import build_report

    tree, located = _tree(tmp_path)
    excluded = [path for path in located if is_excluded(path, [pattern])]
    included = [path for path in located if path not in excluded]
    assert excluded and included, f"{pattern!r} splits nothing: excluded={excluded}"

    config = copy.deepcopy(load_config(None))
    config["paths"]["exclude_patterns"].append(pattern)
    report = build_report(tree, config, run_analyzers=False)
    kept = sorted({f["source_evidence"]["path"] for f in report["semantic_findings"]})
    assert kept == included, f"with {pattern!r} excluded the run kept semantic findings at {kept}"
    prompt = render_ai_prompt(report)
    assert not [path for path in excluded if path in prompt], "the prompt names an excluded file"

    violations = (report["semantic_coverage"].get("violations") or {})
    if violations:
        assert sum(violations.values()) == len(report["semantic_findings"]), (
            f"coverage counts {violations} but the report carries "
            f"{len(report['semantic_findings'])} findings")

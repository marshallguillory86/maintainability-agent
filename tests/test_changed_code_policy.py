"""Code a change touches meets a stricter bar than code it leaves alone (Decision 15).

A team cannot fix a large codebase at once, and a gate that fails on every
old long function is a gate nobody turns on. `--fail-on-new` stops new
findings and the ratchet stops a dimension sliding, but nothing let a
repository say *what you touch must be better than the standard*.

`policy.changed_code` sets stricter function limits. On a run against a
change (`--changed-only REV`), a function is touched when the change added
or altered any line inside it, and only touched functions are held to the
policy; an untouched long function beside it is judged by the standard as
before. A policy only tightens — a limit looser than the standard is a
configuration error — and it decides the gate, never the grade: its
breaches fail `--fail-on-gate` and are reported, and the score is computed
exactly as it would be without it.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import jsonschema
import pytest

from maintainability_audit._catalog import PolicyError
from maintainability_audit._gates import audit_exit_code
from maintainability_audit.config import load_config
from maintainability_audit.git_tools import changed_paths
from maintainability_audit.renderers import render_markdown
from maintainability_audit.report import build_report

ROOT = Path(__file__).resolve().parents[1]
REVSPEC = "HEAD~1...HEAD"


def _body(name: str, lines: int) -> str:
    inner = "".join(f"    x{i} = {i}\n" for i in range(lines))
    return f"def {name}():\n{inner}    return 0\n\n\n"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(tmp_path: Path) -> Path:
    """`legacy` is long and untouched; `fresh` grows from 3 lines to 30."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    # The default config requires a README; without one the gate fails for
    # that reason and the gate test would not be about the policy.
    (root / "README.md").write_text("# fixture\n", encoding="utf-8")
    (root / "app.py").write_text(_body("legacy", 40) + _body("fresh", 3), encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base")
    (root / "app.py").write_text(_body("legacy", 40) + _body("fresh", 30), encoding="utf-8")
    _git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qam", "grow fresh")
    return root


def _report(root: Path, policy: dict | None) -> dict:
    config = load_config(None)
    if policy is not None:
        config["policy"] = policy
    return build_report(root, config, changed_paths(root, REVSPEC), REVSPEC)


def test_a_touched_function_over_the_policy_fails_and_an_untouched_one_does_not(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    report = _report(root, {"changed_code": {"max_function_lines": 20}})

    failures = report["policy"]["failures"]
    assert [(f["name"], f["measure"]) for f in failures] == [("fresh", "function_lines")]
    assert failures[0]["limit"] == 20 and failures[0]["value"] > 20
    # And the grade never moves: the same score and hard gates as without it.
    without = _report(root, None)
    assert report["score"] == without["score"]
    assert report["hard_gate_failures"] == without["hard_gate_failures"]


def test_a_breach_fails_the_gate(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    args = argparse.Namespace(fail_on_new=False, fail_on_gate=True, baseline=None,
                              fail_on_out_of_scope=False, fail_on_regression=False,
                              conformance=None)

    assert audit_exit_code(args, _report(root, {"changed_code": {"max_function_lines": 20}})) == 1
    assert audit_exit_code(args, _report(root, None)) == 0


def test_a_limit_looser_than_the_standard_is_refused_when_the_config_loads(tmp_path: Path) -> None:
    """Refused at load, where both doors already turn a config error into a message."""
    path = tmp_path / "maintainability-agent.json"
    path.write_text(json.dumps({"version": 1, "policy": {"changed_code": {"max_function_lines": 500}}}),
                    encoding="utf-8")

    with pytest.raises(PolicyError, match="only tighten"):
        load_config(str(path))


def test_the_report_names_the_breach(tmp_path: Path) -> None:
    markdown = render_markdown(_report(_repo(tmp_path), {"changed_code": {"max_function_lines": 20}}))

    assert "Changed-code policy" in markdown and "fresh" in markdown


def test_the_published_schema_accepts_it() -> None:
    schema = json.loads((ROOT / "maintainability-agent.schema.json").read_text(encoding="utf-8"))
    config = {"version": 1, "policy": {"changed_code": {
        "max_function_lines": 40, "max_complexity": 10, "max_cognitive_complexity": 15}}}

    jsonschema.validate(config, schema)


def test_the_chat_view_and_the_html_report_name_it_too(tmp_path: Path) -> None:
    """Three skins of one report: a gate failure no surface may omit."""
    from maintainability_audit._html_view import render_html

    report = _report(_repo(tmp_path), {"changed_code": {"max_function_lines": 20}})

    assert "fresh" in render_markdown(report, complete=False)
    assert "fresh" in render_html(report, [])


def test_the_chat_door_reports_the_same_gate(tmp_path: Path) -> None:
    """`gate_passed` read the hard gates only, so the door said pass where the CLI failed."""
    from maintainability_audit._mcp_audit import _top_level_result

    root = _repo(tmp_path)
    report = _report(root, {"changed_code": {"max_function_lines": 20}})

    result = _top_level_result(report, root, "", run_analyzers=False, baseline=None, include_prompt=False)

    assert result["gate_passed"] is False

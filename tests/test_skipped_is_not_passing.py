"""A skipped test is not a passing one (Decision 19, after Ken Pugh).

A suite reports a skipped, pending or expected-failure test as something
other than a failure, so a skip reads as a pass to anyone who only looks at
the result. Spectables generates a failing stub for every unwritten step so
that an unwritten test can never pass; this tool cannot do that for a suite it
does not own, but it can say where the suite has stopped testing.

The claims: every skip marker in a test file of the audited population is
reported by path and line; the same text in a non-test file, inside a string,
or in an excluded file is not; the report carries the credit; and the finding
moves no score, because Decision 19 keeps it out of the rubric.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

MARKERS = {
    "tests/test_py.py": [
        "@pytest.mark.skip(reason='later')",
        "@pytest.mark.skipif(True, reason='later')",
        "@pytest.mark.xfail",
        "@unittest.skip('later')",
        "    pytest.skip('later')",
    ],
    "src/widget.test.js": [
        "it.skip('renders', () => {});",
        "describe.skip('widget', () => {});",
        "xit('renders', () => {});",
        "test.todo('renders');",
    ],
}


def _tree(tmp_path: Path, markers: dict[str, list[str]]) -> Path:
    root = tmp_path / "tree"
    for rel, lines in markers.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(["# a test module", *lines, ""]), encoding="utf-8")
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "app.py").write_text(
        "def run():\n    note = '@pytest.mark.skip is how a test is skipped'\n"
        "    return note\n# it.skip( in a comment of a source file\n", encoding="utf-8")
    return root


def _report(root: Path, exclude: list[str] | None = None) -> dict:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    config = copy.deepcopy(load_config(None))
    config["paths"]["exclude_patterns"].extend(exclude or [])
    return build_report(root, config, run_analyzers=False)


def test_every_skip_marker_in_a_test_file_is_reported_by_path_and_line(tmp_path: Path) -> None:
    report = _report(_tree(tmp_path, MARKERS))

    found = {(item["path"], item["line"]) for item in report["test_honesty"]["skipped"]}
    expected = {(rel, number) for rel, lines in MARKERS.items()
                for number in range(2, len(lines) + 2)}
    assert found == expected


def test_a_skip_outside_a_test_file_or_inside_a_string_is_not_reported(tmp_path: Path) -> None:
    report = _report(_tree(tmp_path, MARKERS))

    assert "src/app.py" not in {item["path"] for item in report["test_honesty"]["skipped"]}


def test_an_excluded_test_file_is_not_reported(tmp_path: Path) -> None:
    report = _report(_tree(tmp_path, MARKERS), exclude=["src/"])

    assert {item["path"] for item in report["test_honesty"]["skipped"]} == {"tests/test_py.py"}


def test_the_report_and_the_prompt_name_the_skips_and_credit_ken_pugh(tmp_path: Path) -> None:
    from maintainability_audit.prompts import render_ai_prompt
    from maintainability_audit.renderers import render_markdown

    report = _report(_tree(tmp_path, MARKERS))
    markdown = render_markdown(report)

    assert "tests/test_py.py:2" in markdown
    assert "Ken Pugh" in markdown
    assert "tests/test_py.py:2" in render_ai_prompt(report)


def test_the_finding_moves_no_score(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The same tree, scored with and without this finding, scores the same.

    Not "a skip marker moves no score": `test.todo(` already counts as a debt
    marker through the risk patterns, which is that rule's business. The
    claim here is only that this block adds nothing to the rubric.
    """
    from maintainability_audit import report as report_module

    root = _tree(tmp_path, MARKERS)
    with_finding = _report(root)
    monkeypatch.setattr(report_module, "test_honesty",
                        lambda *_args: {"skipped": [], "credit": ""})
    without = _report(root)

    assert with_finding["test_honesty"]["skipped"]
    assert with_finding["score"] == without["score"]

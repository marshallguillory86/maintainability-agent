"""A test states its expected value (Decision 19, after Ken Pugh).

Spectables' guide warns that glue code which computes a result "is testing
itself": `assert add(a, b) == a + b` re-implements the code under test and
passes whatever the implementation does, because the expectation is the same
arithmetic. The expected value belongs written down, as Spectables' example
tables write it.

The detected shape is deliberately narrow, for precision: in a Python test
file, a comparison whose one side calls the code under test (directly, or
through a name assigned from a call) while the other side does arithmetic on
variables. Arithmetic on literals alone (`2 * 60`) is a stated value. The
finding is reported only and moves no score.
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest

FLAGGED = {
    "direct": "def test_add():\n    assert add(a, b) == a + b\n",
    "reversed": "def test_add():\n    assert a + b == add(a, b)\n",
    "unittest": ("class T:\n    def test_total(self):\n"
                 "        self.assertEqual(total(items), price * qty)\n"),
    "named expectation": ("def test_total():\n    expected = price * qty\n"
                          "    assert total(items) == expected\n"),
    "named result": ("def test_total():\n    result = total(items)\n"
                     "    assert result == price * qty\n"),
}

STATED = {
    "literal": "def test_add():\n    assert add(2, 3) == 5\n",
    "literal arithmetic": "def test_minutes():\n    assert minutes(2) == 2 * 60\n",
    "no arithmetic": "def test_count():\n    assert len(items) == count\n",
    "both sides call": "def test_same():\n    assert f(x) + 1 == g(x) + 1\n",
    "not a comparison": "def test_sum():\n    total = a + b\n    assert check(total)\n",
    # Found by running the detector over this repository's own suite.
    "path join": "def test_path(tmp_path):\n    assert locate(tmp_path) == tmp_path / \"AGENTS.md\"\n",
    "named path join": ("def test_path(tmp_path):\n    granted = tmp_path / \"g\"\n"
                        "    assert authorize(str(granted)) == granted\n"),
    "relation between two results": ("def test_rel():\n    single = measure(a)\n"
                                     "    plain = measure(b)\n    assert single == plain + 1\n"),
    "literal container holding calls": ("def test_set():\n    after = snapshot()\n"
                                        "    assert after - before == {str(x), str(y)}\n"),
    "input size reused as the expectation": (
        "def test_all_survive():\n    count = BUDGET // 24 + 500\n"
        "    for i in range(count):\n        make(i)\n"
        "    assert len(expand()) == count\n"),
}


def _report(tmp_path: Path, files: dict[str, str]) -> dict:
    from maintainability_audit.config import load_config
    from maintainability_audit.report import build_report

    root = tmp_path / "tree"
    for rel, text in files.items():
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        (root / rel).write_text(text, encoding="utf-8")
    return build_report(root, copy.deepcopy(load_config(None)), run_analyzers=False)


def _computed(report: dict) -> set[tuple[str, int]]:
    return {(item["path"], item["line"]) for item in report["test_honesty"]["computed_expected"]}


@pytest.mark.parametrize("name", sorted(FLAGGED))
def test_an_expected_value_computed_in_the_test_is_reported(tmp_path: Path, name: str) -> None:
    source = FLAGGED[name]
    line = next(n for n, text in enumerate(source.splitlines(), 1)
                if "assert" in text or "assertEqual" in text)

    assert _computed(_report(tmp_path, {"tests/test_x.py": source})) == {("tests/test_x.py", line)}


@pytest.mark.parametrize("name", sorted(STATED))
def test_a_stated_expected_value_is_not_reported(tmp_path: Path, name: str) -> None:
    assert _computed(_report(tmp_path, {"tests/test_x.py": STATED[name]})) == set()


def test_the_same_shape_outside_a_test_file_is_not_reported(tmp_path: Path) -> None:
    assert _computed(_report(tmp_path, {"src/app.py": FLAGGED["direct"]})) == set()


def test_a_file_that_does_not_parse_is_skipped_not_fatal(tmp_path: Path) -> None:
    report = _report(tmp_path, {"tests/test_x.py": "def test_(:\n", "tests/test_y.py": FLAGGED["direct"]})

    assert _computed(report) == {("tests/test_y.py", 2)}


def test_the_report_names_it_and_credits_ken_pugh(tmp_path: Path) -> None:
    from maintainability_audit.renderers import render_markdown

    markdown = render_markdown(_report(tmp_path, {"tests/test_x.py": FLAGGED["direct"]}))

    assert "tests/test_x.py:2" in markdown
    assert "Ken Pugh" in markdown


def test_the_prompt_lists_it_beside_work_and_never_makes_work_of_it(tmp_path: Path) -> None:
    """Reported only: with other work the prompt lists it as evidence; with
    none the prompt says there is nothing to do, as it does for every finding
    that carries no work-order item."""
    from maintainability_audit._prompt_sections import prompt_has_work
    from maintainability_audit.prompts import render_ai_prompt

    alone = _report(tmp_path / "alone", {"tests/test_x.py": FLAGGED["direct"]})
    beside = _report(tmp_path / "beside", {"tests/test_x.py": FLAGGED["direct"],
                                           "src/widget.test.js": "test.todo('renders');\n"})

    assert not prompt_has_work(alone)
    assert "tests/test_x.py:2" not in render_ai_prompt(alone)
    assert prompt_has_work(beside)
    assert "tests/test_x.py:2" in render_ai_prompt(beside)

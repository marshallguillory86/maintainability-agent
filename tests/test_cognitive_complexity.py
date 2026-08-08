"""Reading cost, as distinct from branch count.

The cyclomatic figure this tool already emitted is a keyword tally, and
it scored these two identically at 6:

    five sequential guard clauses  vs  five levels of nesting

Guard clauses are read one at a time; five levels of nesting must be held
in the head at once. Nesting is the strongest driver of how hard code is
to read, and it was invisible.

These tests pin that nesting now compounds, that constructs which do not
add reading load are not charged as though they do, and that the two
figures stay separate — a function can be low in one and high in the
other, and collapsing them would lose the distinction that motivated
this.
"""
from __future__ import annotations

import ast
from pathlib import Path

from maintainability_audit._cognitive import brace_cognitive, python_cognitive
from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.declarations import detect_functions, function_status
from maintainability_audit.metrics import read_lines

THRESHOLDS = DEFAULT_CONFIG["thresholds"]

FLAT = """
def flat(a, b, c, d, e):
    if a: return 1
    if b: return 2
    if c: return 3
    if d: return 4
    if e: return 5
    return 0
"""

NESTED = """
def nested(a, b, c, d, e):
    if a:
        if b:
            if c:
                if d:
                    if e:
                        return 5
    return 0
"""


def cognitive_of(source: str) -> int:
    return python_cognitive(ast.parse(source.strip()).body[0])


# ---------------------------------------------------------------------------
# The blindness this metric exists to fix
# ---------------------------------------------------------------------------

def test_nesting_costs_more_than_the_same_branches_laid_flat() -> None:
    """The motivating case. Under the cyclomatic count both score 6."""
    assert cognitive_of(NESTED) > cognitive_of(FLAT) * 2


def test_each_level_of_nesting_costs_progressively_more() -> None:
    """The charge is the depth, so cost grows faster than depth does."""
    one = cognitive_of("def f(a):\n    if a:\n        return 1\n")
    two = cognitive_of("def f(a, b):\n    if a:\n        if b:\n            return 1\n")
    three = cognitive_of("def f(a, b, c):\n    if a:\n        if b:\n            if c:\n                return 1\n")

    assert two - one > one
    assert three - two > two - one


def test_a_straight_line_body_costs_nothing() -> None:
    assert cognitive_of("def f():\n    a = 1\n    b = 2\n    return a + b\n") == 0


# ---------------------------------------------------------------------------
# Things that must not be over-charged
# ---------------------------------------------------------------------------

def test_a_boolean_run_is_one_idea_not_three() -> None:
    """`a and b and c` reads as a single condition. Charging per operator
    would push ordinary guard clauses over a threshold for no reason."""
    single = cognitive_of("def f(a, b, c):\n    if a and b and c:\n        return 1\n")
    plain = cognitive_of("def f(a):\n    if a:\n        return 1\n")

    assert single == plain + 1


def test_elif_chains_do_not_compound_like_nesting() -> None:
    """An `elif` continues a decision already being tracked; it does not
    open a new context to hold."""
    chain = cognitive_of(
        "def f(a, b, c):\n    if a:\n        return 1\n    elif b:\n        return 2\n    elif c:\n        return 3\n"
    )

    assert chain < cognitive_of(NESTED)


# ---------------------------------------------------------------------------
# C-family approximation
# ---------------------------------------------------------------------------

def test_brace_sources_also_charge_for_depth() -> None:
    flat = brace_cognitive("function f(a,b) {\n  if (a) { return 1; }\n  if (b) { return 2; }\n}".splitlines())
    nested = brace_cognitive(
        "function f(a,b) {\n  if (a) {\n    if (b) {\n      if (a) { return 1; }\n    }\n  }\n}".splitlines()
    )

    assert nested > flat


def test_brace_scoring_ignores_keywords_in_comments_and_strings() -> None:
    clean = brace_cognitive("function f(a) {\n  if (a) { return 1; }\n}".splitlines())
    noisy = brace_cognitive(
        'function f(a) {\n  // if for while\n  const s = "if for while";\n  if (a) { return 1; }\n}'.splitlines()
    )

    assert clean == noisy


# ---------------------------------------------------------------------------
# Grading integration
# ---------------------------------------------------------------------------

def test_a_deeply_nested_function_fails_on_reading_cost_alone() -> None:
    """Short and few-branched, but punishing to read: exactly the case the
    old thresholds waved through."""
    assert function_status(lines=10, complexity=2, thresholds=THRESHOLDS, cognitive=40) == "fail"
    assert function_status(lines=10, complexity=2, thresholds=THRESHOLDS, cognitive=20) == "warn"
    assert function_status(lines=10, complexity=2, thresholds=THRESHOLDS, cognitive=3) == "ok"


def test_configs_without_cognitive_thresholds_behave_as_before() -> None:
    """Absent keys must not start failing existing repos on a metric their
    config never opted into."""
    legacy = {key: value for key, value in THRESHOLDS.items() if "cognitive" not in key}

    assert function_status(lines=10, complexity=2, thresholds=legacy, cognitive=999) == "ok"


def test_cognitive_is_reported_per_declaration(tmp_path: Path) -> None:
    path = tmp_path / "mod.py"
    path.write_text(FLAT.strip() + "\n\n" + NESTED.strip() + "\n", encoding="utf-8")

    found = {m.name: m for m in detect_functions(tmp_path, path, read_lines(path), THRESHOLDS)}

    assert found["nested"].cognitive > found["flat"].cognitive
    # The branch counts stay close; only the reading cost separates them.
    assert abs(found["nested"].complexity - found["flat"].complexity) <= 1


def test_classes_carry_no_reading_cost_of_their_own(tmp_path: Path) -> None:
    """A class is a container, and its methods are charged individually."""
    path = tmp_path / "worker.py"
    path.write_text("class Worker:\n    def run(self, a):\n        if a:\n            return 1\n", encoding="utf-8")

    found = {m.name: m for m in detect_functions(tmp_path, path, read_lines(path), THRESHOLDS)}

    assert found["Worker"].cognitive == 0
    assert found["run"].cognitive > 0

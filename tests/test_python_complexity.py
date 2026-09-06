"""What Python's complexity is counted from, and what it is not.

Every one of these was found by `tools/complexity_oracle.py`, which
compares this project's per-declaration complexity against `lizard` — a
separate implementation, by separate authors, reading the same grammar.
On this repository's own source the two agreed on 448 of 985
declarations, and the disagreements had two causes, both of them here.

The point is not that lizard is right. It is that a disagreement is a
fact the author of either tool cannot talk away, and it sends a reader to
the grammar — which is the only authority either answers to.

Python is the language this project is written in, the language most of
the calibration corpus is measured through, and the one whose numbers the
0–5 scale is fitted against. These were not edge cases.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.declarations import detect_functions, metrics_for

THRESHOLDS = DEFAULT_CONFIG["thresholds"]


def _complexity(tmp_path: Path, source: str) -> int:
    path = tmp_path / "probe.py"
    path.write_text(source, encoding="utf-8")
    found = detect_functions(tmp_path, path, source.splitlines(), THRESHOLDS)
    assert found, "no declaration was detected"
    return found[0].complexity


def test_a_comment_is_not_a_branch(tmp_path: Path) -> None:
    """`declaration_ranges` returned Python's lines unmasked.

    Every other language scores against a comment- and string-masked
    copy; Python was handed the raw source, so a keyword in a comment
    counted as a decision. This function has no branches at all and
    scored 4.
    """
    source = (
        "def trivial(value):\n"
        "    # if the value is odd, or negative, we do nothing for now\n"
        "    return value\n"
    )

    assert _complexity(tmp_path, source) == 1


def test_a_string_literal_is_not_a_branch(tmp_path: Path) -> None:
    source = (
        "def label(value):\n"
        '    note = "check for errors and warnings while parsing"\n'
        "    return note\n"
    )

    assert _complexity(tmp_path, source) == 1


def test_a_docstring_is_not_a_branch(tmp_path: Path) -> None:
    """A multi-line docstring survived even the line-local masker.

    This codebase is written in long docstrings, so its own reported
    complexity was inflated by its own prose — 384 branch points on 121
    files came from inside triple-quoted strings.
    """
    source = (
        "def described(value):\n"
        '    """Return the value.\n'
        "\n"
        "    Counts for each item, if any, while the loop is running,\n"
        "    and reports whichever case applies.\n"
        '    """\n'
        "    return value\n"
    )

    assert _complexity(tmp_path, source) == 1


def test_boolean_operators_are_decisions(tmp_path: Path) -> None:
    """Python spells them `and` and `or`; the pattern looked for `&&`.

    The Python branch pattern carried C's operators into a language that
    does not have them, so every boolean operator was invisible — 3,199
    of them in this repository alone. Standard cyclomatic complexity
    counts each one.
    """
    source = (
        "def gate(a, b, c):\n"
        "    if a and b or c:\n"
        "        return 1\n"
        "    return 0\n"
    )

    # 1 (base) + if + and + or
    assert _complexity(tmp_path, source) == 4


def test_a_comprehension_condition_is_a_decision(tmp_path: Path) -> None:
    source = (
        "def evens(items):\n"
        "    return [x for x in items if x % 2 == 0]\n"
    )

    # 1 (base) + for + if
    assert _complexity(tmp_path, source) == 3


def test_the_c_family_operators_are_not_counted_in_python(tmp_path: Path) -> None:
    """`&&` and `||` are not Python. Left in the pattern they matched
    nothing, which is harmless — but `?` is not Python either, and a
    ternary written `a if b else c` is already counted by its `if`."""
    branch_points, _cognitive = metrics_for(".py")
    assert branch_points("    value = a if b else c") == 1
    assert branch_points("    url = 'http://x/?q=1'") == 0, (
        "a question mark in a string is not a decision"
    )


def test_match_arms_count_and_the_header_does_not() -> None:
    """The rule shared with Go, PHP, Ruby and Fortran: arms, not header."""
    branch_points, _cognitive = metrics_for(".py")
    assert branch_points("    match command:") == 0
    assert branch_points("        case 'go':") == 1


def test_expressions_inside_an_f_string_are_counted(tmp_path: Path) -> None:
    """`{...}` in an f-string is code, and the rest of it is not.

    Blanking the whole token was the first fix's own defect: on Python
    3.11 an f-string is a single `STRING` token, so masking it removed
    the ternaries, comprehensions and `or` defaults written inside the
    braces. Found by hand-counting a function the oracle still disagreed
    on — we said 7, the grammar says 11.
    """
    source = (
        "def render(names, scored):\n"
        "    return [\n"
        '        f"| {n} | {\'yes\' if n in scored else \'no\'} | "\n'
        '        f"{\', \'.join(str(c) for c in n) or \'-\'} |"\n'
        "        for n in names\n"
        "    ]\n"
    )

    # 1 base + outer `for` + ternary `if` + inner `for` + `or`
    assert _complexity(tmp_path, source) == 5


def test_the_literal_text_of_an_f_string_is_still_not_counted(
    tmp_path: Path,
) -> None:
    """Only the braces hold code. The prose around them does not."""
    source = (
        "def label(value):\n"
        '    return f"check for errors and warnings: {value}"\n'
    )

    assert _complexity(tmp_path, source) == 1

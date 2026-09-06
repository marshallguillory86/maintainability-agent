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


def test_a_python_comment_is_not_a_branch(tmp_path: Path) -> None:
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
    """Covers existing behaviour: the shared C-family pattern already
    counted a comprehension's `if`, so this pins behaviour that predates
    Python's own pattern rather than defending a fix. It is here so the
    new pattern cannot lose it.
    """
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
    """Covers existing behaviour: the shared C-family pattern already
    counted `case` and not `match`, by accident of `match` not being one
    of its keywords. The rule — arms, not header, shared with Go, PHP,
    Ruby and Fortran — is now deliberate rather than accidental, and this
    pins it.
    """
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


def test_the_wildcard_case_is_a_default_and_not_a_decision() -> None:
    """`case _` is Python's `default`, and a default is not a test.

    This project already refuses to count Go's `default:`, Rust's
    `_ =>`, and the C family's `default:` — a wildcard always matches, so
    it adds a path without adding a decision to reach it (D117). Python's
    wildcard pattern is the same construct and was counted, which made
    the same `switch` score differently depending on which language it
    was written in.

    lizard counts it. The divergence is declared in
    `tests/test_grammar_constructs.py` with this reasoning, because the
    authority here is the grammar and this project's own rule, not a
    second implementation.
    """
    branch_points, _cognitive = metrics_for(".py")

    assert branch_points("        case _:") == 0
    # A *guarded* wildcard does decide — but the guard is the decision,
    # and `if` is already counted, so the arm must not be counted twice.
    assert branch_points("        case _ if retries:") == 1
    # `_name` is an ordinary capture pattern, not the wildcard.
    assert branch_points("        case _name:") == 1
    # A wildcard *inside* a pattern still leaves a real pattern to match.
    assert branch_points("        case [_, second]:") == 1


def test_an_f_string_is_masked_on_every_supported_python(tmp_path: Path) -> None:
    """The masking must not depend on which interpreter is running it.

    PEP 701 changed f-string tokenisation in 3.12: through 3.11 the whole
    literal is one STRING token, from 3.12 the prose arrives as
    FSTRING_MIDDLE tokens and the braces' contents as ordinary ones. The
    first fix handled only the 3.11 shape, so on 3.12 and later — the
    versions most people run — f-strings were **not masked at all**, and
    this project's own development interpreter being 3.11 is why that
    shipped (D122).

    Both halves are asserted together, because a fix for either one alone
    has already broken the other: blanking the token whole was D114.
    """
    prose = (
        "def label(value):\n"
        '    return f"check for errors and warnings: {value}"\n'
    )
    # `for` and `and` sit in the prose; neither is a decision.
    assert _complexity(tmp_path, prose) == 1

    code = (
        "def pick(value, scored):\n"
        '    return f"{value if value in scored else 0}"\n'
    )
    # The ternary is inside the braces, so it is code and it counts.
    assert _complexity(tmp_path, code) == 2

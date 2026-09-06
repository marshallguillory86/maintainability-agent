"""D78: the JS complexity number has to be about the code.

Decision 10 keeps JavaScript because this project has a detector that can
score it, and D68 made the fallback to that detector *visible*. An audit
pointed out that visibility is not accuracy: D68's closer checks that the
built-in scanner is attributed, and never asks whether its number means
anything.

`COMPLEXITY_RE` counted every `?` character as a decision point. In
JavaScript `?` is three different operators, and only one of them is a
decision:

* `?.` optional chaining is defensive member access, not a branch;
* `??` nullish coalescing is one decision written with two characters,
  so a bare `\\?` counted each occurrence twice;
* `?` ternary is the branch the rule was written for.

The result was that a defaulting expression with a McCabe number of 1
scored 12 and warned, and an eight-argument fallback chain scored 15 --
one under the hard gate. It fires hardest on exactly the modern
JavaScript this project claims to score, which is P7: a score issued
where the thing measured was not the code.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit import declarations
from maintainability_audit.config import DEFAULT_CONFIG

THRESHOLDS = DEFAULT_CONFIG["thresholds"]


def _only(source: str, tmp_path: Path) -> object:
    path = tmp_path / "sample.js"
    path.write_text(source, encoding="utf-8")
    found = declarations.detect_functions(
        tmp_path, path, source.splitlines(), THRESHOLDS)
    assert len(found) == 1, [m.name for m in found]
    return found[0]


# (source, expected cyclomatic, why)
CASES = [
    (
        "function pick(u) {\n"
        "  return u?.user?.profile?.settings?.theme ?? \"light\";\n"
        "}\n",
        2,
        "seven `?.` are one defensive access chain; one `??` is one decision",
    ),
    (
        "function f(a, b, c, d) {\n  return a ?? b ?? c ?? d;\n}\n",
        4,
        "three `??` are three decisions, not six characters",
    ),
    (
        "function t(a) {\n  return a ? 1 : 2;\n}\n",
        2,
        "a ternary is still a decision",
    ),
    (
        "function chain(u) {\n  return u?.a?.b?.c?.d;\n}\n",
        1,
        "optional chaining alone is not a branch at all",
    ),
    (
        "function real(a, b, c) {\n"
        "  if (a && b) { for (let i = 0; i < 3; i++) { if (c) { return 1; } } }\n"
        "  return 0;\n"
        "}\n",
        5,
        "genuine branching must be unaffected: if + && + for + if, plus one",
    ),
]


@pytest.mark.parametrize(
    ("source", "expected", "why"), CASES,
    ids=[why.split(";")[0][:40] for _s, _e, why in CASES],
)
def test_the_scored_complexity_is_the_functions_complexity(
    source: str, expected: int, why: str, tmp_path: Path,
) -> None:
    """Each `?` operator contributes what it actually costs a reader."""
    metric = _only(source, tmp_path)
    assert metric.complexity == expected, (  # type: ignore[attr-defined]
        f"{why}: scored {metric.complexity}, expected {expected}"  # type: ignore[attr-defined]
    )


def test_a_defaulting_expression_does_not_warn(tmp_path: Path) -> None:
    """The reproduction, at the shipped thresholds.

    Not a unit assertion about a regex: the claim that matters is that a
    reader looking at this function would not call it complex, and the
    tool agreed with them.
    """
    metric = _only(
        "function pick(u) {\n"
        "  return u?.user?.profile?.settings?.theme\n"
        "      ?? u?.user?.prefs?.theme\n"
        "      ?? \"light\";\n"
        "}\n",
        tmp_path,
    )
    assert metric.status == "ok", (  # type: ignore[attr-defined]
        "a pure defaulting expression was flagged; its McCabe number is 1 "
        f"and it scored {metric.complexity}"  # type: ignore[attr-defined]
    )


def test_python_complexity_is_unchanged_by_the_javascript_fix(
    tmp_path: Path,
) -> None:
    """`?` is not a Python operator; the shared regex must not have moved.

    The pinned number was 4 and is 5. It was wrong: `if a and b` is two
    decisions, and Python's `and` was invisible because the pattern
    looked for C's `&&`. Verified two ways before changing it — by hand
    against the grammar (1 base + if + and + for + if) and against
    lizard, which also says 5.
    """
    path = tmp_path / "sample.py"
    source = (
        "def branchy(a, b, c):\n"
        "    if a and b:\n"
        "        for item in c:\n"
        "            if item:\n"
        "                return item\n"
        "    return None\n"
    )
    path.write_text(source, encoding="utf-8")
    found = declarations.detect_functions(
        tmp_path, path, source.splitlines(), THRESHOLDS)
    assert len(found) == 1
    assert found[0].complexity == 5, found[0].complexity

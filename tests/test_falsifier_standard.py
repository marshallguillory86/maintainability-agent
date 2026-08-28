"""The standard a falsifier has to meet, enforced where it can be.

A third of this register — thirty of ninety-six entries — is one defect
class wearing different clothes, and it was fixed thirty times without
anyone naming it. The shape:

1. A **universal claim** exists. "No analyzer reads configuration from
   the audited tree." "Every git command disables housekeeping." "No
   document presents a refused analyzer as runnable."
2. An audit finds **one instance** where the claim is false.
3. The check is written **from the instance**, not from the claim.
4. The check goes green, and the claim is still false everywhere else.

Step 3 happens every time because the author has a reproduction in hand
and no enumeration of what the claim quantifies over. It comes out two
ways: the population is hand-picked (two adapters of fifteen, three
sentences, one file), or the property is approximated by a string
instead of executed (`"pytest" in job`, `"42" not in document`, the
presence of a `diff` command that had been neutered with `|| true`).

**Why mutation testing did not catch it.** Mutation was being applied,
and applied to the instance that motivated the fix — which is *inside*
the sample the check was written from. So the mutation confirmed the
sample and said nothing about the claim. Every time an auditor broke one
of these, their mutation came from outside the sample and the author's
came from inside it.

The standard, three clauses:

* **Derive the population** from the source of truth — `ADAPTERS`, an
  `rglob`, the catalog — never from a list typed by hand.
* **Assert the population is not empty**, so a sweep that matches
  nothing fails instead of passing. *This module enforces that clause.*
* **Mutate outside the sample**: the mutation offered as proof must
  break a member the test does not name. Not mechanically checkable, so
  the register requires it to be stated (`test_written_record`).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent

#: Walking the filesystem is how a check reaches a population it did not
#: type out. It is also the point where the population can silently be
#: empty: a renamed directory, a changed suffix, a `parents[1]` that
#: moved, and the sweep asserts nothing about nothing.
WALKS = ("rglob", "glob", "iterdir")
#: `ast.walk` is not a filesystem walk. Including it was this module's
#: own version of the defect it exists to prevent: a population defined
#: by a name rather than by what it is, flagging four tests that derive
#: nothing from disk. Caught by reading what the detector had actually
#: bound instead of trusting the count.


def _population_names(function: ast.FunctionDef) -> set[str]:
    """Names bound to something derived by walking the filesystem."""
    names: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None or not any(
            isinstance(inner, ast.Attribute) and inner.attr in WALKS
            for inner in ast.walk(value)
        ):
            continue
        targets = node.targets if isinstance(node, ast.Assign) else [node.target]
        names |= {t.id for t in targets if isinstance(t, ast.Name)}
    return names


def _unguarded(function: ast.FunctionDef, names: set[str]) -> set[str]:
    """Population names no assertion establishes are non-empty.

    **Every** name, not any of them. The first version returned True as
    soon as one population was asserted, so a test binding two
    populations was covered by guarding either -- and removing the guard
    on the other left this green. That is the defect this module exists
    to catch, arriving inside the module itself, caught by mutating a
    guard the check did not name.
    """
    asserted: set[str] = set()
    for node in ast.walk(function):
        if not isinstance(node, ast.Assert):
            continue
        asserted |= {
            inner.id for inner in ast.walk(node.test) if isinstance(inner, ast.Name)
        }
    return names - asserted


def _sweeping_tests() -> list[tuple[str, ast.FunctionDef, set[str]]]:
    found = []
    for path in sorted(TESTS.glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if not (isinstance(node, ast.FunctionDef)
                    and node.name.startswith("test_")):
                continue
            names = _population_names(node)
            if names:
                found.append((path.name, node, names))
    return found


def test_there_are_sweeps_to_check() -> None:
    """This module is itself a sweep, and owes its own clause.

    If the detector stops finding sweeps, every assertion below passes
    over nothing — which is precisely the defect this file exists to
    make impossible.
    """
    sweeps = _sweeping_tests()
    assert len(sweeps) >= 12, (
        f"only {len(sweeps)} sweep-shaped tests found; the detector has "
        "stopped seeing them and everything below is now vacuous"
    )


@pytest.mark.parametrize(
    ("module", "name", "population"),
    [
        (module, node.name, sorted(names))
        for module, node, names in _sweeping_tests()
    ],
    ids=[f"{module}::{node.name}" for module, node, _n in _sweeping_tests()],
)
def test_a_sweep_asserts_its_population_is_not_empty(
    module: str, name: str, population: list[str],
) -> None:
    """Clause two: a sweep that matched nothing must fail, not pass.

    Four of this suite's sixteen sweeps had no such assertion when this
    was written -- and the first draft of the detector said twenty of
    thirty-three, because it counted `ast.walk` as a filesystem walk.
    Reading what it had actually bound, rather than trusting the count,
    is the same discipline this module is about. Each was one renamed directory or changed
    suffix away from proving nothing while staying green — the same
    failure as the 292-result baseline that was diffed for four days
    before anyone noticed it was one broken line.

    The fix is one line and it is always the same: assert the collection
    is non-empty, with a message saying what it would mean if it were.
    """
    for module_name, node, names in _sweeping_tests():
        if module_name == module and node.name == name:
            missing = _unguarded(node, names)
            assert not missing, (
                f"{module}::{name} walks the filesystem to build "
                f"{population} and never asserts {sorted(missing)} found "
                "anything. If the walk matches nothing this test passes "
                "over an empty set and defends nothing"
            )
            return
    pytest.fail(f"{module}::{name} disappeared between collection and run")

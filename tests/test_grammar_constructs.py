"""Every control-flow construct in each grammar, against a second opinion.

This is the test that should have existed before any language shipped.

Until 2.11.0 each language's branch keywords were written from somebody's
knowledge of that language and checked against examples written from the
same knowledge. That is not evidence: it reads as evidence because the
prose around it is confident, which is worse than reading as a guess. The
measurable consequence was that Python — the language this project is
written in — agreed with an independent implementation on 45% of its own
declarations.

So each fixture here exercises the control-flow constructs its language's
specification defines, one function per construct, and the count is
compared against `lizard`: a separate implementation, by separate
authors, reading the same grammar.

**A disagreement does not say who is right.** Two implementations can
share a misconception. What it does is make the question unavoidable, and
send a reader to the grammar — which is the only authority either answers
to. Every disagreement found this way so far has been resolved *against*
this project:

- Go counted `select` as a decision beside its own cases. A `select` with
  two cases has two paths; the header decides nothing, exactly as a
  `switch` header does not. `select {}` with no cases simply blocks.
- Go counted `goto`, which transfers control unconditionally — an edge
  without a decision.
- Rust refused to count `?`, counted `loop`, and counted a wildcard
  match arm. PHP counted `?int` nullable type hints as ternaries and
  double-counted `do … while`.

Ruby is the one language whose keyword set survived this check unchanged,
and the only disagreement there runs the other way: lizard does not count
`unless`.

Both were added by a test written from the wrong intuition: it failed,
and the code was changed to satisfy the test rather than the grammar. The
C-family pattern had been measuring Go's select dispatch correctly all
along.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit.config import DEFAULT_CONFIG
from maintainability_audit.declarations import detect_functions

FIXTURES = Path(__file__).parent / "fixtures" / "grammar"
THRESHOLDS = DEFAULT_CONFIG["thresholds"]


#: Places this project deliberately counts differently, each with the
#: grammar reasoning that settles it. A divergence has to be *declared*
#: to be tolerated, which is what keeps this a check against the grammar
#: rather than a check against lizard — chasing a second implementation
#: is the same error as trusting the first, with an extra step.
DECLARED_DIVERGENCES: dict[str, dict[str, str]] = {
    ".php": {
        "wordOperators": (
            "lizard counts `&&` and `||` but not PHP's word forms. "
            "`and`, `or` and `xor` are short-circuit boolean operators "
            "that differ from the symbol forms only in precedence, so "
            "`$a and $b` has the same two paths as `$a && $b`. Counting "
            "one and not the other would make the score depend on which "
            "spelling a codebase prefers."
        ),
    },
    ".rb": {
        "unless_statement": (
            "lizard does not count `unless`, though it counts the "
            "modifier `if` in the fixture beside it — so this is not a "
            "parsing gap in its Ruby reader but a missing keyword. "
            "`unless cond` is `if !cond`: two paths, one decision. Ruby "
            "programmers reach for it constantly, and not counting it "
            "would make a guard-heavy method read as branchless."
        ),
    },
    ".rs": {
        "match_arms": (
            "lizard reads a whole `match` as one decision. Two real arms "
            "and a wildcard is three paths, which is the same shape as two "
            "`case`s and a `default` — and lizard already agrees with this "
            "project that Go's version of that is 3. The wildcard is not "
            "counted, as `default:` is not."
        ),
    },
}


def _bare(name: str) -> str:
    """The construct's own name, without whoever qualified it.

    The two tools qualify differently — lizard writes Java's methods as
    `Constructs::forLoop` and Rust's as plain `for_loop`, while this
    project writes `Store::get` for Rust and a bare name for Java. Both
    conventions are defensible and neither is what this test is about, so
    the comparison is on the trailing segment. `_no_two_constructs_share`
    keeps that from silently pairing the wrong functions.
    """
    for separator in ("::", "#", "."):
        name = name.rsplit(separator, 1)[-1]
    return name


def _no_two_constructs_share(names: list[str], where: str) -> None:
    bare = [_bare(name) for name in names]
    duplicates = {name for name in bare if bare.count(name) > 1}
    assert not duplicates, (
        f"{where} has constructs whose short names collide {sorted(duplicates)}; "
        "the comparison would pair the wrong functions"
    )


def _ours(path: Path) -> dict[str, int]:
    lines = path.read_text(encoding="utf-8").splitlines()
    found = detect_functions(path.parent, path, lines, THRESHOLDS)
    _no_two_constructs_share([m.name for m in found], f"{path.name} (ours)")
    return {_bare(metric.name): metric.complexity for metric in found}


def _lizard(path: Path) -> dict[str, int]:
    import lizard

    functions = lizard.analyze_file(str(path)).function_list
    _no_two_constructs_share([f.name for f in functions], f"{path.name} (lizard)")
    return {
        _bare(function.name): function.cyclomatic_complexity
        for function in functions
    }


def _fixtures() -> list[Path]:
    return sorted(FIXTURES.glob("constructs.*"))


def test_there_is_a_grammar_fixture_to_check() -> None:
    """An empty fixture directory would make every check below vacuous."""
    found = _fixtures()
    assert found, "no grammar fixture exists, so nothing is being compared"


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.suffix)
def test_every_construct_agrees_with_an_independent_implementation(
    fixture: Path,
) -> None:
    """Construct by construct, so a disagreement names the construct.

    One function per construct is the point: a whole-file total can be
    right by two errors cancelling, and a reader given "the file differs
    by 3" has nowhere to go.
    """
    ours, theirs = _ours(fixture), _lizard(fixture)
    assert theirs, f"lizard read no functions from {fixture.name}"

    declared = DECLARED_DIVERGENCES.get(fixture.suffix, {})
    differing = {
        name: (ours.get(name), theirs[name])
        for name in theirs
        if ours.get(name) != theirs[name] and name not in declared
    }
    assert not differing, (
        f"{fixture.name}: these constructs are counted differently.\n"
        + "\n".join(
            f"  {name}: ours={mine} lizard={other}"
            for name, (mine, other) in sorted(differing.items())
        )
        + "\nNeither number is authoritative. Take each to the grammar."
    )


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.suffix)
def test_the_fixture_covers_more_than_one_construct(fixture: Path) -> None:
    """A fixture with one function proves almost nothing.

    Stated because the cheapest way to make the check above pass is to
    shrink what it looks at.
    """
    assert len(_ours(fixture)) >= 5, (
        f"{fixture.name} exercises too few constructs to be evidence"
    )

@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.suffix)
def test_every_declared_divergence_is_still_real(fixture: Path) -> None:
    """A declaration that no longer diverges is a stale excuse.

    Left in place it would quietly permit a future disagreement on the
    same construct, which is the failure mode of every allowlist.
    """
    ours, theirs = _ours(fixture), _lizard(fixture)
    for name in DECLARED_DIVERGENCES.get(fixture.suffix, {}):
        assert name in theirs, (
            f"{fixture.name} declares a divergence for {name}, which "
            "lizard no longer reports"
        )
        assert ours.get(name) != theirs[name], (
            f"{fixture.name} declares a divergence for {name}, but the "
            "two now agree — remove the declaration"
        )

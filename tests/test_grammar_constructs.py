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

Ruby, Java, C, C++, Fortran and TypeScript survived the check unchanged.
Several disagreements run the other way, and one is worth naming: lizard
counts TypeScript's `title?: string` optional parameter as a decision —
the very defect this project fixed in its own pattern the same morning.
That is the argument for declaring divergences rather than chasing
them.

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
    ".f90": {
        "if_else": (
            "lizard counts one condition in `if … else if … end if`; "
            "there are two. Fortran's own reading strips `end if` before "
            "counting, which is why this project does not double it."
        ),
        "select_case": (
            "lizard counts the `select case` header and all three arms "
            "including `case default`. The arms carry the branch and a "
            "default is not a test, which is the same rule this project "
            "and lizard already agree on for Go and C."
        ),
        "where_construct": (
            "`where (mask) … end where` is a conditional construct in the "
            "standard — it assigns per element under a condition. lizard "
            "does not count it."
        ),
    },
    ".ts": {
        "optionalParameter": (
            "lizard counts `title?: string` as a decision. An optional "
            "parameter is a type-level marker and decides nothing — the "
            "exact defect this project fixed in its own C-family pattern, "
            "found here in the tool being checked against. Useful as a "
            "reminder that lizard is a second opinion and not an oracle."
        ),
    },
    ".swift": {
        "ternaryAndCoalesce": (
            "`(v ?? 0) > 0 ? 1 : 2` is two decisions: nil-coalescing "
            "short-circuits, and the ternary chooses. lizard scores one. "
            "`??` is counted here for the same reason `and` is counted in "
            "PHP — it is a real branch, whatever it is spelled."
        ),
    },
    ".js": {
        "ternaryAndCoalesce": (
            "A ternary and a `??` are two decisions; lizard scores three. "
            "D78 is the standing lesson on this line: `?.`, `??` and `?` "
            "are three different operators and counting them loosely made "
            "a complexity-1 function score 12. This project counts each "
            "once and optional chaining not at all."
        ),
    },
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
    ".py": {
        "match_statement": (
            "lizard counts the wildcard `case _` arm. It is Python's "
            "`default`: it always matches, so it adds a path without a "
            "decision to reach it. lizard already agrees with this "
            "project that Go's `default:` and the C family's `default:` "
            "are not counted, so counting Python's would make the same "
            "dispatch score differently depending on the language it "
            "happens to be written in."
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
    """Every fixture, and a hard stop if there are none.

    Raising here rather than returning `[]` is deliberate. These checks
    are parametrized over this list, and pytest marks an empty parameter
    set *skipped* — which exits 0, so every gate reads it as green. The
    falsifier gate caught exactly that: with the fixtures removed, the
    four checks D115, D119 and D120 cite reported a pass and defended
    nothing (D121).

    The `empty_parameter_set_mark` setting in `pyproject.toml` says the
    same thing suite-wide, and is not enough on its own **here**: the
    falsifier gate reverts every file except the ones defining the cited
    tests, so it reverts that setting too. A gate that reverts your
    configuration cannot be satisfied by configuration. The guard has to
    live in the file under test.
    """
    found = sorted(FIXTURES.glob("constructs.*"))
    if not found:
        raise RuntimeError(
            f"no grammar fixture exists in {FIXTURES}, so every construct "
            "check below would be parametrized over nothing and report a "
            "pass. Restore the fixtures rather than the checks."
        )
    return found


def test_there_is_a_grammar_fixture_to_check() -> None:
    """An empty fixture directory would make every check below vacuous."""
    found = _fixtures()
    assert found, "no grammar fixture exists, so nothing is being compared"


#: Branch readers with no independent implementation available to check
#: against. Named here rather than quietly skipped, because "checked only
#: against itself" is a limit of the evidence and belongs in the open —
#: the same reason the report says a language is outside the corpus.
NO_INDEPENDENT_IMPLEMENTATION: dict[str, str] = {
    "cobol_branch_points": (
        "lizard has no COBOL reader, and no other implementation this "
        "project can depend on offline reads fixed-format COBOL. The "
        "reader is checked against the standard's own list of scope "
        "terminators in `tests/test_cobol_declarations.py` and against "
        "nothing else."
    ),
}


def test_every_branch_reader_is_checked_against_a_second_opinion() -> None:
    """A fixture per *reader*, not per fixture directory.

    `test_there_is_a_grammar_fixture_to_check` only asks that the
    directory is non-empty, which twelve fixtures satisfy while a
    thirteenth language goes unchecked. That is precisely how Python —
    the language this project is written in, and the one that carried
    three of the eight defects 2.11.0 fixed — sat outside the grammar
    check while eleven other languages were being added to it.

    The reader is the thing that can be wrong, so the reader is the unit
    the coverage is counted in. A language with no second implementation
    available has to say so by name.
    """
    from maintainability_audit.declarations import (
        DECLARATION_SUFFIXES,
        metrics_for,
    )

    def reader(suffix: str) -> str:
        return metrics_for(suffix)[0].__name__       # type: ignore[attr-defined]

    used = {reader(suffix) for suffix in DECLARATION_SUFFIXES}
    checked = {reader(fixture.suffix) for fixture in _fixtures()}
    unchecked = used - checked - set(NO_INDEPENDENT_IMPLEMENTATION)
    assert not unchecked, (
        "these branch readers decide complexity for a supported language "
        f"and nothing independent checks them: {sorted(unchecked)}. Add a "
        "fixture under tests/fixtures/grammar/, or declare the reader in "
        "NO_INDEPENDENT_IMPLEMENTATION with the reason no second opinion "
        "exists."
    )


def test_no_declared_gap_actually_has_a_fixture() -> None:
    """A reader named as unchecked, that is in fact checked, is a stale excuse."""
    from maintainability_audit.declarations import metrics_for

    checked = {
        metrics_for(fixture.suffix)[0].__name__      # type: ignore[attr-defined]
        for fixture in _fixtures()
    }
    stale = checked & set(NO_INDEPENDENT_IMPLEMENTATION)
    assert not stale, (
        f"{sorted(stale)} are declared to have no independent "
        "implementation, but a grammar fixture checks them. Remove the "
        "declaration rather than leaving it to excuse a future gap."
    )


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

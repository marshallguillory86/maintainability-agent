"""Every decision token an independent reader counts is exercised here.

`test_grammar_constructs` compares our count against lizard's, construct
by construct, for the constructs a fixture happens to contain. That is
the right check and it has a blind spot with a track record: a construct
the fixture never contains is compared by nobody. D120 (Python's `case
_`), D125 (Go generic receivers), D126 (Ruby assigned openers), D127
(PHP's Elvis) and D128 (Rust `let ... else`) were all that shape — a
keyword set that was wrong about a construct no fixture exercised.

Python got a check for this after D120: `_python_branching_nodes` asks
`ast` which nodes branch and fails when the fixture stops exercising one.
The other twelve readers had no equivalent, because there is no stdlib
grammar to interrogate for Go or Fortran.

There is a second opinion, though, and this file uses it. `lizard`
publishes the decision tokens it counts per language, and the pinned
version makes that enumeration reproducible. It is not the language
specification — it is another implementation's reading of one, which is
exactly what a second source is for, and it is emphatically not the
author's memory. A token lizard counts and no fixture contains is the
blind spot, named.

Two escapes, because lizard's sets are not gospel either. A token can be
absent from the language entirely (`catch` in its C reader, inherited by
Go, which has no `catch`), or counted differently on purpose (this
project's arms-not-header rule). Both must be written down with a
reason; neither may be silent.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures" / "grammar"


def _fixtures() -> list[Path]:
    found = sorted(FIXTURES.glob("constructs.*"))
    assert found, (
        f"no grammar fixtures under {FIXTURES}, so every check in this file "
        "would collect nothing and report green. Absence read as a pass is "
        "the defect this project keeps finding in itself (D121)."
    )
    return found


def _lizard_conditions(name: str) -> set[str]:
    """The decision tokens lizard counts for this language."""
    import lizard

    reader = lizard.get_reader_for(name)
    if reader is None or not hasattr(reader, "_build_conditions"):
        return set()
    return set(reader._build_conditions())


#: Tokens lizard carries for a language that does not have them. Its
#: readers inherit from a C-like base, so `catch` reaches Go and Rust,
#: and `elseif` reaches JavaScript, none of which spell it that way.
#: Exercising them would mean writing code that does not compile.
ABSENT_FROM_LANGUAGE: dict[str, dict[str, str]] = {
    ".c": {"catch": "C has no exception handling"},
    ".go": {
        "catch": "Go recovers with `recover()`; there is no `catch`",
        "while": "Go's only loop keyword is `for`",
        "?": "Go has no ternary operator, by explicit language design",
    },
    ".rs": {"catch": "Rust has no `catch`; errors travel by `Result` and `?`"},
    ".js": {"elseif": "JavaScript spells it `else if`, two tokens"},
    ".ts": {"elseif": "TypeScript spells it `else if`, two tokens"},
    ".rb": {"elseif": "Ruby spells it `elsif`, which the fixture does exercise"},
}

#: Tokens lizard counts as decisions that this project deliberately does
#: not. Each is a judgment, and D119's argument is that a judgment
#: belongs in the open rather than inside a regex nobody reads.
COUNTED_DIFFERENTLY: dict[str, dict[str, str]] = {
    ".py": {
        "finally": "a `finally` block always runs, so it adds no path a "
                   "reader can take or miss; `try` is priced by its `except` "
                   "arms, which is the arms-not-header rule"
    },
    ".rb": {
        "ensure": "Ruby's `finally`, and excluded for the same reason: it "
                  "always runs. `rescue` is the arm that decides, and it is "
                  "counted"
    },
    ".rs": {
        "where": "a `where` clause constrains a generic bound at compile "
                 "time; it decides nothing at run time and no path depends "
                 "on it"
    },
}


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.suffix)
def test_every_token_an_independent_reader_counts_is_exercised(
    fixture: Path,
) -> None:
    """The blind spot in the construct comparison, closed.

    A keyword set can only be checked against a construct somebody wrote
    down. This asks a second implementation what constructs exist, so
    the list stops being the author's recollection — which is how five
    defects reached a release in code that had a comparison test the
    whole time.
    """
    conditions = _lizard_conditions(fixture.name)
    if not conditions:
        pytest.skip(f"lizard has no reader for {fixture.suffix}")

    text = fixture.read_text(encoding="utf-8")
    declared = {
        **ABSENT_FROM_LANGUAGE.get(fixture.suffix, {}),
        **COUNTED_DIFFERENTLY.get(fixture.suffix, {}),
    }

    missing = sorted(
        token
        for token in conditions
        if token not in declared
        and not re.search(
            rf"\b{re.escape(token)}\b" if token.isalpha() else re.escape(token),
            text,
        )
    )

    assert not missing, (
        f"{fixture.name} never exercises {missing}, which lizard counts as "
        "decisions for this language. Nothing compares our reading of them "
        "against anything. Add them to the fixture, or declare each in "
        "ABSENT_FROM_LANGUAGE or COUNTED_DIFFERENTLY with the reason."
    )


@pytest.mark.parametrize("fixture", _fixtures(), ids=lambda p: p.suffix)
def test_no_declaration_excuses_a_token_the_fixture_already_covers(
    fixture: Path,
) -> None:
    """Covers existing behaviour: this guards the escape tables above,
    not a reader. It passes at the base because no declaration was stale
    the day the tables were written — what it defends against is a future
    one, which is exactly when a stale excuse does its damage.

    A stale excuse is worse than none: it reads as a considered gap. The
    same shape as `test_no_declared_gap_actually_has_a_fixture` next
    door. An entry that stops being true has to be deleted rather than
    left to cover a future omission.
    """
    text = fixture.read_text(encoding="utf-8")
    declared = {
        **ABSENT_FROM_LANGUAGE.get(fixture.suffix, {}),
        **COUNTED_DIFFERENTLY.get(fixture.suffix, {}),
    }

    stale = sorted(
        token
        for token in declared
        if re.search(
            rf"\b{re.escape(token)}\b" if token.isalpha() else re.escape(token),
            text,
        )
    )

    assert not stale, (
        f"{fixture.name} exercises {stale}, which are declared as absent or "
        "deliberately uncounted. Remove the declaration rather than leaving "
        "it to excuse a future gap."
    )


def test_every_declaration_names_a_language_with_a_fixture() -> None:
    """Covers existing behaviour: a guard on the escape tables, which
    passes at the base because both were correct when written. It exists
    for the entry someone adds later for a language that has no fixture,
    where the declaration would read as a considered exemption while
    actually hiding that nothing checks the language at all.

    Neither table may name a suffix nothing checks.
    """
    suffixes = {fixture.suffix for fixture in _fixtures()}
    declared = set(ABSENT_FROM_LANGUAGE) | set(COUNTED_DIFFERENTLY)

    assert declared <= suffixes, (
        f"{sorted(declared - suffixes)} are declared but have no grammar "
        "fixture, so the declaration excuses nothing and hides that the "
        "language is unchecked."
    )


def test_a_reason_is_a_sentence_rather_than_a_shrug() -> None:
    """Covers existing behaviour: a guard on the escape tables, passing
    at the base because every reason written on the first day is a real
    one. It is here so the cheapest way past this file stays "exercise
    the token" rather than "declare it with an empty string".

    Both escapes cost a reason, so neither is cheaper than fixing it.
    """
    for table, label in ((ABSENT_FROM_LANGUAGE, "ABSENT_FROM_LANGUAGE"),
                         (COUNTED_DIFFERENTLY, "COUNTED_DIFFERENTLY")):
        for suffix, tokens in table.items():
            for token, reason in tokens.items():
                assert len(reason) > 25, (
                    f"{label}[{suffix}][{token}] says {reason!r}, which does "
                    "not explain anything to the next reader"
                )

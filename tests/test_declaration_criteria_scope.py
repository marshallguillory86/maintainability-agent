"""The declarations criterion set is checked per language — D137.

The rule the check defends is old and correct: the analyzer tier may
drive the `declarations` dimension only when its readings could have
failed a declaration on any of the three criteria the built-in path
fails on — cyclomatic complexity, declaration lines, cognitive
complexity. A rate built from two of three is not comparable to one
built from three, because every long-but-simple function passes by not
having been measured.

What was wrong was the *scope*. The check took the union of concepts
across every declaration in the repository and applied it to units that
are scored one at a time. The tools are per language and do not overlap:
`complexipy` reads Python and nothing else, `pmd` reads five languages
that do not include C, and `lizard` never reports cognitive complexity
at all. So a C repository holding one `setup.py` satisfied a check meant
to guarantee its C declarations were eligible to fail on all three, and
had them scored on two — silently, because the note explaining a
fallback was computed from the same union and therefore said nothing.

Split into its own file rather than added to `test_analyzer_bridge.py`,
which is 416 lines against the 500-line gate this tool enforces on
everyone else.
"""
from __future__ import annotations

import itertools

import pytest

from maintainability_audit._metrics_types import Measurement
from maintainability_audit._pressures import (
    analyzer_pressures,
    analyzer_production_pressures,
    declined_dimensions,
)


@pytest.fixture
def limits() -> dict:
    return {
        "warn_complexity": 8, "max_complexity": 15,
        "warn_function_lines": 40, "max_function_lines": 60,
        "warn_cognitive_complexity": 10, "max_cognitive_complexity": 20,
    }


def _lizard_unit(path: str, index: int, complexity: float = 5, lines: float = 20):
    """What lizard supplies: cyclomatic complexity and length, no cognitive."""
    unit = f"{path}:fn{index}"
    return [
        Measurement("cyclomatic_complexity", unit, complexity, "lizard", path, index),
        Measurement("declaration_lines", unit, lines, "lizard", path, index),
    ]


def _c_declarations(count: int) -> list[Measurement]:
    return [m for i in range(count) for m in _lizard_unit("decode.c", i)]


def _one_python_helper() -> list[Measurement]:
    """A `setup.py` with a single trivial function, as complexipy reads it."""
    return [
        *_lizard_unit("setup.py", 0, complexity=1, lines=3),
        Measurement("cognitive_complexity", "setup.py:fn0", 0, "complexipy",
                    "setup.py", 0),
    ]


def test_one_python_file_does_not_buy_the_criterion_for_c(limits: dict) -> None:
    """D137: the reproduction, as a test.

    Fifty C declarations lizard measured for complexity and length. No
    tool in the pool reports cognitive complexity for C, so they must
    fall back to the built-in tier. Adding a `setup.py` changes nothing
    about the C and must not change the verdict on it.

    Before the fix the second call returned 0.2451 — the C units in the
    MILD cyclomatic band averaged with the one clean Python unit,
    (50 * 0.25 + 0) / 51 — a confident rate over fifty declarations whose
    cognitive complexity was never read.
    """
    only_c = _c_declarations(50)
    with_helper = only_c + _one_python_helper()

    assert analyzer_pressures(only_c, limits)["declarations"] is None
    assert analyzer_pressures(with_helper, limits)["declarations"] is None
    assert analyzer_production_pressures(with_helper, limits)["declarations"] is None


def test_the_fallback_note_names_the_language_that_caused_it(limits: dict) -> None:
    """The reporting half of D137, which is the half a reader sees.

    `declined_dimensions` computed its missing concepts from the same
    repository-wide union, so it returned nothing whenever any language
    supplied the criterion. The C repository above was both scored on two
    criteria and silent about it, which is precisely what P8 forbids: a
    built-in fallback has to be attributable, not inferred from a number
    that is missing.
    """
    declined = declined_dimensions(_c_declarations(50) + _one_python_helper())

    assert len(declined) == 1
    entry = declined[0]
    assert entry["dimension"] == "declarations"
    assert entry["languages"] == ["C"]
    assert entry["missing_concepts"] == ["cognitive_complexity"]
    assert "C" in entry["reason"]
    assert "cognitive_complexity" in entry["reason"]


def test_an_incomplete_language_is_named_even_beside_a_complete_one(
    limits: dict,
) -> None:
    """Two languages, one measurable and one not.

    Java is complete — lizard supplies complexity and length, pmd
    supplies cognitive complexity for the same declarations. Fortran has
    no cognitive source at all. The repository falls back, and the note
    names Fortran rather than shrugging at the repository as a whole.
    """
    java = [
        *_lizard_unit("App.java", 0),
        Measurement("cognitive_complexity", "App.java:fn0", 4, "pmd", "App.java", 0),
    ]
    fortran = [m for i in range(5) for m in _lizard_unit("solver.f90", i)]

    assert analyzer_pressures(java + fortran, limits)["declarations"] is None

    declined = declined_dimensions(java + fortran)
    assert declined[0]["languages"] == ["Fortran"]


def test_two_tools_supply_one_language_between_them(limits: dict) -> None:
    """Covers existing behaviour: joining lizard and pmd across one
    language already worked, and this is the property the per-language
    scope had to preserve rather than introduce.

    It is pinned here because it is the exact case a careless fix breaks.
    Requiring one *tool* to supply all three, rather than one *language*,
    would read as a tightening and would silently delete Java's only
    complete reading — lizard reports no cognitive complexity anywhere,
    so no single tool in the pool satisfies the criterion set for any
    language except through this join.
    """
    java = [
        m
        for i in range(10)
        for m in (
            *_lizard_unit("App.java", i),
            Measurement("cognitive_complexity", f"App.java:fn{i}", 4, "pmd",
                        "App.java", i),
        )
    ]

    assert analyzer_pressures(java, limits)["declarations"] == pytest.approx(0.25)
    assert declined_dimensions(java) == ()


def test_a_reading_with_no_recognisable_language_gates_nothing(
    limits: dict,
) -> None:
    """Covers existing behaviour: a fully measured Java repository is
    measured, and stays measured when pmd also reports on its XML.

    The guard against the obvious wrong fix. Pooling every unmapped
    suffix into one bucket and demanding all three of it would fail this:
    pmd reports complexity for `beans.xml` and no declaration lines, so
    the bucket is permanently incomplete and every Java repository with a
    Spring config would fall back. A language that was never established
    cannot be missing a criterion, so unmapped units gate nothing —
    though they remain in the population exactly as before.
    """
    java = [
        m
        for i in range(10)
        for m in (
            *_lizard_unit("App.java", i),
            Measurement("cognitive_complexity", f"App.java:fn{i}", 4, "pmd",
                        "App.java", i),
        )
    ]
    xml = [
        Measurement("cyclomatic_complexity", "beans.xml:b", 1, "pmd", "beans.xml", 1),
        Measurement("cognitive_complexity", "beans.xml:b", 0, "pmd", "beans.xml", 1),
    ]

    assert analyzer_pressures(java + xml, limits)["declarations"] is not None
    assert declined_dimensions(java + xml) == ()


# ---------------------------------------------------------------------------
# The class, not the instance
# ---------------------------------------------------------------------------
#
# Five fixes to this bridge, and the first four were each a scenario a
# test did not contain: a sample of one, a Python-only concept mixed with
# a multi-language one, two formulas wearing one name, and complexity
# counted against three criteria. `test_analyzer_bridge` says in its own
# docstring that its tests exist "so the fifth number means something",
# and the fifth arrived anyway — because every fixture in it builds
# measurements for a single language, and D137 only appears when two
# languages are present and a tool covers one of them.
#
# So the checks below are not scenarios. They enumerate the claim's whole
# domain and assert the property over all of it, which is the only form
# that cannot be defeated by a shape nobody thought to write down.

_CRITERIA = ("cyclomatic_complexity", "declaration_lines", "cognitive_complexity")


def _parsed_languages() -> list[str]:
    """Every language this tool scores declarations for, from its own source."""
    from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES
    from maintainability_audit.declarations import DECLARATION_SUFFIXES

    named = {
        KNOWN_SOURCE_SUFFIXES[suffix]
        for suffix in DECLARATION_SUFFIXES
        if suffix in KNOWN_SOURCE_SUFFIXES
    }
    assert named, (
        "no parsed suffix maps to a language name, so the sweep below would "
        "assert over nothing"
    )
    return sorted(named)


def _suffix_for(language: str) -> str:
    from maintainability_audit._metrics_types import KNOWN_SOURCE_SUFFIXES

    return next(s for s, name in KNOWN_SOURCE_SUFFIXES.items() if name == language)


@pytest.mark.parametrize("language", _parsed_languages())
@pytest.mark.parametrize(
    "supplied",
    [
        subset
        for size in range(len(_CRITERIA) + 1)
        for subset in itertools.combinations(_CRITERIA, size)
    ],
)
def test_every_language_is_scored_only_on_a_complete_criterion_set(
    language: str, supplied: tuple[str, ...], limits: dict
) -> None:
    """Covers existing behaviour: for a repository of **one** language the
    union check and the per-language check agree, so every case here
    passed before D137 was fixed. It pins the invariant rather than the
    fix, deliberately, and is not cited as a falsifier for it —
    `test_no_other_language_can_supply_a_missing_criterion` is the one
    that fails at the base, because the defect needs two languages to
    appear at all.

    What this defends is the *next* variant. The claim is one sentence —
    a declaration may be scored by the analyzer tier only when its own
    language was measured on all three criteria — and this asserts that
    sentence over the whole domain: every language in
    `DECLARATION_SUFFIXES` by every subset of the three, generated rather
    than written. There are no fixtures to be unrepresentative.

    Demonstrated rather than claimed: injecting a single-language
    exemption (`language != 'Swift'`) into the completeness check passes
    all three instance tests in this file and fails six cases here. That
    is the shape the previous four fixes to this bridge were defeated by
    — a combination nobody wrote down.
    """
    path = f"unit{_suffix_for(language)}"
    unit = f"{path}:fn0"
    values = {"cyclomatic_complexity": 5.0, "declaration_lines": 20.0,
              "cognitive_complexity": 4.0}
    measurements = [
        Measurement(concept, unit, values[concept], "tool", path, 0)
        for concept in supplied
    ]

    scored = analyzer_pressures(measurements, limits)["declarations"] is not None

    assert scored == (set(supplied) == set(_CRITERIA)), (
        f"{language} with {sorted(supplied)} was "
        f"{'scored' if scored else 'not scored'}; the analyzer tier may score a "
        "declaration only when its own language carries all three criteria"
    )


def test_no_other_language_can_supply_a_missing_criterion(limits: dict) -> None:
    """The D137 mechanism, swept rather than sampled.

    For every parsed language, take a complete reading of it and pair it
    with a language missing exactly one criterion. The complete one must
    never lend what the incomplete one lacks — which is the union bug in
    its general form, not the C-plus-`setup.py` instance that found it.
    """
    languages = _parsed_languages()
    complete_language = languages[0]
    complete_path = f"whole{_suffix_for(complete_language)}"
    complete = [
        Measurement(concept, f"{complete_path}:fn0", 5.0, "tool", complete_path, 0)
        for concept in _CRITERIA
    ]

    for language in languages[1:]:
        for withheld in _CRITERIA:
            path = f"partial{_suffix_for(language)}"
            partial = [
                Measurement(concept, f"{path}:fn0", 5.0, "tool", path, 0)
                for concept in _CRITERIA if concept != withheld
            ]

            assert analyzer_pressures(complete + partial, limits)["declarations"] is None, (
                f"{complete_language} lent {withheld} to {language}"
            )

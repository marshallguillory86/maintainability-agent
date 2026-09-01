"""Where a Java declaration starts and where its body actually ends.

Java is recognised and not scored — `docs/architecture.md` says so under
Known debt. The first thing missing is the thing every other language
here needed first: a range detector that ends a declaration at its own
closing brace.

Why not reuse what exists. `FUNC_PATTERNS`, the last-resort scan, matches
`def`, `function` and arrows. Pointed at Java it finds nothing, reports
zero methods, and a zero that came from looking in the wrong language is
indistinguishable in the report from a file with no methods in it. That
is worse than not scoring Java at all, because it looks measured. So
this is a real detector or it is nothing.

The property that matters is the one this project bought expensively in
TypeScript: **a declaration this module fails to recognise costs one
missed finding, never a cascade of false ones.** Ranges end at their own
brace, never at the next match. A 4-line method must not be reported as
262 lines because the pattern list missed the declaration after it.

This tests the detector directly. Wiring (suffix, include, dispatch)
is held by `test_java_wiring.py` and `test_java_scored.py`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._ranges_java import java_declaration_ranges

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "java"
RangeMap = dict[tuple[str, int], tuple[int, int, str]]


def _lines(name: str) -> list[str]:
    return (FIXTURES / name).read_text(encoding="utf-8").splitlines()


def _ranges(name: str) -> RangeMap:
    """Declarations by (name, start), as (start, end, kind)."""
    found, _masked = java_declaration_ranges(_lines(name))
    return {
        (item.name, item.start): (item.start, item.end, item.kind)
        for item in found
    }


def _names(found: RangeMap) -> set[str]:
    return {name for name, _start in found}


def _range(found: RangeMap, name: str) -> tuple[int, int, str]:
    matches = [value for (candidate, _start), value in found.items() if candidate == name]
    assert len(matches) == 1, f"expected one {name!r} declaration, found {len(matches)}"
    return matches[0]


def _line_of(name: str, needle: str) -> int:
    """1-based line carrying `needle`, so the fixtures stay editable.

    Hard-coded line numbers would make every assertion below a puzzle
    about which blank line moved.
    """
    for number, text in enumerate(_lines(name), start=1):
        if needle in text:
            return number
    raise AssertionError(f"{name} has no line containing {needle!r}")


def test_each_method_is_bounded_by_its_own_body() -> None:
    """Two methods, two ranges, neither running into the other.

    The failure this forbids is the TypeScript one: `first` ending where
    `second` begins, or at end-of-file, because the detector derived one
    declaration's end from the next declaration's start.
    """
    found = _ranges("TwoMethods.java")

    assert _names(found) >= {"first", "second"}, f"methods not found: {sorted(found)}"

    first_start, first_end, kind = _range(found, "first")
    assert kind == "function"
    assert first_start == _line_of("TwoMethods.java", "public int first")
    # The method's own closing brace, not the class's and not the file's.
    assert first_end == _line_of("TwoMethods.java", "return -value") + 1

    second_start, second_end, _ = _range(found, "second")
    assert second_start == _line_of("TwoMethods.java", "public String second")
    assert second_end == _line_of("TwoMethods.java", 'return "ok"') + 1
    assert first_end < second_start, "the first method swallowed the second"


def test_the_enclosing_type_is_its_own_declaration() -> None:
    """A class is a container, and is measured as one.

    It spans its members — that is what a container does, and Python's
    `ast` reports the same — but it is reported as a `class` so the
    per-function line budget is never applied to it.
    """
    found = _ranges("TwoMethods.java")

    start, end, kind = _range(found, "TwoMethods")
    assert kind == "class"
    assert start == _line_of("TwoMethods.java", "public class TwoMethods")
    assert end == len(_lines("TwoMethods.java"))


def test_a_constructor_is_a_declaration() -> None:
    """It has no return type, which is exactly why it gets missed.

    Every method pattern keyed on `Type name(` skips constructors, and a
    constructor is often the longest thing in a class.
    """
    found = _ranges("Widget.java")

    class_line = _line_of("Widget.java", "public class Widget")
    constructor_line = _line_of("Widget.java", "public Widget(int size)")

    class_start, class_end, class_kind = found[("Widget", class_line)]
    assert class_kind == "class"
    assert class_start == class_line
    assert class_end == len(_lines("Widget.java"))

    constructor_start, _constructor_end, constructor_kind = found[
        ("Widget", constructor_line)
    ]
    assert constructor_kind == "function"
    assert constructor_start == constructor_line

    # The field declaration above it is not a declaration of this kind.
    assert "size" in _names(found), "the accessor method was lost"
    assert _range(found, "size")[0] == _line_of("Widget.java", "public int size()")


def test_a_nested_type_is_its_own_range() -> None:
    """The inner type is found, and the method inside it is too.

    A detector that skips a type's body to avoid re-matching its
    contents loses every nested declaration; one that never skips
    reports method bodies as declarations. The inner class and its
    method both have to survive.
    """
    found = _ranges("Outer.java")

    assert _names(found) >= {"Outer", "Inner", "outerMethod", "innerMethod"}, (
        f"nested declarations lost: {sorted(found)}"
    )

    inner_start, inner_end, kind = _range(found, "Inner")
    assert kind == "class"
    assert inner_start == _line_of("Outer.java", "static final class Inner")
    # Ends at its own brace, one line before the outer class closes.
    assert inner_end < _range(found, "Outer")[1], (
        "the inner type ran to the outer type's end"
    )

    method_start, method_end, _ = _range(found, "innerMethod")
    assert inner_start < method_start and method_end <= inner_end, (
        "the nested method is not inside its own type"
    )


def test_a_generic_signature_does_not_end_at_the_first_angle_bracket() -> None:
    """`<T extends Comparable<T>>` is not the end of anything.

    A detector that treats `>` as a terminator, or that lets the generic
    parameter list confuse the name, reports `sorted` starting in the
    wrong place or not at all.
    """
    found = _ranges("Generics.java")

    assert "sorted" in _names(found), f"the generic method was not found: {sorted(found)}"
    start, end, kind = _range(found, "sorted")
    assert kind == "function"
    assert start == _line_of("Generics.java", "public <T extends Comparable<T>> List<T> sorted")
    assert end == _line_of("Generics.java", "return items") + 1

    # A generic *return* type is the same trap facing the other way.
    assert "index" in _names(found)
    assert _range(found, "index")[0] == _line_of(
        "Generics.java", "Map<String, List<Integer>> index"
    )


@pytest.mark.parametrize("ghost", ["SuppressWarnings", "Override", "Deprecated"])
def test_an_annotation_is_never_a_declaration(ghost: str) -> None:
    """`@Deprecated(since = "1.2")` has the shape `name(...)` and is not one.

    An annotation carrying a value is the case that looks most like a
    method signature. Counting it would inflate the declaration
    population with things that are not declarations — a rate computed
    over a denominator of annotations is the founding defect of this
    project wearing a new hat.
    """
    found = _ranges("Annotated.java")

    assert ghost not in _names(found), f"annotation @{ghost} was reported as a declaration"


def test_the_annotated_methods_themselves_are_still_found() -> None:
    """Rejecting annotations must not reject what they decorate."""
    found = _ranges("Annotated.java")

    assert _names(found) >= {"toString", "legacy"}, (
        f"annotated methods were lost with their annotations: {sorted(found)}"
    )
    assert _range(found, "toString")[0] == _line_of(
        "Annotated.java", "public String toString()"
    )
    assert _range(found, "legacy")[0] == _line_of("Annotated.java", "public int legacy()")


def test_no_range_runs_past_the_end_of_the_file() -> None:
    """The cascade guard, over every fixture.

    Cheap, and it is the exact shape of the defect that made this
    approach necessary: a declaration whose end was derived from
    something other than its own body ran to end-of-file.
    """
    for fixture in sorted(FIXTURES.glob("*.java")):
        total = len(_lines(fixture.name))
        found, _masked = java_declaration_ranges(_lines(fixture.name))
        assert found, f"{fixture.name} produced no declarations at all"
        for item in found:
            assert 1 <= item.start <= item.end <= total, (
                f"{fixture.name}: {item.name} spans {item.start}-{item.end} of {total}"
            )

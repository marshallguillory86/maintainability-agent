"""The C# declaration scanner (1.3.0): methods, constructors and types.

C# is the closest of the family to Java — types holding members,
generics written the same way, attributes where Java writes annotations
— and the differences are exactly what these tests pin: namespaces in
both their braced and file-scoped forms, `record`, and the two member
shapes that must *not* mint declarations, a property and a
parameterless expression-bodied member.

The walk is `scan_bounded` from `_ranges_core`, shared with C, C++ and
Java, so what is tested here is what C# recognises.
"""

from __future__ import annotations

from maintainability_audit._ranges_csharp import csharp_declaration_ranges


def _ranges(src: str) -> list[tuple[int, int, str, str]]:
    got, _masked = csharp_declaration_ranges(src.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in got]


def test_a_class_is_descended_into_and_its_methods_are_graded() -> None:
    src = (
        "public class Widget\n"
        "{\n"
        "    public void Draw()\n"
        "    {\n"
        "        Paint();\n"
        "    }\n"
        "    public int Area() { return 1; }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 8, "Widget", "class"),
        (3, 6, "Draw", "function"),
        (7, 7, "Area", "function"),
    ]


def test_a_property_is_not_a_declaration() -> None:
    """The population this scanner refuses to inflate.

    `public int Count { get; set; }` has braces and would bound
    cleanly. An ordinary C# tree holds thousands of them, each one line
    long, and counting them would dilute the population every
    declaration rate divides by with members nobody maintains.
    """
    src = (
        "public class W\n"
        "{\n"
        "    public int Count { get; set; }\n"
        "    public string Name { get; init; }\n"
        "    public int Area => width * height;\n"
        "    public int Real() { return 1; }\n"
        "}\n"
    )
    assert _ranges(src) == [(1, 7, "W", "class"), (6, 6, "Real", "function")]


def test_a_braced_namespace_is_walked_into_but_not_graded() -> None:
    src = (
        "namespace Geo\n"
        "{\n"
        "    public class W\n"
        "    {\n"
        "        public void Go() { Run(); }\n"
        "    }\n"
        "}\n"
    )
    assert _ranges(src) == [(3, 6, "W", "class"), (5, 5, "Go", "function")]


def test_a_file_scoped_namespace_declares_nothing() -> None:
    """C# 10's `namespace Geo;` has no body at all. It must not be read
    as a declaration, and must not swallow what follows it."""
    src = (
        "namespace Geo;\n"
        "\n"
        "public class W\n"
        "{\n"
        "    public void Go() { Run(); }\n"
        "}\n"
    )
    assert _ranges(src) == [(3, 6, "W", "class"), (5, 5, "Go", "function")]


def test_attributes_do_not_become_declarations() -> None:
    """`[Obsolete("x")]` is an identifier with a parameter list, which is
    the shape of a method — the C# form of the annotation case Java had."""
    src = (
        "[Obsolete(\"x\")]\n"
        "public class W\n"
        "{\n"
        "    [Test]\n"
        "    public void Go() { Run(); }\n"
        "}\n"
    )
    assert _ranges(src) == [(2, 6, "W", "class"), (5, 5, "Go", "function")]


def test_a_constructor_chain_and_a_destructor_are_declarations() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public W(int n) : base(n)\n"
        "    {\n"
        "        count_ = n;\n"
        "    }\n"
        "    ~W() { Cleanup(); }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 8, "W", "class"),
        (3, 6, "W", "function"),
        (7, 7, "~W", "function"),
    ]


def test_generics_and_constraints_do_not_confuse_the_name() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public List<T> Sort<T>(List<T> items) where T : IComparable\n"
        "    {\n"
        "        return items;\n"
        "    }\n"
        "    public async Task<int> GetAsync(string key)\n"
        "    {\n"
        "        return 1;\n"
        "    }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 11, "W", "class"),
        (3, 6, "Sort", "function"),
        (7, 10, "GetAsync", "function"),
    ]


def test_an_expression_bodied_method_is_a_declaration() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public int Fast() => count_;\n"
        "    public void Go() { Run(); }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 5, "W", "class"),
        (3, 3, "Fast", "function"),
        (4, 4, "Go", "function"),
    ]


def test_interface_members_and_positional_records_are_bodyless() -> None:
    """Shapes with nothing to measure. Grading them would put one-line
    members into the population every rate divides by."""
    src = (
        "public interface IShape\n"
        "{\n"
        "    double Area();\n"
        "    void Draw();\n"
        "}\n"
        "public record Point(int X, int Y);\n"
    )
    assert _ranges(src) == [(1, 5, "IShape", "class")]


def test_every_type_keyword_is_a_type() -> None:
    src = (
        "public class C1 { }\n"
        "public interface I1 { }\n"
        "public struct S1 { }\n"
        "public enum E1 { A, B }\n"
        "public record R1 { }\n"
        "public record struct R2 { }\n"
    )
    assert [(r[2], r[3]) for r in _ranges(src)] == [
        ("C1", "class"), ("I1", "class"), ("S1", "class"),
        ("E1", "class"), ("R1", "class"), ("R2", "class"),
    ]


def test_control_flow_and_calls_are_not_declarations() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public void Run(int n)\n"
        "    {\n"
        "        if (n > 0) { Go(); }\n"
        "        foreach (var x in items) { Use(x); }\n"
        "        lock (gate) { Touch(); }\n"
        "        var v = Compute();\n"
        "        while (n > 0) { n--; }\n"
        "    }\n"
        "}\n"
    )
    assert _ranges(src) == [(1, 11, "W", "class"), (3, 10, "Run", "function")]


def test_a_range_never_runs_past_its_own_body() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public void First() { A(); }\n"
        "    public void Second() { B(); }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 5, "W", "class"),
        (3, 3, "First", "function"),
        (4, 4, "Second", "function"),
    ]


def test_an_unclosed_body_falls_back_to_indentation() -> None:
    """Braces that never close cost one declaration, never the file."""
    src = (
        "public class W {\n"
        "    public void Broken() {\n"
        "        A();\n"
        "\n"
        "    public void After() { B(); }\n"
    )
    ranges = _ranges(src)

    broken = [r for r in ranges if r[2] == "Broken"]
    assert broken, "the declaration with the unclosed body was not bounded at all"
    assert broken[0][1] < len(src.splitlines()), "the range ran to end-of-file"


def test_an_unclosed_allman_body_is_skipped_rather_than_guessed() -> None:
    """The same damage, in the shape that reads as bodyless.

    With the brace on its own line and never closed, there is nothing to
    tell this signature from a declaration with no body — so it is
    skipped. That is the direction this design errs in, and the
    declaration after it is still found, which is the property that
    matters: one loss, not a cascade.
    """
    src = (
        "public void Broken()\n"
        "{\n"
        "    A();\n"
        "\n"
        "public void After() { B(); }\n"
    )
    assert [r[2] for r in _ranges(src)] == ["After"]


def test_a_brace_in_a_string_or_comment_does_not_desync() -> None:
    src = (
        "public class W\n"
        "{\n"
        "    public void F()\n"
        "    {\n"
        '        var s = "a { b } c";\n'
        "        // an unbalanced } here\n"
        "    }\n"
        "    public void G() { H(); }\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 9, "W", "class"),
        (3, 7, "F", "function"),
        (8, 8, "G", "function"),
    ]


def test_the_preprocessor_is_not_a_declaration() -> None:
    src = (
        "#if DEBUG\n"
        "#endif\n"
        "public class W\n"
        "{\n"
        "    public void Go() { Run(); }\n"
        "}\n"
    )
    assert _ranges(src) == [(3, 6, "W", "class"), (5, 5, "Go", "function")]

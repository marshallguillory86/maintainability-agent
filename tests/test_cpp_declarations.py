"""The C++ declaration scanner (1.2.0): functions, methods and types.

C++ takes one rule from each neighbour. Types are **descended into**, as
in Java, because a class holds its methods. Bodyless signatures are
**skipped**, as in C, because a header full of declarations is a set of
shapes and not a population.

The walk itself is `scan_bounded` from `_ranges_core`, shared with C and
Java, so these tests are about what C++ *recognises*: namespaces,
templates, operator overloads, out-of-line definitions, constructors
with initialiser lists — and the two shapes that must never mint a
declaration, a macro invocation and a control-flow header.
"""

from __future__ import annotations

from maintainability_audit._ranges_cpp import cpp_declaration_ranges


def _ranges(src: str) -> list[tuple[int, int, str, str]]:
    got, _masked = cpp_declaration_ranges(src.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in got]


def test_a_class_is_descended_into_and_its_methods_are_graded() -> None:
    src = (
        "class Widget {\n"
        "public:\n"
        "    void draw() const {\n"
        "        paint();\n"
        "    }\n"
        "    int area() {\n"
        "        return 1;\n"
        "    }\n"
        "};\n"
    )
    assert _ranges(src) == [
        (1, 9, "Widget", "class"),
        (3, 5, "draw", "function"),
        (6, 8, "area", "function"),
    ]


def test_an_access_specifier_is_not_a_declaration() -> None:
    src = (
        "class W {\n"
        "public:\n"
        "private:\n"
        "protected:\n"
        "    void go() { run(); }\n"
        "};\n"
    )
    assert _ranges(src) == [(1, 6, "W", "class"), (5, 5, "go", "function")]


def test_a_namespace_is_walked_into_but_never_graded() -> None:
    """A namespace holds declarations and is not one anybody maintains."""
    src = (
        "namespace geo {\n"
        "int add(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
        "}\n"
    )
    assert _ranges(src) == [(2, 4, "add", "function")]


def test_a_bodyless_declaration_is_not_a_definition() -> None:
    """A header of declarations is a set of shapes, not a population:
    prototypes, pure virtuals and `= default` all have no body."""
    src = (
        "class W {\n"
        "public:\n"
        "    W();\n"
        "    ~W() = default;\n"
        "    virtual int area() const = 0;\n"
        "    void draw();\n"
        "    int real() { return 1; }\n"
        "};\n"
    )
    assert _ranges(src) == [(1, 8, "W", "class"), (7, 7, "real", "function")]


def test_an_out_of_line_definition_keeps_its_qualified_name() -> None:
    """`void Widget::draw()` is reported as `Widget::draw` — the name a
    reader searches for, and the one that distinguishes it from another
    class's `draw`."""
    src = (
        "void geo::Widget::helper(int n)\n"
        "{\n"
        "    work(n);\n"
        "}\n"
        "geo::Widget::Widget() : ready_(0) {\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 4, "geo::Widget::helper", "function"),
        (5, 6, "geo::Widget::Widget", "function"),
    ]


def test_an_operator_overload_is_a_declaration() -> None:
    src = (
        "class W {\n"
        "    W& operator=(const W& other) {\n"
        "        return *this;\n"
        "    }\n"
        "    bool operator==(const W& other) const {\n"
        "        return true;\n"
        "    }\n"
        "};\n"
    )
    assert _ranges(src) == [
        (1, 8, "W", "class"),
        (2, 4, "operator=", "function"),
        (5, 7, "operator==", "function"),
    ]


def test_a_template_header_does_not_hide_what_follows() -> None:
    src = (
        "template <typename T>\n"
        "class Stack {\n"
        "    void push(T v) {\n"
        "        items_.push_back(v);\n"
        "    }\n"
        "};\n"
        "template <typename T> T identity(T v) {\n"
        "    return v;\n"
        "}\n"
    )
    assert _ranges(src) == [
        (2, 6, "Stack", "class"),
        (3, 5, "push", "function"),
        (7, 9, "identity", "function"),
    ]


def test_struct_union_and_scoped_enum_are_types() -> None:
    src = (
        "struct Point {\n"
        "    int x;\n"
        "};\n"
        "union Value { int i; float f; };\n"
        "enum class Color { RED, GREEN };\n"
        "enum Plain { A, B };\n"
    )
    assert _ranges(src) == [
        (1, 3, "Point", "class"),
        (4, 4, "Value", "class"),
        (5, 5, "Color", "class"),
        (6, 6, "Plain", "class"),
    ]


def test_a_base_clause_does_not_end_the_type_name() -> None:
    src = (
        "class Widget final : public Base, private Mixin {\n"
        "    void go() { run(); }\n"
        "};\n"
    )
    assert _ranges(src) == [(1, 3, "Widget", "class"), (2, 2, "go", "function")]


def test_allman_bracing_is_bounded_like_any_other() -> None:
    src = (
        "static int add(int a, int b)\n"
        "{\n"
        "    return a + b;\n"
        "}\n"
        "int after() { return 0; }\n"
    )
    assert _ranges(src) == [
        (1, 4, "add", "function"),
        (5, 5, "after", "function"),
    ]


def test_a_macro_invocation_never_swallows_the_next_declaration() -> None:
    """The falsifier for the over-report this scanner nearly shipped.

    `MY_MACRO(x)` has the shape of an Allman signature: a name, a
    parameter list, then end of line. Accepting it let the *next* line's
    braces close it, so the macro was reported as a function and the real
    function underneath it disappeared — an invented declaration hiding a
    true one, which is worse than missing both.
    """
    src = (
        "MY_MACRO(x)\n"
        "int main() { return 0; }\n"
    )
    assert _ranges(src) == [(2, 2, "main", "function")]


def test_control_flow_and_casts_are_not_declarations() -> None:
    src = (
        "void run(int n) {\n"
        "    if (n) { go(); }\n"
        "    for (int i = 0; i < n; i++) { step(i); }\n"
        "    auto v = static_cast<int>(n);\n"
        "    while (n) { n--; }\n"
        "}\n"
    )
    assert _ranges(src) == [(1, 6, "run", "function")]


def test_a_field_initialised_from_a_call_is_not_a_declaration() -> None:
    src = (
        "class W {\n"
        "    int size_ = compute();\n"
        "    Helper helper_{make()};\n"
        "    void go() { run(); }\n"
        "};\n"
    )
    assert _ranges(src) == [(1, 5, "W", "class"), (4, 4, "go", "function")]


def test_the_preprocessor_is_not_a_function() -> None:
    src = (
        "#include <string>\n"
        "#define SQ(x) ((x)*(x))\n"
        "int use(int a) {\n"
        "    return SQ(a);\n"
        "}\n"
    )
    assert _ranges(src) == [(3, 5, "use", "function")]


def test_a_range_never_runs_past_its_own_body() -> None:
    src = (
        "void first() {\n"
        "    a();\n"
        "}\n"
        "void second() {\n"
        "    b();\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 3, "first", "function"),
        (4, 6, "second", "function"),
    ]


def test_an_unclosed_body_falls_back_to_indentation() -> None:
    src = (
        "void broken() {\n"
        "    a();\n"
        "\n"
        "void after() { b(); }\n"
    )
    ranges = _ranges(src)

    assert ranges
    assert ranges[0][2] == "broken"
    assert ranges[0][1] < len(src.splitlines()), "the range ran to end-of-file"


def test_a_brace_in_a_string_or_comment_does_not_desync() -> None:
    src = (
        "void f() {\n"
        '    std::string s = "a { b } c";\n'
        "    /* an unbalanced } here */\n"
        "}\n"
        "void g() { h(); }\n"
    )
    assert _ranges(src) == [(1, 4, "f", "function"), (5, 5, "g", "function")]

"""The C declaration scanner (1.1.0): file-scope functions and
`struct`/`enum`/`union` types, each bounded by its own body.

C is brace-delimited like Java, so `c_declaration_ranges` reuses the same
brace-bounding primitives it imports from `_ranges_core` (`_block_end`,
`_is_bare_signature`, `indent_bounded_end`). These tests hold the C-specific behaviour: the
preprocessor is not a function, a prototype is not a definition, and — the
guarantee `_ranges_core` exists for — a declaration's range
never runs past its own body into the next one.
"""

from __future__ import annotations

from maintainability_audit._ranges_c import c_declaration_ranges


def _ranges(src: str) -> list[tuple[int, int, str, str]]:
    got, _masked = c_declaration_ranges(src.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in got]


def test_a_function_is_bounded_by_its_own_braces() -> None:
    src = (
        "int add(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    assert _ranges(src) == [(1, 3, "add", "function")]


def test_a_range_never_runs_past_its_own_body_into_the_next() -> None:
    """The falsifier the module exists for: two functions are two ranges,
    not one that absorbs the rest of the file (the TS-client bug in C form)."""
    src = (
        "int first(void) {\n"
        "    return 1;\n"
        "}\n"
        "\n"
        "int second(void) {\n"
        "    return 2;\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 3, "first", "function"),
        (5, 7, "second", "function"),
    ]


def test_control_flow_inside_a_body_is_not_a_declaration() -> None:
    """`if (...)` / `for (...)` share the `name(` shape but must never mint a
    declaration; the body is stepped over, so they are never even offered."""
    src = (
        "int classify(int n) {\n"
        "    if (n > 0) {\n"
        "        return 1;\n"
        "    }\n"
        "    for (int i = 0; i < n; i++) {\n"
        "        n += i;\n"
        "    }\n"
        "    while (n) { n--; }\n"
        "    return n;\n"
        "}\n"
    )
    assert _ranges(src) == [(1, 10, "classify", "function")]


def test_a_prototype_is_not_a_definition() -> None:
    """A declaration with no body mints no population (P7)."""
    src = (
        "int add(int a, int b);\n"
        "long compute(void);\n"
        "int add(int a, int b) {\n"
        "    return a + b;\n"
        "}\n"
    )
    assert _ranges(src) == [(3, 5, "add", "function")]


def test_the_preprocessor_is_not_a_function() -> None:
    """`#define MAX(a, b) ...` is function-shaped but is a macro, and
    `#include`/`#ifdef` are not declarations either."""
    src = (
        "#include <stdio.h>\n"
        "#define MAX(a, b) ((a) > (b) ? (a) : (b))\n"
        "#ifdef DEBUG\n"
        "#endif\n"
        "int use(int a, int b) {\n"
        "    return MAX(a, b);\n"
        "}\n"
    )
    assert _ranges(src) == [(5, 7, "use", "function")]


def test_struct_enum_and_union_are_types() -> None:
    src = (
        "struct Point {\n"
        "    int x;\n"
        "    int y;\n"
        "};\n"
        "enum Color { RED, GREEN, BLUE };\n"
        "union Value {\n"
        "    int i;\n"
        "    float f;\n"
        "};\n"
    )
    assert _ranges(src) == [
        (1, 4, "Point", "class"),
        (5, 5, "Color", "class"),
        (6, 9, "Value", "class"),
    ]


def test_a_typedef_struct_keeps_its_tag_name() -> None:
    src = (
        "typedef struct Node {\n"
        "    int val;\n"
        "    struct Node *next;\n"
        "} Node;\n"
    )
    assert _ranges(src) == [(1, 4, "Node", "class")]


def test_a_pointer_return_type_yields_the_function_name_not_the_type() -> None:
    """`const char *greeting(` names `greeting`, not something from the type."""
    src = (
        "static const char *greeting(void) {\n"
        '    return "hi";\n'
        "}\n"
        "struct Node *find(struct Node *head, int key) {\n"
        "    return head;\n"
        "}\n"
    )
    assert _ranges(src) == [
        (1, 3, "greeting", "function"),
        (4, 6, "find", "function"),
    ]


def test_a_variable_of_struct_type_is_not_a_type_declaration() -> None:
    """`struct Foo bar;` declares a variable, and `struct Foo;` forward-declares
    — neither opens a body, so neither is counted."""
    src = (
        "struct Foo;\n"
        "struct Foo bar;\n"
        "int real(void) { return 0; }\n"
    )
    assert _ranges(src) == [(3, 3, "real", "function")]


def test_an_allman_brace_still_bounds_the_function() -> None:
    """The opening brace on its own line is ordinary C style, not a
    prototype. Getting this wrong would silently halve the population on
    most real C, so it is pinned rather than assumed."""
    src = (
        "int add(int a, int b)\n"
        "{\n"
        "    return a + b;\n"
        "}\n"
        "int after(void) { return 0; }\n"
    )
    assert _ranges(src) == [
        (1, 4, "add", "function"),
        (5, 5, "after", "function"),
    ]


def test_a_signature_split_over_several_lines_is_one_declaration() -> None:
    src = (
        "int add(\n"
        "    int a,\n"
        "    int b)\n"
        "{\n"
        "    return a + b;\n"
        "}\n"
        "int after(void) { return 0; }\n"
    )
    assert _ranges(src) == [
        (1, 6, "add", "function"),
        (7, 7, "after", "function"),
    ]


def test_a_kr_definition_is_missed_but_costs_only_itself() -> None:
    """Old-style K&R parameter declarations sit between the signature and
    the body, and the scanner does not read them. It under-reports by one
    declaration — the next function is still found, which is the trade
    this design makes everywhere."""
    src = (
        "int add(a, b)\n"
        "    int a;\n"
        "    int b;\n"
        "{\n"
        "    return a + b;\n"
        "}\n"
        "int after(void) { return 0; }\n"
    )
    assert _ranges(src) == [(7, 7, "after", "function")]


def test_an_array_initializer_is_not_a_declaration() -> None:
    """`static const struct opt opts[] = {` opens a brace and names a
    struct, and is a variable — neither a function nor a type."""
    src = (
        "static const struct opt opts[] = {\n"
        '    { "a", 1 },\n'
        "};\n"
        "int after(void) { return 0; }\n"
    )
    assert _ranges(src) == [(4, 4, "after", "function")]


def test_an_unclosed_body_falls_back_to_indentation_and_never_runs_away() -> None:
    """The fallback the whole design turns on: when braces cannot resolve
    a body, the range is bounded by indentation rather than running to
    end-of-file. A truncated or macro-mangled file costs one bad range,
    not every finding after it."""
    src = (
        "int broken(void) {\n"
        "    return 1;\n"          # never closed
        "\n"
        "int after(void) { return 2; }\n"
    )
    ranges = _ranges(src)

    assert ranges, "an unclosed body must still yield a bounded range"
    assert ranges[0][0] == 1
    assert ranges[0][2] == "broken"
    assert ranges[0][1] < len(src.splitlines()), (
        "the range ran to end-of-file — the pre-0.4.0 defect, in C"
    )


def test_a_brace_in_a_comment_or_string_does_not_desync() -> None:
    """Masking runs first, so a `{` inside a comment or string cannot open or
    close a body."""
    src = (
        "int f(void) {\n"
        '    const char *s = "a { b } c";\n'
        "    /* an unbalanced } in a comment */\n"
        "    return 0;\n"
        "}\n"
        "int g(void) { return 1; }\n"
    )
    assert _ranges(src) == [
        (1, 5, "f", "function"),
        (6, 6, "g", "function"),
    ]

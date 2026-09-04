"""Swift (2.4.0): keyword-led declarations, and three shapes that are not.

Braced, so the walk is shared with C, C++, C# and Java. Every declaration
is keyword-led — `func`, `init`, `subscript`, `class`, `struct`, `enum`,
`protocol`, `actor`, `extension` — which makes recognition *easier* than
C++, where a bare `name(` is equally a call, a macro and a constructor.

What is worth testing is the four judgments, not the regexes:

- an `extension` member is reported under the type it extends;
- a protocol requirement has no body and mints nothing;
- a computed property is not a declaration;
- `guard` is a branch.

Two of those were wrong in the first working version and are pinned here
because of it: the extension member came back as a bare `describe`, and the
protocol requirement came back measured as two lines of body.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._ranges_swift import swift_declaration_ranges
from maintainability_audit.config import load_config
from maintainability_audit.declarations import detect_functions

THRESHOLDS = load_config("maintainability-agent.json")["thresholds"]


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = swift_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_type_and_its_methods_are_bounded_by_their_own_braces() -> None:
    source = (
        "struct Widget {\n"
        "    func draw() {\n"
        "        print(1)\n"
        "    }\n"
        "}\n"
        "func free() {\n"
        "    print(2)\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 5, "Widget", "class"),
        (2, 4, "draw", "function"),
        (6, 8, "free", "function"),
    ]


def test_an_extension_member_is_reported_under_the_type_it_extends() -> None:
    """`draw` alone is unfindable; `Widget.draw` is an instruction.

    An extension adds members to a type declared elsewhere, often in
    another file, and Swift does not write the qualification into the
    source the way C++ does for an out-of-line definition — so the scanner
    carries it. A work order saying "shorten `draw`" against a tree with
    eleven `draw`s is not a bounded instruction.
    """
    source = (
        "extension Widget: Drawable {\n"
        "    func describe() -> String {\n"
        "        return \"w\"\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Widget.describe"]


def test_the_extension_itself_is_walked_into_but_not_graded() -> None:
    """It is a container. Grading it counts its members twice."""
    source = (
        "extension Widget {\n"
        "    func a() { print(1) }\n"
        "    func b() { print(2) }\n"
        "}\n"
    )

    assert _names(source) == ["Widget.a", "Widget.b"]


def test_a_protocol_requirement_has_no_body_and_mints_nothing() -> None:
    """The defect the first version shipped with.

    Swift has no statement terminator, so the shared bare-signature check
    could not see where the requirement ended — it walked on and adopted
    the *next* line's brace, reporting `describe` as two lines of body. A
    protocol of forty requirements is not forty declarations.
    """
    source = (
        "protocol Drawable {\n"
        "    func describe() -> String\n"
        "    func render(into target: Canvas) throws\n"
        "    var summary: String { get }\n"
        "}\n"
    )

    assert _names(source) == ["Drawable"], (
        "a protocol requirement was counted as a declaration"
    )


def test_a_computed_property_is_not_a_declaration() -> None:
    """The C# properties problem in Swift spelling.

    `var area: Double { w * h }` has braces and would bound cleanly, and an
    ordinary Swift type has many — each a line or two, none anybody's
    maintenance burden. Counting them dilutes the population every
    declaration rate divides by.
    """
    source = (
        "struct Widget {\n"
        "    var width: Double\n"
        "    var area: Double { width * width }\n"
        "    var label: String {\n"
        "        get { \"w\" }\n"
        "        set { store(newValue) }\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Widget"]


def test_initialisers_and_subscripts_are_declarations() -> None:
    """They carry no `func` keyword and are still functions."""
    source = (
        "final class Store {\n"
        "    init(size: Int) {\n"
        "        self.size = size\n"
        "    }\n"
        "    deinit {\n"
        "        close()\n"
        "    }\n"
        "    subscript(index: Int) -> Int {\n"
        "        return items[index]\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Store", "init", "deinit", "subscript"]


def test_attributes_and_modifiers_do_not_become_the_name() -> None:
    """`@available(...)` leads a declaration; it is not one."""
    source = (
        "@available(iOS 13, *)\n"
        "public final class Service {\n"
        "    @MainActor private func refresh() async throws {\n"
        "        try await load()\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Service", "refresh"]


def test_a_wrapped_signature_is_still_a_declaration() -> None:
    """Its parentheses do not balance on the first line, so it is kept.

    This is the line between "requirement" and "wrapped signature", and
    getting it wrong in the other direction would drop real declarations
    from every Swift codebase that wraps its parameters.
    """
    source = (
        "func draw(\n"
        "    into target: Canvas,\n"
        "    scale: Double\n"
        ") throws {\n"
        "    target.plot(scale)\n"
        "}\n"
    )

    assert _names(source) == ["draw"]


def test_guard_is_a_branch() -> None:
    """Swift's primary early exit, absent from the C-family pattern.

    Fortran shipped with exactly this defect: six nested `do` loops scored
    complexity 1 because the pattern did not know the keyword. A
    guard-heavy Swift function would have read as branchless.
    """
    source = (
        "func validate(_ input: String?) -> Bool {\n"
        "    guard let value = input else { return false }\n"
        "    guard !value.isEmpty else { return false }\n"
        "    guard value.count < 100 else { return false }\n"
        "    return true\n"
        "}\n"
    )

    metric = detect_functions(
        Path("."), Path("v.swift"), source.splitlines(), THRESHOLDS
    )[0]

    assert metric.complexity >= 4, (
        f"three guards and a base scored {metric.complexity}; `guard` is not "
        "being counted as a branch"
    )


def test_a_brace_inside_a_string_does_not_desync_the_walk() -> None:
    """The ordinary masking risk, not the one the roadmap claimed.

    Swift interpolates with `\\(expr)` — parentheses, not braces — so the
    roadmap's "interpolation puts braces inside literals" was wrong. What
    is real is the risk every language shares: a literal `{` in a string.
    """
    source = (
        "func render() -> String {\n"
        "    let template = \"{ \\\"key\\\": value }\"\n"
        "    return template\n"
        "}\n"
        "func after() {\n"
        "    print(1)\n"
        "}\n"
    )

    assert _names(source) == ["render", "after"]


def test_swift_is_routed_to_its_own_scanner_and_metrics() -> None:
    from maintainability_audit.declarations import SCANNERS, metrics_for

    routed = {
        suffix: scanner.__name__
        for suffixes, scanner in SCANNERS
        for suffix in suffixes
    }
    assert routed[".swift"] == "swift_declaration_ranges"

    branch, cognitive = metrics_for(".swift")
    assert branch.__name__ == "swift_branch_points"
    assert cognitive.__name__ == "swift_cognitive"


def test_class_is_read_as_a_keyword_or_a_modifier_as_the_line_requires() -> None:
    """Swift spells two different things with the same word.

    `class Widget` declares a type; `class func make()` declares a
    type-level method. Stripping `class` with the other modifiers cost
    every `final class Store` its keyword — the type vanished from the
    report and only its members came back, which is the shape that makes a
    declaration rate wrong rather than merely incomplete.
    """
    source = (
        "final class Store {\n"
        "    class func shared() -> Store {\n"
        "        return instance\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Store", "shared"]

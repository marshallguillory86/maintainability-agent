"""Kotlin: keyword-led declarations, and the four places it is not Swift.

Braced and keyword-led, so the walk is shared with C, C++, C#, Java and
Swift — `fun`, `class`, `interface`, `object`, and the modifiers that
precede them. What is worth testing is where Kotlin's reading has to
differ, not the regexes:

- **An extension function writes its own receiver.** `fun Widget.draw()`
  is `Widget.draw` in the source. Swift does not write it and
  `_ranges_swift` carries the qualification through a second pass; Kotlin
  needs none, which is the one place it is *easier*.
- **A primary constructor puts parentheses on the class line.**
  `class Widget(val w: Int) {` balances them and then opens a brace, so
  the Swift bodyless rule — parentheses balanced and no `{` means a
  requirement — must not misread a class header as bodyless.
- **An expression-bodied function is a function.** `fun area() = w * h`
  has no brace and is idiomatic, not exotic. It is counted, because the
  source writes `fun` and the thing is named and callable. A computed
  property (`val area: Int get() = w * h`) is not, which is the call C#
  and Swift already make for the same dilution reason.
- **`companion object` is named `Companion` when the source leaves it
  anonymous**, so the walk descends into it. Returning no name would skip
  the members, and a companion object is where Kotlin puts its factories.
"""

from __future__ import annotations

from maintainability_audit._ranges_kotlin import kotlin_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = kotlin_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_class_and_its_methods_are_bounded_by_their_own_braces() -> None:
    source = (
        "class Widget {\n"
        "    fun draw() {\n"
        "        println(1)\n"
        "    }\n"
        "}\n"
        "fun free() {\n"
        "    println(2)\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 5, "Widget", "class"),
        (2, 4, "draw", "function"),
        (6, 8, "free", "function"),
    ]


def test_an_extension_function_carries_the_receiver_the_source_wrote() -> None:
    """The one place Kotlin is easier than Swift.

    Swift's `extension Widget { func draw() }` leaves `draw` bare and
    `_ranges_swift` runs a second pass to qualify it. Kotlin writes
    `fun Widget.draw()`, so the name is already an instruction a reader
    can act on and nothing has to be carried.
    """
    source = (
        "fun Widget.draw(canvas: Canvas) {\n"
        "    canvas.clear()\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 3, "Widget.draw", "function")]


def test_a_primary_constructor_does_not_make_a_class_look_bodyless() -> None:
    """Parentheses balance on the class line and a brace still follows.

    The Swift rule — balanced parentheses and no `{` means a requirement
    with no body — is the right rule and reaches the wrong answer here if
    it stops at the parentheses. `class Widget(val w: Int) {` is a class
    with a body and two members to walk into.
    """
    source = (
        "class Widget(val w: Int, val h: Int) {\n"
        "    fun area(): Int {\n"
        "        return w * h\n"
        "    }\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 5, "Widget", "class"),
        (2, 4, "area", "function"),
    ]


def test_an_interface_method_without_a_body_mints_nothing() -> None:
    """A signature with nothing to measure, as in C, C++, C# and Swift.

    Grading it would put one-line members into the population every rate
    divides by. A default implementation is a body and is counted.
    """
    source = (
        "interface Drawable {\n"
        "    fun draw()\n"
        "    fun describe(): String {\n"
        "        return \"shape\"\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Drawable", "describe"]


def test_an_expression_bodied_function_is_a_declaration() -> None:
    """`fun area() = w * h` is named, callable, and written with `fun`.

    Idiomatic Kotlin, not an exotic corner: excluding it would drop a
    large share of a real tree's functions out of the population. It has
    no brace, so its range is the one line it occupies.
    """
    source = (
        "class Widget(val w: Int, val h: Int) {\n"
        "    fun area() = w * h\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 3, "Widget", "class"),
        (2, 2, "area", "function"),
    ]


def test_a_wrapped_expression_body_keeps_its_continuation() -> None:
    """An `=` that ends the line has its body on the next one."""
    source = (
        "fun area(w: Int, h: Int) =\n"
        "    w * h\n"
    )

    assert _ranges(source) == [(1, 2, "area", "function")]


def test_a_computed_property_is_not_a_declaration() -> None:
    """The call C# and Swift already make, for the same reason.

    An ordinary type has many, each a line or two, and counting them
    dilutes the population every rate divides by. `val`/`var` is not a
    declaration this tool measures whether or not it has an accessor.
    """
    source = (
        "class Widget(val w: Int, val h: Int) {\n"
        "    val area: Int get() = w * h\n"
        "    var label: String = \"\"\n"
        "}\n"
    )

    assert _names(source) == ["Widget"]


def test_the_type_keywords_are_read_through_their_modifiers() -> None:
    """`data`, `sealed`, `enum`, `annotation`, `value`, `inner` lead `class`.

    Each is a modifier and the declaration keyword is still `class`.
    Stripping them is what keeps `data class Point` a type rather than
    losing its keyword the way `final class Store` did in Swift.
    """
    source = (
        "data class Point(val x: Int)\n"
        "sealed class Shape\n"
        "enum class Color { RED, GREEN }\n"
        "annotation class Marker\n"
        "value class Meters(val v: Int)\n"
        "object Registry {\n"
        "    fun get() = 1\n"
        "}\n"
    )

    assert _names(source) == [
        "Point", "Shape", "Color", "Marker", "Meters", "Registry", "get",
    ]


def test_an_anonymous_companion_object_is_named_so_it_is_walked_into() -> None:
    """A companion object is where Kotlin puts its factories.

    Returning no name would mean not descending, and every factory
    function inside it would go unmeasured. The source leaves it
    anonymous; Kotlin's own default name for it is `Companion`.
    """
    source = (
        "class Widget {\n"
        "    companion object {\n"
        "        fun make(): Widget {\n"
        "            return Widget()\n"
        "        }\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Widget", "Companion", "make"]


def test_a_named_companion_object_keeps_its_name() -> None:
    source = (
        "class Widget {\n"
        "    companion object Factory {\n"
        "        fun make() = Widget()\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Widget", "Factory", "make"]


def test_a_suspend_function_is_a_function() -> None:
    source = (
        "suspend fun load(id: Int): Widget {\n"
        "    return fetch(id)\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 3, "load", "function")]


def test_an_annotation_leads_a_declaration_and_is_not_one() -> None:
    source = (
        "@JvmStatic\n"
        "@Suppress(\"UNCHECKED_CAST\")\n"
        "fun cast(x: Any): String {\n"
        "    return x as String\n"
        "}\n"
    )

    assert _ranges(source) == [(3, 5, "cast", "function")]


def test_a_lambda_is_not_a_declaration() -> None:
    """A brace with no declaration keyword in front of it.

    Kotlin's trailing-lambda syntax puts braces almost everywhere, and
    none of them declare anything.
    """
    source = (
        "fun render(items: List<Item>) {\n"
        "    items.forEach { item ->\n"
        "        println(item)\n"
        "    }\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 5, "render", "function")]


def test_a_local_function_inside_a_body_is_not_reported() -> None:
    """A function body is stepped over, as in every braced language here."""
    source = (
        "fun outer() {\n"
        "    fun inner() {\n"
        "        println(1)\n"
        "    }\n"
        "    inner()\n"
        "}\n"
    )

    assert _names(source) == ["outer"]


def test_a_constructor_and_an_init_block_are_read() -> None:
    """`constructor` is named; `init` is Kotlin's initialiser block."""
    source = (
        "class Widget {\n"
        "    constructor(w: Int) {\n"
        "        this.w = w\n"
        "    }\n"
        "    init {\n"
        "        register()\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Widget", "constructor", "init"]

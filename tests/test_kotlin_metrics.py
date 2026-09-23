"""Kotlin decides in three spellings the C-family pattern cannot read.

Each is the same defect as Fortran's `do`, Swift's `guard` and C#'s
`foreach`: a pattern that does not know a language's primary keyword
reads its branching as straight-line code.

- **`when` is the multi-way branch**, and like every `switch` here it is
  counted at its arms, not at its header — the Fortran `select case`
  rule. Kotlin spells an arm `->`, which is also how it spells a lambda
  parameter and a function type, so the arm count has to exclude both.
- **`?:` (elvis) decides**, and is Kotlin's `??`. Both halves are
  written, which is the test the C family already applies to a ternary.
- **`?.` does not decide** — it yields `null` and carries on down the
  same path. Rust's `?` *is* counted here because it returns early from
  the function; Kotlin's safe call does not, and is the optional
  chaining that C, C#, TypeScript and Java all decline to count.

Kotlin has no ternary at all — `if` is an expression — so the C-family
`?…:` alternative must not be present. With it, every nullable type in
the file (`String?`) scores a decision, which is D115's defect in a
sixth spelling.
"""

from __future__ import annotations

from maintainability_audit._cognitive import kotlin_cognitive
from maintainability_audit._metrics_types import kotlin_branch_points


def test_a_when_is_counted_at_its_arms() -> None:
    """Three real arms, three decisions. The header decides nothing."""
    source = [
        "when (shape) {",
        "    is Circle -> draw(shape)",
        "    is Square -> fill(shape)",
        "    is Line -> stroke(shape)",
        "}",
    ]

    assert sum(kotlin_branch_points(line) for line in source) == 3


def test_the_else_arm_is_not_counted() -> None:
    """The wildcard, as Go declines `default` and Rust declines `_ =>`.

    Two real arms and an `else` is two decisions and a fallthrough.
    """
    source = [
        "when (code) {",
        "    200 -> ok()",
        "    404 -> missing()",
        "    else -> unknown()",
        "}",
    ]

    assert sum(kotlin_branch_points(line) for line in source) == 2


def test_a_lambda_parameter_is_not_an_arm() -> None:
    """`{ item ->` is a parameter list, not a branch.

    Kotlin's trailing-lambda syntax puts `->` on lines all over an
    ordinary file. Counting them would make every collection pipeline
    read as a dispatch table.
    """
    assert kotlin_branch_points("items.forEach { item -> println(item) }") == 0
    assert kotlin_branch_points("items.map { a, b -> a + b }") == 0


def test_a_function_type_is_not_an_arm() -> None:
    """`(Int) -> String` is a type, and types decide nothing."""
    assert kotlin_branch_points("fun apply(cb: (Int) -> Unit) {") == 0
    assert kotlin_branch_points("val f: (String) -> Int = { it.length }") == 0


def test_elvis_decides_and_a_safe_call_does_not() -> None:
    """Both halves are written for `?:`; `?.` writes only one.

    `a ?: b` chooses between two values. `a?.b` yields `null` and
    continues on the same path — the optional chaining every other
    language here declines to count.
    """
    assert kotlin_branch_points("val name = user?.name ?: \"anonymous\"") == 1
    assert kotlin_branch_points("val city = user?.address?.city") == 0


def test_a_nullable_type_is_not_a_decision() -> None:
    """D115 in a sixth spelling.

    Kotlin has no ternary, so a `?` in type position has nothing to be
    confused with — provided the C-family alternative is absent. With
    it, a signature of four nullable parameters scores four.
    """
    signature = "fun find(id: Int?, name: String?, tag: Tag?): Widget? {"

    assert kotlin_branch_points(signature) == 0


def test_the_ordinary_keywords_still_count() -> None:
    assert kotlin_branch_points("if (x > 1 && y < 2) {") == 2
    assert kotlin_branch_points("for (x in xs) {") == 1
    assert kotlin_branch_points("while (running) {") == 1
    assert kotlin_branch_points("} catch (e: IOException) {") == 1


def test_do_while_is_one_loop() -> None:
    """One loop with one condition, and the `while` carries it.

    The call PHP and Swift already make about `do`/`repeat`. Counting
    the head as well scores the construct and its own test.
    """
    source = ["do {", "    step()", "} while (more)"]

    assert sum(kotlin_branch_points(line) for line in source) == 1


def test_a_when_is_charged_cognitively_at_the_nesting_it_sits_in() -> None:
    """Once, like any switch, and at its depth — not zero.

    `when` is absent from the shared control vocabulary, so a dispatch
    written the idiomatic way read as cognitively *flat* while the same
    dispatch written `if`/`else if` was charged in full. Charged once
    rather than per arm is the point of cognitive complexity and the
    reason this is not the equality the loop fixtures assert: a `when`
    is genuinely easier to read than the chain it replaces.

    One for the construct plus one for sitting a brace deep.
    """
    dispatch = [
        "fun classify(code: Int): String {",
        "    when (code) {",
        "        200 -> return \"ok\"",
        "        404 -> return \"missing\"",
        "    }",
        "    return \"other\"",
        "}",
    ]

    assert kotlin_cognitive(dispatch) == 2

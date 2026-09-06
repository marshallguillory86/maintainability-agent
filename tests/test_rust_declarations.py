"""Rust: the brace walk again, with three things Go did not have.

Shares `scan_bounded` with C, C++, C#, Java and Go. What is worth testing
is what Rust spells differently, and it is not the `fn` keyword:

- **`impl` blocks are containers**, and a method inside one belongs to
  the type being implemented — `Store::get`, not `get`. Go's receiver is
  written on the method itself; Rust's lives on the block above it, so
  the scanner has to carry it down. Swift's extensions were the same
  problem and C++'s `void geo::Widget::draw()` is the same problem
  written out longhand.
- **Attributes lead declarations without being them.** `#[derive(Clone)]`
  and `#[cfg(test)]` sit on their own lines; Java's annotations forced
  the same treatment.
- **`trait` methods may or may not have a body.** One with a body is a
  default implementation and is a real declaration; one without is a
  requirement, exactly as a Go interface method is.

Generics are angle-bracketed like Java's rather than square like Go's, so
`_mask_generics` already handles them — and lifetimes (`<'a>`) ride along
in the same syntax.

Three of this file's assertions about *measurement* were wrong and are
corrected below: `?` is a decision, `loop` is not, and a wildcard match
arm is not. All three were found by checking every construct in the
reference against an independent implementation.
"""

from __future__ import annotations

from maintainability_audit._ranges_rust import rust_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = rust_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_free_function_is_bounded_by_its_own_braces() -> None:
    source = (
        "pub fn add(a: i32, b: i32) -> i32 {\n"
        "    a + b\n"
        "}\n"
        "\n"
        "fn sub(a: i32, b: i32) -> i32 {\n"
        "    a - b\n"
        "}\n"
    )

    assert _ranges(source) == [
        (1, 3, "add", "function"),
        (5, 7, "sub", "function"),
    ]


def test_a_method_belongs_to_the_type_its_impl_block_names() -> None:
    """`get` alone is unfindable; `Store::get` is an instruction.

    Rust writes the type on the `impl` block rather than on the method,
    so unlike Go the qualification has to be carried down rather than
    read off the signature.
    """
    source = (
        "impl Store {\n"
        "    pub fn get(&self, key: &str) -> Option<&str> {\n"
        "        self.items.get(key)\n"
        "    }\n"
        "    fn len(&self) -> usize {\n"
        "        self.items.len()\n"
        "    }\n"
        "}\n"
    )

    # The `impl` block itself is not graded. It is a container, exactly as
    # a Swift `extension` is, and measuring it as well as its methods
    # counts the same lines twice.
    assert _names(source) == ["Store::get", "Store::len"]


def test_a_trait_implementation_names_the_type_not_the_trait() -> None:
    """`impl Display for Widget` implements Display *on* Widget.

    The type is what a reader searches for and what a work order has to
    name; the trait is how it behaves.
    """
    source = (
        "impl Display for Widget {\n"
        "    fn fmt(&self, f: &mut Formatter) -> Result {\n"
        "        write!(f, \"w\")\n"
        "    }\n"
        "}\n"
    )

    assert "Widget::fmt" in _names(source)


def test_a_struct_is_a_declaration_and_holds_no_methods() -> None:
    """Rust splits data from behaviour; the struct is only the data."""
    source = (
        "pub struct Store {\n"
        "    items: HashMap<String, String>,\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 3, "Store", "class")]


def test_a_trait_requirement_has_no_body_and_mints_nothing() -> None:
    """A default implementation is a declaration; a requirement is not."""
    source = (
        "pub trait Reader {\n"
        "    fn read(&self) -> usize;\n"
        "    fn describe(&self) -> String {\n"
        "        String::from(\"r\")\n"
        "    }\n"
        "}\n"
    )

    names = _names(source)
    assert "Reader" in names, "the trait itself is a declaration"
    assert "Reader::describe" in names, "a default implementation was not read"
    assert not any(name.endswith("::read") for name in names), (
        "a bodyless trait requirement was counted as a declaration"
    )


def test_attributes_lead_a_declaration_without_being_one() -> None:
    """`#[derive(Clone)]` has a name and a parenthesised list, like Java's
    annotations, and would read as a signature if it were not stripped."""
    source = (
        "#[derive(Clone, Debug)]\n"
        "#[cfg(test)]\n"
        "pub fn build() -> Config {\n"
        "    Config::default()\n"
        "}\n"
    )

    assert _names(source) == ["build"]


def test_a_macro_invocation_is_not_a_declaration() -> None:
    """`println!(…)` and `vec![…]` are calls that look like signatures."""
    source = (
        "fn emit() {\n"
        "    println!(\"x\");\n"
        "    let v = vec![1, 2];\n"
        "    let _ = v;\n"
        "}\n"
    )

    assert _names(source) == ["emit"]


def test_the_error_operator_is_a_decision() -> None:
    """`?` decides, and this test previously asserted it does not.

    The claim was that `?` "propagates an error and decides nothing",
    reasoning by analogy with JavaScript's optional chaining (D78). The
    analogy is false. `let x = f()?` has two paths — continue, or return
    early — and the operator expands to a `match` with two arms. That
    idiomatic Rust is full of them is a fact about Rust, not a reason to
    under-count it.

    Found by comparing every construct in the reference against an
    independent implementation, which disagreed here and was right.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".rs")
    assert branch_points("    let value = read(path)?;") == 1
    assert branch_points("    if value > 0 && other {") == 2


def test_an_unconditional_loop_is_not_a_decision() -> None:
    """`loop` has no condition; the `if … break` inside it decides.

    Counted at the head as well, an ordinary `loop { … if x { break } }`
    scored one higher than its paths — the same double-count as reading
    a `switch` header beside its cases.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".rs")
    assert branch_points("    loop {") == 0
    assert branch_points("        if n < 0 {") == 1


def test_a_wildcard_match_arm_is_not_a_decision() -> None:
    """`_ =>` is the default, and a default is not a test.

    Two real arms and a wildcard is three paths, which is exactly what
    two `case`s and a `default` score in Go.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".rs")
    assert branch_points('        1 => "one",') == 1
    assert branch_points('        _ => "many",') == 0


def test_a_let_else_is_a_decision() -> None:
    """`let Some(x) = opt else { … }` continues or diverges, and scored 0.

    Stable since Rust 1.65 and the idiomatic early return for a
    refutable pattern. There is no `if` token in it, so nothing in the
    keyword set saw it: the fixture had `if let`, `while let` and `?`,
    but not `let … else` (D128).
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".rs")

    assert branch_points("    let Some(x) = opt else { return; };") == 1
    # `if let … else` is one decision carried by its `if`. Counting the
    # `let … else` shape here too would score it twice.
    assert branch_points("    if let Some(x) = opt { } else { }") == 1
    assert branch_points("    while let Some(x) = it.next() { }") == 1
    # An ordinary binding decides nothing.
    assert branch_points("    let x = compute();") == 0

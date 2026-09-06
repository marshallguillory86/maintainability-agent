"""PHP: brace-bounded code living inside a template.

The walk is `scan_bounded` again. What makes PHP different from Go and
Rust is not its declarations — `function`, `class`, `interface`, `trait`
are ordinary — but that a `.php` file is HTML until `<?php` says
otherwise, and is HTML again after `?>`.

That matters because the text outside those tags is *not code*, and a
scanner that reads it will find declarations in prose and count braces
that belong to a CSS block or a JavaScript snippet. Depth desyncs, and a
desynced depth mis-bounds every declaration after it.

The judgments worth testing:

- **text outside `<?php … ?>` is not read**, and a brace in it does not
  move depth;
- **a method carries its class**, `Store::get`, for the reason every
  other language here does;
- **an interface method and an abstract method mint nothing** — no body,
  nothing to maintain;
- **`elseif` is one branch, and the C pattern scores it zero.** There is
  no word boundary inside `elseif`, so neither `if` nor `elif` matches
  it: a PHP dispatch chain reads as branchless. That is Fortran's defect
  exactly — a language measured with another language's keywords is not
  approximately wrong, it is wrong.
"""

from __future__ import annotations

from maintainability_audit._ranges_php import php_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = php_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_function_is_bounded_by_its_own_braces() -> None:
    source = (
        "<?php\n"
        "function add(int $a, int $b): int {\n"
        "    return $a + $b;\n"
        "}\n"
        "\n"
        "function sub(int $a, int $b): int {\n"
        "    return $a - $b;\n"
        "}\n"
    )

    assert _ranges(source) == [
        (2, 4, "add", "function"),
        (6, 8, "sub", "function"),
    ]


def test_a_method_carries_its_class() -> None:
    """`get` alone is unfindable in a tree with eleven of them."""
    source = (
        "<?php\n"
        "class Store {\n"
        "    public function get(string $key): ?string {\n"
        "        return $this->items[$key] ?? null;\n"
        "    }\n"
        "    private function len(): int {\n"
        "        return count($this->items);\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["Store", "Store::get", "Store::len"]


def test_html_outside_the_tags_is_not_read_as_code() -> None:
    """A `.php` file is a template. The prose in it is not source.

    The braces here belong to CSS. Counted, they desync depth and
    mis-bound every declaration after them — which is why this is the
    first thing the scanner does rather than a refinement.
    """
    source = (
        "<style>\n"
        "  .box { margin: 0; }\n"
        "</style>\n"
        "<p>function decoy() { not code }</p>\n"
        "<?php\n"
        "function real(): int {\n"
        "    return 1;\n"
        "}\n"
        "?>\n"
        "<p>trailing { brace</p>\n"
    )

    assert _names(source) == ["real"]


def test_code_resumes_after_a_closing_tag() -> None:
    """Templates interleave; the second block is as real as the first."""
    source = (
        "<?php\n"
        "function first(): int { return 1; }\n"
        "?>\n"
        "<p>markup { here</p>\n"
        "<?php\n"
        "function second(): int { return 2; }\n"
    )

    assert _names(source) == ["first", "second"]


def test_an_interface_method_and_an_abstract_method_mint_nothing() -> None:
    """No body, nothing to maintain — as in Go, Rust, C and Swift."""
    source = (
        "<?php\n"
        "interface Reader {\n"
        "    public function read(): string;\n"
        "}\n"
        "abstract class Base {\n"
        "    abstract protected function load(): void;\n"
        "    public function describe(): string {\n"
        "        return 'b';\n"
        "    }\n"
        "}\n"
    )

    names = _names(source)
    assert "Reader" in names and "Base" in names
    assert "Base::describe" in names, "a real method was not read"
    assert not any(name.endswith("::read") for name in names)
    assert not any(name.endswith("::load") for name in names)


def test_a_closure_assigned_to_a_variable_is_not_a_declaration() -> None:
    """`$f = function () { … };` lives inside a body and is stepped over."""
    source = (
        "<?php\n"
        "function outer(): callable {\n"
        "    $f = function (int $x): int {\n"
        "        return $x + 1;\n"
        "    };\n"
        "    return $f;\n"
        "}\n"
    )

    assert _names(source) == ["outer"]


def test_elseif_is_one_branch_not_two() -> None:
    """The C-family pattern scores `elseif` as *zero*, not as two.

    Written expecting a double count and corrected by running it: there
    is no word boundary between `else` and `if`, so neither `if` nor
    `elif` matches inside `elseif`. A chain of them — the ordinary way
    PHP writes a multi-way branch — therefore reads as branchless, and
    every dispatch function in the language scores 1.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".php")
    assert branch_points("    } elseif ($x > 2) {") == 1, (
        "elseif decided nothing; a chain of them reads as branchless"
    )
    assert branch_points("    if ($x > 1 && $y) {") == 2


def test_do_while_and_match_are_branches() -> None:
    """Derived from the PHP grammar rather than from recollection.

    `match` (PHP 8) was absent from the first keyword set, which was
    assembled from memory. `do` and `goto` were then added and both were
    wrong: a `do … while` has one condition, carried by its `while`, and
    `goto` is unconditional. Corrected against the reference.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".php")
    # `do` is *not* counted: `do { … } while (cond)` is one loop with one
    # condition, and the `while` clause carries it. Counting both scored
    # every do-while one high — corrected against the reference.
    assert branch_points("    do {") == 0
    assert branch_points("    } while ($n > 0);") == 1
    assert branch_points("    $r = match($x) {") == 1
    # `goto` transfers control unconditionally: an edge, not a decision.
    assert branch_points("    goto retry;") == 0


def test_the_switch_header_is_not_counted_beside_its_cases() -> None:
    """Covers existing behaviour: `switch` is deliberately absent.

    Its cases carry the branch, as in Go and Fortran. `match` is counted
    because its arms are `=>` expressions, not `case` labels.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".php")
    assert branch_points("    switch ($value) {") == 0
    assert branch_points("        case 1:") == 1

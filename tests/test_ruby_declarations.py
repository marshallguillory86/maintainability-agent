"""Ruby: `def … end`, where `end` closes almost everything.

Not brace-bounded, so this is the second language after Fortran to hand
`scan_bounded` its own end-finder. Fortran's `subroutine` ends at `end
subroutine` — the closer names what it closes. Ruby's does not: one bare
`end` closes a method, a class, a block, an `if`, a `while` and a `case`,
and telling them apart means counting openers.

That counting is the whole difficulty, and it is why this file leads with
it rather than with `def`:

- **`do … end` is a block, not a declaration**, and it is the reason a
  naive `def`/`end` pairing mis-bounds. A method containing one `each do`
  ends at the *block's* `end` and reports half its real length.
- **Modifier forms open nothing.** `return x if y` has an `if` that never
  needs an `end`, and counting it as an opener eats the enclosing method.
- **`=begin`/`=end` blocks and heredocs are not code** and must be
  blanked before anything counts a keyword, or prose closes a method.
- **A method carries its class**, `Store#get`, in Ruby's own notation.

What is deliberately *not* here: `define_method` and other metaprogrammed
declarations do not exist in the source and are not seen, exactly as C
macros and Swift macros are not.
"""

from __future__ import annotations

from maintainability_audit._ranges_ruby import ruby_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = ruby_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_method_is_bounded_by_its_own_end() -> None:
    source = (
        "def add(a, b)\n"
        "  a + b\n"
        "end\n"
        "\n"
        "def sub(a, b)\n"
        "  a - b\n"
        "end\n"
    )

    assert _ranges(source) == [
        (1, 3, "add", "function"),
        (5, 7, "sub", "function"),
    ]


def test_a_block_end_does_not_close_the_method_containing_it() -> None:
    """The defect this scanner exists to avoid.

    A naive `def`/`end` pairing stops at the block's `end` on line 4 and
    reports `each_item` as a three-line method. It is six, and every
    length and complexity drawn from it would be wrong — not
    approximately, but for a different span of code.
    """
    source = (
        "def each_item(items)\n"
        "  items.each do |item|\n"
        "    puts item\n"
        "  end\n"
        "  items.size\n"
        "end\n"
    )

    assert _ranges(source) == [(1, 6, "each_item", "function")]


def test_a_modifier_if_opens_nothing() -> None:
    """`return x if y` needs no `end`, and counting one eats the method."""
    source = (
        "def guard(value)\n"
        "  return 0 if value.nil?\n"
        "  value * 2 unless value.negative?\n"
        "  value\n"
        "end\n"
        "\n"
        "def after\n"
        "  1\n"
        "end\n"
    )

    assert _ranges(source) == [
        (1, 5, "guard", "function"),
        (7, 9, "after", "function"),
    ]


def test_a_method_carries_its_class_in_ruby_notation() -> None:
    """`get` alone is unfindable; `Store#get` is how Ruby writes it."""
    source = (
        "class Store\n"
        "  def get(key)\n"
        "    @items[key]\n"
        "  end\n"
        "\n"
        "  def self.build\n"
        "    new\n"
        "  end\n"
        "end\n"
    )

    assert _names(source) == ["Store", "Store#get", "Store.build"]


def test_a_module_is_a_container_and_holds_its_methods() -> None:
    source = (
        "module Countable\n"
        "  def count_all\n"
        "    1\n"
        "  end\n"
        "end\n"
    )

    assert _names(source) == ["Countable", "Countable#count_all"]


def test_a_comment_block_is_not_code() -> None:
    """`=begin`/`=end` is Ruby's block comment, and `=end` is not an `end`."""
    source = (
        "def real\n"
        "=begin\n"
        "  def decoy\n"
        "  end\n"
        "=end\n"
        "  1\n"
        "end\n"
    )

    assert _ranges(source) == [(1, 7, "real", "function")]


def test_a_heredoc_body_is_not_code() -> None:
    """Text in a heredoc closes nothing, however much it looks like Ruby."""
    source = (
        "def render\n"
        "  text = <<~SQL\n"
        "    select 1\n"
        "    end\n"
        "  SQL\n"
        "  text\n"
        "end\n"
    )

    assert _ranges(source) == [(1, 7, "render", "function")]


def test_unless_and_until_are_branches() -> None:
    """Ruby's negated forms are branches the C-family pattern never sees."""
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".rb")
    assert branch_points("  return 0 unless value") == 1
    assert branch_points("  x += 1 until done") == 1
    assert branch_points("  if a && b") == 2


def test_an_endless_method_ends_on_its_own_line() -> None:
    """`def square(x) = x * x` (Ruby 3.0) has no body and no `end`.

    Found by running cases the contract above did not cover: the endless
    form matched the `def` opener, so depth never returned to zero on its
    own line and it consumed the *next* method whole — which then
    disappeared from the report entirely. A declaration that eats its
    neighbour is worse than one that is missed.
    """
    source = (
        "def square(x) = x * x\n"
        "def after\n"
        "  1\n"
        "end\n"
    )

    assert _ranges(source) == [
        (1, 1, "square", "function"),
        (2, 4, "after", "function"),
    ]


def test_a_nested_class_owns_its_own_methods() -> None:
    """`Inner#deep`, not `Outer#deep`.

    The span pass stepped over each container's body, so it never saw a
    class inside a class and every nested method was attributed to the
    outermost one. Naming the wrong class is worse than naming none: a
    work order pointing at `Outer#deep` sends a reader to a method that
    is not there.
    """
    source = (
        "class Outer\n"
        "  class Inner\n"
        "    def deep\n"
        "      1\n"
        "    end\n"
        "  end\n"
        "end\n"
    )

    assert _names(source) == ["Outer", "Inner", "Inner#deep"]

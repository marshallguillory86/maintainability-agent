"""Go: brace-bounded like its C-family siblings, with four differences.

The walk is `scan_bounded`, shared with C, C++, C# and Java. What Go
spells differently is what is worth testing, and it is not the regexes:

- a **method** carries its receiver type, because `Get` alone is not an
  instruction in a tree with eleven of them — the same judgment Swift's
  extension members forced;
- `type … struct` and `type … interface` are containers holding members,
  and grading the container as well as its members counts them twice;
- an **interface method** has no body, so it is a requirement rather than
  a declaration, exactly as a Swift protocol requirement is;
- `select` is a branch. The C-family reading does not know the word, and
  Fortran is the standing lesson that a language measured with another
  language's keywords is not approximately wrong but wrong.

Go has no `while`, no ternary, and no exceptions; `for` covers looping and
`if err != nil` carries what other languages put in `catch`.
"""

from __future__ import annotations

from maintainability_audit._ranges_go import go_declaration_ranges


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = go_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


def test_a_function_is_bounded_by_its_own_braces() -> None:
    source = (
        "package main\n"
        "\n"
        "func Add(a int, b int) int {\n"
        "    return a + b\n"
        "}\n"
        "\n"
        "func Sub(a int, b int) int {\n"
        "    return a - b\n"
        "}\n"
    )

    assert _ranges(source) == [
        (3, 5, "Add", "function"),
        (7, 9, "Sub", "function"),
    ]


def test_a_method_carries_its_receiver_type() -> None:
    """`Get` alone is unfindable in a tree with eleven of them.

    Go writes the receiver into the signature, so unlike Swift's
    extensions the qualification is already there — it only has to be
    kept rather than reconstructed.
    """
    source = (
        "func (s *Store) Get(key string) string {\n"
        "    return s.items[key]\n"
        "}\n"
        "func (s Store) Len() int {\n"
        "    return len(s.items)\n"
        "}\n"
    )

    assert _names(source) == ["Store.Get", "Store.Len"]


def test_a_struct_holds_its_members_and_is_not_graded_twice() -> None:
    """A container is walked into, not measured as though it were a unit."""
    source = (
        "type Store struct {\n"
        "    items map[string]string\n"
        "    mu    sync.Mutex\n"
        "}\n"
    )

    assert _ranges(source) == [(1, 4, "Store", "class")]


def test_an_interface_method_is_a_requirement_not_a_declaration() -> None:
    """No body, nothing to maintain, nothing to measure.

    Counting them would put a pile of one-line members into the
    denominator of every declaration rate — the same reason a C# property
    is deliberately not a declaration here.
    """
    source = (
        "type Reader interface {\n"
        "    Read(p []byte) (int, error)\n"
        "    Close() error\n"
        "}\n"
    )

    assert _names(source) == ["Reader"]


def test_a_generic_function_is_read_through_its_type_parameters() -> None:
    """`[T any]` is not a parameter list and must not be read as one."""
    source = (
        "func Map[T any, U any](in []T, f func(T) U) []U {\n"
        "    out := make([]U, 0, len(in))\n"
        "    return out\n"
        "}\n"
    )

    assert _names(source) == ["Map"]


def test_a_struct_literal_inside_a_body_is_not_a_declaration() -> None:
    """The classic false positive: braces that are data, not a body."""
    source = (
        "func build() Config {\n"
        "    return Config{\n"
        "        Name: \"x\",\n"
        "    }\n"
        "}\n"
    )

    assert _names(source) == ["build"]


def test_select_counts_as_a_branch() -> None:
    """Go's concurrency branch, absent from the C-family keyword set.

    A dispatch loop built from `select` and its cases scores 1 under the C
    reading — branchless — which is the Fortran defect repeated: the
    number is not approximate, it is wrong.
    """
    from maintainability_audit.declarations import metrics_for

    branch_points, _cognitive = metrics_for(".go")
    body = [
        "    select {",
        "    case a := <-ch1:",
        "        _ = a",
        "    case b := <-ch2:",
        "        _ = b",
        "    default:",
        "    }",
    ]
    assert sum(branch_points(line) for line in body) >= 3, (
        "select and its cases scored as branchless"
    )

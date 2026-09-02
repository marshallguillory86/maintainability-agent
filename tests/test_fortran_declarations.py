"""The Fortran declaration scanner (1.4.0): the family's first language
with no braces.

C, C++, C# and Java share one walk because a body sits between `{` and
`}`. Fortran closes a program unit with a keyword, so `scan_bounded`
takes a `find_end` and Fortran supplies `_fortran_end`. The guarantee is
unchanged — a range never runs past its own body, and never to
end-of-file — so the tests that matter most here are the ones that would
catch a range ending too early (at an inner `end if`) or too late (at
the next unit's `end`).

Free-form only. Fixed-form (`.f`, `.for`, `.ftn`) is column-sensitive
and is deliberately not claimed.
"""

from __future__ import annotations

from maintainability_audit._ranges_fortran import fortran_declaration_ranges


def _ranges(src: str) -> list[tuple[int, int, str, str]]:
    got, _masked = fortran_declaration_ranges(src.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in got]


def test_a_module_is_descended_into_and_its_procedures_are_graded() -> None:
    src = (
        "module gravity_mod\n"
        "  implicit none\n"
        "contains\n"
        "  subroutine spin(n)\n"
        "    integer :: n\n"
        "  end subroutine spin\n"
        "  function accel(h)\n"
        "    real :: h\n"
        "  end function accel\n"
        "end module gravity_mod\n"
    )
    assert _ranges(src) == [
        (1, 10, "gravity_mod", "class"),
        (4, 6, "spin", "function"),
        (7, 9, "accel", "function"),
    ]


def test_an_inner_block_does_not_end_the_procedure_early() -> None:
    """The falsifier this scanner exists for.

    `if`/`do`/`select` all close with `end`, so a scanner that stopped at
    the first `end` would report a 3-line subroutine as ending at its
    first `end if` — and everything after would be read as top-level.
    Depth counting is what prevents it.
    """
    src = (
        "subroutine classify(n)\n"
        "  integer :: n, i\n"
        "  if (n > 0) then\n"
        "     n = 1\n"
        "  else\n"
        "     n = 0\n"
        "  end if\n"
        "  do i = 1, n\n"
        "     call step(i)\n"
        "  end do\n"
        "  select case (n)\n"
        "  case default\n"
        "     n = 2\n"
        "  end select\n"
        "end subroutine classify\n"
    )
    assert _ranges(src) == [(1, 15, "classify", "function")]


def test_a_bare_end_closes_a_procedure() -> None:
    """`end` with no keyword is legal, and common in older free-form."""
    src = (
        "subroutine first(n)\n"
        "  integer :: n\n"
        "end\n"
        "subroutine second(n)\n"
        "  integer :: n\n"
        "end\n"
    )
    assert _ranges(src) == [
        (1, 3, "first", "function"),
        (4, 6, "second", "function"),
    ]


def test_an_interface_block_mints_no_declarations() -> None:
    """A module that *describes* forty procedures does not contain forty.

    An interface block holds signatures with no bodies. Walking into one
    would put a one-line entry into the population every declaration
    rate divides by, for procedures defined somewhere else entirely.
    """
    src = (
        "module api_mod\n"
        "  interface\n"
        "     subroutine described(x)\n"
        "       real :: x\n"
        "     end subroutine described\n"
        "     function also_described(y)\n"
        "       real :: y\n"
        "     end function also_described\n"
        "  end interface\n"
        "contains\n"
        "  subroutine real_one(z)\n"
        "    real :: z\n"
        "  end subroutine real_one\n"
        "end module api_mod\n"
    )
    assert _ranges(src) == [
        (1, 14, "api_mod", "class"),
        (11, 13, "real_one", "function"),
    ]


def test_a_typed_function_with_a_result_clause_is_named_correctly() -> None:
    src = (
        "real function accel(h) result(a)\n"
        "  real :: h, a\n"
        "  a = 9.81\n"
        "end function accel\n"
        "pure elemental real(dp) function norm(v)\n"
        "  real :: v\n"
        "  norm = abs(v)\n"
        "end function norm\n"
        "recursive subroutine walk(node)\n"
        "  integer :: node\n"
        "end subroutine walk\n"
    )
    assert _ranges(src) == [
        (1, 4, "accel", "function"),
        (5, 8, "norm", "function"),
        (9, 11, "walk", "function"),
    ]


def test_a_derived_type_is_a_type_and_a_variable_of_it_is_not() -> None:
    """`type :: point` defines; `type(point) :: v` declares a variable."""
    src = (
        "module shapes_mod\n"
        "  type :: point\n"
        "     real :: x\n"
        "  end type point\n"
        "  type, extends(point) :: point3\n"
        "     real :: z\n"
        "  end type point3\n"
        "  type(point) :: origin\n"
        "contains\n"
        "  subroutine go(p)\n"
        "    type(point) :: p\n"
        "  end subroutine go\n"
        "end module shapes_mod\n"
    )
    assert _ranges(src) == [
        (1, 13, "shapes_mod", "class"),
        (2, 4, "point", "class"),
        (5, 7, "point3", "class"),
        (10, 12, "go", "function"),
    ]


def test_keywords_are_case_insensitive() -> None:
    """Fortran is case-insensitive, and older code SHOUTS."""
    src = (
        "MODULE LEGACY_MOD\n"
        "CONTAINS\n"
        "  SUBROUTINE COMPUTE(N)\n"
        "    INTEGER :: N\n"
        "  END SUBROUTINE COMPUTE\n"
        "END MODULE LEGACY_MOD\n"
    )
    assert _ranges(src) == [
        (1, 6, "LEGACY_MOD", "class"),
        (3, 5, "COMPUTE", "function"),
    ]


def test_a_comment_is_not_a_declaration() -> None:
    """`!` starts a comment anywhere on a free-form line."""
    src = (
        "! subroutine ghost(x)\n"
        "subroutine real_one(x)   ! subroutine mentioned again\n"
        "  real :: x\n"
        "end subroutine real_one\n"
    )
    assert _ranges(src) == [(2, 4, "real_one", "function")]


def test_contains_is_not_a_declaration() -> None:
    src = (
        "module m\n"
        "contains\n"
        "  subroutine a()\n"
        "  end subroutine a\n"
        "end module m\n"
    )
    assert [r[2] for r in _ranges(src)] == ["m", "a"]


def test_a_submodule_names_its_child() -> None:
    src = (
        "submodule (parent_mod) child_mod\n"
        "contains\n"
        "  subroutine impl(x)\n"
        "    real :: x\n"
        "  end subroutine impl\n"
        "end submodule child_mod\n"
    )
    assert _ranges(src) == [
        (1, 6, "child_mod", "class"),
        (3, 5, "impl", "function"),
    ]


def test_a_range_never_runs_past_its_own_body() -> None:
    src = (
        "subroutine first(n)\n"
        "  integer :: n\n"
        "end subroutine first\n"
        "\n"
        "subroutine second(n)\n"
        "  integer :: n\n"
        "end subroutine second\n"
    )
    assert _ranges(src) == [
        (1, 3, "first", "function"),
        (5, 7, "second", "function"),
    ]


def test_an_unclosed_unit_does_not_run_to_end_of_file() -> None:
    """A truncated file costs one declaration, not everything after it."""
    src = (
        "subroutine broken(n)\n"
        "  integer :: n\n"
        "  if (n > 0) then\n"
        "\n"
        "subroutine after(n)\n"
        "  integer :: n\n"
        "end subroutine after\n"
    )
    ranges = _ranges(src)

    broken = [r for r in ranges if r[2] == "broken"]
    assert broken, "the unclosed unit was not bounded at all"
    assert broken[0][1] < len(src.splitlines()), "the range ran to end-of-file"


def test_a_program_is_a_unit() -> None:
    src = (
        "program driver\n"
        "  use gravity_mod\n"
        "  print *, accel(0.0)\n"
        "end program driver\n"
    )
    assert _ranges(src) == [(1, 4, "driver", "class")]


def test_a_continuation_marker_does_not_break_a_signature() -> None:
    src = (
        "subroutine long_name(a, &\n"
        "                     b)\n"
        "  real :: a, b\n"
        "end subroutine long_name\n"
    )
    assert _ranges(src) == [(1, 4, "long_name", "function")]

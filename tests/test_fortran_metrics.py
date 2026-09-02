"""Fortran is measured with Fortran's own reading (1.6.0).

The scanner shipped in 1.4.0 found Fortran declarations correctly and
then handed them to a C-family measurement, which produced numbers that
were not approximate but wrong:

- `do` — the language's primary loop — is not in the C-family branch
  pattern, so **six nested loops scored complexity 1**.
- Fortran spells its logical operators `.and.` / `.or.`, not `&&` /
  `||`, so five of them scored 3.
- `end if` contains the word `if`, so every branch counted twice.
- Nesting was read from brace depth, and Fortran has no braces, so
  **four flat `if`s and four deeply nested ones both scored 8** — the
  metric that exists to measure nesting reporting none.

Scientific Fortran is mostly nested loops, so a numerical kernel read as
trivial: the score was wrong, and so was the ranking that decides which
routines a maintainer is told to fix.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from maintainability_audit._cognitive import fortran_cognitive
from maintainability_audit._metrics_types import fortran_branch_points
from maintainability_audit.config import load_config
from maintainability_audit.declarations import detect_functions, metrics_for


def _measure(src: str) -> tuple[int, int]:
    thresholds = load_config("maintainability-agent.json")["thresholds"]
    metric = detect_functions(
        Path("."), Path("x.f90"), src.splitlines(), thresholds
    )[0]
    return metric.complexity, metric.cognitive


@pytest.mark.parametrize(
    ("statement", "expected"),
    [
        ("do i = 1, n", 1),
        ("do while (x > 0)", 1),
        ("do concurrent (i = 1:n)", 1),
        ("if (a > b) then", 1),
        ("else if (a > c) then", 1),
        ("where (a > 0)", 1),
        ("elsewhere", 1),
        ("forall (i = 1:n)", 1),
        ("case (1)", 1),
        ("if (a .and. b) then", 2),
        ("if (a .or. b .or. c) then", 3),
        # Closers end a construct and decide nothing.
        ("end do", 0),
        ("end if", 0),
        ("enddo", 0),
        ("endif", 0),
        ("end where", 0),
        ("end select", 0),
        # `select case (n)` is a header whose *cases* are the branches,
        # and `case default` is its else.
        ("select case (n)", 0),
        ("case default", 0),
        # Not decisions at all.
        ("x = merge(1, 2, flag)", 0),
        ("call solve(a, b)", 0),
        ("integer :: i, j", 0),
    ],
)
def test_a_branch_point_is_counted_once_and_a_closer_never(
    statement: str, expected: int
) -> None:
    assert fortran_branch_points(statement) == expected


def test_the_primary_loop_is_not_free() -> None:
    """The defect that mattered most: `do` is most of scientific Fortran."""
    src = (
        "subroutine loops(n)\n"
        "  integer :: i, j, k, n\n"
        "  do i = 1, n\n"
        "     do j = 1, n\n"
        "        do k = 1, n\n"
        "           call work(i, j, k)\n"
        "        end do\n"
        "     end do\n"
        "  end do\n"
        "end subroutine loops\n"
    )
    complexity, cognitive = _measure(src)

    assert complexity == 4, "three loops plus the base path"
    assert cognitive == 6, "1 + 2 + 3: each loop costs one more than the last"


def test_nesting_is_visible_at_all() -> None:
    """Flat and deep must not score the same.

    This is the whole purpose of cognitive complexity, and on Fortran it
    was reporting the same number for both shapes.
    """
    flat = (
        "subroutine flat(n)\n  integer :: n\n"
        + "  if (n > 0) then\n     n = 1\n  end if\n" * 3
        + "end subroutine flat\n"
    )
    deep = (
        "subroutine deep(n)\n  integer :: n\n"
        "  if (n > 0) then\n"
        "     if (n > 1) then\n"
        "        if (n > 2) then\n"
        "           n = 1\n"
        "        end if\n"
        "     end if\n"
        "  end if\n"
        "end subroutine deep\n"
    )
    flat_complexity, flat_cognitive = _measure(flat)
    deep_complexity, deep_cognitive = _measure(deep)

    assert flat_complexity == deep_complexity == 4, (
        "cyclomatic complexity counts paths, and both shapes have three "
        "decisions — this is the number that is *supposed* to match"
    )
    assert flat_cognitive == 3, "three decisions, none nested"
    assert deep_cognitive == 6, "1 + 2 + 3 for the same three decisions, nested"
    assert deep_cognitive > flat_cognitive, (
        "nesting is what cognitive complexity is for; equal scores meant "
        "the metric could not see the thing it measures"
    )


def test_a_comment_is_not_a_branch() -> None:
    """Fortran comments start at `!`, which the C-family masker leaves
    alone because there `!` is negation. Unmasked, this comment reads as
    three branch points."""
    src = (
        "subroutine quiet(n)\n"
        "  integer :: n\n"
        "  ! if the residual is large, loop while it shrinks\n"
        "  n = 1   ! do not count this either\n"
        "end subroutine quiet\n"
    )
    assert _measure(src) == (1, 0)


def test_a_string_holding_keywords_is_not_a_branch() -> None:
    src = (
        "subroutine talk(n)\n"
        "  integer :: n\n"
        "  call log('if you do this while running, case closed')\n"
        "end subroutine talk\n"
    )
    assert _measure(src) == (1, 0)


def test_the_select_construct_counts_its_cases_not_its_header() -> None:
    src = (
        "subroutine pick(n)\n"
        "  integer :: n\n"
        "  select case (n)\n"
        "  case (1)\n"
        "     n = 10\n"
        "  case (2)\n"
        "     n = 20\n"
        "  case default\n"
        "     n = 0\n"
        "  end select\n"
        "end subroutine pick\n"
    )
    complexity, _cognitive = _measure(src)

    assert complexity == 3, "two cases plus the base path; default is the else"


def test_the_built_in_reading_agrees_with_lizard() -> None:
    """The cross-check that makes this more than self-consistent.

    lizard is an independent implementation that reads Fortran, and on
    this kernel it reports CCN 5. Before 1.6.0 the built-in said 1 for
    the same code. Pinned as a number rather than run as a subprocess so
    the suite stays offline; the recorded run is lizard 1.24.0.
    """
    kernel = (
        "subroutine kernel(a, n)\n"
        "  real :: a(:)\n"
        "  integer :: i, j, n\n"
        "  do i = 1, n\n"
        "     do j = 1, n\n"
        "        if (a(i) > 0.0 .and. a(j) < 1.0) then\n"
        "           a(i) = a(j)\n"
        "        end if\n"
        "     end do\n"
        "  end do\n"
        "end subroutine kernel\n"
    )
    complexity, _cognitive = _measure(kernel)

    assert complexity == 5, (
        "two loops, one condition and one `.and.`, plus the base path — "
        "and the same 5 lizard 1.24.0 reports for this file"
    )


def test_only_fortran_gets_the_fortran_reading() -> None:
    """The table is per language, and the C family must be untouched."""
    from maintainability_audit._cognitive import brace_cognitive
    from maintainability_audit._metrics_types import branch_points

    assert metrics_for(".f90") == (fortran_branch_points, fortran_cognitive)
    assert metrics_for(".F90") == (fortran_branch_points, fortran_cognitive)
    assert metrics_for(".pf") == (fortran_branch_points, fortran_cognitive)
    for suffix in (".c", ".cpp", ".cs", ".java", ".ts", ".py"):
        assert metrics_for(suffix) == (branch_points, brace_cognitive), (
            f"{suffix} must keep the C-family reading"
        )

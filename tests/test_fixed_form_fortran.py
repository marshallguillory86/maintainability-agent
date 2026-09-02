"""Fixed-form Fortran (1.6.0): the same language, laid out for cards.

1.4.0 claimed free-form and left `.f`, `.for` and `.ftn` unread, which
is exactly the code a legacy client has most of. Fixed-form is
column-significant — a label in columns 1-5, a continuation marker in
column 6, the statement in 7-72, sequence numbers after that, and a
`C` in column 1 for a comment — but none of that changes what a program
unit *is*. So it shares the recogniser and the `end`-keyword bounding
with free-form and differs only in how a line becomes a statement.

**Strength, in this project's own vocabulary** (`architecture.md` grades
every invariant Property or Regression, and these tests deserve the same
honesty). The numbers below are measured by mutation, not estimated:

- Swapping the fixed-form masker for the free-form one fails **one of
  nine** — `test_a_continued_condition_does_not_end_the_procedure_early`.
  That single test carries the whole card-column rule.
- Removing Fortran 77 labelled-`DO` tracking fails **three of nine**.

Everything else is a **defensive regression**, not a discriminator: a `C`
in column 1, a statement label, sequence numbers past column 72, and the
`ELSE IF` continuation below all assert the right answer, and on these
inputs the free-form reader reaches the same answer by another route,
because none of those shapes match its patterns either. Worth keeping;
they do not prove the masker runs.

That distinction was itself measured the hard way. The `ELSE IF` case was
added to this file as a *second* load-bearing test and this docstring
claimed it as one. It is not: without joining, the `IF ... THEN` above it
still opens and the `END IF` still closes, so the balance holds and the
answer is right either way. The claim was removed rather than the test.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._ranges_fortran import fixed_form_declaration_ranges
from maintainability_audit.config import load_config
from maintainability_audit.declarations import detect_functions


def _ranges(src: str) -> list[tuple[int, int, str, str]]:
    got, _masked = fixed_form_declaration_ranges(src.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in got]


def test_a_card_column_comment_is_not_code() -> None:
    """`C` in column 1 is how Fortran 77 wrote every comment, and it is
    a letter, so nothing about it looks like a comment to a scanner that
    was not told."""
    src = (
        "C     SUBROUTINE GHOST(X) -- OLD, DO NOT USE\n"
        "*     ANOTHER COMMENT WITH IF AND DO IN IT\n"
        "!     AND THE FREE-FORM MARKER, ALSO LEGAL HERE\n"
        "      SUBROUTINE REAL_ONE(X)\n"
        "      REAL X\n"
        "      END\n"
    )
    assert _ranges(src) == [(4, 6, "REAL_ONE", "function")]


def test_a_statement_label_is_not_part_of_the_statement() -> None:
    src = (
        "      SUBROUTINE LOOPY(N)\n"
        "      INTEGER N, I\n"
        "      DO 10 I = 1, N\n"
        "         CALL WORK(I)\n"
        "  10  CONTINUE\n"
        "      END\n"
    )
    assert _ranges(src) == [(1, 6, "LOOPY", "function")]


def test_a_continued_condition_does_not_end_the_procedure_early() -> None:
    """The falsifier this masker exists for.

    `THEN` sits on the continuation line. Read one line at a time, the
    `IF` looks single-line, no block opens, and the `END IF` below then
    closes the *procedure* — reporting it as ending four lines early and
    reading the rest of its body as top-level code.
    """
    src = (
        "      SUBROUTINE PICK(A, B, C, D)\n"
        "      REAL A, B, C, D\n"
        "      IF (A .GT. B .AND.\n"
        "     &    C .LT. D) THEN\n"
        "         A = B\n"
        "      END IF\n"
        "      A = A + 1.0\n"
        "      END\n"
    )
    assert _ranges(src) == [(1, 8, "PICK", "function")], (
        "the procedure must run to its own END, not stop at the END IF "
        "of a block the scanner failed to see open"
    )


def test_an_else_if_continuation_keeps_the_block_open() -> None:
    """A continued `ELSE IF`, kept as a regression rather than a proof.

    `ELSE IF` continues a block rather than opening one, so a reader that
    fails to join its continuation still sees the `IF ... THEN` above it
    open and the `END IF` below it close. The balance holds and the
    answer comes out right either way — which is why this test passes
    under the masker mutation and is documented above as defensive.
    It is worth keeping: it pins the shape against a future change that
    *would* unbalance it.
    """
    src = (
        "      SUBROUTINE GRADE(A, B)\n"
        "      REAL A, B\n"
        "      IF (A .GT. B) THEN\n"
        "         A = B\n"
        "      ELSE IF (A .LT. B .AND.\n"
        "     &         B .GT. 0.0) THEN\n"
        "         A = 0.0\n"
        "      END IF\n"
        "      A = A + 1.0\n"
        "      END\n"
    )
    assert _ranges(src) == [(1, 10, "GRADE", "function")], (
        "the procedure must run to its own END; a continuation that "
        "carries THEN is what keeps the ELSE IF balanced"
    )


def test_sequence_numbers_in_columns_73_onward_are_ignored() -> None:
    """Columns 73-80 held card sequence numbers and often hold junk."""
    src = (
        "      SUBROUTINE SEQ(N)                                                 00010\n"
        "      INTEGER N                                                         00020\n"
        "      END                                                               00030\n"
    )
    assert _ranges(src) == [(1, 3, "SEQ", "function")]


def test_a_program_unit_is_bounded_by_its_own_end() -> None:
    src = (
        "      SUBROUTINE FIRST(N)\n"
        "      INTEGER N\n"
        "      END\n"
        "      SUBROUTINE SECOND(N)\n"
        "      INTEGER N\n"
        "      END\n"
        "      FUNCTION THIRD(N)\n"
        "      INTEGER N, THIRD\n"
        "      THIRD = N\n"
        "      END\n"
    )
    assert _ranges(src) == [
        (1, 3, "FIRST", "function"),
        (4, 6, "SECOND", "function"),
        (7, 10, "THIRD", "function"),
    ]


def test_a_fixed_form_program_and_common_block_style_source() -> None:
    """A shape a 1980s tree is full of: PROGRAM, COMMON, nested DO."""
    src = (
        "      PROGRAM MAIN\n"
        "      COMMON /STATE/ X, Y\n"
        "      REAL X, Y\n"
        "      INTEGER I, J\n"
        "      DO 20 I = 1, 10\n"
        "         DO 10 J = 1, 10\n"
        "            IF (X .GT. Y) THEN\n"
        "               X = Y\n"
        "            END IF\n"
        "  10     CONTINUE\n"
        "  20  CONTINUE\n"
        "      END\n"
    )
    assert _ranges(src) == [(1, 12, "MAIN", "class")]


def test_fixed_form_is_measured_with_the_fortran_reading() -> None:
    """The metrics table must route `.for` like `.f90`, or a legacy tree
    gets the C-family reading that scored six nested loops as 1."""
    src = (
        "      SUBROUTINE KERNEL(A, N)\n"
        "      REAL A(*)\n"
        "      INTEGER I, J, N\n"
        "      DO 20 I = 1, N\n"
        "         DO 10 J = 1, N\n"
        "            IF (A(I) .GT. 0.0 .AND. A(J) .LT. 1.0) THEN\n"
        "               A(I) = A(J)\n"
        "            END IF\n"
        "  10     CONTINUE\n"
        "  20  CONTINUE\n"
        "      END\n"
    )
    thresholds = load_config("maintainability-agent.json")["thresholds"]
    metric = detect_functions(
        Path("."), Path("kernel.for"), src.splitlines(), thresholds
    )[0]

    assert metric.complexity == 5, "two loops, a condition and an .AND., plus the base"
    assert metric.cognitive > 0, "nesting must be visible in fixed-form too"


def test_uppercase_and_lowercase_suffixes_both_route_to_fixed_form() -> None:
    from maintainability_audit.declarations import SCANNERS

    routed = {
        suffix: scanner.__name__
        for suffixes, scanner in SCANNERS
        for suffix in suffixes
    }
    for suffix in (".f", ".for", ".ftn", ".F", ".FOR", ".FTN"):
        assert routed[suffix] == "fixed_form_declaration_ranges", suffix
    # And free-form must not have been swept up with them.
    assert routed[".f90"] == "fortran_declaration_ranges"

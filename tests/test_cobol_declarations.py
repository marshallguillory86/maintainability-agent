"""COBOL (2.7.0): the first language whose declarations have no end.

C closes a body with `}`. Fortran closes one with `end`. A COBOL
paragraph ends where the next paragraph begins, and nothing in the source
says so — the boundary is the *start* of the next thing. That is the one
genuinely new problem, and most of what follows tests it.

The other four judgments, each of which would be a defect if taken the
other way:

- a **level number is not a declaration**, or a DATA DIVISION floods the
  population every rate divides by;
- **programs and sections are containers**, graded not at all, or their
  paragraphs' lines are counted twice;
- **free-form is the default**, because reading fixed-form as free-form
  loses a declaration while the reverse mangles real code;
- and a **period closes every open scope**, which is how classic COBOL
  writes an `IF` with no `END-IF` at all.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit._ranges_cobol import cobol_declaration_ranges
from maintainability_audit.config import load_config
from maintainability_audit.declarations import detect_functions

THRESHOLDS = load_config("maintainability-agent.json")["thresholds"]


def _ranges(source: str) -> list[tuple[int, int, str, str]]:
    found, _masked = cobol_declaration_ranges(source.splitlines())
    return [(r.start, r.end, r.name, r.kind) for r in found]


def _names(source: str) -> list[str]:
    return [name for _s, _e, name, _k in _ranges(source)]


FREE = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. PAYROLL.
       DATA DIVISION.
       WORKING-STORAGE SECTION.
       01  WS-TOTAL     PIC 9(5) VALUE ZERO.
       01  WS-CUSTOMER.
           05  WS-NAME  PIC X(30).
           05  WS-ID    PIC 9(9).
       PROCEDURE DIVISION.
       MAIN-LOGIC.
           PERFORM READ-INPUT
           PERFORM COMPUTE-PAY
           STOP RUN.
       READ-INPUT.
           MOVE ZERO TO WS-TOTAL.
       COMPUTE-PAY.
           ADD 1 TO WS-TOTAL.
"""


def test_a_paragraph_ends_where_the_next_one_begins() -> None:
    """The whole problem, in one assertion.

    With no end marker, the risk is that the first paragraph swallows the
    rest of the division — which is what happens if the bounding rule
    looks for a terminator that never arrives.
    """
    assert _ranges(FREE) == [
        (10, 13, "MAIN-LOGIC", "function"),
        (14, 15, "READ-INPUT", "function"),
        (16, 17, "COMPUTE-PAY", "function"),
    ]


def test_a_level_number_is_not_a_declaration() -> None:
    """`01 WS-CUSTOMER.` is shaped exactly like a paragraph header.

    An ordinary program has hundreds of them. Counting them would not
    merely add noise — it would dominate the declaration population every
    rate divides by, and every COBOL repository would read as though it
    were nothing but tiny declarations.
    """
    assert "WS-CUSTOMER" not in _names(FREE)
    assert "WS-TOTAL" not in _names(FREE)


def test_the_program_and_its_sections_are_walked_into_but_not_graded() -> None:
    """Containers. Grading them counts their paragraphs' lines twice."""
    source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. REPORTER.
       PROCEDURE DIVISION.
       MAIN-SECTION SECTION.
       FIRST-PARA.
           DISPLAY "A".
       SECOND-PARA.
           DISPLAY "B".
"""

    assert _names(source) == ["FIRST-PARA", "SECOND-PARA"]


def test_a_paragraph_is_bounded_by_a_following_section_header() -> None:
    source = """\
       PROCEDURE DIVISION.
       SETUP-SECTION SECTION.
       OPEN-FILES.
           OPEN INPUT CUSTOMER-FILE.
       TEARDOWN-SECTION SECTION.
       CLOSE-FILES.
           CLOSE CUSTOMER-FILE.
"""

    assert _ranges(source) == [
        (3, 4, "OPEN-FILES", "function"),
        (6, 7, "CLOSE-FILES", "function"),
    ]


def test_a_paragraph_is_bounded_by_end_program() -> None:
    """A nested or explicitly-terminated program stops the last paragraph."""
    source = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. OUTER.
       PROCEDURE DIVISION.
       ONLY-PARA.
           DISPLAY "X".
       END PROGRAM OUTER.
"""

    assert _ranges(source) == [(4, 5, "ONLY-PARA", "function")]


def test_a_statement_that_looks_like_a_paragraph_header_is_not_one() -> None:
    """`EXIT.` alone on a line has a paragraph's exact shape.

    The EXIT-paragraph style writes one per paragraph, so reading these
    as declarations would roughly double the count in a codebase that
    uses it.
    """
    source = """\
       PROCEDURE DIVISION.
       DO-WORK.
           DISPLAY "working".
       DO-WORK-EXIT.
           EXIT.
"""

    assert _names(source) == ["DO-WORK", "DO-WORK-EXIT"]


def test_a_statement_in_area_b_is_never_a_paragraph_header() -> None:
    """Area A holds headers; Area B holds statements. That is the rule.

    `MOVE ZERO TO WS-TOTAL.` ends in a period and is one word away from
    matching, so the indentation bound is doing real work rather than
    being a stylistic guess.
    """
    source = """\
       PROCEDURE DIVISION.
       ONLY-PARA.
           MOVE ZERO TO WS-TOTAL.
           DISPLAY WS-TOTAL.
"""

    assert _names(source) == ["ONLY-PARA"]


def test_a_period_inside_a_literal_does_not_end_anything() -> None:
    """Masked before anything reads it, as in every other language."""
    source = """\
       PROCEDURE DIVISION.
       GREET.
           DISPLAY "END PROGRAM. NOT REALLY.".
       AFTER.
           DISPLAY "B".
"""

    assert _names(source) == ["GREET", "AFTER"]


# ---------------------------------------------------------------------------
# Fixed-form: the punched-card layout
# ---------------------------------------------------------------------------

FIXED = (
    "000100 IDENTIFICATION DIVISION.                                         \n"
    "000200 PROGRAM-ID. LEGACY.                                              \n"
    "000300 DATA DIVISION.                                                   \n"
    "000400 WORKING-STORAGE SECTION.                                         \n"
    "000500 01  WS-COUNT PIC 9(4).                                           \n"
    "000600 PROCEDURE DIVISION.                                              \n"
    "000700 MAIN-PARA.                                                       \n"
    "000800     MOVE 0 TO WS-COUNT.                                          \n"
    "000900 NEXT-PARA.                                                       \n"
    "001000     ADD 1 TO WS-COUNT.                                           \n"
)


def test_fixed_form_source_is_read_from_its_card_columns() -> None:
    """Sequence numbers in 1-6 are not code, and code stops at 72."""
    assert _ranges(FIXED) == [
        (7, 8, "MAIN-PARA", "function"),
        (9, 10, "NEXT-PARA", "function"),
    ]


def test_a_comment_card_is_not_read_as_code() -> None:
    source = (
        "000100 PROCEDURE DIVISION.                                          \n"
        "000200* THIS-IS-A-COMMENT.                                          \n"
        "000300 REAL-PARA.                                                   \n"
        "000400     DISPLAY 'X'.                                             \n"
    )

    assert _names(source) == ["REAL-PARA"]


def test_columns_are_stripped_only_where_no_code_lives_in_them() -> None:
    """The layout test asks a narrower question than it first appears.

    Not "was this written for a card punch" — unknowable, and the wrong
    question. Free-form source indented seven spaces is byte-identical in
    columns 1-7 to card source with a blank sequence field, so stripping
    seven blanks from it changes nothing and both are read correctly.

    What must be excluded is source with **code in columns 1-7**, where
    stripping deletes it. That is the only reading that invents findings
    rather than losing them.
    """
    from maintainability_audit._ranges_cobol import _looks_fixed_form

    assert _looks_fixed_form(FIXED.splitlines()) is True

    margin = [
        "IDENTIFICATION DIVISION.",
        "PROGRAM-ID. MODERN.",
        "PROCEDURE DIVISION.",
        "MAIN-PARA.",
        "    DISPLAY 'X'.",
    ]
    assert _looks_fixed_form(margin) is False, (
        "code in the first seven columns would have been deleted"
    )
    assert _names("\n".join(margin) + "\n") == ["MAIN-PARA"]


def test_free_form_source_read_as_free_form_keeps_its_declarations() -> None:
    """The consequence of the default being right for modern source."""
    assert len(_names(FREE)) == 3


# ---------------------------------------------------------------------------
# How COBOL is measured
# ---------------------------------------------------------------------------

def test_cobol_is_routed_to_its_own_scanner_and_metrics() -> None:
    from maintainability_audit.declarations import SCANNERS, metrics_for

    routed = {
        suffix: scanner.__name__
        for suffixes, scanner in SCANNERS
        for suffix in suffixes
    }
    assert routed[".cbl"] == "cobol_declaration_ranges"
    assert routed[".cob"] == "cobol_declaration_ranges"

    branch, cognitive = metrics_for(".cbl")
    assert branch.__name__ == "cobol_branch_points"
    assert cognitive.__name__ == "cobol_cognitive"


def test_an_end_scope_terminator_is_not_a_second_branch() -> None:
    """`END-IF` contains `IF`, with a word boundary at the hyphen.

    This is Fortran's `end if` defect in COBOL spelling: without stripping
    the closers first, every construct counts twice.
    """
    from maintainability_audit._metrics_types import cobol_branch_points

    assert cobol_branch_points("           IF X = 1") == 1
    assert cobol_branch_points("           END-IF") == 0
    assert cobol_branch_points("           END-EVALUATE") == 0


def test_a_perform_that_calls_is_not_a_loop_and_one_that_loops_is() -> None:
    """`PERFORM SOME-PARA` is a call; `PERFORM UNTIL` is a loop.

    Counting every `PERFORM` as a branch would make an ordinary
    call-per-line paragraph read as heavily branched, which is the shape
    of most well-factored COBOL.
    """
    from maintainability_audit._metrics_types import cobol_branch_points

    assert cobol_branch_points("           PERFORM READ-INPUT") == 0
    assert cobol_branch_points("           PERFORM UNTIL WS-EOF = 'Y'") == 1
    assert cobol_branch_points("           PERFORM VARYING I FROM 1 BY 1") == 1


def test_when_other_is_a_default_arm_not_a_decision() -> None:
    from maintainability_audit._metrics_types import cobol_branch_points

    assert cobol_branch_points("           WHEN 'A'") == 1
    assert cobol_branch_points("           WHEN OTHER") == 0


def test_a_branchy_paragraph_scores_above_a_flat_one() -> None:
    """The Fortran lesson: a language measured with the wrong vocabulary
    does not read approximately, it reads wrong. Six nested `do` loops
    scored complexity 1 before Fortran got its own reading."""
    source = """\
       PROCEDURE DIVISION.
       CLASSIFY.
           EVALUATE WS-CODE
               WHEN 'A' MOVE 1 TO WS-RANK
               WHEN 'B' MOVE 2 TO WS-RANK
               WHEN OTHER MOVE 9 TO WS-RANK
           END-EVALUATE
           IF WS-RANK > 1 AND WS-ACTIVE = 'Y'
               DISPLAY "HIGH"
           END-IF.
"""

    metric = detect_functions(
        Path("."), Path("p.cbl"), source.splitlines(), THRESHOLDS
    )[0]

    # Two `WHEN` arms, one `IF`, one `AND`, plus the base path. `EVALUATE`
    # itself is not counted, exactly as Fortran drops the `select case`
    # header and counts its `case` arms: the header is not a decision.
    assert metric.complexity == 5, (
        f"an EVALUATE with two arms, an IF and an AND scored "
        f"{metric.complexity}; COBOL's branch keywords are not being read"
    )


def test_a_period_closes_every_open_scope() -> None:
    """Classic COBOL writes `IF X DISPLAY Y.` with no `END-IF` at all.

    A reader that only decremented on `END-` terminators would let depth
    climb through the whole paragraph and charge the last statement for
    every branch above it.
    """
    from maintainability_audit._cognitive import cobol_cognitive

    periods = [
        "       PROCEDURE DIVISION.",
        "       P.",
        "           IF A = 1 DISPLAY 'A'.",
        "           IF B = 2 DISPLAY 'B'.",
        "           IF C = 3 DISPLAY 'C'.",
    ]
    nested = [
        "       PROCEDURE DIVISION.",
        "       P.",
        "           IF A = 1",
        "               IF B = 2",
        "                   IF C = 3",
        "                       DISPLAY 'C'",
        "                   END-IF",
        "               END-IF",
        "           END-IF.",
    ]

    assert cobol_cognitive(nested) > cobol_cognitive(periods), (
        "three nested IFs did not cost more than three sequential ones; "
        "either the period is not closing scopes or nesting is not counted"
    )


def test_a_copybook_with_no_procedure_division_mints_nothing() -> None:
    """`.cpy` is DATA DIVISION text, like a C header of prototypes.

    It still counts toward repository size, and it produces no
    declarations, which is the truth about it rather than a gap.
    """
    source = """\
       01  CUSTOMER-RECORD.
           05  CUST-ID      PIC 9(9).
           05  CUST-NAME    PIC X(30).
           05  CUST-BALANCE PIC S9(7)V99 COMP-3.
"""

    assert _names(source) == []

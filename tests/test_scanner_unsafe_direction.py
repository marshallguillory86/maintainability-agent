"""New scanners must miss in the safe direction, on the production path.

COBOL and Swift ship parsed. Under-count is accepted. Inventing a
declaration, or a cognitive score of 0 on nested control, is P7: a
number a reader with the file in front of them would call absurd.

The souvenir tests for both languages feed the parser a named fixture
and, for COBOL cognitive, call ``cobol_cognitive`` on a full file that
still contains ``PROCEDURE DIVISION``. Production grading goes through
``detect_functions``, which remasks a paragraph slice.

Population: suffix sets from ``SCANNERS``, not a list typed here.
Every COBOL suffix and every Swift suffix is exercised.

*Mutation:* 0-indent ``DISPLAY "A".`` after string blanking; a nested
``IF``/``END-IF`` paragraph through ``detect_functions``; a ``func``
inside a Swift ``\"\"\"`` string. None of those members is the
indented ``FREE`` fixture in ``test_cobol_declarations.py``.
"""

from __future__ import annotations

from pathlib import Path

from maintainability_audit.config import load_config
from maintainability_audit.declarations import (
    COBOL_SUFFIXES,
    SCANNERS,
    SWIFT_SUFFIXES,
    detect_functions,
)

THRESHOLDS = load_config("maintainability-agent.json")["thresholds"]


def _scanner_suffixes(wanted: set[str]) -> set[str]:
    """The SCANNERS row whose suffix set is ``wanted``.

    Fails if that language is no longer a scanner row, so this file
    cannot keep testing a set the dispatcher dropped.
    """
    for suffixes, _scanner in SCANNERS:
        if suffixes == wanted:
            assert suffixes, "SCANNERS row is empty"
            return suffixes
    raise AssertionError(
        f"{sorted(wanted)} is not a SCANNERS row; the unsafe-direction "
        "tests would be asserting against a language the dispatcher "
        "does not call"
    )


def _grade(source: str, suffix: str) -> list:
    return detect_functions(Path("."), Path(f"unit{suffix}"), source.splitlines(), THRESHOLDS)


COBOL_DISPLAY = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. HELLO.
       PROCEDURE DIVISION.
DISPLAY "A".
CALL "SUB".
MAIN-PARA.
    MOVE 1 TO WS-X.
"""

COBOL_NESTED = """\
       IDENTIFICATION DIVISION.
       PROGRAM-ID. NEST.
       PROCEDURE DIVISION.
       WORK.
           IF A = 1
               IF B = 2
                   DISPLAY "X"
               END-IF
           END-IF.
"""

SWIFT_TRIPLE = '''
let docs = """
func injected() {
    return 1
}
"""
func real() {
    return 2
}
'''


def test_cobol_and_swift_are_still_scanner_rows() -> None:
    """Population is derived from SCANNERS, then shown not empty."""
    cobol = _scanner_suffixes(COBOL_SUFFIXES)
    swift = _scanner_suffixes(SWIFT_SUFFIXES)
    assert cobol
    assert swift


def test_a_column_one_display_literal_is_not_a_cobol_paragraph() -> None:
    """Free-form statements live in column 1. Masking ``"A"`` must not
    leave ``DISPLAY    .`` looking like a paragraph header.

    *Mutation:* this source is not the indented ``FREE`` fixture.
    """
    suffixes = _scanner_suffixes(COBOL_SUFFIXES)
    for suffix in suffixes:
        names = [item.name.upper() for item in _grade(COBOL_DISPLAY, suffix)]
        invented = [name for name in names if name in {"DISPLAY", "CALL"}]
        assert not invented, (
            f"{suffix}: string-blanked statements became declarations {invented}; miss is allowed, inventing DISPLAY is not"
        )
        assert "MAIN-PARA" in names, f"{suffix}: the real paragraph vanished, so this is not a test of the production COBOL path"


def test_cobol_cognitive_is_nonzero_for_nested_ifs_on_detect_functions() -> None:
    """``cobol_cognitive`` remasks. A paragraph slice has no
    ``PROCEDURE DIVISION``, so production cognitive is identically 0.

    *Mutation:* ``detect_functions``, not ``cobol_cognitive(full file)``.
    The period-reset test in ``test_cobol_declarations`` does not
    go through this door.
    """
    suffixes = _scanner_suffixes(COBOL_SUFFIXES)
    for suffix in suffixes:
        funcs = _grade(COBOL_NESTED, suffix)
        assert funcs, f"{suffix}: nested IF paragraph produced no declaration"
        cognitive = [item.cognitive for item in funcs if item.name.upper() == "WORK"]
        assert cognitive, f"{suffix}: WORK was not graded"
        assert all(value > 0 for value in cognitive), (
            f"{suffix}: nested IF/END-IF scored cognitive {cognitive} "
            "through detect_functions; a reader of the paragraph would "
            "not call that nesting cost zero"
        )


def test_a_func_inside_a_swift_multiline_string_is_not_a_declaration() -> None:
    """``mask_lines`` is line-local. ``\"\"\"`` is an empty string plus a
    leftover quote, so later lines of the literal are read as code.

    *Mutation:* the injected ``func`` is not the ``real()`` the scanner
    should still find.
    """
    suffixes = _scanner_suffixes(SWIFT_SUFFIXES)
    for suffix in suffixes:
        names = [item.name for item in _grade(SWIFT_TRIPLE, suffix)]
        assert "injected" not in names, f"{suffix}: func injected() inside a triple-quoted string was reported as a declaration {names}"
        assert "real" in names, f"{suffix}: the real function vanished, so this is not a test of the production Swift path"

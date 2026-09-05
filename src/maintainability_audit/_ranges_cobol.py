"""Declaration ranges for COBOL.

The tenth parsed language, and the first whose declarations have **no end
marker at all**. C closes a body with `}`, Fortran with `end`. A COBOL
paragraph ends where the next paragraph begins — the boundary is the
*start* of the next thing, and nothing in the source announces it. That is
the one genuinely new problem here, and `_cobol_end` is the answer:
`scan_bounded` already takes the bounding rule as an argument, because
"a range never runs past its own body" is what is shared, not the
mechanism enforcing it.

**The unit of work is the paragraph.** A COBOL program is divided into
IDENTIFICATION, ENVIRONMENT, DATA and PROCEDURE divisions, and only the
last holds executable code. Inside it, work is organised into sections and
paragraphs, and `PERFORM SOME-PARAGRAPH` is how one is called. So a
paragraph is what a function is elsewhere: the named, callable, measurable
piece.

**Programs and sections are walked into and not graded.** Both are
containers, and grading them would count their paragraphs' lines a second
time — the same call `_ranges_swift` makes about an `extension`, for the
same reason. It costs one thing, stated plainly below: a section whose
statements sit outside any paragraph mints nothing.

**Level numbers are not declarations.** A DATA DIVISION is a wall of `01`,
`05`, `77` and `88` items, and an ordinary program has hundreds. They are
data, not work, and counting them would flood the population every
declaration rate divides by — the C# properties problem at a scale that
would swamp everything else. They are excluded by construction: the mask
blanks every division before PROCEDURE, so a level number is never offered
to the recogniser at all.

**Two source formats, and the default is the safe one.** Fixed-form COBOL
is punched-card source: a sequence number in columns 1-6, an indicator in
column 7, code in 8-72, and an identification field after that. Free-form
has none of it. Both use the same file extensions, so the extension cannot
decide, and this reads the file to find out.

The default when the evidence is weak is **free-form**, and the direction
matters. Reading fixed-form source as free-form leaves `000100` glued to
the front of a statement, so the recogniser does not match and the
declaration is missed — it under-reports. Reading free-form source as
fixed-form *deletes the first seven characters of every line*, which
mangles real code into plausible-looking nonsense and invents findings.
One of those errors is recoverable by a reader; the other is not.
"""
from __future__ import annotations

import re

from ._metrics_types import DeclRange
from ._ranges_core import scan_bounded

#: Column 7 in fixed-form source. A space is code, `*` and `/` are
#: comments, `-` continues a literal, and `D`/`d` is a debugging line that
#: several dialects compile only under WITH DEBUGGING MODE.
_INDICATORS = frozenset(" */-Dd")

#: Columns 1-6 hold a sequence number — digits, or blanks in source that
#: never went near a card punch.
_SEQUENCE_RE = re.compile(r"^[0-9 ]{6}$")

#: `PROGRAM-ID. NAME.` — the compilation unit. `IDENTIFICATION DIVISION`
#: precedes it and names nothing.
_PROGRAM_RE = re.compile(r"^\s*PROGRAM-ID\s*\.\s*([A-Za-z0-9][A-Za-z0-9-]*)", re.I)
#: `NAME SECTION.` — a container of paragraphs.
_SECTION_RE = re.compile(r"^\s{0,3}([A-Za-z0-9][A-Za-z0-9-]*)\s+SECTION\s*\.", re.I)
#: A paragraph header: a name alone on the line, ending in a period.
#:
#: The leading-space bound is Area A, and it is the real rule rather than a
#: guess about indentation. Fixed-form COBOL puts division, section and
#: paragraph headers in columns 8-11 (Area A) and statements in 12-72
#: (Area B); after the sequence and indicator columns are stripped, Area A
#: is offset 0-3 and Area B begins at offset 4 — which is why the bound is
#: three spaces and not four. Written `{0,4}` first, and a masked
#: `DISPLAY "A".` sitting at column 12 came straight back as a declaration
#: named DISPLAY — one per statement in the file.
#:
#: **The period abuts the name**, and that is the load-bearing half. Area A
#: only separates a header from an *indented* statement; free-form COBOL
#: writes statements in column 1 too, and once `"A"` is blanked to spaces
#: `DISPLAY "A".` is a word, a gap, and a period — the exact shape of a
#: header. The gap is what gives it away, because a real header has
#: nothing between its name and its period. That rejects the whole class
#: of operand-bearing statements (`CALL "SUB".`, `MOVE 1 TO X.`) rather
#: than a list of verbs, which would need a new entry per verb forever.
#: `_STATEMENT_WORDS` still covers the operand-*less* ones, where no gap
#: exists to see.
_PARAGRAPH_RE = re.compile(r"^\s{0,3}([A-Za-z0-9][A-Za-z0-9-]*)\.\s*$")
_DIVISION_RE = re.compile(r"^\s*[A-Za-z0-9-]+\s+DIVISION\s*\.", re.I)
_PROCEDURE_RE = re.compile(r"^\s*PROCEDURE\s+DIVISION\b", re.I)
_END_PROGRAM_RE = re.compile(r"^\s*END\s+PROGRAM\b", re.I)
#: `EXIT.`, `STOP.`, `CONTINUE.` and friends read as paragraph headers by
#: shape — a bare word and a period — and are statements.
_STATEMENT_WORDS = frozenset({
    "EXIT", "STOP", "CONTINUE", "GOBACK", "END-IF", "END-EVALUATE",
    "END-PERFORM", "END-READ", "END-SEARCH", "END-CALL", "END-STRING",
    "END-UNSTRING", "END-COMPUTE", "END-ADD", "END-SUBTRACT",
    "END-MULTIPLY", "END-DIVIDE", "END-RETURN", "END-WRITE", "END-START",
    "END-DELETE", "END-REWRITE", "END-ACCEPT", "END-DISPLAY",
})


def _looks_fixed_form(lines: list[str]) -> bool:
    """Whether the first seven columns can be stripped without losing code.

    Not "was this file written for a card punch", which is unknowable and
    would be the wrong question anyway. Free-form COBOL indented seven
    spaces — the overwhelmingly common convention — is byte-identical in
    those columns to fixed-form source whose sequence field is blank, and
    stripping seven blanks from it changes nothing. Both answer *yes*
    here, and both are then read correctly.

    What the test actually excludes is source with **code in columns 1-7**,
    where stripping would delete it. That is the only case where the two
    readings disagree, and it is the case worth being careful about:
    reading fixed-form as free-form loses declarations, while reading
    free-form as fixed-form deletes the front of every line and invents
    findings from the wreckage.

    Nine in ten substantive lines must qualify, so a handful of long
    literals cannot flip a file either way.
    """
    candidates = [line for line in lines if len(line.rstrip()) > 7]
    if len(candidates) < 3:
        return False
    fixed = sum(
        1 for line in candidates
        if _SEQUENCE_RE.match(line[:6]) and line[6] in _INDICATORS
    )
    return fixed >= 0.9 * len(candidates)


def _strip_card(line: str) -> str:
    """One fixed-form card, reduced to its statement.

    Columns 1-6 and 73-80 are not code. A `*` or `/` in column 7 is a
    comment line and is blanked whole; a `D` is a debugging line, read as
    code because it is code wherever debugging mode is on.
    """
    if len(line) <= 6:
        return ""
    indicator = line[6]
    if indicator in "*/":
        return ""
    return line[7:72]


def mask_cobol_lines(lines: list[str]) -> list[str]:
    """Source reduced to the statements a declaration can appear in.

    Three passes, and the last is the one that makes the recogniser
    simple. Card columns are stripped where the file is fixed-form.
    Comments and quoted literals are blanked, so a `PIC X(9) VALUE "A."`
    cannot look like a paragraph header. And **every division before
    PROCEDURE is blanked**, except the `PROGRAM-ID` line that names the
    unit.

    That third pass is what keeps level numbers out of the population
    without a single rule about level numbers. `WORKING-STORAGE SECTION.`
    and `FILE SECTION.` are shaped exactly like a procedure section, and
    `01 CUSTOMER-RECORD.` is shaped exactly like a paragraph header; no
    line-local pattern can tell them apart, because the difference is
    which division they are in. The mask has the whole file, so it is the
    one place that knows.

    Line count is preserved throughout: ranges are line numbers, and a
    mask that dropped a line would shift every declaration after it.
    """
    fixed = _looks_fixed_form(lines)
    masked: list[str] = []
    in_procedure = False
    for raw in lines:
        text = _strip_card(raw) if fixed else raw.rstrip("\n")
        if not fixed and text.lstrip().startswith("*>"):
            text = ""  # free-form inline comment marker
        text = re.sub(r"'[^']*'|\"[^\"]*\"", lambda m: " " * len(m.group(0)), text)
        if _PROCEDURE_RE.match(text):
            in_procedure = True
            masked.append(text)
            continue
        if _END_PROGRAM_RE.match(text):
            in_procedure = False
            masked.append(text)
            continue
        if not in_procedure and not _PROGRAM_RE.match(text):
            masked.append("")
            continue
        masked.append(text)
    return masked


def _cobol_declaration(text: str) -> tuple[str, str | None] | None:
    """``(name, kind)`` for a COBOL declaration on one masked line.

    ``kind`` is ``None`` for a program and a section: walk in, grade
    nothing. Only a paragraph is graded, because only a paragraph is the
    unit `PERFORM` calls and a maintainer reads as one piece.
    """
    program = _PROGRAM_RE.match(text)
    if program is not None:
        return program.group(1), None

    section = _SECTION_RE.match(text)
    if section is not None:
        return section.group(1), None

    if _DIVISION_RE.match(text) or _END_PROGRAM_RE.match(text):
        return None

    paragraph = _PARAGRAPH_RE.match(text)
    if paragraph is None:
        return None
    name = paragraph.group(1)
    if name.upper() in _STATEMENT_WORDS:
        # `EXIT.` alone on a line is a statement wearing a paragraph's
        # shape. Reading it as a declaration would mint one per paragraph
        # in every program written in the EXIT-paragraph style.
        return None
    return name, "function"


def _cobol_end(masked: list[str], lines: list[str], start: int) -> int:
    """Where the declaration starting at ``start`` ends.

    The new problem this language brings. There is no `}` and no `end`:
    a paragraph runs until the next paragraph, the next section, the end
    of the program, or the end of the file — whichever comes first. So
    the end is found by looking for the next *beginning*.

    A program ends at its `END PROGRAM` where one is written and at the
    end of the file where it is not, which is legal and common in
    single-program members.
    """
    here = _cobol_declaration(masked[start - 1])
    program = here is not None and _PROGRAM_RE.match(masked[start - 1]) is not None

    for index in range(start, len(masked)):
        text = masked[index]
        if _END_PROGRAM_RE.match(text):
            return index + 1 if program else index
        if program:
            continue
        # A section or paragraph is ended by the next header of either
        # kind. `PROCEDURE DIVISION` itself ends nothing that started
        # after it, and cannot appear inside one.
        if _SECTION_RE.match(text) or _cobol_declaration(text) is not None:
            return index
    return len(masked)


def cobol_declaration_ranges(lines: list[str]) -> tuple[list[DeclRange], list[str]]:
    """Paragraphs, each bounded by the start of whatever follows it.

    Programs and sections are descended into, because that is where
    paragraphs live, and are not graded themselves.

    Everything it misses, it misses in the safe direction:

    - **A section whose statements sit outside any paragraph** mints
      nothing. Grading the section instead would double-count the lines
      of every section that does contain paragraphs, which is the more
      common shape by far.
    - **`COPY` members are not expanded**, so a paragraph that arrives
      from a copybook is invisible here, exactly as an `#include`'d
      function is in C. The copybook is scanned on its own if it is in
      the tree.
    - **`REPLACE` and nested `COPY ... REPLACING`** are not applied; the
      source is read as written.
    - **A continuation line** (`-` in column 7) is read as its own line
      rather than joined. It continues a literal, and a literal is masked
      before anything reads it.
    - **Free-form source is the default**, so genuinely fixed-form source
      that fails the layout test loses its declarations rather than
      having its columns cut off.
    """
    return scan_bounded(
        lines,
        _cobol_declaration,
        descend=("class",),
        skip_bare=False,
        find_end=_cobol_end,
        mask=mask_cobol_lines,
    )

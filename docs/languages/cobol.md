# COBOL

**The paragraph is the unit of work.** A COBOL program has four divisions
— IDENTIFICATION, ENVIRONMENT, DATA and PROCEDURE — and only the last
holds executable code. Inside it, work is organised into sections and
paragraphs, and `PERFORM SOME-PARAGRAPH` is how one is called. A paragraph
is therefore what a function is elsewhere: the named, callable,
measurable piece.

**COBOL is the first language here whose declarations have no end.** C
closes a body with `}`; Fortran closes one with `end`. A paragraph ends
where the next paragraph, the next section, `END PROGRAM` or the file
begins — the boundary is the *start* of the next thing, and nothing in
the source announces it. `scan_bounded` already took the bounding rule as
an argument, so this needed no change to the shared walk: what is shared
is that a range never runs past its own body, not the mechanism that
enforces it.

**Level numbers are not declarations.** A DATA DIVISION is a wall of `01`,
`05`, `77` and `88` items, and an ordinary program has hundreds. `01
CUSTOMER-RECORD.` is shaped *exactly* like a paragraph header, and no
line-local rule can tell them apart, because the difference is which
division they are in. So the mask blanks every division before PROCEDURE,
and a level number is never offered to the recogniser at all. Counting
them would not merely add noise — it would dominate the declaration
population every rate divides by, and every COBOL repository would read as
though it were nothing but tiny declarations.

**Programs and sections are walked into and not graded.** Both are
containers, and grading them would count their paragraphs' lines a second
time — the same call the Swift scanner makes about an `extension`.

**Area A is the rule, not a guess about indentation.** Fixed-form COBOL
puts division, section and paragraph headers in columns 8-11 and
statements in 12-72, and free-form convention keeps the same shape. That
is why a paragraph header is recognised only within the first four columns
of the stripped statement. Allowing one more column, which the first
working version did, matched a masked `DISPLAY "A".` sitting at column 12
and reported a declaration named DISPLAY once per statement in the file.

**Both source formats, and the default is the safe one.** Fixed-form is
punched-card source: a sequence number in columns 1-6, an indicator in
column 7, code in 8-72. Both formats use the same extensions, so the
extension cannot decide and the file is read to find out. The test is
narrower than it looks: free-form indented seven spaces is byte-identical
in those columns to card source with a blank sequence field, and stripping
seven blanks from it changes nothing. What is excluded is source with
*code* in columns 1-7 — the only case where the two readings disagree.
The direction matters: reading fixed-form as free-form loses declarations,
while reading free-form as fixed-form deletes the front of every line and
invents findings from the wreckage.

**A period closes every open scope.** Classic COBOL writes `IF X DISPLAY
Y.` with no `END-IF` anywhere, so a reader that only decremented on `END-`
terminators would let nesting climb through a whole paragraph and charge
the last statement for every branch above it.

What it misses, it misses in the safe direction:

- **A section whose statements sit outside any paragraph** mints nothing.
- **`COPY` members are not expanded**, so a paragraph arriving from a
  copybook is invisible, exactly as an `#include`d function is in C. The
  copybook is scanned on its own if it is in the tree — and a `.cpy` of
  DATA DIVISION text produces no declarations, like a C header of
  prototypes.
- **`REPLACE` and `COPY ... REPLACING`** are not applied; source is read
  as written.
- **A continuation line** (`-` in column 7) is read as its own line rather
  than joined. It continues a literal, and literals are masked first.

**Analyzer coverage is thin, and this is where COBOL differs most from
the other nine.** lizard does not read COBOL; neither does jscpd usefully.
The mainframe world's tooling — IBM Developer for z/OS, Application
Discovery and Delivery Intelligence, and the build tooling around IBM
Dependency Based Build — lives outside anything this project can invoke
offline. So the built-in scanner is the only path to a declaration
population here, as it is for Fortran, and the analyzer tier will report
COBOL as unmeasured rather than pretending otherwise.


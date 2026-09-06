# Fortran

**The first language here with no braces.** C, C++, C# and Java share
one walk because a body sits between `{` and `}`. Fortran closes a
program unit with a keyword — a `subroutine` ends at `end subroutine`, a
`module` at `end module`, and a bare `end` is legal for several of them.
The rule is unchanged and the mechanism is not: the shared walk takes a
`find_end`, and Fortran supplies one that counts program units instead
of braces.

Counting matters because `if`, `do`, `select`, `associate` and `block`
all close with `end` too. A scanner that stopped at the first `end`
would report a subroutine as ending at its first `end if`, and read the
rest of its body as top-level code.

Modules, submodules, programs and derived types are descended into,
because that is where procedures live; a procedure body is stepped over.
A function is named correctly whether it is written with a type prefix
(`pure elemental real(dp) function norm(v)`) or a `result` clause
(`real function accel(h) result(a)`). Keywords are matched
case-insensitively, because Fortran is and older code SHOUTS.

**An `interface` block is stepped over, not descended into.** It holds
signatures with no bodies, so walking in would mint a one-line
declaration for every procedure a module merely *describes* — inflating
the population every declaration rate divides by, with procedures
defined somewhere else entirely.

**Fixed-form is read as of 1.6.0.** `.f`, `.for`, `.ftn` and their
uppercase spellings are column-significant, and the columns mean what
punched cards meant: a label in 1-5, a continuation marker in column 6,
the statement in 7-72, and sequence numbers after that. A `C`, `c`, `*`
or `!` in column 1 makes the whole line a comment.

None of that changes what a program unit *is*, so fixed-form shares the
recogniser and the `end`-keyword bounding with free-form and differs
only in how a line becomes a statement. **Continuation lines are joined
onto the statement they continue** before anything is read, which is
not tidiness: a condition written

```fortran
      IF (A .GT. B .AND.
     &    C .LT. D) THEN
```

has its `THEN` on the second line. Read line by line the first looks
like a single-line `IF`, no block opens, and the matching `END IF` then
closes something that was never opened — ending the enclosing procedure
early and reading the rest of its body as top-level code.

Two limits: indentation carries no meaning in fixed-form, so the
fallback for a unit whose `end` is missing is weaker here than in
free-form; and a `D` in column 1 is a debug line in several legacy
dialects but is not standard, so it is read as code rather than guessed
at.

`.F90` (capital F) means "run the C preprocessor first" and is read as
free-form; unexpanded macros are invisible, the same limitation C
documents. `.pf` is pFUnit test source — free-form Fortran plus `@test`
directives — and is read and treated as a test file.

Everything else it misses, it misses in the safe direction:

- **Statement functions** (a one-line `f(x) = x*2`) are not declarations.
- **Declarations produced by `#include` or a macro** are invisible.
- **A procedure whose `end` is missing** falls back to indentation, which
  is a weak signal in Fortran; it costs that one declaration.

**Testing conventions are recognised, because the claim depends on it.**
fpm puts tests in `test/`; test-drive writes `test_gravity.f90`; pFUnit
writes `.pf` files and the camelCase `testGravity_mod.F90`. A module file
is conventionally `gravity_mod.f90`, so `_mod` comes off both sides when
pairing. Claiming Fortran without these would report untested production
code on every Fortran repository there is.

Fortran gained an analyzer in 1.5.0 — **fortitude**, 100+ lint rules —
but it is a verdict emitter: it reports findings and cannot supply a
declaration population. lizard, which could, does not read Fortran. So
the built-in scanner remains the only path to a population here, rather
than the zero-install convenience it is for C and C++.


# Language Support and Detection Accuracy

What the scanner can see per language, how it decides where a declaration
ends, and — deliberately — where it under-reports.

## How each language is measured

| Language | Declaration ranges | Accuracy |
|---|---|---|
| Python (`.py`) | `ast` — exact `end_lineno` | Exact. Falls back to the pattern scan only if the file has a syntax error. |
| Java (`.java`) | dedicated scanner: methods, constructors and types, bounded by their own braces | Bounded. Under-reports — see below. |
| C (`.c`, `.h`) | dedicated scanner: file-scope functions and `struct`/`enum`/`union` types, bounded by their own braces | Bounded. Under-reports — see below. |
| C++ (`.cpp`, `.hpp`, `.cc`, `.cxx`, `.hh`) | dedicated scanner: functions, class/struct members, namespaces and templates, bounded by their own braces | Bounded. Under-reports — see below. |
| C# (`.cs`) | dedicated scanner: methods, constructors and types (`class`, `interface`, `struct`, `record`, `enum`), bounded by their own braces | Bounded. Properties are not declarations — see below. |
| Fortran, free-form (`.f90`, `.f95`, `.f03`, `.f08`, `.F90`, `.F95`, `.F03`, `.F08`, `.pf`) | dedicated scanner: modules, submodules, programs, subroutines, functions and derived types, bounded by their own `end` | Bounded by keyword rather than braces. Fixed-form is excluded — see below. |
| JS / TS / JSX / TSX (`.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`) | brace/paren depth over a comment- and string-masked copy | Bounded by the declaration's own braces. |
| HTML (`.html`) | same brace scanner, so inline `<script>` bodies are measured | Bounded. |
| Anything else | not parsed for declarations | File length, duplication and risk only, and declaration rates **withheld** with the missing parser named. Adding the suffix to `include_extensions` does not produce a declaration population. |

**This table is the claim, and it is enforced.** An audit found the
page and [Decision 10](decisions.md) saying v1.0 handled Python and
Java while the scanner also read JS, TS, JSX and HTML — and it does,
with three baseline-tier adapters (lizard, jscpd, multimetric)
measuring those files besides. The mismatch was in the writing, not the
code: a language belongs here when this project can detect and score
it.

What the tool must never do is produce a declaration population for a
language it can neither parse nor send to an adapter. That is the P7
failure — a number a reader with the repository in front of them would
call absurd —
and `test_the_parsed_languages_are_exactly_the_claimed_languages`
fails when this page and the parser disagree in either direction, so a
suffix added to one has to reach the other.

Only these extensions get declaration-level findings. Every other
extension in `include_extensions` is still measured for file length,
duplication, and risk patterns.

The pattern scan named in the Python row is the only place it runs.
`SourceIndex` asks for declaration ranges only when the suffix is one of
the rows above, so a `.go` or `.rs` file does not reach it — deliberately,
because its patterns match `def` and `function` and would report such a
file as containing no declarations rather than as unparsed. A repository
whose code is mostly outside those extensions has its declaration rates
**withheld**, naming the missing parser as the reason; it does not get an
approximate population.

### What the Java scanner sees, and what it misses

Methods, constructors, and types — classes, interfaces, enums, records
and `@interface` declarations. Generic parameter lists are blanked
before matching, so `<T extends Comparable<T>>` neither ends a signature
early nor supplies the name; leading annotations are stripped with their
values, so `@Deprecated(since = "1.2")` is not read as a method called
`Deprecated`.

It walks member context only. A type's body is descended into, because
that is where its members live; a method's body is stepped over once its
end is known, so no statement inside it can be read as a declaration.
That single rule is why a nested class and its methods stay visible
while `doThing(x);` never becomes a declaration named `doThing`.

Everything it misses, it misses in the safe direction:

- **Declarations inside anonymous classes and lambdas** are not counted,
  because they sit inside a method body.
- **Text blocks** (`"""`) are not masked, so a brace inside one can
  desync depth. The indentation fallback bounds that to one declaration.
- **A field initialised with a method reference or an inline array** is
  not a declaration and is not reported as one.

Complexity for Java is the same keyword count used everywhere else here,
not a control-flow graph. Pair it with an external analyzer when the
number has to be exact.

### What the C scanner sees, and what it misses

File-scope function definitions and `struct`, `enum` and `union` types,
each bounded by its own braces. Storage-class and inline keywords
(`static`, `extern`, `inline`, `_Noreturn`, …) are stripped before
matching, so `static inline int clamp(` is a function named `clamp`; a
pointer return type is stripped with them, so `const char *greeting(`
names `greeting` and not its type. The brace may sit on the signature
line or on its own line below it, and the signature may span several
lines — all three are ordinary C style and all three are bounded
correctly.

Two things are deliberately not declarations. A **prototype** has no
body, so it mints no population — a header of 40 prototypes is not 40
declarations. A **preprocessor line** is skipped whole, so
`#define MAX(a, b) ((a) > (b) ? (a) : (b))` is not read as a function
called `MAX`; macros are text substitution, and measuring one as a
declaration would report a length and a complexity nobody wrote.

Function bodies are stepped over once their end is known, so nothing
inside one — `if (`, `for (`, a call — can be read as a declaration.
Unlike Java, type bodies are not descended into either: C types hold
fields, not methods, so there is nothing inside them to grade.

Everything it misses, it misses in the safe direction:

- **K&R-style definitions** (`int add(a, b)` with the parameter
  declarations on following lines) are not recognised. Cost: that one
  function, not the file.
- **Declarations produced by macros** — a function defined inside a
  `#define`, or a body wrapped in `BEGIN_/END_` macros — are invisible.
- **`.h` is treated as C.** A C++ header using `.h` gets the C scanner,
  which reads its free functions and `struct`s and misses its classes
  and methods. The C++ increment disambiguates this.
- **Conditional compilation is not evaluated.** Both arms of an
  `#if`/`#else` are read as ordinary source, so a declaration in a
  disabled arm still counts.

Complexity for C is the same keyword count used everywhere else here,
not a control-flow graph. Pair it with an external analyzer — lizard
covers C and is in the shipped pool — when the number has to be exact.

### What the C++ scanner sees, and what it misses

Free functions, class and struct members, constructors, destructors,
operator overloads, and the types themselves — `class`, `struct`,
`union`, `enum` and `enum class`. A type is descended into, because that
is where its methods live; a function body is stepped over once its end
is known, so nothing inside one is read as a declaration.

Names are reported the way a reader searches for them. An out-of-line
definition keeps its qualification — `void geo::Widget::draw()` is
`geo::Widget::draw`, not a second `draw` indistinguishable from every
other class's. An operator overload is `operator==`. A `template <...>`
header is stripped, so the declaration under it is measured rather than
the template line.

A **bodyless declaration is not a definition**, as in C: a prototype, a
pure virtual (`virtual int area() const = 0;`) and `= default` / `=
delete` all mint nothing. A header of forty declarations is not forty
declarations.

Everything it misses, it misses in the safe direction:

- **A constructor braced Allman inside its class** (`W()` with `{` on
  the next line, no return type and no qualification) is not counted.
  That shape is indistinguishable from a bodyless macro invocation
  written `MY_MACRO(x)`, and accepting it let the macro absorb the next
  declaration's braces — an invented function hiding a real one. Missing
  one constructor is the cheaper error.
- **Declarations produced by macros** are invisible, as in C.
- **A template header spanning several lines** leaves its declaration
  unrecognised — one missed declaration, never a cascade.
- **Methods of a local class or inside a lambda** sit within a function
  body and are not counted.
- **Conditional compilation is not evaluated**, so a declaration in a
  disabled `#if` arm still counts.

`.h` remains **C**, not C++: it is the one extension both languages
write, and the C reading under-reports a C++ header (finding its free
functions and structs, missing its classes) where the reverse would
invent nothing but read nothing either.

Complexity for C++ is the same keyword count used everywhere else here.
lizard covers C++ and is in the shipped pool when the number has to be
exact.

### What the C# scanner sees, and what it misses

Methods, constructors, destructors, and the types — `class`,
`interface`, `struct`, `record`, `record struct` and `enum`. Types are
descended into, because that is where members live; a method body is
stepped over. Generic parameter lists are blanked before matching, so
`public List<T> Sort<T>(List<T> items) where T : IComparable` yields
`Sort`, and attributes are stripped with their arguments, so
`[Obsolete("x")]` is not read as a method called `Obsolete`.

Namespaces are handled in both forms: a braced `namespace Geo {` is
walked into without being graded, and C# 10's file-scoped `namespace
Geo;` declares nothing and is ignored rather than being allowed to
swallow the file.

**Properties are deliberately not declarations.** `public int Count {
get; set; }` has braces and would bound cleanly, and an ordinary C# tree
holds thousands of them — each one line long, each nobody's maintenance
burden. Counting them would dilute the population that every
declaration rate divides by. They are excluded by construction: a
property has no parameter list, and every pattern here requires one. The
same applies to a parameterless expression-bodied member
(`public int Area => w * h;`). A method written `public int Fast() =>
count_;` **is** counted — it has a parameter list.

Everything it misses, it misses in the safe direction:

- **Interface and abstract members** have no body, so they mint nothing.
  A positional `record Point(int X, int Y);` likewise.
- **Local functions** live inside a method body and are not counted.
- **Source-generated declarations** are not in the tree and are not seen.
- **Conditional compilation is not evaluated**, so a member in a
  disabled `#if` arm still counts.

### What the Fortran scanner sees, and what it misses

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

**Fixed-form is deliberately not claimed.** `.f`, `.for` and `.ftn` are
column-sensitive: a comment is `C` in column 1, a continuation is any
character in column 6. That is a different scanner with different
failure modes, and reading it with free-form rules would be an
approximation nobody asked for. Those suffixes stay out of the default
extensions until they have a scanner and falsifiers of their own.

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

## The rule that matters: a range never runs past its own body

Before v0.4.0, a declaration ended where the *next* pattern match began.
That is only safe if the pattern list matches every declaration in the
file — and it didn't. `export function`, generic signatures like
`async function request<T>(`, and object/class methods were invisible, so
the first recognised declaration absorbed everything up to the next match
or to end-of-file.

The damage was not subtle. In one TypeScript API client a 4-line
`csrfToken()` was reported as **262 lines with complexity 35**, the clean
file holding it was graded an **F**, and every one of the 18 function
findings on that repo was false.

Ranges are now bounded by the declaration's own braces, counted over a
copy of the source with comments and string/template literals blanked
out. The consequence is the important part: **a declaration this scanner
fails to recognise costs one missed finding, not a cascade of false
ones.** Where braces are unavailable or inconclusive, the range falls
back to indentation. Nothing runs to end-of-file any more.

Complexity is scored against that same masked copy, so `if` in a doc
comment and `?` in a URL are no longer counted as branches.

## Known limitations

All of these under-report rather than over-report, which is the trade
this design deliberately makes:

- **Object-literal properties holding arrow functions** (`onSave: () => {…}`)
  are not treated as declarations. Class fields and `const` bindings are.
- **Regex literals are not tokenized**, so an unbalanced brace inside one
  (`/[{]/`) can desync brace depth. The indentation fallback bounds the
  fallout to that single declaration.
- **An inline object return type** (`function f(): { a: string } {`) can
  end a range at the annotation when no second `{` follows on the same line.
- **Complexity is approximate** everywhere — a keyword count, not a real
  control-flow graph. Pair this with Radon, ESLint, or SonarQube when you
  need a precise number.

## Classes are not graded as functions

A class is a container, so the per-function line budget is the wrong
yardstick — an ordinary six-method class is not a defect. Classes are
measured against `max_class_lines` / `warn_class_lines` (default 300 /
200) on **length alone**.

Complexity is not applied to a class at all, and the report shows `-`
rather than a number. `ast.walk` yields a class *and* each of its
methods, so a class's measured complexity is the sum of branches already
charged to those methods — acting on it would mean double-counting.

In the report, prompt, PR comment, and SARIF output a class is labelled
as one: `` `ScanWorker` (class) ``.

## Migrations are excluded by default

`migrations/` is in the default `exclude_patterns`. A 102-line,
complexity-2 `upgrade()` is what a correct migration looks like, and
migrations are append-only history — refactoring one rewrites the past.
Remove the pattern from your config if you disagree.

# C

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


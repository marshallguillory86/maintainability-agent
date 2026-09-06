# C++

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


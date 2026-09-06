# Swift

Functions, initialisers, deinitialisers, subscripts, and the types —
`class`, `struct`, `enum`, `protocol` and `actor`. Types and extensions are
descended into, because that is where members live; a function body is
stepped over.

**Every Swift declaration is keyword-led**, which makes recognition easier
here than in C++: a bare `name(` there is equally a call, a macro and a
constructor, and a wrong guess once let a macro swallow the next
declaration's braces. Nothing in Swift has to be guessed.

**An `extension` member is reported under the type it extends.**
`extension Widget { func draw() }` is `Widget.draw`, not a second bare
`draw` indistinguishable from every other type's. C++ gets this for free
because the source writes `void geo::Widget::draw()`; Swift does not write
it, so the scanner carries it. A work order saying "shorten `draw`" against
a tree with eleven of them is not a bounded instruction.

**`class` is read as a keyword or a modifier as the line requires.** Swift
spells two things with it: `class Widget` declares a type, `class func
make()` declares a type-level method. Stripping it with the other modifiers
cost every `final class Store` its keyword — the type vanished and only its
members were reported, which makes a declaration *rate* wrong rather than
merely incomplete.

**A protocol requirement mints nothing.** Swift has no statement
terminator, so the shared bare-signature rule — a signature that closes
without opening a brace, which in C is a `;` — cannot see where a
requirement ends. The first version walked on and adopted the next line's
brace, reporting `func describe() -> String` as two lines of body. The rule
that replaces it: parentheses balancing on the line with no `{` following
means no body. A wrapped signature leaves them unbalanced and is kept.

Everything it misses, it misses in the safe direction:

- **Computed properties** (`var area: Double { w * h }`) are not
  declarations — the C# properties call, for the C# reason: an ordinary
  type has many, each a line or two, and counting them dilutes the
  population every rate divides by.
- **A body written Allman** — `func f()` with `{` alone on the next line —
  is read as a requirement and mints nothing. Legal Swift, vanishingly rare
  in it, and missing one declaration is cheaper than counting every
  protocol requirement in the tree.
- **A closure assigned to a property** is a body with no declaration
  keyword and is not counted.
- **Declarations produced by a macro** are not in the source and are not
  seen, as in C and C++.
- **Conditional compilation is not evaluated**, so a declaration in a
  disabled `#if` arm still counts.

**Swift has analyzer coverage, unlike Fortran.** `lizard` reads it for
complexity and `jscpd` for duplication, both in the shipped pool, and
`swiftlint`, `swiftformat` and `tailor` are catalogued as verdict emitters.
So a Swift repository gets analyzer-primary evidence rather than depending
on the built-in scanner alone — the position Fortran is still in, where
`fortitude` reports findings but cannot supply a declaration population.

**Swift is measured with its own reading of a branch.** `guard` is the
language's primary early exit and is absent from the C-family pattern, so a
guard-heavy function would have read as branchless — the defect Fortran
shipped with, where six nested `do` loops scored complexity 1 because the
pattern did not know the keyword.

Three constructs are deliberately **not** counted, each of which was
counted until 2.11.0:

- **`Int?` is an optional type, not a ternary.** A `?` was read as a
  conditional wherever it appeared, so every optional in the file scored
  a branch. A ternary needs both halves, so a following `:` is now
  required (D115). The cost is a ternary split across lines, which is
  not counted — under-reporting, the direction this project errs in.
- **`repeat` is not counted.** `repeat { … } while cond` is one loop with
  one condition, and the `while` carries it. Counting both scored the
  construct and its own test (D117).
- **`switch` is counted at its cases, not at its header**, the rule
  shared with Go, PHP, Ruby, Python and Fortran.


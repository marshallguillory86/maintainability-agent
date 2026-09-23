# Kotlin

Functions, constructors, `init` blocks, and the types — `class`,
`interface`, `object`, and the `data`, `sealed`, `enum`, `annotation`,
`value` and `inner` forms, each of which is a *modifier* on `class` or
`object` rather than a keyword of its own. Types and objects are
descended into, because that is where members live; a function body is
stepped over.

**Kotlin is keyword-led and braced**, so the walk is the one C, C++, C#,
Java and Swift share. Three things make its reading its own.

**An extension function writes its own receiver.** `fun Widget.draw()`
is `Widget.draw` in the report because it is `Widget.draw` in the
source. This is the one place Kotlin is *easier* than Swift, which
spells the same idea `extension Widget { func draw() }` and needs a
second pass to carry the type name onto the member. A work order saying
"shorten `draw`" against a tree with eleven of them is not a bounded
instruction, and Kotlin hands over the qualification for free.

**An expression body has no brace.** `fun area() = w * h` is idiomatic
Kotlin rather than a corner, and two shared mechanisms reach the wrong
answer on it. The end-finder bounds a body by its braces and falls back
to indentation, and that fallback walks to the closing `}` of the
*enclosing class* — so a one-line function came back two lines long,
with the brace that ends its container counted as its last line. And the
shared bodyless check looks for `=>`, the arrow JavaScript and C# use
for an expression member; Kotlin writes `=`, so every expression-bodied
function in the tree would have been dropped as a signature with nothing
behind it. Kotlin therefore supplies its own end-finder and answers the
bodyless question itself.

**A type with no body is still a type.** `data class Point(val x: Int)`
is a complete, useful class and mints a declaration. `fun draw()` inside
an interface is a requirement and mints nothing, as in C, C++, C# and
Swift. The bodyless rule is about functions, not about declarations in
general — which is where C++ and Swift, whose bodyless *types* are
forward declarations, are not a guide.

Everything it misses, it misses in the safe direction:

- **Properties are not declarations**, accessor or not. `val area: Int
  get() = w * h` is the computed property C# and Swift already exclude,
  for the reason they exclude it: an ordinary type has many, each a line
  or two, and counting them dilutes the population every rate divides by.
- **A trailing lambda mints nothing.** Kotlin's syntax puts one in
  almost every collection pipeline, and grading each as a function would
  flood the population with one-line members. `lizard` does mint them,
  which is declared as a divergence rather than absorbed.
- **An anonymous `object : Foo { }` expression** is a body with no
  declaration keyword leading the line and is not counted.
- **An anonymous `companion object` is named `Companion`** — Kotlin's
  own default — so the walk descends into it. Returning no name would
  skip its members, and a companion object is where Kotlin puts its
  factories.
- **A body written with the brace on the next line** leaves the
  signature's parentheses balanced with no `{` and no `=`, so it reads
  as a requirement and mints nothing. Legal Kotlin, vanishingly rare in
  it, and missing one declaration is cheaper than counting every
  interface requirement in the tree.

## What counts as a decision

**`when` is counted at its arms, not at its header** — the rule shared
with `switch` in Go, PHP, Ruby, Python, Swift and Fortran, and bought by
the Fortran `select case` defect where an N-way branch scored 1. Kotlin
spells an arm `->`, which is also how it spells a lambda's parameter
list and a function type, so both are consumed before the arms are
counted. The cost is a `when` written entirely on one line, whose first
arm is eaten with the brace — under-reporting, the direction this
project errs in. The `else` arm is not counted, as Go declines
`default` and Rust declines `_ =>`.

**`?:` decides and `?.` does not.** Elvis is Kotlin's `??`: both halves
are written, which is the test the C family already applies. A safe call
yields `null` and carries on down the same path, and is the optional
chaining C, C#, TypeScript and Java all decline to count. Rust's `?` *is*
counted here and the difference is real rather than a taste — Rust's
returns early from the function.

**There is no ternary.** `if` is an expression in Kotlin, so the
C-family `?…:` alternative is absent rather than merely unused. With it,
`fun find(id: Int?, name: String?)` would score two: D115's defect in a
sixth spelling, after C#, TypeScript, PHP, Java and Swift.

**`do` is not counted.** `do { … } while (cond)` is one loop with one
condition and the `while` carries it, as PHP's `do` and Swift's `repeat`
already do.

## Second opinion

Checked construct by construct against `lizard` 1.24.0, which reads
Kotlin although the upstream analyzer inventory never said so — the same
stale-row problem that left Fortran without a metric emitter for two
releases. The two readings agree on `if`, `&&`, `for`, `while`, elvis,
and on a `when` with an `else`.

They differ in one place, declared in
`tests/test_grammar_constructs.py`: lizard counts a `when`'s arms minus
one, treating `else` as an arm. That is right for an exhaustive `when`
and one short for a statement `when` without one, where falling through
to the next line is a path that exists and is not counted.

## Analyzer coverage

Kotlin has it. `lizard` reads it for complexity and `jscpd` for
duplication, both in the shipped pool, so a Kotlin repository gets
analyzer-primary evidence rather than depending on the built-in scanner
alone.

## Not yet anchored

Kotlin is **parsed but absent from the reference corpus**, so every skin
discloses that its grade is provisional — the same caveat COBOL carries,
for a different reason and with a different expected end. The scanner
shipped ahead of the corpus in 3.8.0; Kotlin anchors at the next
recalibration on the corpus policy's own terms, where COBOL is excluded
permanently.

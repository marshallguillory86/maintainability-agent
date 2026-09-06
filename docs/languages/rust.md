# Rust

**A method belongs to the type its `impl` block names.** Rust splits data
from behaviour — `struct Store` holds the fields, `impl Store` holds the
methods, often far apart and sometimes in another file — so `get` alone
is not an instruction in a tree with eleven of them. A method inside
`impl Store` reports as `Store::get`, and `impl Display for Widget`
reports its members under `Widget`, because the type is what a reader
searches for and the trait is how it behaves.

That is the same problem Swift's extensions posed and it is solved the
same way, with a pass over the block spans. Go needed none of it: a Go
receiver is written on the method itself.

**An `impl` block is not graded**, exactly as a Swift `extension` is not.
It is a container, and measuring it as well as its methods counts the
same lines twice. A `trait` *is* graded — it is a declaration in its own
right — and it also qualifies its default implementations, so
`Reader::describe` rather than `describe`.

**A bodyless `fn` mints nothing.** A trait requirement is a signature
with nothing to maintain, as a C prototype and a Swift protocol
requirement are.

**Attributes are stripped, not matched.** `#[derive(Clone)]` is a name
followed by a parenthesised list — the shape of a signature — and Java's
annotations forced the same treatment.

**What it misses**, all under-reporting rather than over:

- Closures (`|x| { … }`) live inside a body and are stepped over, so a
  long one is invisible. Rust uses them heavily for iterators and error
  handling.
- Declarations produced by a macro are not in the source and are not
  seen, as in C, C++ and Swift. A `macro_rules!` body is stepped over as
  a unit rather than read.
- Raw strings (`r#"…"#`) are not masked, so a brace inside one can
  desync depth; the indentation fallback bounds that to one declaration.
- Conditional compilation is not evaluated, so a declaration behind a
  disabled `#[cfg]` still counts.

**Measured with Rust's own keywords.** Branches are counted on `match`
*arms* rather than on the `match` keyword — counting both would score the
construct and its first arm, which is the `select case` lesson Fortran
taught. And `?` is not a ternary: it propagates an error and decides
nothing, while idiomatic Rust is full of it. Counting it would make
ordinary error handling read as branching.


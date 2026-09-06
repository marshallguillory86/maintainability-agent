# Go

**Recognition is easier than in the C family, not harder.** Every Go
declaration is keyword-led — `func` or `type` — so a bare `name(` is
always a call and never a definition. That is the ambiguity that makes
C++ expensive, and Go does not have it.

**A method carries its receiver type.** `func (s *Store) Get(...)` is
reported as `Store.Get`. `Get` alone is not an instruction in a tree with
eleven of them, which is the same judgment Swift's extension members
forced; the difference is that Go writes the qualification into the
signature already, so it is kept rather than reconstructed. A generic
receiver (`func (s *Store[T]) Get`) reports through its base name,
`Store`, because that is the name a reader searches for.

**Containers are walked into, not graded.** `type Store struct` and
`type Reader interface` hold members, and measuring the container as well
as its members counts the same lines twice.

**An interface method mints nothing.** It has no body — nothing to
maintain and nothing to measure — so it is skipped exactly as a C
prototype and a Swift protocol requirement are. Counting them would put a
pile of one-line members into the denominator of every declaration rate.

**Generic type parameters are stepped over.** A generic function writes
`func Map[T any, U any]` and *then* its parameter list; a scanner reading
the bracket list as the signature would report a function taking one
argument named `T` and lose the real list entirely.

**What it misses**, all under-reporting rather than over:

- A function literal assigned inside a body — `f := func() {…}` — lives
  inside a stepped-over body and is never counted. Go uses these for
  callbacks and goroutine bodies, so a long one is invisible here.
- Raw string literals (backticks) are not masked, so a brace inside one
  can desync depth. The indentation fallback bounds that to a single
  declaration.
- `type ID string` and other plain type definitions are not declarations.
  They hold nothing and have no body.

**Measured with Go's own keywords, not C's.** Go has no `while` (`for`
covers looping), no ternary, and no `catch` — `if err != nil` carries
what other languages put in a catch block and is already counted as an
`if`. What the C-family pattern misses is `select`: a dispatch loop built
from `select` and its cases scored only the cases, so the construct
choosing between them decided nothing. That is the Fortran defect in
miniature.


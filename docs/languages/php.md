# PHP

**A `.php` file is a template that happens to contain code.** It is HTML
until `<?php` says otherwise and HTML again after `?>`, and the text in
between is not source. That text is full of braces — a CSS rule, an
inline script, a snippet in a paragraph — and a brace counted from markup
moves depth. A desynced depth does not mis-bound the declaration it
appeared in; it mis-bounds every declaration after it.

So everything outside the tags is blanked before anything reads a line,
in the same way Swift's multiline literals are. It is the first thing
that happens rather than a refinement. A file that never opens a PHP tag
declares nothing, which is correct.

**A method carries its class.** `get` alone is not an instruction in a
tree with eleven of them, so a method inside `class Store` reports as
`Store::get`. PHP writes the class on the container rather than the
member, so the qualification is carried down by a span pass, exactly as
Rust's `impl` and Swift's `extension` are.

**Bodyless members mint nothing.** An interface method and an `abstract`
method are signatures with nothing to maintain, as a C prototype and a
Swift protocol requirement are.

## What it misses

All under-reporting rather than over:

- A closure or arrow function assigned inside a body is stepped over with
  that body, as Rust's closures and Go's function literals are.
- Text outside `<?php … ?>` is not read at all, so a declaration written
  into markup — which would never execute — is correctly absent.
- Heredoc and nowdoc bodies (`<<<EOT`) are not masked, so a brace inside
  one can desync depth; the indentation fallback bounds that to a single
  declaration.
- A method created by `__call`, or resolved by a trait's `insteadof`,
  does not exist in the source and is not seen.

## Measured with PHP's own keywords

`elseif` is one word with no boundary inside it, so the C-family pattern
matched neither `if` nor `elif` and scored a dispatch chain **zero** —
the ordinary way PHP writes a multi-way branch, reading as branchless.
That is Fortran's defect in a language nobody expected it in. `foreach`
is the primary loop, and `and`/`or`/`xor` are word operators alongside
`&&` and `||`.

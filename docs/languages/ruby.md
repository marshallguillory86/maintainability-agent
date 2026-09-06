# Ruby

The second language here with no braces, and the harder of the two.
Fortran's closer names what it closes — a `subroutine` ends at `end
subroutine` — so its end-finder looks for a word. Ruby's one bare `end`
closes a method, a class, a module, a block, an `if`, a `while`, a `case`
and a `begin`, so telling them apart means counting openers.

**That counting is the whole scanner.** A method containing one
`items.each do |item| … end` ends at its *own* `end`, not the block's,
and a naive `def`/`end` pairing reports half the method. The lengths and
complexities drawn from that are not approximately wrong — they describe
a different span of code.

Three things make the count wrong if they are not handled first:

- **Modifier forms open nothing.** `return 0 if value.nil?` has an `if`
  that never needs an `end`. Counted as an opener it eats the enclosing
  method and everything after it, so a keyword opens only when it
  *leads* the statement.
- **`=begin`/`=end` blocks are comments**, and `=end` is not an `end`.
- **Heredoc bodies are not code.** `<<~SQL` … `SQL` may contain the word
  `end` in a query or in prose.

All three are blanked or discounted before a single keyword is counted,
because a miscount does not corrupt one declaration — it shifts every
range after it.

**A method carries its class in Ruby's own notation**: `Store#get` for an
instance method, `Store.build` for one defined with `def self.`.

## Two defects found by adversarial cases, not by the contract

Both were the dangerous kind, and both are now pinned by tests:

- **An endless method swallowed its neighbour.** `def square(x) = x * x`
  (Ruby 3.0) has no body and no `end`, but it matched the `def` opener,
  so depth never returned to zero on its own line and the declaration
  consumed the following method whole — which then disappeared from the
  report entirely.
- **A nested class named the wrong owner.** The span pass stepped over
  each container's body and never saw a class inside a class, so
  `Inner#deep` was reported as `Outer#deep`. Naming the wrong class is
  worse than naming none: it sends a reader to a method that is not
  there.

## What it misses

All under-reporting rather than over:

- **Metaprogrammed declarations are not in the source and are not seen.**
  `define_method`, `attr_accessor` and anything built by `class_eval`
  produce methods no scanner can read, exactly as C and Swift macros do.
  Ruby leans on these more than most languages, so this is the largest
  gap here and it is stated first.
- A `{ … }` block is closed by `}` rather than `end` and is not counted
  as an opener. Idiomatic Ruby uses `do … end` for multi-line blocks,
  which is counted.
- A singleton class body (`class << self`) reads as a container named
  `self`, so its methods qualify oddly.
- Operator method names beyond the ordinary forms (`<=>`, `[]=`) are not
  matched and are not reported.

## Measured with Ruby's own keywords

`unless` is the idiomatic guard clause and `until` the negated loop;
neither is in the C-family pattern, and `elsif` has one `e` so `elif`
misses it too. Measured with C's keywords a guard-heavy Ruby method reads
as branchless. `and` and `or` are word operators alongside `&&` and `||`.

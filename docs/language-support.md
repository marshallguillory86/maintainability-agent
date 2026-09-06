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
| Swift (`.swift`) | dedicated scanner: functions, initialisers, subscripts and types (`class`, `struct`, `enum`, `protocol`, `actor`), bounded by their own braces | Bounded. Extension members carry the type they extend; protocol requirements and computed properties are not declarations — see below. |
| Go (`.go`) | dedicated scanner: functions, methods and container types (`struct`, `interface`), bounded by their own braces | Bounded. Methods carry their receiver type; interface methods are requirements rather than declarations; function literals inside a body are not seen — see below. |
| Rust (`.rs`) | dedicated scanner: functions, `impl` and `trait` members, and types (`struct`, `enum`, `trait`, `union`), bounded by their own braces | Bounded. Methods carry the type their `impl` block names; trait requirements without a body mint nothing; closures and macro bodies are not read — see below. |
| PHP (`.php`, `.phtml`) | dedicated scanner: functions, methods and types (`class`, `interface`, `trait`, `enum`), with everything outside `<?php … ?>` blanked first | Bounded. Methods carry their class; interface and abstract methods mint nothing; closures and heredoc bodies are not read — see below. |
| Ruby (`.rb`, `.rake`, `.gemspec`) | dedicated scanner: methods, classes and modules bounded by their own `end`, counted by openers because one `end` closes everything | Bounded by depth. Methods carry their class (`Store#get`); blocks, modifier forms, heredocs and `=begin` blocks are discounted first; metaprogrammed methods are not seen — see below. |
| COBOL (`.cbl`, `.cob`, `.cpy`, `.CBL`, `.COB`, `.CPY`) | dedicated scanner: PROCEDURE DIVISION paragraphs, bounded by the start of whatever follows them. Fixed-form card columns are read where the layout carries them | Bounded by the next header. Programs and sections are containers and are not graded; level numbers are not declarations; a section whose statements sit outside any paragraph mints nothing — see below. |
| Fortran, free-form (`.f90`, `.f95`, `.f03`, `.f08`, `.F90`, `.F95`, `.F03`, `.F08`, `.pf`) | dedicated scanner: modules, submodules, programs, subroutines, functions and derived types, bounded by their own `end` | Bounded by keyword rather than braces. |
| Fortran, fixed-form (`.f`, `.for`, `.ftn`, `.F`, `.FOR`, `.FTN`) | the same scanner, over source laid out for punched cards: label in columns 1-5, continuation in 6, statement in 7-72 | Bounded by keyword. Continuations are joined before reading — see below. |
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

**Per-language accuracy — what each scanner sees and what it misses** is
one page per language, so adding a language adds a file rather than
growing this one: [Java](languages/java.md), [C](languages/c.md), [C++](languages/cpp.md), [C#](languages/csharp.md), [Fortran](languages/fortran.md), [Rust](languages/rust.md), [Go](languages/go.md), [PHP](languages/php.md), [Ruby](languages/ruby.md), [Swift](languages/swift.md), [COBOL](languages/cobol.md).

## What counts as a decision, per language

Each language's branch set is derived from **its own grammar**, and every
one of them is checked construct-by-construct against an independent
implementation — see [How this is verified](#how-this-is-verified) below.
That check is not decoration: it found nine defects in 2.11.0, including
this project measuring Python against its own comments.

The distinction from the C-family pattern is not pedantry either. PHP's
`elseif` chains scored zero, because the C pattern looks for `elif` and
`elseif` has no word boundary inside it. Ruby's `unless` guards scored
zero. Fortran's `do` loops scored 1.

**One rule is shared and is stated here once.** A multi-way construct is
counted at its **arms, not its header**, and a *default* arm is not
counted at all. `switch`, `select`, `match` and `case` headers score
nothing; their `case`, `when` and `=>` arms score one each; `default:`,
`_ =>` and `case _` score nothing, because a branch that always matches
adds a path without a decision to reach it.

Counting a header *and* its arms scores the construct and its first arm
together, which is the mistake Fortran's `select case` made before 1.6.0.
It was made again in 2.11.0 for Go's `select`, PHP's `do … while` and
Swift's `repeat … while`, and the wildcard half of the rule was missed
for Rust and Python — five languages, one rule, written down and then not
applied.

| Language | Counted | Deliberately not counted |
|---|---|---|
| Python | `if`, `elif`, `for`, `while`, `except`, `case`, `and`, `or` | `match` (its cases carry it); `case _`, the wildcard, which is Python's `default` |
| Go | `if`, `for`, `case`, `&&`, `\|\|` | `switch` and `select` headers (their cases carry them); `goto`, which transfers control without deciding; no `while`, ternary or `catch` exists |
| Rust | `if`, `for`, `while`, `?`, `=>` arms, `&&`, `\|\|` | `match` (its arms carry it); `loop`, which has no condition; the wildcard `_ =>` |
| PHP | `elseif`, `if`, `for`, `foreach`, `while`, `match`, `case`, `catch`, `and`, `or`, `xor`, `&&`, `\|\|`, `??`, ternary `?` | `switch` (its cases carry it); `do`, whose `while` carries the loop; `goto`; `?int`, a nullable type hint |
| Ruby | `if`, `elsif`, `unless`, `while`, `until`, `for`, `when`, `rescue`, `and`, `or`, `&&`, `\|\|`, ternary `?` | `case` (its `when`s carry it); `&.`, which is navigation rather than a decision |
| Swift | `if`, `for`, `while`, `case`, `catch`, `guard`, `&&`, `\|\|`, `??`, ternary `?` | `switch` (its cases carry it); `repeat`, whose `while` carries the loop; `Int?`, an optional type |
| C, C++, C#, Java, JS, TS, HTML | `if`, `else if`, `for`, `while`, `case`, `catch`, `&&`, `\|\|`, `??`, ternary `?` | `switch` (its cases carry it); `default`; a `?` in type position — `int?`, `List<?>`, `v?:` |

### Where this deliberately under-reports

Both of these under-report, which is the direction this project errs in
when it has to choose, and both are consequences of counting keywords on
a line rather than building a control-flow graph.

- **A many-armed PHP `match` scores 1.** The arms rule is not applied
  here, and this is the one place it is not: PHP spells array keys with
  `=>` as well (`['a' => 1]`), so counting arms would count every array
  literal in the file. The `match` keyword is counted once instead, which
  under-counts a wide dispatch. `lizard` reads it the same way.
- **A ternary split across lines is not counted.** Both halves have to be
  visible on one line, because that is what distinguishes `?` the
  conditional operator from `?` the nullable-type marker — the defect
  (D115) that made every `int?`, `List<?>` and `title?:` in five
  languages read as a branch.

### How this is verified

Until 2.11.0 every branch set here was **asserted rather than tested**: a
list written from somebody's knowledge of a language, checked against
examples written by the same person from the same knowledge. That reads
as evidence because the prose around it is confident, which is worse than
reading as a guess. Measured against an independent implementation on
this project's own source, it agreed on **45%** of declarations.

Now `tests/fixtures/grammar/` holds one fixture per language exercising
a set of control-flow constructs from that language's specification, and
CI compares each construct against
[`lizard`](https://github.com/terryyin/lizard) — a separate codebase, by
separate authors, with its own reading of each grammar. **Thirteen
languages** are covered.

**A set, not the specification.** This page said "the constructs that
language's specification defines" and that was not true: the fixtures
exercise the constructs their author already knew about, written from the
same knowledge as the scanners they check. An audit found four defects
whose constructs were all absent from them — a generic Go receiver, an
assigned Ruby `if`, PHP's Elvis operator, Rust's `let … else` (D125–D129).
The set grows whenever a gap is found, and the comparison says nothing
about the constructs it does not contain.

**Agreement has a ceiling as well as a floor.** lizard finds no method on
a generic Go type either, so that defect was invisible to a check built on
two implementations agreeing — the same limit already noted for PHP's
`match`, met by a real defect rather than a hypothetical one.

Coverage is counted in *branch readers* rather than fixtures, because the
reader is the thing that can be wrong: counting fixtures is what let
Python go unchecked while twelve other languages were added (D120). A
reader with no second implementation available has to be named with the
reason, and **COBOL is the only one**.

A disagreement does not say who is right — two implementations can share
a misconception, and PHP's `match` above is one they share. What it does
is make the question unavoidable and send a reader to the grammar, which
is the only authority either tool answers to. Divergences are therefore
**declared with the reasoning that settles them**, and a further test
fails when a declared divergence stops being real. `lizard`'s own
TypeScript reader carries D115, so a harness built to chase agreement
would have re-introduced the bug to match the oracle.

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

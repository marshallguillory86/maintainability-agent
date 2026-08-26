# Language Support and Detection Accuracy

What the scanner can see per language, how it decides where a declaration
ends, and — deliberately — where it under-reports.

## How each language is measured

| Language | Declaration ranges | Accuracy |
|---|---|---|
| Python (`.py`) | `ast` — exact `end_lineno` | Exact. Falls back to the pattern scan only if the file has a syntax error. |
| Java (`.java`) | dedicated scanner: methods, constructors and types, bounded by their own braces | Bounded. Under-reports — see below. |
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

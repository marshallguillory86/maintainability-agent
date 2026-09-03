# Changelog

All notable changes to Maintainability Agent will be documented here.

## Unreleased

_Nothing yet._

## 1.10.0 - 2026-09-03

**[ADR 013](docs/adr-013-hostile-audit-prompt.md) ships.** The adversarial
audit now has an artifact.

### Added

- **`render_hostile_audit_prompt` — a third emitter on the prompt seam**,
  beside `render_ai_prompt` and `render_agent_instructions`. Surfaced as
  CLI `--hostile-prompt-output` and the MCP prompt
  `maintainability-hostile-audit`.

  The hostile audit is the highest-leverage quality process this project
  has and was the only one with no artifact: it depended on a person
  hand-writing a fresh prompt into a fresh session, re-deriving context
  the report already held, with audit quality riding on whoever wrote the
  prompt that day. Not seeded, not repeatable, not comparable run to run.

  The brief is emitted deterministically from one run and carries the
  commit under audit (and whether the tree was dirty), the evidence
  already computed — what ran, what did not, which concepts nothing
  measured, which have a single source — the eight published promises each
  with the shape of evidence that falsifies it, and the audit contract:
  reproduce rather than speculate, verify against the named commit, and
  turn every accepted finding into a test that fails without its fix.

  The boundary is the one ADR 008 drew: **the deterministic core seeds the
  hostile audit; it never performs it.** An LLM red-team inside the audit
  would break P1 outright, so the reasoning happens outside exactly as the
  fixing does. It returns text — no gate, no score, nothing written,
  nothing sent — and its findings return to the falsifier-and-fix loop,
  never to the estimate, range or grade.

- **The promise table lives in code** so the brief renders offline without
  `docs/` installed beside the package, and
  `test_every_published_promise_reaches_the_adversary` holds it to
  `docs/product-intent.md` in both directions. A promise handed over in a
  stale wording is worse than one not handed over at all: it aims the
  audit at a claim the project no longer makes.

### Fixed

- **Two defects in the emitter, caught on its first render.** The
  analyzer outcomes were pasted in as stringified nested dicts — several
  thousand characters on one line, including every language jscpd claims —
  and `evidence_status` printed as `{'status': 'complete', ...}` rather
  than `complete`. A brief that buries its own content is worse than the
  hand-written prompt it replaces, so `test_no_stringified_structure_reaches_the_brief`
  now fails on any dict or list-of-dicts in the output and on any line
  long enough to be a dumped structure.

## 1.9.0 - 2026-09-02

**ADR 001 is finished.** Stage 9 was the last unmigrated stage and the one
with a shipped false result behind it.

### Added

- **History is pinned, and a drifted cache is refused.**
  `tools/calibration/history_manifest.py` materializes once — touching the
  network — and writes down exactly what it fetched: pinned head, the
  selection rule, the selected commit ids, the parent objects those
  commits require, and the tool version. `measure_fix_breadth` now reads
  that manifest and **never touches the network**; a cache that has
  drifted from the pin is refused with the difference named, rather than
  measured as if it were pinned.

  The coupling this replaces produced a real false number and took six
  audits to find. The oldest commit a shallow clone holds has no parent
  locally, so git diffs it against the empty tree and `--numstat` reports
  the whole tree as added: one fix commit measured (1 file, 75 lines) in a
  full clone and (2 files, 39 lines) at the shallow boundary. Each audit
  repaired the symptom it found because there was nothing to check a cache
  *against*. Now there is, and
  `tests/test_history_manifest.py` reproduces the boundary with real git
  repositories cloned shallow over `file://` rather than mocking it.

- **The checked-in manifest**, `tools/calibration/history_manifest.json`:
  33 subjects, 6,120 pinned commit ids, 293 required parent objects, and
  14 subjects whose cache sits on a graft boundary. It also records
  something the study could not previously see — **five of the original 38
  subjects no longer exist**, deleted or made private since selection,
  which is an argument for pinning rather than against it.

### Fixed

- **Documents that called shipped work open.** `release-plan.md` said 1.0
  "still waits on Marshall's acceptance (8.8), the 7.5 hostile audit
  (8.9), and the human tag (8.10)" — all three done on 2026-09-01, nine
  releases earlier — and separately that "8.8–8.10 remain open below".
  `adr-011` said an ask "remains open under D3" when D3's register
  heading reads Closed. Phase 7.2's exit condition is that no document
  calls shipped work open or deferred; these were the fourth, fifth and
  sixth instances in the paperwork of the project that exists to catch
  drift.

## 1.8.3 - 2026-09-02

The falsifier gate could not see a test added to a file that already
existed, 1.8.2 walked through that hole, and closing it immediately
caught 1.8.2's own guard.

### Fixed

- **The gate reaches tests added to existing files.** `_added_test_files`
  is added-files-only for a stated reason: a modified file may defend a
  fix older than the base, so proving its tests would be a false
  accusation. That covers the tests already in the file — not one the
  diff *adds* to it, which is exactly as new as one arriving in a new
  file. 1.8.2 added its guard to an existing
  `tests/test_readme_claims.py`; CI printed a pass for this gate having
  proven nothing about it, and the guard was mutation-tested by hand
  instead, which is the manual step the gate exists to replace. Selection
  is now per-test and read from the diff, so a function that merely moved
  does not read as new, with the same stated-not-assumed
  `Covers existing behaviour:` escape read from the function's own source.
- **1.8.2's README guard did not falsify, and the repaired gate said so.**
  It asserted the language sentence was internally consistent — the "as
  of" version no older than the newest version it named. At the base
  commit that sentence was self-consistent (1.5.0 ≥ 1.4) and merely
  *incomplete*: it named free-form Fortran and stopped, while the table
  below already carried fixed-form Fortran and HTML. The hand mutation
  that appeared to prove it had spliced together a state that never
  existed in history. The defect was an omission, and only a count sees an
  omission, so the guard now holds the sentence's count against the
  languages its own table lists — which is what would have caught the
  1.8.1 README, saying seven while its table listed eight.

### Changed

- **Swift is the next language, not Go.** 1.8.2's roadmap named Go
  (1.9.0) and Rust (1.10.0), read out of [ADR 006](docs/decisions.md)'s
  "Go and Rust remain unwritten on exactly those terms". That entry
  records what was decided, not what comes next, and reading a register
  entry as a plan was the error. Swift takes 1.9.0, with the four shapes
  that make it not quite C-family stated: an `extension` adds methods to
  a type declared elsewhere, a `protocol` declares bodiless requirements,
  computed properties have braces and are the C# properties problem
  again, and string interpolation puts braces inside literals. Go and
  Rust stay named and unscheduled.

## 1.8.2 - 2026-09-02

The roadmap never mentioned the language work — not the five scanners
shipped between 1.1.0 and 1.6.0, and not the ones still to come. The help
docs never mentioned languages at all. Both are the front door for
somebody deciding whether this tool reads their code.

### Added

- **The roadmap states the language plan.** Shipped now records the nine
  declaration languages with the release each arrived in, the shared
  `_ranges_core` walk, and Fortran's three follow-on increments. A new
  **Language adapters** section carries the planned work: Go (1.9.0) and
  Rust (1.10.0), which are the two [ADR 006](docs/decisions.md) names
  "unwritten on exactly those terms", with the hard part of each stated —
  Go's receivers and method sets, Rust's `impl` blocks, bodiless trait
  signatures and macro-generated declarations. It also records what Go
  and Rust already get without a scanner (discovery, practice signals,
  multimetric for Go) and what they do not: a declaration population.
- **Two gaps that widen with every language added**, named on the roadmap
  rather than discovered again later: test-command detection stops at
  `pytest -q`, so `fpm test`, `ctest`, `go test` and `cargo test` leave
  `expected_commands.test` hand-configured; and the calibration corpus is
  40 JS/TS/Python repositories, which every added language inherits.
- **The help docs explain withheld declaration rates.** A repository in an
  unparsed language shows few declaration findings and may have its grade
  withheld; that is the disclosure working, not the scan failing, and
  nothing said so. Adding a suffix to `include_extensions` widens what is
  scanned, not what can be parsed. The analyzer help now also states that
  language decides tool eligibility, and that fortitude emits verdicts
  rather than a population.

### Fixed

- **The README contradicted itself for two releases.** It read "Seven
  languages are parsed as of **1.5.0**" while listing fixed-form Fortran,
  which shipped in 1.6.0. The existing guard pins the language *table*,
  and the table was right the whole time, so nothing caught the sentence
  above it. Now eight languages as of 1.6.0, and
  `test_the_readme_language_sentence_is_not_older_than_what_it_lists`
  holds the sentence to its own contents: the "as of" version must be at
  least the newest per-language version the sentence names. Restoring the
  old wording fails it.

## 1.8.1 - 2026-09-02

1.8.0 fixed the falsifier gate and could not prove it. Running that down
found a second defect underneath the first, and both are now guarded by
tests that fail without them.

### Fixed

- **A child that never ran counted as a proof.** `_prove` read every
  non-zero exit as "the test failed at the base", which it treats as
  proof — so an interpreter that could not start pytest at all reported
  that every falsifier falsified. This is not hypothetical: it is what
  hid the 1.8.0 fix from its own guard. The mutation that should have
  failed that guard passed instead, because the child was exiting 1 with
  `No module named pytest` and the tool was reading that as evidence.

  The line is now drawn at **output, not exit code**, because a
  collection error is a real signal here: a new test file naming a module
  the base does not have cannot be collected, and this tool already
  counts that as the weaker proof it is. Only a child that printed
  nothing at all never ran.
- **The 1.8.0 fix broke pytest for the child on some interpreters.**
  Replacing `PYTHONPATH` with the worktree's `src` alone left the child
  unable to import pytest itself wherever pytest lives outside the
  default path. The worktree now goes **first** and the parent's path
  follows.

### Added

- **Two guards, each mutation-verified.** Reverting the shadowing fix
  fails `test_the_reverted_tree_is_the_tree_the_tests_import`; reverting
  the never-ran rule fails `test_a_child_that_never_ran_is_not_a_proof`.
  Both were written, watched to fail, and corrected twice before they
  discriminated — the first draft passed in 0.14s against a scratch
  repository whose every commit had been refused by a machine-level hook,
  and the second put its decoy where the code does not read from. A guard
  nobody has watched fail is not a guard, and neither of these was until
  it was.

End to end against v1.5.1, the gate now reports **19 of 20** added tests
failing without their change, where before the 1.8.0 fix it reported 0 of
19.

## 1.8.0 - 2026-09-02

A retrospective audit of everything from v0.9.1 through v1.7.0 — 104
commits, benched against product intent, the architecture and the
decision register — and the five findings it produced, fixed.

### Fixed

- **The falsifier gate proved nothing about code.** `prove_falsifiers.py`
  reverts the tree to the base and runs the new tests against it, and the
  reverted tree was never the tree the tests *imported*: `pip install -e .`
  puts the checkout's own `src` on the path, so every run imported the
  package at HEAD. Reverting the files changed what a test could **read**
  and nothing about what it could **call** — which is why document
  falsifiers proved correctly for months while every behaviour falsifier
  passed vacuously. `PYTHONPATH` now names the worktree's own source.
  Measured on the Fortran work: **0 of 19 tests failed at base before the
  fix, 18 of 19 after.**
- **The gate also could not see how work now arrives.** It triggered only
  on register entries citing closing tests, or added `tests/*_class.py`
  files. The language increments used neither, so roughly 300 tests
  merged unproven. It now revert-proves every added test file, with an
  explicit `Covers existing behaviour:` marker for the legitimate case of
  a test that documents behaviour which already worked — stated, not
  assumed.
- **The decision register contradicted the product.** ADR 006 still read
  *"we will not write more range detectors"* after five were written; two
  further passages named v1.0's six languages as current and listed C, C#
  and Fortran as absent from the default extensions. Amended in place with
  what overturned each, rather than rewritten — the register's value is
  that it records both.
- **Stale known debt.** Declaration extraction was described as gated on
  "Python, JS/TS/HTML, and Java", and the scanner note said "both suffix
  sets" where there are now six.

### Changed

- **A report now names the corpus its anchor is drawn from.**
  `score.reference` gains `corpus_languages` and `corpus_note`, and the
  bounded prompt says "the median of a mature open-source corpus of
  Python, TypeScript and JavaScript". The rubric is uniform across
  repositories, which is the promise; the **corpus is not uniform across
  languages**, which is a limit that was true and unstated. Java, C, C++,
  C# and Fortran are scored against medians measured on none of their
  code: audited against that anchor LAPACK reports declarations at 7.18x
  and fortran-lang/stdlib at 1.10x, and the first number is a true
  statement about LAPACK against mature OSS web code rather than a
  statement about typical Fortran.

  Disclosed rather than corrected. Per-language references would remove
  the awkwardness by trading a stated limit for a silent breach of P2,
  and extending the corpus moves `CALIBRATION_C` and re-grades every
  repository — a deliberate release, not a patch. `docs/standard.md`
  carries the reasoning under "What the anchor does not cover".
- **Fixed-form Fortran tests state their strength**, measured by mutation
  rather than claimed: swapping the card-column masker fails 1 of 9,
  removing labelled-`DO` tracking fails 3 of 9, and the rest are
  defensive regressions. A second test was added as a load-bearing case,
  measured, found not to discriminate, and is documented as defensive —
  the claim was removed rather than the test.

**What the audit found holding:** layering and acyclicity intact across
104 commits under 13 property tests; jscpd reporting 0 duplicate blocks
across six sibling scanner modules; the setup question set unchanged
through seven releases; and the tool ending its own audit at zero
failures of every kind, having split four pieces of code that tripped its
gates rather than shaving them to fit.

## 1.7.0 - 2026-09-02

**Practice detection speaks the Fortran toolchain.** Every list in
`_practice` — linter configs, formatter configs, the lint command
pattern, the gate manifests — was written from the Python, JS, JVM and
Go ecosystems. Fortran appeared in none of them.

### Fixed

- **A Fortran project that lints on every change scored as though it did
  not.** Measured on a tree carrying `fortitude.toml`, `.fprettify.rc`
  and a CI job running both: **level 2, zero signals** — the tool saw
  nothing. `fortitude` joins the lint commands, `fortitude.toml` and
  `.fortitude.toml` the linter configs, `.fprettify.rc` and
  `fprettify.ini` the formatter configs. That tree is now level 3.
- **`fpm.toml` is read as a gate manifest.** A Fortran project declares
  its build, its tests and — since fortitude 0.9 — its lint settings
  there, so a coverage or complexity gate written in it was invisible
  for exactly the reason one in `pyproject.toml` would have been.

**It does not lift every Fortran repository, and that is the point.**
`fortran-lang/stdlib` has CI, an `.editorconfig` and no linter at all;
it was level 2 before this change and is level 2 after. A detector that
promoted every Fortran tree would be measuring the language rather than
the practice, so that case is pinned as a test beside the fix.

## 1.6.0 - 2026-09-02

**Fortran is measured with Fortran's reading.** 1.4.0 found Fortran
declarations correctly and then handed them to a C-family measurement,
which produced numbers that were not approximate but wrong. This release
fixes the measurement, gives Fortran the analyzer tier it was locked out
of, and claims fixed-form.

### Fixed

- **`do` — Fortran's primary loop — was not counted at all.** The
  branch pattern was the C family's, so **six nested loops scored
  complexity 1**. `.and.`/`.or.` are not `&&`/`||`, so five operators
  scored 3. `end if` contains the word `if`, so every branch counted
  twice. Scientific Fortran is mostly nested loops, so a numerical
  kernel read as trivial — and the ranking that decides which routines a
  maintainer is told to fix was drawn from those numbers.
- **Nesting was invisible.** Cognitive complexity was read from brace
  depth, and Fortran has no braces, so **four flat `if`s and four deeply
  nested ones both scored 8** — the metric that exists to measure
  nesting reporting none of it. It now counts nesting from the
  constructs themselves.
- **Comments were read as code.** The masker is the C family's, where
  `!` is negation; in Fortran it starts a comment. `! loop while the
  residual is large` was three branch points. Fortran now has its own
  masker.
- **lizard never ran on Fortran.** It reads Fortran and measures a
  nested-loop kernel at CCN 5. This project's catalog row for it omitted
  `fortran`, and selection is gated on that row, so lizard came out
  `not-applicable` on every Fortran repository — leaving the language
  with no complexity reading from any analyzer, while the tool that
  could supply one sat installed in the pool. Corrected through a new
  `VERIFIED_EXTRA_LANGUAGES` map, for corrections proven by *running*
  the tool rather than by trusting an upstream inventory.
- **`TODO`/`FIXME` were invisible outside the web stack.** The one risk
  pattern that ships by default listed `.py`, `.js` and friends only, so
  Java, C, C++, C# and Fortran could carry debt markers nothing looked
  at — silent on exactly the trees where the debt is oldest. All claimed
  languages are covered now.

### Added

- **Fixed-form Fortran** (`.f`, `.for`, `.ftn` and uppercase). Same
  scanner, same `end`-keyword bounding; only how a line becomes a
  statement differs — which is why it is a masker rather than a second
  scanner. Card columns are honoured (label 1-5, continuation 6,
  statement 7-72, sequence numbers ignored), and **continuation lines
  are joined onto the statement they continue**: a condition whose
  `THEN` sits on the next line otherwise reads as a single-line `IF`,
  and the matching `END IF` then closes the enclosing *procedure*,
  ending it early and reading the rest of its body as top-level code.
- **Fortran 77 labelled `DO` loops** (`DO 20 I = 1, N` … `20 CONTINUE`)
  are understood. They do not close with `END DO`, so a reader waiting
  for one never balances — the procedure collapsed to a single line.
  Terminating labels are now tracked.
- **A lint that fails the build if any parsed language has no analyzer
  measuring complexity.** The first version asked whether *some* adapted
  tool claimed the language and passed with the stale row still in
  place, because jscpd lists nearly every language and reads duplication
  only. A language with duplication and no complexity has half the
  rubric unmeasured.

### Verification

Audited **fortran-lang/stdlib** — 640 Fortran files, 488 scanned. Ranges
land exactly: `add_log_unit` is reported at lines 260-404, and the source
has `subroutine add_log_unit` on 260 and `end subroutine add_log_unit` on
404. Complexity agrees with lizard on 4 of 5 procedures in a real file;
the fifth is ours at 16 against lizard's 10, and all 15 decisions are
enumerable in the source — 13 `if`s, two `do`s and one `.or.` — so the
difference is lizard under-counting single-line `if (…) return`.

## 1.5.1 - 2026-09-02

Documentation, and two guards so it cannot drift again.

### Fixed

- **The README named version 1.0.0** — five releases stale, at the top of
  the first thing anyone reads, while four languages were added
  underneath it. `SECURITY.md` is guarded against exactly this (D45) and
  the README was not, so it now is: the version line is checked against
  `config.VERSION`, and the next release either updates it or fails.
- **The README language table is now held to the parser.**
  `docs/language-support.md` was already tied to `DECLARATION_SUFFIXES`
  in both directions; the README carries its own shorter table, which is
  what most people actually read, and nothing tied it to anything. A
  language could ship parsed, be documented in `docs/`, and be missing
  from the front page. The guard caught two rows immediately: the JS/TS
  row named no suffixes at all, and Fortran omitted `.F95`, `.F03` and
  `.F08`.

### Documentation

- **A languages line in the header**, so what the tool reads is visible
  without scrolling to line 238.
- **A correction.** 1.4.0 and 1.5.0 both said lizard does not read
  Fortran. It does — verified against lizard 1.24.0, which measures a
  nested-loop kernel at CCN 5. What is true is that *this project's
  catalog row for lizard* omits `fortran`, so lizard is marked
  `not-applicable` on a Fortran repository and never runs. That is a
  stale data row rather than a missing capability, and 1.6.0 fixes it.
- **Which analyzer covers which language**, as a table. That is the part
  1.5.0 changed and the page never said: Fortran is the one language with
  no metric emitter — lizard does not read it and fortitude reports
  findings rather than measurements — so its declaration population comes
  from the built-in scanner alone.

## 1.5.0 - 2026-09-01

**Fortran gets an analyzer.** 1.4.0 shipped the scanner and noted that
Fortran was the one claimed language with nothing external beside it —
lizard does not read it. Fortitude is the answer: Rust-fast,
`pip install`-able, 100+ rules across correctness, obsolescent features,
modernisation, portability and style.

### Added

- **A fortitude adapter**, registered in the pool at `baseline` depth —
  zero project configuration, fast, runs on whatever Fortran is present.
  Verified the way this project requires before a tool leaves the `all`
  tier: installed (0.9.2), run, and its output parsed. On a 12-module
  synthetic tree it contributes 84 findings, each with a rule code, a
  file and a line.

**It does not claim `types`.** Fortitude's correctness rules are about
declaring things explicitly — `implicit none`, `intent`, kind parameters
— and a reader who saw `types` in a coverage record would take it to
mean the code was type-checked. Nothing type-checks Fortran here. Only
`C191: unreachable-statement` maps off `style`, to `dead-code`, because
unreachable code is exactly that.

It is also a **verdict emitter**: it reports findings and cannot supply a
declaration population. The built-in scanner remains the only path to a
population for Fortran, which `docs/language-support.md` now says
precisely rather than saying Fortran has no analyzer at all.

### Notes

The recorded-output test pins the one way fortitude differs from ruff,
whose JSON is otherwise the same shape: the location key is `line`, not
`row`. Reading ruff's spelling here would have dropped every line number
silently, leaving findings that name a file and no place in it.

## 1.4.0 - 2026-09-01

**Free-form Fortran is a first-class language** — and the first one here
with no braces, which is why this release also generalises the walk that
every other language shares.

### Added

- **A dedicated Fortran scanner (`fortran_declaration_ranges`).**
  Modules, submodules, programs, subroutines, functions and derived
  types, each bounded by its own `end`. `.f90`, `.f95`, `.f03`, `.f08`,
  their preprocessed `.F90` spellings, and pFUnit's `.pf` are parsed and
  opened by default.
- Functions are named correctly with a type prefix
  (`pure elemental real(dp) function norm(v)`) or a `result` clause
  (`real function accel(h) result(a)`). Keywords match
  case-insensitively, because Fortran is and older code SHOUTS.
- **An `interface` block is stepped over, not descended into.** It holds
  signatures with no bodies; walking in would mint a one-line
  declaration for every procedure a module merely *describes*.
- **Fortran test conventions are recognised, in the same release as the
  scanner.** fpm puts tests in `test/`; test-drive writes
  `test_gravity.f90`; pFUnit writes `.pf` and the camelCase
  `testGravity_mod.F90`; module files are conventionally
  `gravity_mod.f90`, so `_mod` comes off both sides when pairing.
  Claiming Fortran without these would have reported untested production
  code on every Fortran repository there is.

**Fixed-form is deliberately not claimed.** `.f`, `.for` and `.ftn` are
column-sensitive — a comment is `C` in column 1, a continuation is any
character in column 6 — which is a different scanner with different
failure modes. Those suffixes stay out until they have one, and their
own falsifiers.

There is no analyzer fallback here: lizard does not read Fortran, so the
built-in scanner is the only path to a declaration population rather
than a zero-install convenience.

### Changed

- **The shared walk now takes its bounding rule as an argument.**
  `scan_bounded` gained `find_end` (braces by default) and `ignore`
  (kinds stepped over without being graded). Fortran supplies an
  `end`-keyword finder that counts program units, because `if`, `do`,
  `select`, `associate` and `block` all close with `end` too — a scanner
  stopping at the first one would end a subroutine at its first `end if`
  and read the rest of its body as top-level code. Every other language
  is untouched, proven by their suites passing unchanged.
- **`.F90` and its siblings are recognised at all.** Suffixes are
  matched case-sensitively throughout and only lowercase Fortran
  spellings were in the extension map, so preprocessed Fortran was
  invisible — not even counted as unread source.

### Fixed

- **Two documentation lints could not read a suffix containing a digit.**
  Both matched `` `\.[A-Za-z]+` ``, so `.f90` and `.F90` were invisible
  to them: the language-table contract reported the page as silent about
  nine suffixes it documents in full, and the "does not market a
  detector that never runs" lint silently skipped the row it exists to
  police — a lint that stops linting without failing.
- **The claimed-languages fixture failed this project's own gate.** It
  had grown one nested conditional per language and reached complexity
  24 at the fifth. It is a table now, and the next language is a row.

14 Fortran falsifiers cover keyword bounding against inner
`if`/`do`/`select` blocks, bare `end`, interface blocks, typed and
`result`-clause functions, derived types versus variables of them, case
insensitivity, comments, `contains`, submodules, continuations, and the
unclosed-unit fallback.

## 1.3.0 - 2026-09-01

**C# is a first-class language, and the C family is complete.** Third of
the three increments — C in 1.1.0, C++ in 1.2.0, C# here. The
architecture held to the end: a language is a module and a row.

### Added

- **A dedicated C# scanner (`csharp_declaration_ranges`).** Methods,
  constructors, destructors, and the types — `class`, `interface`,
  `struct`, `record`, `record struct` and `enum`. `.cs` is parsed and
  opened by default.
- Generic parameter lists are blanked before matching, so
  `public List<T> Sort<T>(List<T> items) where T : IComparable` yields
  `Sort`; attributes are stripped with their arguments, so
  `[Obsolete("x")]` is not read as a method called `Obsolete`.
- Namespaces are handled in both forms: a braced `namespace Geo {` is
  walked into without being graded, and C# 10's file-scoped `namespace
  Geo;` declares nothing and is ignored rather than being allowed to
  swallow the file.

**Properties are deliberately not declarations.** `public int Count {
get; set; }` has braces and would bound cleanly, and an ordinary C# tree
holds thousands of them — each one line long, each nobody's maintenance
burden. Counting them would dilute the population every declaration rate
divides by. They are excluded by construction rather than by a rule: a
property has no parameter list, and every pattern requires one. A method
written `public int Fast() => count_;` **is** counted, because it has
one.

### Changed

- **`_mask_generics` moved to `_ranges_core`.** Java and C# write
  generics the same way, and the second consumer got the shared helper
  rather than a copy — otherwise one of the two grows a fix the other
  never gets. Java's behaviour is unchanged, proven by its suite passing
  untouched.

### Fixed

- **The one test covering the real MCP stdio transport could not run
  outside CI.** It spawns a child process, and the SDK spawns that child
  with a scrubbed environment — `HOME`, `LOGNAME`, `PATH`, `SHELL`,
  `USER` and nothing else — so `PYTHONPATH` did not survive. In a source
  checkout the child died with `ModuleNotFoundError: No module named
  'maintainability_audit'`, the client reported only `Connection
  closed`, and the failure looked environmental rather than like a test
  that could never pass. It now inherits this process's own import path,
  which covers both layouts (`src/` in a checkout, site-packages when
  installed) and the `mcp` SDK the child needs before it can answer at
  all. The full suite now runs locally with nothing deselected.

16 C# falsifiers cover properties, both namespace forms, attributes,
constructor chains and destructors, generics with constraints,
expression-bodied members, interface members, positional records,
control flow inside bodies, and both unclosed-body shapes.

## 1.2.0 - 2026-09-01

**C++ is a first-class language.** Second of the three C-family
increments (C shipped in 1.1.0; C# follows in 1.3.0). The architecture
1.1.0 built held: C++ is a module and a row, with no edit to the
dispatcher and none to the shared core beyond the loop it now provides.

### Added

- **A dedicated C++ scanner (`cpp_declaration_ranges`).** Free
  functions, class and struct members, constructors, destructors,
  operator overloads, and the types themselves — `class`, `struct`,
  `union`, `enum` and `enum class`. `.cpp`, `.hpp`, `.cc`, `.cxx` and
  `.hh` are parsed and opened by default.
- It takes one rule from each neighbour: **types are descended into**,
  as in Java, because a C++ class holds its methods; **bodyless
  declarations are skipped**, as in C, so a prototype, a pure virtual
  (`virtual int area() const = 0;`) and `= default` mint nothing. A
  header of forty declarations is not forty declarations.
- Names are reported as a reader searches for them: an out-of-line
  definition keeps its qualification (`void geo::Widget::draw()` is
  `geo::Widget::draw`), an operator overload is `operator==`, and a
  `template <...>` header is stripped so the declaration under it is
  what gets measured.

`.h` stays **C**. It is the one extension both languages write, and the
C reading under-reports a C++ header where the reverse would read no
more and risk more.

### Changed

- **One walk for every brace-delimited language.** `scan_bounded` moves
  into `_ranges_core` and C, C++ and Java all use it; each language now
  supplies only its patterns. Java and C each had their own copy of that
  loop, and C++ and C# would have made four — which is how a fix lands
  in three of them and the fourth keeps the bug. The two migrated
  scanners are behaviour-identical, proven by their existing suites
  passing unchanged.

### Fixed

- **A macro invocation can no longer swallow the next declaration.**
  `MY_MACRO(x)` on its own line has the shape of an Allman signature — a
  name, a parameter list, end of line — and the first version of the C++
  scanner accepted it, letting the *next* line's braces close it. The
  macro was reported as a function and the real function beneath it
  disappeared: an invented declaration hiding a true one. An
  end-of-line tail is now trusted only when a return type was written or
  the name is qualified. The cost is a constructor braced Allman inside
  its class, which is missed — the direction this design errs in. C was
  checked for the same defect and does not have it; its pattern already
  requires a return type.

17 C++ falsifiers cover namespaces, templates, operator overloads,
out-of-line definitions, initialiser lists, access specifiers, the macro
case, control flow and casts inside bodies, and the indentation fallback.

## 1.1.0 - 2026-09-01

**C is a first-class language.** The first of three C-family increments
(C, then C++ in 1.2.0, then C# in 1.3.0). A C repository now gets
declaration-level findings from a `pip install` with no analyzer
installed, instead of a withheld declaration rate.

### Added

- **A dedicated C scanner (`c_declaration_ranges`).** File-scope
  function definitions and `struct`/`enum`/`union` types, each bounded
  by its own braces. It reuses the Java scanner's brace primitives
  rather than inventing a second bounding rule, so the guarantee that
  covers every other language covers C: **a declaration's range never
  runs past its own body.** Storage-class and inline keywords and
  pointer return types are stripped before matching (`static inline int
  clamp(` is `clamp`; `const char *greeting(` is `greeting`), and the
  brace may sit on the signature line, on its own line, or after a
  signature split over several lines — all three are bounded correctly.
- **`.c` and `.h` are parsed and opened by default.** Both join
  `DECLARATION_SUFFIXES` and the default `include_extensions`; a suffix
  is listed in one only when the other agrees, which
  `test_claimed_languages` enforces in both directions. `.h` is read as
  C for now; the C++ increment disambiguates it.

Two things are deliberately not declarations: a **prototype** has no
body, so a header of 40 prototypes is not 40 declarations, and a
**preprocessor line** is skipped whole, so `#define MAX(a, b) …` is not
read as a function called `MAX`. K&R-style definitions and
macro-generated declarations are missed, each costing one declaration
and never a cascade. The full list is in
[docs/language-support.md](docs/language-support.md).

**The calibration is unchanged, and that was verified rather than
assumed.** Only 3 of the 40 pinned corpus repositories contain any C at
all (27, 16 and 2 files in trees of 4008, 3085 and 878), all three are
analyzer-primary, and re-deriving the constants with C included moves
every reference and `CALIBRATION_C` by less than 0.0001. No repository
is re-graded by this release for a language it does not contain.

### Changed

- **Declaration scanning is one module per language over a shared core.**
  `_ranges.py` held the brace machinery and the JS/TS patterns together,
  and sat at its 500-line budget — so every new language either grew that
  file or reached into it for private names. It is now `_ranges_core`
  (the rule: a range is bounded by its own body), with `_ranges_js`,
  `_ranges_java` and `_ranges_c` owning one language's patterns each. The
  dependency runs one way: a language imports the core, and the core
  never learns a language.
- **The dispatch is a table, not an `if` chain.**
  `declarations.SCANNERS` maps a suffix set to its scanner, so **adding a
  language is a module and a row** — no edit to the dispatcher, the core,
  or any structural test. The Java-only wiring guards were generalised to
  read that table and hold *every* claimed language to the rule, so C++
  and C# inherit them on arrival.
- **The shipped defaults moved to `_config_defaults`.** `config.py` was
  carrying both the default configuration and the loading/validation
  logic, also at 500 lines, and `include_extensions` is a list every new
  language must edit. `config` re-exports `DEFAULT_CONFIG` and
  `DEFAULT_IDIOM_GROUPS`, so every existing import is unchanged.

Together these are the reason 1.1.0 is a structural release and not just
a scanner: C++ and C# are now additive rather than another argument with
a file-length gate.

### Fixed

- **`tools/calibration/measure.py --check` no longer rewrites the
  corpus it checks against.** A check now reports and leaves
  `measurements.json` alone; previously it overwrote the checked-in
  analyzer-primary measurements with whatever that run produced. Run
  without `--with-analyzers` it therefore reported a large false
  `CALIBRATION_C` drift _and_ left the tree holding the corpus that
  appeared to prove it. It also now warns when a built-ins-only run is
  being compared against analyzer-fitted constants.

## 1.0.1 - 2026-09-01

A housekeeping release: no runtime behavior changed (the reconfigure and
TypeScript-semantic fixes shipped in 1.0.0). This ships the release-pipeline
fix and internal headroom, and refreshes the docs.

### Changed

- **The release pipeline is idempotent and cuts the GitHub Release itself.**
  `release.yml` now publishes to PyPI with `skip-existing` (a re-run or
  re-pointed tag no longer hard-fails with `400 File already exists`) and a
  new tag-only job creates or updates the GitHub Release from the CHANGELOG
  section for the tag. A `git push origin vX.Y.Z` runs build → PyPI → GitHub
  Release end to end, every job safe to re-run.
- **`_mcp_setup` split for headroom (#127).** The setup persistence
  (`_apply_bounds`/`_apply_command`/`_persist_answers` and the value helpers)
  moved to `_setup_persist`, and the `SetupRequired` exception to
  `_setup_errors`; `apply_answers` stays in `_mcp_setup` and delegates. Output
  is byte-identical — a pure internal refactor, `_mcp_setup` 500 → 364 lines.

### Documentation

- README gained a **Language support** section — Python is first-class
  (AST-exact), Java and the JS/TS/JSX/TSX family are bounded, TypeScript
  semantics come from a local `tsc`, and every other language is
  under-reported unless an external analyzer (lizard/jscpd/ESLint/PMD/…)
  covers it — and a **Support/Sponsor** section with `.github/FUNDING.yml`.
- The architecture Known-debt note no longer pins a stale `CALIBRATION_C`
  (2.2658 → 5.8843), pointing at `_calibration.py` as the source of truth.

## 1.0.0 - 2026-09-01

**The 1.0 milestone.** Not a rewrite — a line drawn under a long arc of
subtraction. 1.0 is what remained after every claim this project could not
stand behind was removed: the scoring engine that graded repo *size* was
rebuilt into per-dimension rates calibrated against a query-selected corpus
(0.5.0); the headline claim that near-duplication distinguishes AI-written
code was **retracted** when a matched control erased the gap (0.6.0); the
score learned to be **withheld** when the evidence cannot support one, and
external analyzers became the primary evidence with disagreement widening
the range rather than being averaged (0.7.0); the surfaces converged on
**one setup, three transports** with chat as the primary door (0.8–0.9);
and a real-repo acceptance round (Phase 8, on bighound) hardened the last
edges. What ships as 1.0 is the thing the whole project is for: a
deterministic, offline, one-rubric audit whose output is a **bounded work
order** — a copy-paste prompt per finding that tells an agent to fix
exactly these and refactor nothing else.

### 1.0 — the bounded work order, delivered

- **The report is the complete work order; chat/CLI is a bounded UI.** The
  HTML and Markdown reports carry the *entire* backlog with a self-contained
  copy-paste prompt for every item; the chat/CLI surface stays a tight
  summary plus a pointer, so a host's payload cap can never truncate the
  prompt (the tool's whole point). Per-item prompts are deterministic — built
  from finding fields, no LLM, same bytes for the same inputs.
- **HTML report charts rebuilt for legibility.** The pillar legend moved to
  its own band below the plot (it used to overlap the lines), the x-axis is
  dated, and the y-axis shows the full 0–5 gridline ladder. SVG extracted to
  `_charts` — still deterministic, offline, library-free.
- **TypeScript semantic coverage now finds workspace projects and a local
  `tsc`.** A repo whose `tsconfig.json` lives in a workspace (`web/`,
  `packages/*`) and whose compiler is in `node_modules/.bin` no longer reports
  `unknown`. Never installs, never fetches; a missing compiler still reads
  `unknown`, never a fabricated clean run.
- **Reconfigure preserves hand-tuned config.** Re-running setup used to write
  the config from the wizard's answers alone, deleting `paths` scoping,
  `thresholds`, gates, commands, risk patterns and the instruction pack. It
  now merges the answers over the existing config. Falsified.
- **The report header states its provenance** — run date, commit, branch,
  root, and the scoring standard — in both skins. The run date is a disclosed
  determinism exception (P1).
- **The opted-in test suite gets its own timeout** (default 600s) instead of
  dying to the 120s analyzer cap, and the Class 5 opt-in is surfaced on
  repositories configured before it existed.
- **Internal headroom.** `renderers` and `_mcp_setup` were split along real
  seams (`_markdown_sections`, `_setup_persist`/`_setup_errors`) so neither
  rides its own 500-line gate; output is byte-identical.

### Fixed

- **A boundary refusal reaches the caller as a refusal, not as a crash.** The
  MCP SDK distinguishes a failure the server anticipated — whose message
  reaches the caller — from a crash, which is reduced to `Error executing tool
  <name>` (or a resource's bare URI) with the traceback kept server-side. This
  product raised its most anticipated failure, the allowed-roots boundary, as a
  plain `PathNotAllowed`, so it was classified as a crash and its text
  withheld: a user pointing the tool outside its roots was no longer told why,
  nor that `--allow-root` and `MAINTAINABILITY_MCP_ALLOWED_ROOTS` exist. The
  report resource lost `SetupRequired`'s message the same way. Both MCP seams
  now declare their anticipated refusals (`ToolError`, `ResourceError`) while
  the plain functions keep raising the domain types for the CLI and library
  callers. The anticipated set is derived from every named exception in the
  package: each is in the tuple, or excluded with a stated reason, so a sixth
  type added tomorrow fails the build instead of a reviewer. Surfaced when
  `mcp` 2.1.0 stopped interpolating crash text; the dependency range is
  unchanged, because the SDK's behavior is correct and the misclassification
  was ours (D48). Every member of that set which can reach a seam is now
  driven through one — `StaleBaseline` and `InvalidAuditArgument` out of the
  audit tool, `SetupRequired` out of the report resource's own handler, each
  verified by deleting its type from the tuple and watching the test fail.
  What proves "declared" differs by seam, and two drafts of these tests got
  it wrong in opposite directions. The first asserted only that the caller's
  message is not the SDK's generic crash string, which on `mcp` 2.0.0 is true
  of the tool either way — it passed with `StaleBaseline` removed. The tool
  tests now call the registered coroutine directly, so `ToolError` plus the
  chained domain type is our own translation on any 2.x. Applying that same
  reasoning to the resource was the second mistake: there the SDK wraps and
  chains an escaping exception, so a crash also arrives as `ResourceError`
  with the original `__cause__`. That test excludes the 2.1.0 crash wrapper
  `UnexpectedResourceError` and requires the refusal's own text, which is
  what separates the two on 2.0.0. The third mistake was *which* text: it
  looked for `audit_repository`, and the 2.0.0 wrapper interpolates the URI,
  so a repository directory of that name puts the substring into a crash
  message — reproduced, a crash satisfying the assertion meant to catch
  crashes. The fixture now builds under exactly that directory name and the
  discriminator is `has not been set up`, a fragment of the refusal's own
  sentence that a URI cannot carry; the door-naming check stays as D30's
  separate requirement. A falsifier that shares a vocabulary with the thing
  it tests can be satisfied by the failure it exists to catch.
- **Three documentation claims that outran the code.** An audit of the change
  above found each of them. Architecture invariant 12 justified `PolicyError`'s
  place in the anticipated set by saying a missing type stops teaching — but
  `PolicyError` cannot reach any seam, because `_analysis.analyze()` catches it
  and returns `Analysis(error=...)`; it is declared ahead of a path that does
  not exist yet, and the invariant now says so while keeping the claim for
  `StaleBaseline`, which does travel. `docs/cli.md` described `--install-skill`
  as checking its copy against the reviewed
  `skills/maintainability-agent/SKILL.md`; the command reads the packaged
  `_skill_data` payload and consults no repository, and what holds that payload
  to the reviewed file is the suite. And `_audit_tool_for`'s docstring
  explained the function in terms of this repository's own 500-line gate
  rather than what it does.

### Changed

- **The three entries below are renumbered D47–D49; the register jumps from
  D31 to D47.** They were written as D32–D34 on a branch cut from the same
  commit as `fix/round-two-findings`, which had already minted D32–D46, so for
  a day two live branches defined six different defects under three
  identifiers. Nothing conflicts in git — the branches touch different regions
  of the register — so nothing would have failed until a reader tried to work
  out which D34 a changelog line meant. The release gate is "zero open entries
  in the register", which is only countable if an entry number means one
  defect. The gap is reserved, not missing, and closes when that branch lands.
- **The chat surface calls the audit before it inspects configuration, on every
  door it is reached through.** D21 established the rule — call
  `audit_repository` first, never deliberate over a missing or stale
  `maintainability-agent.json` — but its falsifier read only the opt-in skill.
  `SERVER_INSTRUCTIONS` never carried the rule, and the slash prompt taught
  the opposite: "First offer the presentation choice ... Then call
  `audit_repository`". Both MCP surfaces now state the rule in D21's words.
  Found by inspection while diagnosing a field report that this does not
  explain — that host loaded a pre-D21 skill from a wheel older than the fix
  (D47).
- **The skill inside the distribution is checked, not assumed.** Two tests read
  `_skill_data/SKILL.md` from the source checkout, so the payload a host
  actually loads — carried in the built distribution and written out by
  `--install-skill` — was asserted by nothing. The staged build must now carry
  it, byte-identical to the reviewed skill, with D21's call-first rule in it
  and no "configuration check first" anywhere. Same shape as D23, on the
  payload D23 did not cover (D49).

## 0.9.1 - 2026-08-21

### Security

- **A configured history path can no longer escape its repository.**
  `paths.history` is read from a file inside the repository under audit, and
  every consumer built `root / configured` without validating the result — so
  a repository could name `../outside.jsonl`, an absolute path, or a path
  through a symlinked directory, and an audit with history enabled would
  create and append that file outside the authorized root. Found by audit
  through the public MCP seam. `config.repository_path` now resolves and
  bounds every configured repository-scoped path before any existence check,
  directory creation or append, and all five construction sites use it: the
  MCP audit tool, the MCP report resource, and both CLI paths. Traversal,
  absolute escapes and symlink escapes are one comparison, refused with the
  same structured `PathNotAllowed` the roots boundary already used.

### Added

- **`--install-skill` / `--force-skill`.** The agent skill ships inside the
  package, byte-pinned to the repository's `skills/` tree by test, and one
  command syncs it into an agent's skills directory — closing the drift that
  left a dead CLI-first recipe installed for three days after the docs sweep
  fixed it. A differing installed copy is refused with the list of
  differences; `--force-skill` performs the full sync.

### Fixed

- **Skill installation is bound, atomic and complete.** The skill root is
  opened once with `O_NOFOLLOW|O_DIRECTORY` and every read, write and unlink
  is relative to that descriptor, so swapping the pathname afterwards cannot
  redirect a write; a failed rebind refuses rather than resolving against the
  process working directory; files are staged and renamed into place, so a
  destination replaced by a hard link is never written through; and every byte
  is written or the install refuses instead of reporting success on a
  truncated file.
- **Occupancy is every directory entry.** An empty directory, a FIFO or a
  socket in the skill root used to read as a fresh install and be modified
  without consent, and a FIFO named `SKILL.md` hung the installer because
  reading it meant opening it. Occupancy is decided from `stat` metadata
  without opening anything.
- **Analyzer selection composes the runnable set from the repository.** The
  language inventory and concern mapping decide what runs before any probe or
  spawn; a catalogued tool with no adapter is stated rather than counted as
  runnable; and refused path identifications are visible in JSON, Markdown and
  HTML alike.

### Added

- **`--install-skill` / `--force-skill`.** The agent skill ships inside the
  package, byte-pinned to the repository's `skills/` tree by test, and one
  command syncs it into an agent's skills directory. A differing installed
  copy is refused with the list of differences; `--force-skill` performs the
  full sync — overwriting edits and removing files the package no longer
  ships. Closes the field-found drift that left a dead CLI-first recipe
  installed for three days after D12 fixed it. The repository's own self-scan
  excludes the packaged mirror (`_skill_data/`): its byte-identity to
  `skills/` is the pin, not duplication.
- **Refused path identifications are visible.** `unidentified_source_paths`
  lists tool path spellings that matched zero or several files, so a refusal
  is never mistaken for an identification.
- **D15's original requirement, proven as written.** An audit caught the D15
  close rewriting the entry; the original goal-directed-selection requirement
  is restored to the register and holds behind `tests/test_d15_goal_directed.py`.


## 0.9.0 - 2026-08-19

### Added

- **The JVM analyzer track (decision 9): PMD, Checkstyle, SpotBugs.** Three
  adapters in two shapes. PMD pins two design rules (cognitive and cyclomatic
  complexity) over source, live-proven on Apache commons-cli. Checkstyle runs
  the bundled Google ruleset from a neutral working directory (the audited
  tree's suppressions are never read) and claims exactly what it emits: style
  and documentation. SpotBugs reads bytecode that already exists — the agent
  never builds (ADR 012); missing bytecode becomes a build-then-rerun entry in
  the environment work order, runs record staleness evidence (source vs class
  mtimes) on the coverage row, stale findings say so, and the SECURITY
  category is excluded by a bundled filter (that boundary belongs to
  secure-code-agent).
- **D15 composition honesty.** One report composes both adapter shapes:
  finding identity is the located rule for rule-backed findings — never a shared concept; rule-less findings fall back to message identity, a
  package-relative sourcepath is identified with its repo-relative file when
  exactly one match exists (refused on ambiguity), composed coverage states
  stale_artifact_evidence, and artifact-read applicability follows artifacts
  rather than the source-language inventory. Closes the seventeenth and final
  chat-surface register entry.
- **Root grants over MCP (decisions 4–5).** An out-of-roots audit asks one
  structured question — this session (default) / always / no. Session grants
  live in the process; always grants persist to the user tier and survive
  first-run setup; consent binds to the resolved path the question named, and
  a retargeted symlink voids it. History recording follows persisted consent
  on both doors — written `history.record: false` outranks a TTY (decision 7).
- **Baseline adoption and per-format payloads over MCP (D7, D8),** install
  remedies with the concepts they restore (D9), and chat-first documentation,
  help files, and instruction packs across every operator surface
  (D4, D12, D16, D17).

### Changed

- Coverage rows state the languages the integration actually reads, tool
  versions skip ASCII-art banners, concern pools select by what a pinned
  invocation can emit, and the analyzer-pool tier promise names its two
  disclosed exceptions (Checkstyle and SpotBugs live spawns remain unproven
  until binaries exist).
- **Chat-first setup and audit repairs after v0.8.1.** Local MCP first-run
  elicitation now closes D2 and D11 and ships D3's structured-setup portion,
  persists accepted analyzer, depth, license, economic-context and presentation
  choices, and returns unanswered setup for the host to ask again. The H1/M1/M2
  follow-up makes prompt remedies honor analyzer coverage, re-elicits until
  answers are written, and uses chat as the unconfigured presentation default.

## 0.8.1 - 2026-08-16

### Changed

- **Chat-surface foundations D1 and D13.** Analyzer-pool execution is
  config-driven through `build_report`, both CLI overrides, the MCP tool,
  and the MCP report resource. XDG user configuration, repository-over-user
  precedence, and persistent first-run state also ship. These changes landed
  after v0.8.0, are not in the v0.8.0 tag, and ship in v0.8.1.

## 0.8.0 - 2026-08-16

Pre-1.0 test release: everything merged since 0.7.0, packaged for field
testing. The known defects of the primary (chat/MCP) surface are
recorded in
[docs/defect-register-chat-surface.md](docs/defect-register-chat-surface.md)
(D1-D15) and are the next fix cycle; this release ships them disclosed,
not resolved.

### Added

- **ADR 009 identity resolution.** Finding identity is structured
  (kind, path, name, ordinal, body digest) and matching follows git's
  rename evidence: `git mv` and same-name reorders no longer read as
  fixed-plus-new in `--fail-on-new` or recurrence. Baseline v3 stores
  identity records and the commit; history records are schema 3.

- **ADR 003 option C (TypeScript prototype).** Type-backed universal
  facts, checked-in `semantic_policy` violations, and prompt-only
  design-review candidates, from recorded type analysis or a local
  tsc. Semantic results render on all three skins and never change
  the score, the gates, or the grade.

- **ADR 004 v1 economic context.** An optional, clearly-labeled
  low/base/high scenario computed from configured labor rates beside
  the score; exposure-ordered work order; scenario vocabulary only.
  The score is byte-identical with and without it.

- **Executive HTML report.** The HTML skin leads with estimate, grade,
  gate state, Severe/High/Medium/Low counts from published class risk,
  and direction; findings are HTML tables sharing `render_markdown`'s
  identities; charts gained axes, ticks, titles and a pillar legend.
  Severity labels are presentation only.

- **flake8 and cohesion adapters (2.7).** flake8's default
  `path:row:col: CODE` lines become located findings (verdict emitter).
  cohesion's per-class `Total:` percentages become measurements.
  xenon stays unadapted: it re-ranks radon and would fake corroboration.

### Changed

- **Network-boundary disclosure.** README, product intent, architecture
  and the analyzer pool state that this agent does not transmit the
  audited tree, and that third-party tools it spawns are not
  network-sandboxed. Claiming an air-gapped child process fails a lint.

- **ADR 011 presentations and history schema 2 shipped.** Three report
  skins (chat default, Markdown file, one self-contained HTML file) render
  one report dictionary. New history records carry the per-scan score
  breakdown, while schema-1 records remain readable as gaps. 1.0 still
  waits on Marshall's acceptance, the 7.5 hostile audit, and a human tag.

- **Self-audit restamped (7.1).** Provenance commit `9c2257a`, 235 files
  scanned. README table matches the stamp. Still a B.

- **PyYAML is a declared `dev` extra, not a silent test import.**
  `tools/build_catalog.py` is the only user. Tests cannot import `yaml`.
  A structural lint fails undeclared third-party imports in `tests/` and
  `tools/`.

- **CI history cache (6.4).** The consumer workflow restores and saves
  `.maintainability/history.jsonl` around a recorded scan (`if: always()`
  on save). `action.yml` takes opt-in `record-history`. `examples/local-ci.sh`
  records. No new release tag.

- **Per-concept analyzer spread moves `maintainability_range` (3.4).**
  Independent tools disagreeing on one concept widens the interval;
  a lone tool is not priced as perfect agreement. The estimate stays
  the analyzer-primary point. The band matrix is still unused.

- **MCP ships all three primitives.** Resources expose the rubric, the
  analyzer catalog, and a Markdown report that is byte-identical to the
  CLI rendering. The `maintainability-agent` prompt is the slash command.
  Start it with `maintainability-agent mcp`; `maintainability-agent-mcp`
  remains for existing IDE configs.

- **A 1.0 migration note.** [docs/migration-1.0.md](docs/migration-1.0.md)
  names the post-0.7 breaks: `--analyzers` moves the point estimate, and
  `CALIBRATION_C` 2.6279 → 2.2658. Schema 3 and baseline v2 do not break
  again. 1.0 is not tagged.

- **The report contract, 0.7 migration note, and tool inventory match the
  shipped tree.** Schema version 3 (nullable estimate), Java has a declaration
  population, `CALIBRATION_C` is 2.2658 after 3.6, and coverage is reported.
  A structural lint fails the build if those pages revert to the 0.7-era story.

- **First-run prompt (6.1).** On a TTY with no config the CLI asks
  depth and license policy and writes `maintainability-agent.json`.
  Non-TTY and existing-config runs never prompt and never rewrite.

- **Environment work order (2.5c).** The report names each selected
  analyzer that could not run, why, the install command, and how to
  verify it. The agent never installs.

- **The point estimate uses analyzer measurements where the full concept set
  was measured.** `--analyzers` is no longer a coverage-only side channel:
  `scoring._primary_pressures` takes the analyzer reading per dimension and
  keeps the built-in fallback where the analyzers were silent. The range
  widens to contain both sources; they are never averaged. The Markdown
  report, the remediation prompt, CLI `--help`, and the README name that
  mix rather than claiming the opposite.

- **Calibration 3.6.** `CALIBRATION_C` 2.6279 → 2.2658 and the declarations
  reference 0.0599 → 0.0860, fitted to the analyzer-primary mix after
  generated and vendored code left the scored population. 13 of 40 corpus
  members supplied an analyzer declaration reading; 27 stayed on the
  built-in fallback. Old and new numbers are in `_calibration.py`.

## 0.7.0 - 2026-08-13

Scores the evidence cannot support are withheld. `--fail-on-new` no longer
fires on code that only moved. Two incompatibilities: **report schema
version 3** (`maintainability_estimate` is nullable) and **baseline format
version 2**. See [docs/migration-0.7.md](docs/migration-0.7.md).

### Added

- **The MCP server can run the analyzer pool.** `audit_repository` takes `run_analyzers`
  and returns the coverage, findings and measurements alongside the report, with
  `analyzers_run` stated at the top level so a caller cannot mistake a six-detector audit
  for a ten-tool one.

- **Three new default risk patterns, each earned by a defect this project actually shipped.**
  `absence-as-zero` catches a measurement default that conflates "measured none" with
  "never measured" — the bug behind a one-function repository scoring 5.0/A+, and behind
  a clean scan reading as unexamined. `vacuous-assertion` catches assertions that cannot
  fail, after one let a gap survive the test written to catch it. `silent-truncation`
  catches a returned collection cut without saying so. They are review prompts, not defect
  assertions: narrowed until they stay quiet on accumulators and named limits.

- **`--analyzers` runs external quality tools and reports coverage.** Nine adapters ship
  working: lizard, radon, ruff, vulture, interrogate, jscpd, complexipy, multimetric
  and pydocstyle. Every report states which
  tools were attempted, which ran, which were unavailable and why, their versions, and
  **which concerns nothing examined** — a concern nobody looked at is reported unexamined,
  never clean. Off by default in 0.7.0 because analyzer measurements did not
  move the point estimate, not because the pool was unfinished.
- **A copy-paste GitHub Actions recipe** at `.github/workflows/maintainability.yml`,
  the file the README already named.

### Fixed

- **Every entry point uses the repository's own `maintainability-agent.json`.** Discovery
  lived in the CLI at first, which was not enough — the MCP server returned 405 findings
  where the CLI returned 162 on the same repository. It now lives in `config`.
- **The repository's own `maintainability-agent.json` is used without `--config`.** The CLI
  previously fell back to built-in defaults when no config was named, so a repository with
  a config file beside it was audited against different exclusions than it asked for. On
  this project the difference was 422 findings versus 162, most of the excess from a
  generated data file its config had excluded all along. An explicit `--config` still wins.
- **File patterns in `exclude_patterns` now reach the external analyzers.** Directory and
  file patterns were both wrapped as directory globs, so `data/generated.json` became
  `**/data/generated.json/**` and never matched.

- **`--changed-only` no longer reports a whole-repository grade for a diff.** It previously
  returned an estimate and `evidence_status: complete` over as few as zero declarations, and
  every PR-scoped CI run inherited it. A scope-limited scan now withholds the estimate, the
  range and the verified grade, with a reason naming the scope and the remedy. Findings and
  aspects are unaffected, and `--fail-on-gate` exit codes are unchanged.
- **Finding identity survives edits elsewhere in the file.** Fingerprints embedded the start
  line, so inserting one import above an untouched function made it read as simultaneously
  fixed and new — a false failure for `--fail-on-new` after any refactor that shifts lines.
  Identity now uses the path, declaration name and same-name ordinal instead of the start line.
- **Two same-named declarations in one file are two findings everywhere, not just in the
  baseline.** `finding_fingerprints` numbered overloads `#0` and `#1` correctly, but the work
  order, `prompt_targets` and the prompt's escalation check each rebuilt the identity with a
  hardcoded ordinal of `0`. So two `huge` methods in one file were one finding: the work
  order named the same declaration twice, recurrence recorded advice about the first one
  twice and never about the second, and escalating either overload suppressed whichever the
  prompt compared first. The population, the order rule and the numbering now live in
  `declaration_identities` / `risk_identities`, and consumers look identity up rather than
  derive it.
- **Risk findings can be tracked across scans at all.** `prompt_targets` rebuilt a risk
  identity from the work-order item's rendered *title*, so the name it hashed was the label
  "configured risk pattern" rather than the pattern's own name. No such identity is ever in a
  report, so every risk target failed the corroboration check and was silently dropped — on
  this repository, all 21 of them.

- **A repository too small to measure gets no score.** A tree holding one production
  function and one test reported 5.0/A+ with every finding count genuinely zero — the
  arithmetic was right and the number was empty. Rates now require a population the scale
  was calibrated on: the whole score is gated on the tree's size, and inside a scorable
  repository each aspect is gated on its own denominator. Findings are never suppressed,
  only rates.
- **The unread-source remedy no longer says the repository is too small.** Adding
  the missing extension was the right next step; calling the tree undersized after
  that was a second, false diagnosis.
- **Work-order items use the hotspot's `start_line`.** Oversized declarations
  carried `line: None` because the work order read a key the hotspot never had.
- **Competing-libraries items read `divergent_idioms`.** The work order looked up
  `idiom_concerns`, a key the report never carries, and dropped every idiom finding.
- **The AI prompt names complete evidence and the estimate's source.** A complete
  report used to be silent about evidence status. Analyzer findings sat under a
  built-in estimate with no caveat. The status is now printed in every state, and
  the built-in-only caveat appears only when analyzers spoke.

### Changed

- **Promise P1 amended: analysis performs no network access; tool *acquisition* may.**
  The audit now invokes external analyzers, and some live in ecosystems whose normal
  install path is a fetch — `npx` for the Node tools. The property the promise protected
  is intact: the analysis itself touches no network and your code is never transmitted
  anywhere. Acquiring a tool may fetch it on first run, and the version acquired is
  recorded. Install ahead of time (`npm install -g jscpd`) to pin a version or build
  air-gapped. Prerequisites are listed in `docs/analyzer-pool.md`.
- **Report schema version 3.** `maintainability_estimate` and `maintainability_range` are
  nullable and `evidence_status.status` may be `insufficient`. Consumers assuming a number
  must handle null.
- **Baseline format version 2.** Old fingerprints cannot be converted, so a version-1 baseline
  is rejected with an instruction to regenerate rather than silently suppressing nothing.
  Regenerate with `--write-baseline`.


Recalibration, and a retraction. The reference corpus is now chosen by a query instead of by the author's taste, which moved every constant in the scale — read the table before comparing a score to one from 0.6.x.

### Added — local MCP server

- **A read-only stdio MCP boundary for Codex and its VS Code extension.** `maintainability-agent-mcp` exposes the production audit and its bounded remediation prompt together; it does not restate scanning, scoring or rendering. Canonical repository allow-lists block path and symlink escapes, config files must remain inside the audited repository, changed-only input cannot inject git options, and the server accepts no command strings or output paths. MCP remains an optional install extra, so the base CLI keeps its dependency footprint.

### Changed — ADR 001 stage 8 (**breaking report contract**)

**Stage 8 moved the report schema from 1 to 2.** The four ambiguous
compatibility score fields left with no aliases. **0.7 then moved the
schema to 3** when the estimate became nullable; that is the version this
release writes. Version 1 is still rejected. There is no migration.

| Removed | Replacement |
|---|---|
| `score.overall` | `score.maintainability_estimate` |
| `score.overall_range` | `score.maintainability_range` |
| `score.grade` | *nothing* — `score.verified_grade` is the only letter a report carries |
| `score.grade_blockers` | `score.verified_grade_blockers` |

- **Why `grade` has no replacement.** It was banded from the evidence floor, so on an incomplete report it meant "the worst the evidence allows" while reading as the repository's grade. Stage 7 labelled it; stage 8 removes it. A report now either issues a verified grade or issues none, and there is no second letter to fall back to.
- **`verified_grade_blockers` explains an issued grade only.** When no grade was issued the list is empty, because there is nothing to cap — what is missing is named in `evidence_status.reasons` with its measurement path and provenance. Conflating the two is what let an evidence gap read as a quality demotion.
- **No value moved.** Parity was proven against four reports captured from `a6b3c0f` before any edit — complete, complete-with-NotApplicable, incomplete from unavailable history, and incomplete from a missing summary measurement — checked in under `tests/fixtures/stage8_anchors/`. Estimate, range, verified grade, categories, aspects, rubric, dimensions, reference, worst dimension and evidence status are identical in all four. The calibration constant re-derives to the same value and all 40 corpus repositories still produce a median of exactly 4.0.
- **No version-1 migration exists, deliberately.** The consumer inventory established that nothing rescores a persisted report, so a migration would have served no caller. Version 1, unversioned and unknown versions all fail with `UnsupportedReportSchema`.
- **Baselines stop carrying a score snapshot.** Nothing ever read it back — `load_baseline` takes the fingerprint list alone — and writing one would freeze an obsolete contract into every new baseline. At stage 8 the file version stayed 1 and older files still loaded. **0.7 later rejected version-1 baselines** because finding identity changed and those fingerprints cannot be converted; this release writes baseline format version 2.
- **The presentation boundary lost its fallbacks.** `_evidence_view` reads canonical fields directly; `compatibility_grade` and `NOT_REPORTED` are gone, along with the legacy-field defaults. A malformed score object now fails rather than receiving compatibility semantics.
- **Guarded against reintroduction.** A structural test fails the build if `src/` or `tools/` reads or emits any of the four removed keys, while leaving internal variable names, test descriptions and historical prose alone.

### Added — ADR 001 stage 7 (consumer migration)

- **Every consumer now distinguishes the estimate from the verified grade.** Through stage 6 the Markdown report, PR comment, remediation prompt and agent instructions all headlined `score.grade` — which is banded from the *evidence floor*, so on an incomplete report it means "the worst the evidence allows" while reading as though it were the repository's grade. All four now show the maintainability estimate, its range, the evidence status with its named profile, and either the verified grade or the words **Not verified**. The compatibility grade stays visible for the deprecation window and is labelled as compatibility/evidence-floor wherever it appears; removing it is stage 8.
- **A null verified grade is never rendered as a letter, a dash, or a blank.** Each of those reads as a result, and the point of the field is that no result was issued.
- **Unavailable measurements are named with their typed path and provenance**, so a reader knows which measurement to restore rather than that "history" is vaguely absent.
- **The remediation prompt states that incomplete evidence is not a code defect** and must not widen the work order, and names the usual cause (`actions/checkout` defaults to `fetch-depth: 1`). Without that, an agent told "evidence is incomplete" does what agents do and starts changing code — the measured cost of an unbounded instruction is in `docs/studies.md`.
- **SARIF carries evidence at run level only.** Profile, status, verified grade and reasons ride in the run's property bag; missing evidence never becomes a result, because "this clone was shallow" is not a source-code finding and does not belong in the Security tab beside real defects. Result count, rule ids, levels and locations are unchanged. A report with no score object omits the bag entirely rather than emitting `verifiedGrade: null`, which would assert a withholding that never happened.
- **One presentation helper owns the wording** (`_evidence_view`), so four consumers cannot arrive at four interpretations of what null means. It reads the public report dictionary, computes no score and imports nothing from the scoring layer.
- **Nothing about scoring changed**, verified by comparing a complete and an incomplete production report before and after: no field of `score` differs. `--fail-on-gate` still reads hard findings only and still exits 0 for a withheld grade, per the rejected ADR 002.
- **Five audit findings closed before this shipped.** A collapsed range no longer claims "no unmeasured evidence" — rounding can make the bounds coincide on a report whose grade was withheld, so the phrasing now consults the typed status and a property test sweeps every required measurement rather than the one example. The agent instructions were only half migrated, showing the grade value while omitting the range, status, profile, reasons and the don't-widen rule; the changelog and standard claimed otherwise and were wrong. Remediation advice now follows the missing measurement paths instead of telling every incomplete report to check its clone depth — including one whose only gap was `summary.test_file_count`. The SARIF preservation test compared nothing: it now diffs results and rules against output captured from commit 91430f3. And the roadmap still listed finished stages as pending.
- **Deliberate no-ops, confirmed in source rather than assumed:** no badge consumer and no API grade consumer exist, and `load_baseline` still reads fingerprint strings only.

### Fixed — ADR 001 Stage 6 closure

- **fix(scoring): typed ownership evidence is now the only source of applicability.** `NormalizedEvidence` carried both `history.single_author_files` and a companion `history_present` Boolean. Grading used the Boolean to exempt `knowledge_concentration` whenever any history block existed, so deleting only `single_author_files` produced an explicit `Unknown` yet retained an A+ compatibility grade with no unmeasured-ownership blocker. The companion flag is removed. Only a genuine `NotApplicable` state receives the no-population exemption; `Unknown` now demotes top grades to B and names the missing aspect, as the standard has always claimed.
- **correction: Stage 6 changed only externally supplied incomplete compatibility input.** The `404d82c` handoff said compatibility JSON and Markdown were unchanged. Comparing `build_report` output before and after Stage 6 shows no compatibility-field difference because the producer always emits all three documentation flags. A versioned report supplied externally with `has_readme`, `has_changelog`, or `has_docs_dir` omitted does change intentionally: its documentation aspect becomes unmeasured and its range, grade and blockers may move. No rubric weights, grade bands or calibration constants changed.
- **fix(scoring): NotApplicable no longer widens the uncertainty interval.** A young repository with readable history but no settled files reported complete evidence and a verified A+ beside a range of `[4.8, 5.0]`. The aspect layer represented both `Unknown` and `NotApplicable` as `None`, and the rollup priced both across 0..5. The typed state now supplies a NotApplicable exclusion to the one shared rollup: the aspect is removed from its category denominator for the point and both bounds. It earns no clean score, pays no unknown price, and complete evidence collapses the range.

### Retracted

- **retract: the claim that near-duplication distinguishes AI-written code.** 0.6.0 reported production cross-file near-duplication at **1.49%** for AI-written applications against **0.20%** for human-written OSS, and the README called it "the first signal that separates AI-written applications from mature human-written OSS". The AI cohort was six young applications; the control was twelve libraries with a decade of maintenance behind them. Authorship, age, domain and size all differed at once, and the release attributed the gap to the one variable it found interesting — while a paragraph further down admitted the confound. Re-run against a control matched on age, popularity (both cohorts median **zero** stars) and language, the difference is **not significant: p = 0.546**, and **p = 0.871** inside a common size band. What moved since 0.6.0 is not the AI figure (1.49% → 1.73%) but the *control*, 0.20% → 0.83%. The signal was maturity, not authorship.
- **no other metric earns the claim either, though one is left genuinely open.** File-failure rate (p = 0.043) and duplicate-block rate (p = 0.042) fall under 0.05 — more than chance alone would typically yield across five tests, but both are the metrics most correlated with codebase size (r = 0.58, 0.49), and the AI cohort carries 1.8x the declarations because **size was not matched at selection**, only handled afterwards by re-testing inside a shared size band. Banded, file failures converge on near-identical medians (1.82% vs 1.77%, p = 0.123) — that one really does look like size. Duplicate blocks keep a **3.3x banded median gap at p = 0.117**: underpowered, not resolved. And the design's stated hole is that the control is "no AI trailer found", which Copilot and pasted LLM output would pass — so the honest conclusion is **"this design could not measure a difference"**, not "there is no difference".
- **checkable rather than asserted:** the cohort definitions are pinned in `tools/calibration/ai.json` and `human.json` (URL, commit, stars, trailer fraction per repo), `cohorts.json` carries all 78 measurements, and `analyze_cohorts.py` reproduces the tables offline with no network. The rank-sum test carries tie and continuity corrections and is pinned numerically against scipy — the first version lacked the tie correction, inflating p by up to 2.4x on tie-heavy metrics, in the null's favor.
- **the near-duplicate detector itself is unaffected and still shipped.** A helper written twice under two names is worth finding regardless of who wrote it. What is withdrawn is the claim that finding it tells you anything about authorship.

### Fixed — second hostile-audit response

A second adversarial audit probed the rubric within hours of it landing. Its stale claims are answered in the tracker; its live findings are all fixed here:

- **fix(scoring): the reported overall is always the mean of the reported categories.** The zero-test testability cap used to mutate the displayed category *after* the overall was computed, so exactly the repos being penalized got an overall that contradicted the published rollup formula. The cap now applies before the rollup.
- **fix(scoring): an empty test-shaped artifact no longer buys an A.** `test_file_count` counted any path-matching file (a Markdown note under `tests/`, an empty `test_x.py`), and a 1.5-point floor priced "tests exist" without asking whether they contained anything. Test files must now be source files, and test files holding zero declarations score the same as no tests: probes for zero tests, one empty test file, and md-in-tests/ all read B / testability 2.0 / named blocker.
- **fix(scoring): history aspects score from full counts, not truncated display lists.** Hotspot and coupling rates were computed as `len(capped-at-25 list) / files_changed`, so a repository with 100 real hotspots in 1,000 changed files scored as 25/1000 and the pressure *fell* as repositories grew — the size-bias class this scale exists to forbid, reintroduced by its newest metric. `history_section` now records `qualifying_hotspots` and `code_coupling_pairs` before truncation and the scorer reads only those.
- **feat(scoring): unknown evidence blocks the top grades.** A shallow clone could omit coupling, hotspots and ownership and outscore the same repository with its history visible. Unmeasured aspects now demote A-grades to B with a blocker naming them; "looked and found nothing to measure" (a young repo with no settled files) is distinguished from "couldn't look" and does not block.
- **fix(calibration): the anchor is derived through the full rubric, not a structural-only approximation.** The corpus measurements now carry an `evidence` block per repo (test presence, dead code, near-duplication, idioms, documentation — captured by re-measuring all 40 pinned clones), and the derivation prices it via the *same* `evidence_aspect_scores` function live reports use. `CALIBRATION_C` 2.966 → **3.1994**. History aspects stay out of the anchor (shallow pins) and renormalize away exactly as they do for any shallow clone. The re-measure also reconfirmed every dimension reference byte-for-byte, disproving the audit's repeated staleness claim.
- **docs: the "override it in config" sentence was false and is corrected.** Rubric weights and bands are source, not config; per-repo override is roadmap, and any future mechanism will label its output a house variant.

### Fixed — third hostile-audit response

- **fix(scoring): unknown aspects price at the corpus anchor instead of renormalizing away.** Renormalization let a shallow clone of clean code score 5.0 while the same code with worst-band history scored 4.2 — hiding the log was worth +0.8. Anchor pricing puts the shallow point estimate *between* worst and clean (worst 4.2 < shallow < clean 5.0). **An earlier revision of this entry claimed "hiding evidence can no longer raise the score"; a fourth audit correctly showed that false** — hiding worse-than-anchor history still gains up to the anchor-to-worst gap, which no single imputed value can prevent. The honest closure is `score.overall_range`: unknowns priced at 0 and 5 bound the overall, so concealment visibly widens the interval instead of silently improving a point. **A fifth audit called "closure" spin here, correctly** — the interval disclosed the exploit to a human reader while `grade` still improved under concealment for every machine consumer. The actual closure is grading from the interval's floor, in the fifth-round entry. Pinned by tests (ordering, bound, and interval collapse under full evidence). `CALIBRATION_C` re-fitted: 3.1994 → 2.8545.
- **fix(scoring): `overall == weighted mean of the printed categories`, exactly.** An audit produced categories displaying 3.5/4.2/5.0/4.5/2.0 with overall 3.9 against a displayed mean of 3.8 — the overall came from hidden unrounded values. It is now computed from the categories exactly as displayed, so the published identity is arithmetic a reader can check on the report itself.
- **fix(experiment): the fix-scope runner and analyzer now implement their protocol.** Subjects are validated against pinned manifest commits before every copy; diffs are taken against a recorded base SHA rather than a movable HEAD (verified no agent had moved HEAD, so no recorded run was affected); the rerun-once rule exists; non-completed runs are excluded and listed; a nothing-touched run no longer scores perfect scope. The analyzer computes both statistic phrasings the protocol contains — marginal medians (the registered inequalities) and paired per-repo differences — and returns INCONCLUSIVE if they disagree: ambiguity in a pre-registration resolves against the experimenter.
- **docs: synced to the implementation.** "Signals reported but not yet scored" said unscored about three aspects the rubric scores; the scoring-inputs list omitted eight of thirteen aspects; both fixed with the drift named.

### Fixed — sixth hostile-audit response

The fifth round's response claimed all five findings were closed. Two were not, and the sixth audit proved it. Both were cases of fixing the demonstrated instance instead of the class — the exact failure the previous entry congratulated itself for avoiding.

- **fix(scoring): withholding evidence could still raise the floor.** The untested testability cap only applied when `test_file_count` was present, so *deleting* the field escaped the penalty that reporting zero tests incurred, and the evidence floor rose. Grading the floor is worthless if absent evidence can raise the floor. Unknown test evidence is now three-valued and priced by the same dial as every other unknown — typical for the point estimate, worst case for the floor. Sweeping every summary key then found **three more fields with the identical shape** (`file_failures`, `files_scanned`, `risk_findings`), where `.get(key, 0)` silently turned "this report does not say" into "there were none": a perfect score for saying nothing. Absent inputs now make their dimension unmeasured. The replacement test sweeps `summary` itself rather than a hand-maintained list, and the audit was right that the old test's name — "hiding evidence can never raise the grade" — claimed far more than hiding one history object proved.
- **fix(fix-breadth): the shallow boundary commit fabricated its own diff, and it changed published numbers.** The oldest commit a shallow clone holds has no parent, so git diffs it against the empty tree and `--numstat` reports the whole tree as added: a synthetic fix measured 1 file / 75 lines deep and 2 files / 39 lines at the boundary. **Two AI-cohort repositories had a fix commit on that boundary, and the fabricated whole-tree diff counted as a "broad" fix** — the defect inflated the AI cohort's broad-fix share in the direction that flattered the hypothesis. Clones now fetch one commit deeper than the window and grafted commits are excluded. Corrected: `broad_fix_share` **p = 0.025 → 0.028** unbanded, two per-repo shares down (0.114 → 0.102, 0.434 → 0.427); banded tests and quoted medians unchanged. **The previous entry's claim that re-measurement "reproduced the published results identically" was true only of the cache-depth repair and is corrected in place below.** New `tests/test_fix_breadth_window.py` pins the property across four cache depths with synthetic repositories instead of pinning the one repo whose failure had been demonstrated.

### Fixed — fifth hostile-audit response

The fifth audit accepted the fourth round's corrections and then found that two of them had introduced new defects, plus three older claims still weaker than stated. Every finding was reproduced against the pushed snapshot before being fixed; all five were true.

- **fix(scoring): the uncertainty interval no longer excludes the score it bounds.** The untested-repository testability cap was applied to the point estimate but not to the interval endpoints, so a perfect-structure, zero-test repository reported **4.4 with a range of [4.5, 4.5]** — and because the endpoints were equal the markdown renderer hid the range, leaving only JSON consumers able to see the contradiction. Both endpoints now run the identical pipeline with only the unknown price swapped, so `low <= overall <= high` holds by construction. The collapse test that existed used a *tested* repository and walked straight past the boundary; the new test checks five configurations including both untested cases.
- **fix(scoring): `knowledge_concentration` was a decorative aspect and now carries weight.** It was measured, printed under "Aspect Scores", documented as one of thirteen scored aspects, and weighted in no category at all: moving a repository from every settled file having many authors to every settled file having one changed the overall by **exactly zero**. Thirteen were advertised; twelve did the work. Bus factor now takes .10 of analyzability and .10 of modifiability, and `test_every_scored_aspect_carries_weight_in_some_category` fails the build if any advertised aspect is ever unweighted again — the structural block, not just the instance fix.
- **feat(scoring): the grade is banded from the evidence floor, closing concealment at every boundary.** The fourth round shipped `overall_range` and called it the closure; the fifth correctly named that spin. The interval warned a careful human while `score.overall` and `score.grade` — the fields CI gates, badges, rankings and API consumers actually read — still improved when evidence was withheld (3.9/C visible, 4.5/B hidden). `grade` now comes from `overall_range[0]`. Hiding an aspect can only widen the interval downward, so concealment is now monotonically unprofitable rather than merely disclosed, and a blocker names both numbers whenever the floor and the point estimate differ. Blockers also render in the report itself for the first time — they previously reached only the remediation prompt, so a demotion arrived unexplained in the artifact people open.
- **fix(calibration): "the same pipeline" is now one pipeline rather than two that agree at the median.** Three consecutive audits found the derivation differing from the live scorer by exactly one step — category rounding, then the untested cap (corpus member `tabby`: derived 3.9, live 3.8), then per-aspect rounding inside the curve. Each time the median survived and the per-repository claim did not. `_derive` now calls `_formula.overall_from_aspects` directly, the curve is a single shared function, and a new test compares derivation against `score_report` **for all forty corpus repositories** instead of at the median. `CALIBRATION_C` 2.8712 → **2.6279**; the reference medians re-measured byte-identical for the third audit running.
- **fix(fix-breadth): the deterministic window is now actually deterministic.** The deepening step was gated on the cached HEAD differing from the pinned commit, so a *shallow cache already at the pin* was used untouched: a depth-one clone of `open-mercato/cezar` at its recorded pin produced **0 fix commits against the deep cache's 96**, silently dropping the repository from the population rather than measuring it. Depth is now verified and repaired independently of HEAD, and a subject that cannot be deepened is refused rather than measured short. Re-measuring under that repair reproduced the published cohorts, comparisons and banded tests identically. **That was not the whole defect**: a sixth audit found the shallow *boundary* commit fabricating its own diff, which had inflated two AI-cohort repositories' broad-fix share and moved an unbanded p-value. Corrected in the sixth-round entry.
- **chore: CI now runs on every branch.** The audit noted that pushing `e4a7fbf` triggered no workflow at all, because the push trigger was limited to `main`/`master` and no PR was open — so the tool's own gate went unenforced on exactly the commits under review.
- **refactor: `scoring.py` split into `_pressures`, `_aspects`, and `scoring`.** Not housekeeping: the tool's own gate failed the build on this repo twice during this round — an 85-line `score_report` over the function ceiling, then a 517-line `scoring.py` over the 500-line file ceiling. The split follows the real layering (counts → aspect scores → grading), and it also removed the import cycle that had forced `_derive` to import the scorer from inside a function body. Self-audit: **4.6 / B**, 94 files, zero hard-gate failures, coverage 95.34%.

### Fixed — fourth hostile-audit response

The fourth audit examined the pushed snapshot itself and caught this changelog telling two direct falsehoods, both corrected in place above with the correction named rather than silently rewritten:

- **"Hiding evidence can no longer raise the score" was false.** No single imputed value can make concealment neutral for repos whose true evidence is worse than the imputation. Closed honestly instead: `score.overall_range` prices every unknown at 0 and at 5 and ships in the report and the markdown summary, so hidden evidence visibly widens an interval rather than silently flattering a point. New tests pin the concealment ordering, its bound, and the interval's collapse under full evidence — the audit correctly noted the prior fix shipped with zero test changes.
- **"Three generic runs got worse" was false — it was two** (plus one bounded run at net −1, miscounted into the generic column). Corrected in the standard and here.
- **The preregistration narrative overstated itself.** The protocol and decision rule predate the first run; the analyzer does not — its first version landed about a minute into the runs and it was rewritten mid-run. The standard now states the chronology instead of the flattering summary of it.
- **The anchor now goes through the literally-same pipeline.** The derivation rounds categories to one decimal exactly as `score_report` ships them (an audit found 6/40 corpus repos differing between paths while the docs said "same pipeline"). The rounded pipeline is a step function, so `CALIBRATION_C` is the midpoint of the plateau where the corpus median hits 4.0 *exactly* — asserted by a new test as `== 4.0`, not a 3.9–4.1 band. 2.8545 → **2.8712**. **A fifth audit showed "literally-same" was still false at this revision**: the derivation skipped the untested testability cap, and `tabby` derived 3.9 against a live 3.8. The median reproduced anyway, which is exactly why a median is not the test. See the fifth-round entry for the fix.
- **Experiment evidence is now durable in-repo.** `tools/experiments/fix_scope/artifacts/` carries every arm's full diff against its pinned base and every bounded prompt; regenerated prompts match recorded lengths byte-for-byte. The agents' full transcripts were never captured (2,000-char tails only) — that loss is permanent and stated.
- **Fix-breadth measures a fixed window.** `git log -n 300` from each pinned HEAD, so cache deepening cannot shift results (the audit demonstrated it could); the false "capped at 300" note now truthfully describes window vs. clone depth. **Incomplete as shipped**: a fifth audit showed a *shallower* same-HEAD cache could still erase the window entirely, because the deepening step was gated on the commit matching rather than on the depth. Fixed in the fifth-round entry.
- **CI lint now covers `tools/`**, and for the record: the coverage percentage gates the `maintainability_audit` package only — the calibration and experiment programs under `tools/` are exercised by their own runs and spot-verified by audits, not by the coverage gate, and no one should read 95% as claiming otherwise.

### Measured — the bounded prompt, tested: INCONCLUSIVE on the registered rule

- **feat(experiment): the product's central promise met its first controlled test.** Pre-registered protocol (committed before any run, analyzer committed mid-run), six pinned repositories, paired `codex exec` runs on `gpt-5.6-sol`: generic "improve maintainability" vs this tool's bounded prompt. Registered verdict **INCONCLUSIVE** — bounded was *not* narrower on files touched (median 3.0 vs 2.5), which the rule required, but was better-targeted (out-of-scope 0.484 vs 0.500) and closed far more findings (**median 7.5 vs 0.0**, positive in 5/6 pairs, best +78). Two generic runs made their codebase measurably worse (an earlier revision of this entry said three, miscounting a bounded −1 as generic). The registered rule braced for generic thrashing; what showed up was generic *timidity* — so the bounded prompt's measured value in this test is effectiveness, not narrowness. Limits stated with the result, including that findings-closed is this tool's own ruler and the bounded prompt names what the ruler measures. Every arm re-derived against pinned bases after an audit; zero mismatches. See `docs/studies.md` "Does the bounded prompt work?" and `tools/experiments/fix_scope/`.

### Measured — fix breadth: a direction that did not survive pinning

- **feat(study): fix-commit breadth, per cohort — reported as an exploratory trend, after its first significance failed to replicate.** "Broad rewrites for narrow bugs" is a diff property, so `tools/calibration/measure_fix_breadth.py` measures it from history: files and lines touched per fix-labeled non-merge commit. A first run over unpinned caches showed nominally significant gaps and was briefly described as "the first signal to survive the controls"; an audit correctly noted the histories were not reproducible from pinned inputs, and the pinned re-run — per-repo commit and actual history depth now recorded in `fix_breadth.json`, size-banding computed by the script rather than by hand — keeps the direction (AI-assisted median 3 vs 2 files per fix, 21% vs 13% broad); a later deterministic-window respecification (`git log -n 300` from each pinned HEAD) lands nominally under 0.05 again (banded 0.029/0.046/0.037) — three specifications straddling the threshold is fragility by demonstration, and none survives Holm (0.0167). Three correlated outcomes, no registered primary, repo-level rather than commit-level authorship, and subject-line fix detection that agents satisfy far more often than humans (19/20 vs 11/18 repos): the claim is downgraded to *a consistent direction worth a better-designed study*, and nothing more.
- **docs(philosophy): "Why AI-Specific?" rewritten — volume, not pathology.** The page asserted five recognizably-AI failure modes; the one tested did not survive its control, and decades of hand-written unmaintainable code say slop needed no AI to exist. What AI changes is the *rate*: code arrives faster than it can be read. The same volume makes the fix loop viable — deterministic findings, one uniform standard, bounded prompts — which needs no claim that AI writes worse code, only that it writes more.

### Added

- **feat(scoring): the score is now a full rubric — 13 aspects, explicit weights, honest unknowns.** A hostile audit demonstrated the previous score's worst property with one input: a 100-file repository with **zero test files** scored **5.0/A+ with testability 5.0**, because every category was a re-weighting of five structural pressures and nothing ever asked whether a test existed — and the test suite blessed it. The overall is now a three-layer rollup defined in one place (`_formula.py`): thirteen **aspect scores** (five corpus-calibrated structural pressures; eight rubric-banded evidence scores — test presence, dead code, near-duplication, idiom consistency, churn hotspots, code-to-code change coupling, knowledge concentration, documentation) → ISO categories as weighted means → overall as their equal-weighted mean. Every weight and band is data, printed in the report (`score.aspects`, `score.rubric`) and documented in `docs/standard.md`. An unmeasurable aspect scores `null` and its weight renormalizes — a shallow clone must not grade as either clean or dirty — and the five aspects the tool cannot measure at all (test effectiveness, naming, comment accuracy, indirection, architectural coherence) are named in every report as unscored, with reasons. **A repository with production code and zero test files can no longer receive an A-grade**; its testability caps at 2.0 and the blocker says why. `CALIBRATION_C` re-fitted through the new pipeline by bisection (3.5466 → 2.966); the corpus median still rolls up to exactly 4.0. The rubric is a **standard**: judgments made explicit, deterministic, and applied identically to every repository — which is what every standard is, ISO/IEC 25010 included, and needs no apology. Empirical claims about the world are the thing held to an evidence bar (see *Retracted*, below). An outcome study specified in `docs/standard.md` would *tune* the weights against measured change effort; it has not been run.
- **fix(self): this repo now opts into its own gates, and its README stops lying.** The same audit caught that making threshold gates opt-in had silently neutered `--fail-on-gate` for this repository's CI, and that the README advertised a stale 5.0/A+ while a fresh run said 4.8/B with warnings. All three threshold gates are now `true` in `maintainability-agent.json` (the two live failures they exposed were fixed: a measurement-data JSON excluded from line audits, one function refactored under the ceiling), and the README table now states the current 4.8/B and names the audit that caught the stale claim.
- **feat(history): churn, hotspots and change coupling from the repo's own log.** Every other metric here is a photograph of the code as it stands; maintainability is defined (ISO/IEC 25010) as the effort to *modify*, and effort is paid per change — so a 600-line file untouched for three years and a 600-line file edited weekly scored identically, when only one is costing anything. The report now carries: per-file **churn** (commits, lines, authors) over a 12-month window; **hotspots**, churn multiplied by the file's summed cognitive complexity, so a file ranks only by being both hard to read and constantly read; and **change coupling**, pairs of files that co-change in most of their commits — the shape of a boundary drawn in the wrong place, invisible to every static metric in the package. Merges are excluded (their numstat double-counts the branch), sweep commits (>30 files) are excluded from coupling by raw commit size, rename notation is resolved including multi-segment and empty-side forms, and a shallow clone reports `history: null` rather than zeros, because "no history" and "no changes" are opposite findings. **Reported, not scored** — these have not been validated against an outcome, and unvalidated signals no longer move grades here.

### Changed

- **feat(calibration): the corpus is selected mechanically — 14 repositories to 40.** The old corpus was fourteen projects picked because the author knew them, which is selection bias sitting directly underneath a scale used to grade other people's code. `tools/calibration/select_corpus.py` now issues a GitHub search anyone can re-run — `stars:>3000 created:<2021-01-01 pushed:>2026-01-01` across Python, TypeScript and JavaScript — and `tools/calibration/verify_corpus.py` clones each candidate and keeps only those holding 20+ source files and 100+ declarations, pinning each to the commit measured. The result spans **32 to 18,789 source files and 463,581 declarations**. Seven candidates were rejected on contents rather than on name (`PayloadsAllTheThings`, 33 declarations; `airbnb/javascript`, 14), and the rejections are recorded in `corpus.json` rather than silently dropped.
- **`created:<2021-01-01` is load-bearing.** This corpus is the human-written baseline against which AI-assisted code is compared, and today's most-starred repositories include projects begun well into the LLM era. Admitting those would answer the question before measuring it.
- **the constants moved, and the direction is not uniform:**

  |dimension|0.6.x (14 hand-picked)|now (40 queried)|
  |---|---|---|
  |file_size|0.0779|0.0576|
  |declarations|0.0243|0.0599|
  |duplication|1.4659|3.7350|
  |risk|0.0546|0.0726|
  |`CALIBRATION_C`|5.2754|3.5466|

  **Duplication is 2.5x more lenient**: identical code that scored `5.0x` now scores `2.0x`. The hand-picked corpus was almost entirely libraries, which are built for reuse and have had years of review pressure to remove repetition; sorting by stars also returns applications and tools (n8n, excalidraw, playwright, transformers), which carry far more. The queried corpus describes *widely-used code* rather than *well-factored libraries* — the more honest reference for a tool that grades arbitrary repositories, but the bar is now set by a population that includes application code.
- **excluded one repository on what it is, not on how it scored.** `33-js-concepts` cleared verification — an `index.js` plus thirty concept-demo test files is enough declarations to look like a codebase — and landed as the corpus outlier on duplication (38.8x the median) and file size (3x the next repo), because parallel teaching examples are supposed to repeat. It is excluded as a teaching repo, alongside the tutorials and courses the name filter already removed. The distinction matters: filtering a corpus by its own measurements manufactures whatever reference the filter was aimed at. Removing it moved `c` 3.5724 → 3.5466, which is what a median is for.
- **fix(gates): the file, function and duplicate-block gates are opt-in.** Measured across the corpus these fired on **every single repository** — duplicate counts of 33 to 5,325 against a default `max_duplicate_blocks` of 20 — so `--fail-on-gate` failed everywhere out of the box. A gate that always fails is not a gate; it trains people to pass the flag and ignore the result, and it gave the gates dimension zero variance. `fail_on_file_failures`, `fail_on_function_failures` and `fail_on_duplicate_blocks` now default to `false`. **The findings are still reported** — only whether they block CI changed, and a repo opts in to that.
- **the gates reference is now fixed at 0.05 rather than corpus-derived.** Hard gates are discrete policy breaches a repository opts into, not a rate drawn from a population. Once gating became opt-in the corpus median went to zero, and dividing by zero would have made the dimension silently ignore real failures. One gate failure now reads as `1.0x`. `scoring._relative` reports `0.0` for any zero reference instead of dividing.
- **fix(config): vendored third-party code is excluded by default.** `vendor/`, `third_party/`, `*.min.js` and friends. Auditing vendored code measures someone else's decisions, and — worse for a reference corpus — constants drawn from a population containing it describe bundles rather than maintained source. **lodash's corpus entry was 41% vendored.**
- **fix(metrics): the README gate accepts any README.** It required `README.md` exactly, so Django — which ships `README.rst` — was reported as having none. That is the class of finding that teaches people the tool does not know what it is looking at.

## 0.6.1 - 2026-08-08

Release plumbing and a performance consolidation. No behaviour changes.

- **feat(ci): PyPI publishing is automated on tag push, via Trusted Publishing.** `.github/workflows/release.yml` verifies the tag matches the packaged version *before* building — a mismatch would publish the wrong code under the right name, and PyPI uploads cannot be replaced — then builds, runs `twine check`, installs the wheel, runs the suite and the tool's own `--fail-on-gate` audit against the built artifact, and only then publishes. Authentication is OIDC: GitHub mints a short-lived token scoped to this workflow in this repository. **There is no API token in repository secrets**, so there is nothing to leak and nothing to expire — which is exactly what took the SonarQube scan down for three months.
- **perf: each file is read once and parsed once per audit.** Five scanners each needed the same lines and the same declarations and each computed them independently, so an audit read every file five times and parsed every source file three times. `SourceIndex` holds both for the life of one audit. On Django (3,153 files, 529 KLOC): **10.4s → 8.5s for +27MB**, 18% faster for 8% more memory. The headline number is modest; the point is that cost no longer scales with the number of scanners — a sixth now costs no additional reads. Deliberately not a global or decorator cache, so a long-lived process does not accumulate every file it has ever seen and a re-audit sees current content.
- **fix(config): this repo's own config now excludes build artifacts.** `maintainability-agent.json` overrides `exclude_patterns` wholesale, and unlike the shipped defaults it omitted `build/` and `dist/`. `python -m build` leaves `build/lib/maintainability_audit/` — an exact copy of every source file — so the audit reported the whole codebase as duplicated and `max_duplicate_blocks: 0` failed the gate. Caught by the release workflow on its first real run, which is what that step is for. Note the general lesson for any config: overriding `exclude_patterns` replaces the defaults rather than extending them.
- **tests:** +8 in `tests/test_source_index.py` pinning that the work is genuinely shared, that a shared index never changes a result, and that every scanner still runs standalone.

## 0.6.0 - 2026-08-08

Adds four Tier-1 signals aimed directly at the "AI writes code humans cannot maintain" criticism. Reported as findings; deliberately not yet scored. No breaking changes.

- **feat(similarity): near-duplicate declaration detection — a helper written twice under two names.** The most-cited empirical complaint about AI-written code is clone-instead-of-reuse: an agent that cannot see your existing helper writes a second one, the copies drift, and a bug fixed in one survives in the others. Exact text matching cannot catch it, because the second copy is the same *structure* with different identifiers. Declaration bodies are now reduced to a token sequence with identifiers anonymized by order of first appearance (Python via stdlib `tokenize`, C-family via a regex over the `_masking`-scrubbed source), compared as sets of 6-token shingles by Jaccard similarity, and reported at or above 0.8. An inverted shingle index keeps the comparison linear enough to audit Django (3,153 files) in 7.5s.
- **feat(prompts): the finding names the declaration to reuse.** This is the one finding that ships with its own fix. "There is duplication" is not actionable; "`toAtomicAmount` at `TradeTicket.tsx:862` already does this" is. Cross-file pairs lead, since those are the ones written without knowing the first existed. The prompt also tells the agent *not* to merge two functions that merely look alike but would need to change for different reasons.
- **measured:** production cross-file near-duplication, as a share of eligible declarations, across the reference corpus — mature human-written OSS **median 0.20%, max 2.15%** (n=12); AI-written applications **median 1.49%, max 12.05%** (n=6). Three of the AI repositories exceed every repository in the OSS corpus. This is the first signal measured here that separates the two populations: on file size, declaration size and complexity they are statistically indistinguishable. The confounds are real and documented — the OSS corpus is libraries, the AI cohort is applications, and both samples are small.
- **not scored, deliberately.** Most repositories sit at zero, so a median-based reference would be unstable: dividing by ~0.002 turns a rounding difference into a large multiple. Signals earn a place in the score by holding up across more repositories, not by being new.
- **fitted, not guessed:** the eligibility thresholds (80 normalized tokens, 2+ control-flow tokens) were tuned against the corpus to remove two false-positive classes it exposed — bodies too short for similarity to mean anything, and thin delegations whose shape is dictated by the API surface rather than by what they do (requests' `put`/`patch`, flask's `template_filter`/`template_test`). Test files are excluded: in mature projects nearly every near-duplicate is a deliberately parallel test variant, which is not the defect being measured.
- **feat(cognitive): cognitive complexity — nesting-weighted reading cost.** The cyclomatic figure is a keyword tally and is blind to nesting: five sequential guard clauses and five levels of nesting both scored 6, though one is read a line at a time and the other must be held in the head at once. Each flow break is now charged *plus the depth it sits at*, so nesting compounds — that pair now scores 5 and 15. `else` and `elif` are charged flat rather than nested (they resolve a decision already being tracked), and a run of boolean operators counts once, because `a and b and c` is one idea to read. Python is exact from the AST; C-family nesting is inferred from brace depth over the masked source, which under-reports on brace-free bodies — the safe direction. Reported beside the branch count rather than replacing it: a function can be low in one and high in the other, and that difference is the point.
- **feat(config): `max_cognitive_complexity` (25) and `warn_cognitive_complexity` (15).** Fitted against **21,300 declarations** in the reference corpus (p50 = 1, p90 = 9, p95 = 17, p99 = 49): warning at 15 flags 5.5% of declarations, failing at 25 flags 2.7% — comparable hit rates to the existing file thresholds. Configs omitting both keys are unaffected, so no existing repo starts failing on a metric it never opted into.
- **chore(calibration): constants re-fitted after the threshold change.** Adding a threshold changes what counts as a finding, which moves the declarations reference — this is precisely the case `tools/calibration/measure.py` exists for. It reported the drift, the corpus was re-measured, and `declarations` moved 0.0233 → 0.0243 with `CALIBRATION_C` 5.2318 → 5.2754. Small, because the new threshold flags only a modest additional tail in mature code.
- **feat(deadcode): unreferenced private declarations.** Agents leave debris — a helper written for an approach abandoned two prompts later, still compiling, tested by nothing. Naive "no callers" scanning reports a library's entire public surface, so only declarations the language marks internal are candidates: a leading underscore in Python, no `export` in JS/TS. Privacy is the load-bearing assumption — it is the author's own claim that no external caller exists, which is what makes "no references in this repo" sufficient. Decorated declarations, dunder methods and test files are excluded. The prompt lists them as deletion candidates while telling the agent to confirm each one, because a name reached only through dynamic dispatch is indistinguishable from a dead one here.
- **fixed two false-positive classes found on first contact with the corpus.** Counting identifiers over the comment/string-masked copy blanked **f-string interpolations, which are live code** — flask's `_get_werkzeug_version` is called from inside one and was reported dead; counting now runs over raw source, which errs toward hiding a dead function rather than inventing one. And an **object-literal method** (`beforeBreadcrumb(crumb) { … }` in a Sentry config) binds no name and is invoked by whoever receives the object, so C-family candidates must now bind a name. Together these dropped one repo from 15 findings to 0. Both are pinned by regression tests.
- **measured, and reported honestly:** the rate barely separates the cohorts — mature OSS median 0.0% (max 0.55%), AI-written median 0.14% (max 1.53%). Unlike near-duplication this is *not* evidence about AI-written code; it earns its place as hygiene. Findings-only, not scored.
- **feat(idioms): competing libraries for one concern.** Three HTTP clients means three error shapes, three retry stories, three sets of behaviour to learn. The cost is not duplication — each call site may be fine — it is that no single mental model covers the codebase, which is the signature of independent generation: every answer locally reasonable, nothing reconciling them. Detected from imports across production source, grouped by concern.
- **this one needs a curated list, and the changelog should say so.** There is no structural way to know that `moment` and `date-fns` compete while `react` and `react-dom` do not — it requires knowing what the packages do. The shipped list is deliberately small (HTTP clients, date handling, client state, schema validation, ORMs, web frameworks), restricted to alternatives that are well known and change slowly, and **incomplete by construction**. `idiom_groups` in config replaces it wholesale.
- **its first corpus run produced *only* false positives**, both now pinned by tests. A package named in a fenced code block inside a Markdown document counted as an import — two of three findings on one repo came from documentation prose. And `black` was reported as running two HTTP clients when one was `aiohttp` in the `blackd` daemon and the other `urllib3` in a CI helper under `scripts/`: separate programs sharing a repository, not one codebase with two mental models. Non-source files and standalone script directories are now excluded, alongside tests and the repository's own package.
- **measured:** after those fixes it reports **nothing across all 14 corpus repositories** and fires once, correctly, on a repo running `aiohttp` in 27 service files and `httpx` in 3 — with two files importing both. High precision, low recall, and quiet by design: silence means "nothing recognised", never "nothing wrong".
- **tests:** +40 across `tests/test_near_duplicates.py`, `tests/test_cognitive_complexity.py`, `tests/test_dead_code.py` and `tests/test_idiom_divergence.py`, covering renamed-copy detection, comment/string immunity, both false-positive classes, the reporting shape, nesting compounding, and back-compatibility for configs without the new thresholds. One caught a spec error of mine: I had asserted each declaration appears in at most one pair, when the useful behaviour for N copies is N-1 pairs all referencing a single original — one instruction to reuse it, rather than a clique.
- **dogfood:** self-audit holds at **5.0 / 5 (A+)** across 69 files, with zero near-duplicates, zero unreferenced private declarations, and nothing over the new reading-cost threshold.

## 0.5.0 - 2026-08-07

The scoring engine was rebuilt after being measured against real code and found to be wrong. Config is unchanged; the shape of `report["score"]` gains fields.

- **fix(scoring): scores are rates, not counts — the old model was measuring repo size.** Findings were counted absolutely, so 20 oversized files cost the same in a 50-file project as in a 3,000-file one. Run against a corpus of mature open-source repositories, the 0.4.0 model scored **Django, pytest, black, tornado, click, httpx, attrs, lodash, svelte, axios and fastapi all at 0.0 / F**, while a 53-file toy repo scored 4.6 / A. Above roughly a 3% file-warning rate every repo pinned to the floor, so the scale could not distinguish a mediocre codebase from a catastrophic one — and a tool that grades Django unmaintainable cannot be used to argue anything about code quality. Every pressure is now a finding count divided by the population it was drawn from.
- **fix(scoring): each dimension is normalized against what real code actually carries.** Raw pressures live on wildly different scales — measured across the corpus, duplication runs ~15x file-size pressure and ~93x declaration pressure — so summing them raw scored duplication and essentially nothing else. Each is divided by its own corpus median, and `score["dimensions"]` now reports multiples where **1.0x is typical real-world code**. The curve is hyperbolic and fitted so the corpus median scores exactly 4.0: a well-run real codebase earns a B.
- **feat(scoring): A+ is gated, not averaged.** A mean lets a repo hide one bad dimension behind four good ones. The top two grades now additionally require every dimension to be clean, and demotion cascades — a repo denied A+ must still satisfy A's ceilings to receive an A, so a single hard-gate failure disqualifies both. `score["grade_blockers"]` names the specific measurement that capped the grade.
- **feat(prompts): the remediation prompt leads with the dimension costing the most.** A letter grade is not actionable; `duplication at 4.4x` is. The prompt now lists only elevated dimensions (>1.0x), names the worst one as the starting point, and explicitly tells the agent to prefer leaving a repo alone over manufacturing work when nothing is elevated. This is the point of the score — it exists to aim the prompt.
- **refactor:** `_calibration.py` holds the fitted constants apart from the scoring logic, since they are empirical findings with provenance rather than tunable knobs; `prompts.py` splits agent-facing output from human-facing rendering (`sarif.py` no longer reaches through the markdown renderer).
- **tests:** +10 in `tests/test_scoring_calibration.py` pinning the properties the old model violated — size independence, non-saturation, corpus calibration, and gated top grades. One of them caught a real bug during development: demotion stepped down exactly one grade without re-checking, letting a hard-gate failure land on an A.
- **feat(calibration): the reference corpus is checked in, pinned, and reproducible.** `tools/calibration/corpus.json` names 14 mature OSS repositories at exact commits (52 to 4,034 files, Python and JS/TS); `tools/calibration/measure.py` clones them at those commits, measures, and reports drift against the stored constants (`--check` exits 1 when stale). The derivation from measurements to constants is pure arithmetic in `_derive.py`, and `tests/test_calibration_corpus.py` re-runs it **offline** from the checked-in `measurements.json` — no clone, no network — so a hand-edited constant or an unwritten re-measurement fails the suite. Constants that cannot be re-derived are exactly the unfalsifiable claim this release exists to stop making.
- **fix(calibration): references re-fitted on the full 14-repo corpus.** The initial constants came from an 11-repo subset that omitted django, fastapi and svelte. Adding them moved the file-size reference from 0.1233 to 0.0779 — a 37% shift, because large repos carry proportionally *less* file-size pressure than small ones. A small-repo-only corpus would have re-introduced the very size bias this release removed.
- **known limits:** these remain structural proxies. They say nothing about naming, comment accuracy, architectural coherence, or whether a reader can build a correct mental model. The corpus is finite — recalibrate `DIMENSION_REFERENCES` whenever the default thresholds change.
- **dogfood:** self-audit holds at **5.0 / 5 (A+)** across 57 files under the new engine, with the A+ gate satisfied on every dimension.

## 0.4.0 - 2026-08-06

Bug-fix release for TypeScript/JavaScript function detection, plus two threshold corrections. Config gains two optional keys; no breaking changes.

- **fix(metrics): JS/TS/HTML declarations are bounded by their own braces, not by the next regex match.** `_regex_function_ranges` ended every declaration at "next match minus one", which is only safe if the pattern list matches *every* declaration in the file. It didn't — `export function`, generic signatures (`async function request<T>(`), and object/class methods were all invisible — so the first recognised declaration absorbed everything up to the next match or to end-of-file. On a downstream TypeScript repo a 4-line `csrfToken()` was reported as **262 lines / complexity 35** and the clean file it lived in was graded an F; **all 18** function findings on that repo were false. New `_ranges.js_declaration_ranges` walks brace/paren depth over a `_masking`-scrubbed copy of the source (comments and string/template literals blanked), so an unrecognised declaration now costs one *missed* finding instead of a cascade of false ones. Unresolvable bodies fall back to `indent_bounded_end`, which the plain regex detector now uses too — the old "run to end-of-file" fallback is gone everywhere.
- **fix(metrics): complexity for JS/TS/HTML is scored against code only.** `if` in a doc comment and `?` in a URL string are no longer counted as branches.
- **fix(metrics): classes are graded on `max_class_lines` / `warn_class_lines` (new, default 300/200), on length alone.** A class was being judged against `max_function_lines`, so an ordinary six-method class was reported as an over-long "function"; and because `ast.walk` yields a class *and* each of its methods, its complexity was the sum of branches already charged to those methods. `FunctionMetric` gains a `kind` field (`"function"` / `"class"`), carried into the JSON report.
- **fix(renderers): a flagged class now reads as a class in every output.** Storing `kind` is not enough — a class printed unlabelled under a "Function Hotspots" heading, beside a complexity number, reproduces the misreading the field exists to prevent. The markdown table's `Function` column is now `Declaration`; a class is rendered `` `ScanWorker` (class) `` in the report, remediation prompt, PR comment, and SARIF message, and its complexity cell is `-` because that figure is a double count and nothing is graded against it. New `_hotspots.py` holds this phrasing so `sarif.py` no longer imports the markdown renderer. Reports and baselines written before 0.4.0 carry no `kind`; its absence is read as `"function"`.
- **fix(config): `migrations/` is excluded by default.** A 102-line, complexity-2 `upgrade()` is what a correct migration looks like. Migrations are append-only history; refactoring one rewrites the past.
- **tests:** +23 regression tests across `tests/test_declaration_ranges.py` (brace bounding, `export function`, generics, object-literal methods, class methods and field arrows, callbacks vs. methods, control-flow keywords, comment/string/template noise, inline object return types, multi-line parameter lists, runaway expression bodies, unclosed braces, inline HTML `<script>`) and `tests/test_declaration_grading.py` (indentation-bounded fallback, class thresholds, migration exclusion, and how a flagged class is worded in each renderer). New modules are at 100% coverage; suite total 98% over 61 tests.
- **refactor: `metrics.py` (426 lines) split along its actual responsibilities.** It had accumulated four jobs. Now: `metrics` walks the repo (which files count, how big, what gates trip), `declarations` measures and grades what's inside a file, `duplication` compares files against each other, and `report` assembles the JSON every renderer consumes. The graph is acyclic — the upper three import `metrics`, which imports none of them. `build_report` moved to `report`; `cli` and the package entry points are unchanged, but a direct `from maintainability_audit.metrics import build_report` now needs `.report`. `tests/test_audit_components.py` and `tests/test_declaration_ranges.py` were split to match the modules they exercise.
- **docs:** new [docs/language-support.md](docs/language-support.md) states per-language accuracy, the deliberate under-report bias, and every known limitation. README trimmed of content that duplicated `CONTRIBUTING.md`.
- **dogfood:** self-audit scores **5.0 / 5 (A+)** across 54 files — zero warnings, zero failures, zero duplicates, zero risk findings, zero hard gates, all five ISO/IEC 25010 categories at 5.0. This is the output of the refactor above, not a claim that preceded it: the fix work alone landed the repo at 4.4 / 5 (B) with four files past the 250-line warn threshold, and the README was still advertising a stale 5.0 from v0.1.0. Shipping a false-positive fix while publishing an inaccurate grade would have been the same failure mode the release exists to correct.

## 0.3.0 - 2026-05-23

Bug-fix release. Three independent false-positive sources observed during a downstream audit are eliminated; no breaking config changes.

- **fix(metrics): use `ast.end_lineno` for Python function/class line counts.** The detector previously computed the end of a function as "next sibling start − 1" (with end-of-file as the fallback), so a 4-line `Enum` followed by 300 lines of unrelated code reported 321 lines / complexity 23. Short Python functions and classes now report their actual indented body length. Non-Python files keep the regex fallback. `async def` is also detected now (the regex never matched it). New helpers: `_python_function_ranges`, `_regex_function_ranges` in `metrics.py`.
- **fix(scoring): testability/analyzability no longer punish test-only function pressure.** Refactoring duplicate test boilerplate into a shared fixture used to drop testability 0.9 → 0.4 and analyzability 0.7 → 0.3 even though the same assertions still passed. The summary now exposes `production_file_failures` / `production_function_failures` / `production_hard_gate_failures` (plus their warning + test-side counterparts), and `scoring.score_report` uses the production-only pressure for `testability` and `analyzability`. `modularity`, `reusability`, and `modifiability` keep their original combined-pressure formulas. New helper: `is_test_path` in `metrics.py`.
- **fix(metrics): duplicate-block detector skips low-information lines.** Five-line column-name lists collided between an INSERT column tuple and a function's keyword-argument signature, even though that shared ordering IS the architectural contract. Blocks made entirely of bare identifiers (e.g. `name,`), simple kwarg passthroughs (`x=x,`), or pure punctuation are now ignored. Real cross-file code duplication still surfaces (covered by a new regression test).
- **refactor(metrics):** extract `_compute_gates_and_summary`, `_function_hotspots`, `_count_status`, `_split_by_test_path` so the main `build_report` and `report_summary` stay inside the self-audit complexity threshold after the new logic lands.
- **tests:** +10 regression tests in `tests/test_audit_components.py` covering the three bugs (Enum-after-300-lines, single-return-then-def, empty-class-then-long-func, async def, fallback-on-SyntaxError, identifier-list dup skipping, real duplication still flagged, test-only function failure not dropping testability/analyzability, production/test summary split).
- **dogfood:** self-audit on this repo post-fix scores **4.6 / 5 (A)** under the project's strict local config (zero function failures, zero hard gates, 98% coverage).

## 0.2.0 - 2026-05-12

- Adds a portable invokable skill under `skills/maintainability-agent/` that drops into Codex, Claude Code, and GitHub Copilot Chat so `/maintainability-agent` is one keystroke away in any of them.
- Adds per-host adapters: `agents/openai.yaml` (Codex, already present), `agents/anthropic.yaml` (Claude Code install paths), `agents/copilot.yaml` (Copilot prompt-file source/destination).
- Adds `copilot/maintainability-agent.prompt.md` — VS Code Copilot Chat prompt file shaped for Copilot's prompt-file frontmatter; reuses the SKILL.md body verbatim.
- Documents the new install paths in README ("Invokable Skill / Slash Command" section + 5th bullet in the feature list).
- Updates SKILL.md description so Claude's relevance ranker fires correctly while staying valid for Codex.

## 0.1.0 - 2026-05-11

- Initial local implementation of deterministic maintainability auditing.
- Adds Markdown, JSON, SARIF, PR comment, baseline, and AI remediation prompt outputs.
- Adds model/tool-specific instruction generation for Claude Code, Codex, Cursor, Copilot, Windsurf, and generic agents.
- Adds 92% coverage gating, `coverage.xml` output, SonarQube Cloud starter config, and external quality-tool readiness docs.
- Self-audit on this codebase: **5.0 / 5 (A+)**, zero warnings across every category. Checked in at [docs/self-audit.md](docs/self-audit.md).

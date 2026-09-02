# Retrospective audit: v0.9.1 → v1.7.0

**Scope.** 104 commits, 267 files, +30,006 / −3,475 lines, spanning v1.0.0,
v1.0.1 and the language increments 1.1.0 (C), 1.2.0 (C++), 1.3.0 (C#),
1.4.0 (Fortran), 1.5.0 (fortitude adapter), 1.5.1 (docs), 1.6.0 (Fortran
measurement + fixed-form), 1.7.0 (Fortran practice detection).

**Benchmark.** `docs/product-intent.md` (governing), `docs/architecture.md`
(layers, 12 rules, invariants, known debt), `docs/decisions.md` (canonical
for decision status).

**Method.** Read the benchmark documents first. Ran the tool on itself with
the analyzer pool. Verified promises P1–P8 where this window could have
broken them. Mutation-tested five of the shipped fixes by reverting each
and confirming its tests fail. Compared documented claims against shipped
reality. No diff-slicing: findings are at the level of a claim, a promise
or a mechanism, not a line.

---

## Verdict

**The code is in good shape. The paperwork is not, and one measurement
assumption is undisclosed.**

The self-audit reports 4.1 / 5, verified grade **B**, **evidence complete**,
and **zero** file failures, function failures, duplicate blocks, risk
findings and hard gates across 402 files. Layering and acyclicity hold
under 13 property tests after 104 commits. Coverage is 94.72%, with every
module added in this window between 87% and 100%.

Five findings follow. Two are documents that now contradict the product,
one is a disclosure gap that affects every score issued for four of the
seven claimed languages, and two concern the strength of verification
rather than the correctness of code.

---

## F1 — The calibration corpus contains none of four claimed languages *(High)*

**Evidence.** `tools/calibration/corpus.json` is 40 repositories: **12
JavaScript, 15 TypeScript, 13 Python**. Zero Java, C, C++, C# or Fortran.
Every score is normalised against `DIMENSION_REFERENCES`, which are medians
over that corpus.

Measured consequence, from the two Fortran audits run this week:

| Dimension | stdlib | LAPACK | anchored to |
|---|---|---|---|
| declarations | 1.10x | **7.18x** | median of 40 JS/TS/Python repos |
| duplication | 0.93x | 2.84x | same |
| file_size | 0.84x | 2.05x | same |

`docs/standard.md:121` does disclose the corpus composition — "across
Python, TypeScript and JavaScript" — so this is not a concealed fact. What
is missing is the **consequence at the point of use**. A LAPACK maintainer
reading "7.18x the median" and "the corpus median lands at 4.0 (B): a
well-run real codebase earns a B" would reasonably infer the comparison set
includes code like theirs. It does not. Long, deeply-looped numerical
subroutines are idiomatic in dense linear algebra and absent from the
anchor.

This is not a P2 violation — the rubric is uniform, and uniformity is the
promise. It is the shape the intent document names as this project's one
committed failure: *a claim outrunning its evidence tier*, here by silence
rather than by assertion.

**Recommendation.** Two changes, one now and one planned.
1. Name the limit where the number is read: the report's reference section
   and `docs/standard.md` should state that references derive from a
   JS/TS/Python corpus and that Java, C, C++, C# and Fortran are scored
   against it.
2. Plan a corpus extension. Note the cost honestly: adding non-web
   languages will move `CALIBRATION_C` and re-grade every repository, so it
   is a deliberate release, not a patch.

**Do not** fix this with per-language references. That would trade a stated
limit for a silent violation of P2.

---

## F2 — The decision register contradicts what shipped *(High)*

`docs/architecture.md` names `decisions.md` canonical for decision status.
Three passages there are now false:

1. **ADR 006 status line:** *"Java has a built-in range fallback; **we will
   not write more range detectors** for Go/C/C++/C#/Rust."* Four were
   written: C (1.1.0), C++ (1.2.0), C# (1.3.0), Fortran (1.4.0), plus
   fixed-form Fortran (1.6.0).
2. **"v1.0's declaration languages are Python, Java, JS, TS, JSX and
   HTML"** — now seven languages.
3. **"languages nothing here reads yet: Go, Rust, C, C# and Fortran, which
   are absent from the default extensions"** — C, C# and Fortran are in the
   default extensions and are read.

The architecture document *was* amended ("The 2026-08 wording here said
there would be no further scanners; the C++ and C# increments amend it").
The register was not, so the two now disagree, and the register is the one
the architecture document points readers to.

**Recommendation.** Amend the three passages with the same explicit
"this was the wording, here is what changed it" form already used in
`architecture.md`. Do not silently rewrite them — the register's value is
that it records what was decided *and* what overturned it.

**Positive worth recording:** the cadence the register promised — *"one
adapter per release, not as a batch"*, recorded as Marshall's own reason —
was honoured exactly: 1.1.0 C, 1.2.0 C++, 1.3.0 C#, 1.4.0 Fortran.

---

## F3 — The falsifier gate did not cover the largest body of work *(Medium)*

`tools/prove_falsifiers.py` exists precisely because "an agent is in
control of both the code and its test". It triggers on two things: register
entries added in the diff that cite closing tests, and newly added
`tests/*_class.py` files.

The language increments used **neither**. Roughly 300 tests across
`test_c_declarations.py`, `test_cpp_declarations.py`,
`test_csharp_declarations.py`, `test_fortran_declarations.py`,
`test_fixed_form_fortran.py`, `test_fortran_metrics.py`,
`test_fortran_practice.py`, `test_language_coverage.py` and
`test_readme_claims.py` were merged without the gate ever proving one of
them fails without its fix.

**I ran that proof retroactively.** Five mutations, each reverting one
shipped fix while keeping its tests:

| Mutation | Assertion failures |
|---|---|
| `METRICS` table emptied (Fortran falls back to the C-family reading) | **5** |
| fortitude / fprettify / `fpm.toml` recognition removed | **2** |
| Fixed-form masker replaced by the free-form masker | **1** |
| Fortran 77 labelled-`DO` tracking removed | **3** |
| `fortran` removed from lizard's catalog languages | **1** |

All five are genuinely falsified, with real assertion failures rather than
import errors. The work is sound; the *gate* did not know about it.

**Recommendation.** Either add register entries for the language increments
citing their closing tests, which is what the gate reads, or widen
`prove_falsifiers.py` to revert-prove added test files generally. The
second is more honest about how work now arrives.

---

## F4 — Fixed-form test strength is narrower than it reads *(Medium)*

`tests/test_fixed_form_fortran.py` carries eight behavioural tests. Under
the mutation that bypasses the card-column masker, **one** fails — the
continuation case. Under the labelled-`DO` mutation, three fail.

The remaining tests are true but not discriminating: `C` in column 1,
sequence numbers in columns 73+, and statement labels all produce the same
result whether or not fixed-form rules are applied, because the free-form
recogniser does not match those shapes either. They are defensive, not
load-bearing.

That is acceptable — but the file's docstring implies stronger coverage
than the tests deliver, and this project already has vocabulary for the
distinction: `architecture.md` grades every invariant **Property** or
**Regression**.

**Recommendation.** Say which they are, or add one case where column-72
truncation is load-bearing. Not urgent; the load-bearing behaviours are
covered.

---

## F5 — Stale known-debt text *(Low)*

`docs/architecture.md:269`: *"Declaration extraction is gated on
`DECLARATION_SUFFIXES` (Python, JS/TS/HTML, and Java)"* — missing C, C++,
C# and both Fortran forms. In the same section, "**Both** suffix sets" and
"**Neither** invents a bounding rule" describe two languages where there
are now six.

**Recommendation.** Mechanical correction.

---

## What held up

Reported because an audit that lists only failures is not a measurement.

- **The architecture absorbed six languages without deforming.** Adding a
  language is a module and a row in `declarations.SCANNERS`. Layering and
  acyclicity pass 13 property tests over the real import graph; no cycle was
  introduced across 104 commits.
- **The shared walk stayed shared.** `scan_bounded` took two new parameters
  (`find_end`, `mask`) and every prior language's suite passed unchanged —
  which is how the generalisations were shown to be behaviour-preserving.
  jscpd reports **0 duplicate blocks** across six sibling scanner modules.
- **The guards added in this window immediately caught real regressions.**
  The README language-table guard failed the moment it existed (JS/TS named
  no suffixes; Fortran omitted three spellings). The analyzer-coverage lint
  failed on the stale lizard row. Both were written, then watched to fail.
- **"One setup, three transports" is intact.** No diff to `_first_run`,
  `_mcp_setup` or `_setup_persist` across the whole window; the question set
  did not drift while seven releases shipped.
- **The tool held its own line.** Four pieces of code written in this window
  tripped its own gates — two files over the length budget, two functions
  over cognitive complexity — and each was split rather than shaved. The
  self-audit ends at zero failures of every kind.
- **P7 and P8 behaved on unfamiliar input.** On both Fortran repositories
  the tool declined to issue a verified grade, named the five missing
  measurements, identified the shallow clone as the cause, and told the
  agent not to treat its own blind spot as a code defect.

---

## Recommended order

1. **F2** — correct the register. Cheapest, and it is the canonical
   document currently disagreeing with the product.
2. **F5** — correct the known-debt text. Same pass.
3. **F1(1)** — state the calibration limit where scores are read. This is a
   claim change; it needs your call, not mine.
4. **F3** — decide how the falsifier gate should reach work that arrives as
   feature increments rather than register entries.
5. **F1(2)** — plan the corpus extension as its own release, knowing it
   re-grades every repository.
6. **F4** — label or strengthen. Lowest value of the six.

Nothing here blocks a release. Nothing here is a code defect.

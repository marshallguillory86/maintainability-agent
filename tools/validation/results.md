# Report validation: what fourteen real repositories showed

Run against the [frame](sample-frame.md), committed before any repository was selected, and the [sample](sample.json), pinned to exact commits before any repository was cloned. Every number here comes from [`results.json`](results.json), produced by `tools/validation/run_sample.py`.

**The sample found the tool issuing scores for code it had never read, and the number was flattering.** curl reported 4.3 computed from its Markdown and Python test scripts while 20,547 declarations of C went unopened. That defect and five others are fixed, each with a test written before the fix, and the sample has been re-run against the result.

## The five pass criteria, judged

Stated in the frame before selection so the results could not be graded generously afterwards. **First run: three of five failed. After the fixes: all five pass**, with one limitation recorded below rather than fixed.

| # | Criterion | First run | Now |
|---|---|---|---|
| 1 | Completes on every repository, or reports why | **Pass** — 14 of 14, no crash, no hang | Pass |
| 2 | Findings are locatable | **Fail** — 3 of 40 sampled findings pointed at files that do not exist | Pass — cause fixed |
| 3 | Coverage is honest | **Fail** — the score came from a different file set than coverage described | Pass |
| 4 | The floor behaves | **Fail** — fired for the wrong reason on 5 repositories | Pass |
| 5 | Nothing is fabricated | Pass as process, **fail as substance** | Pass |

## The finding

`paths.include_extensions` defaulted to `.py .js .jsx .ts .tsx .html .css .md`. No `.c`, `.java`, `.go`, `.rs`, `.cpp`, `.cs`, `.f90`. The analyzer pool read those files perfectly well; the scan that produces the score did not.

| repo | language | analyzers read | score read from | reported |
|---|---|---|---|---|
| curl | C | 20,547 declarations | 1,041 (`.md`, `.py`) | **4.3** |
| whisper.cpp | C++ | — | 296 (`.js`, `.md`, `.html`, `.py`) | **3.5** |
| machinelearning-samples | C# | — | 162 files | **3.1** |
| gson | Java | 9,639 declarations | 0 | withheld: *"0 is below the calibration floor of 139"* |
| ripgrep, lapack | Rust, Fortran | — | 0 | withheld, same wording |

Two distinct failures. The first three **produced a number about a minority of a repository and presented it as a number about the repository** — flattering, because documentation and test scripts are simpler than the code they describe. The last three withheld correctly but blamed the repository's size; gson has 9,639 declarations.

This is the project's founding defect in its most complete form. Every earlier instance was a *count* absent and read as zero. This is the **population** being absent.

**Why six audit rounds missed it.** The calibration corpus is Python, TypeScript and JavaScript **by selection**. The defect is invisible on every repository the tool had ever been measured against.

## After the fixes

Same fourteen repositories, same pinned commits, run against everything built since:

| repo | estimate | practice | generated | vendored | work items |
|---|---:|---:|---:|---:|---:|
| babel | 4.4 | 3 | 15 | 0 | 188 |
| click | 4.3 | 3 | 0 | 0 | 41 |
| requests | 4.1 | 3 | 0 | 0 | 35 |
| date-fns | 4.0 | 3 | 0 | 0 | 88 |
| formik | 4.0 | 2 | 0 | 0 | 45 |
| curl | withheld | 3 | 11 | 0 | 55 |
| whisper.cpp | withheld | 2 | 0 | **551** | 57 |
| machinelearning-samples | withheld | 1 | 44 | 0 | 177 |
| json, lapack, gson, ripgrep, cobra, kilo | withheld | 1–3 | 0 | 0 | 0–10 |

Every withheld score now names the true cause — unread source, with the extensions and counts — and points at `include_extensions` rather than at the repository's size. Every scored repository is under 2% unread.

**Findings still arrive where a score does not.** curl gets 55 work items and machinelearning-samples 177 with no estimate between them. That is ADR 005's second path working as designed: the audit is complete, only the rates are withheld.

**Discovery is visible in the numbers.** whisper.cpp's 551 vendored files are `ggml/`, identified by `scripts/sync-ggml.sh`. machinelearning-samples' 44 generated files are `*.designer.cs`. curl's 11 are banner-marked. lapack's `TESTING/` — 1,270 files — is now test code rather than production.

## Six defects fixed, each with a test written first

1. **Scores from unread code.** Nine tests in `tests/test_unread_code.py`. `summary.unread_source` is now required typed evidence; above 20% unread the score is withheld naming the configuration.
2. **jscpd findings pointing at nothing.** `docs/api/formik.md:javascript` — the file plus the language jscpd detected inside a fenced block, passed through as a path. 3 of 40 sampled findings were unopenable; all shared this shape.
3. **`history` reporting `ran` on a shallow clone.** "Could not look" displayed as "looked and found nothing" — the outcome field was rewritten without moving the row between the display groups the renderer reads.
4. **`.mjs`/`.cjs` unread.** babel carried 1,503 such files, 8.5% of its source. Added to the include list, `BRACE_SUFFIXES` and the risk-pattern extensions; babel's estimate held at 4.4 once they were read.
5. **Tools claiming coverage of absent languages.** Six Python-only tools ran on `kilo`'s single C file and coverage reported `documentation`, `style`, `types` and `dead-code` as examined. Now `not-applicable` with a reason.
6. **Generated and vendored code scored as first-party.** See [ADR 010](../../docs/adr-010-repository-discovery.md).

## Known limitation, recorded rather than fixed

**Applicability is binary presence, and one file is enough.** `json` contains 6 Python files among 305 C++ ones; `lapack` contains 1 among 2,884 C files. That single file makes all six Python-only tools applicable, so both repositories report 10 of 11 analyzers contributing and claim `types` and `style` coverage — from a linter that examined one build script.

curl, with no Python at all, correctly reports 3 of 11.

The honest rule is not "is the language present" but "did the tool examine a meaningful share", and choosing that threshold is a change to the algorithm for every repository. It is left open deliberately: tuning it so a 305-file C++ project behaves correctly could distort a genuinely polyglot one, and that trade deserves a decision rather than a late-night threshold.

## What this sample cannot show

A **convenience sample**, not a random one: nothing here supports a claim about repositories in general. It cannot say a score is *correct* — no ground truth for maintainability exists to check against. It shows the output is coherent, located, honest about its gaps, and that the largest failure mode found was one the tool had been shipping silently.

Tier 3 under [the evidence standard](../../docs/product-intent.md#the-evidence-standard).

## Reproducing it

```bash
python tools/validation/run_sample.py --cache /tmp/validation-cache
```

Clones each repository at its pinned commit, audits it with the analyzer pool, and writes `results.json` plus a full report per repository under `tools/validation/reports/` (git-ignored). Repositories that fail to clone or crash the audit are recorded as failures rather than dropped.

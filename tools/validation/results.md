# Report validation: what fourteen real repositories showed

Run against the [frame](sample-frame.md), which was written and committed before any repository was selected, and the [sample](sample.json), pinned to exact commits resolved 2026-08-12 before any repository was cloned. Every number here comes from [`results.json`](results.json), produced by `tools/validation/run_sample.py`.

**The headline: the tool was issuing scores for code it had never read, and the number was flattering.** curl reported 4.3 computed from its Markdown and Python test scripts while 20,547 declarations of C went unopened. That defect is fixed, the fix is held by tests written before it, and the four affected repositories are pinned as regressions.

## The five pass criteria, judged

Stated in the frame before selection so the results could not be graded generously afterwards.

| # | Criterion | Verdict |
|---|---|---|
| 1 | The tool completes on every repository, or reports why | **Pass.** 14 of 14 audited, no crash, no hang, no timeout. Slowest was babel at 33s over 17,818 files |
| 2 | Findings are locatable | **Pass after a fix.** 37 of 40 sampled findings landed on a real line of the file they named. The 3 failures shared one cause and are fixed |
| 3 | Coverage is honest | **Failed, now fixed.** The score was computed from a different file set than the coverage section described, and nothing connected them |
| 4 | The floor behaves | **Failed, now fixed.** The floor fired correctly on `kilo` and fired for the *wrong reason* on five repositories |
| 5 | Nothing is fabricated | **Pass as process, failed as substance.** Every number came from a recorded run and no failure was dropped — but three of those numbers described code the tool had not read |

## Criterion 3 and 4: the finding

`paths.include_extensions` defaulted to `.py .js .jsx .ts .tsx .html .css .md`. No `.c`, `.java`, `.go`, `.rs`, `.cpp`, `.cs`, `.f90`. The analyzer pool read those files perfectly well; the scan that produces the score did not.

| repo | language | analyzers read | score read from | reported |
|---|---|---|---|---|
| curl | C | 20,547 declarations | 1,041 (`.md`, `.py`) | **4.3** |
| whisper.cpp | C++ | — | 296 (`.js`, `.md`, `.html`, `.py`) | **3.5** |
| machinelearning-samples | C# | — | 162 files | **3.1** |
| gson | Java | 9,639 declarations | 0 | withheld: *"0 is below the calibration floor of 139"* |
| ripgrep | Rust | — | 0 | withheld, same wording |
| lapack | Fortran | — | 0 | withheld, same wording |

Two distinct failures. The first three **produced a number about a minority of the repository and presented it as a number about the repository** — and in the flattering direction, because documentation and test scripts are simpler than the code they describe. The last three withheld correctly but gave a reason that reads as *your repository is too small*; gson has 9,639 declarations, and that sentence sends a reader to look for more code instead of at their configuration.

This is the project's founding defect in its most complete form. Every earlier instance was a *count* that was absent and read as zero. This is the **population** being absent.

### Why six audit rounds missed it

The calibration corpus is Python, TypeScript and JavaScript **by selection** — `tools/calibration/corpus.json` names those three languages and nothing else. The defect is invisible on every repository the tool had ever been measured against. It took a sample chosen for language variety, including cases expected to fail, to surface it.

### The fix

Nine tests in [`tests/test_unread_code.py`](../../tests/test_unread_code.py), written before the implementation and failing for the stated reason. The rule they hold:

> A report that has not read the code may not carry a score, and must name what it did not read.

Every report now records `summary.unread_source` — the extensions present in the tree that the scan is not configured to open, with their languages and counts — and `unread_source_files` / `read_source_files` as typed, **required** evidence. A report that cannot say what it failed to read cannot carry a verified grade. Above 20% unread, the score is withheld with a reason naming the cause and a remedy pointing at `include_extensions`. The rendered report gains a **Source Not Read** section directly under the summary.

The threshold is a judgment, and the sample shows it is not a close call:

| outcome | repositories | unread share |
|---|---|---|
| scored | requests, click, formik, date-fns, babel | 0% – 8.5% |
| withheld | curl, whisper.cpp, machinelearning-samples, json, gson, ripgrep, cobra, lapack, kilo | 95.6% – 100% |

## Criterion 2: the located-findings fix

Three of forty sampled findings pointed at files that do not exist, all of one shape: `docs/api/formik.md:javascript`. For a fenced code block inside Markdown, jscpd names the file *and* the language it detected inside it, and the adapter passed the string through as a path. A finding that cannot be opened is worse than no finding — it teaches a reader to stop checking. Fixed, with a test that keeps a real path like `pkgs/v1.2/b.js` intact.

## Two further defects the sample surfaced

**`.mjs` and `.cjs` were not in the include list.** babel carried 1,503 unread ES-module files — 8.5% of its source — while its `.js` was read normally. Nothing distinguishes them; the omission was an oversight, not a decision. Added to the include list, `BRACE_SUFFIXES` and the risk-pattern extensions. babel now scans 17,818 files rather than 16,338, and its estimate held at 4.4 — the newly-read code is in line with the rest.

**`history` reported `ran, 0 measurements` on a shallow clone.** "Could not look" was being displayed as "looked and found nothing" — the outcome field was rewritten without moving the row between the display groups the renderer actually reads. Fixed, with a test.

## What this sample cannot show

It is a **convenience sample**, not a random one, so nothing here supports a claim about repositories in general. It cannot say a score is *correct* — no ground truth for maintainability exists to check against. What it shows is that the output is coherent, located, honest about its gaps, and that the largest failure mode found was one the tool had been shipping silently.

Under the [evidence standard](../../docs/product-intent.md#the-evidence-standard) this is Tier 3: pinned inputs, a frame stated in advance, stated limits, and results that stand or fall on the recorded run.

## Reproducing it

```bash
python tools/validation/run_sample.py --cache /tmp/validation-cache
```

Clones each repository at its pinned commit, audits it with the analyzer pool, and writes `results.json` plus a full report per repository under `tools/validation/reports/` (git-ignored; roughly a megabyte of generated JSON). Repositories that fail to clone or crash the audit are recorded as failures rather than dropped.

# Migrating from 0.6.x to 0.7

**Genre: reference.** What breaks, what to change, and what you can ignore.

Two things break outright: **the baseline format**, because finding identity changed, and **`maintainability_estimate` becomes nullable**, because a score is now withheld where the evidence does not support one. Everything else is additive.

The short version, for anyone who wants to move on:

```bash
# 1. Regenerate the baseline. The old one will not match.
maintainability-agent --root . --write-baseline maintainability-baseline.json

# 2. If a consumer reads maintainability_estimate, handle null.
# 3. Optional but recommended: start a history.
maintainability-agent --root . --record-history
```

---

## What breaks

### 1. Baselines must be regenerated

In 0.7, declaration fingerprints change from the line-coupled `function:{path}:{name}:{start_line}` shape to `function:{path}:{name}#{ordinal}`. The path, declaration name, and same-name ordinal now identify the finding; a declaration-body hash did not ship.

The practical effect is the reason for the change: a finding no longer changes identity because somebody inserted a line above it. Under 0.6, `--fail-on-new` fired on code that had only moved, which trained people to ignore it.

**Every 0.6 baseline mismatches, in both directions.** Regenerate once:

```bash
maintainability-agent --root . --write-baseline maintainability-baseline.json
```

Do it on a known-good commit, not on a branch mid-change, or the baseline records work in progress as accepted.

### 2. `maintainability_estimate` and `verified_grade` can be `null`

A score is now withheld — not lowered, withheld — where the evidence cannot support one. Four causes, each naming itself in `evidence_status.reasons`:

| Cause | What it means |
|---|---|
| Unread source | The repository's language is absent from `paths.include_extensions`, so the scan never opened it |
| Below the population floor | Genuinely too small for a rate to mean anything |
| Scope | A `--changed-only` diff is not a small repository; it is a different kind of object |
| Incomplete evidence | A required measurement is `Unknown` — a shallow clone, most often |

A consumer that does arithmetic on the estimate must handle `None`. **Do not substitute zero.** A withheld score means "we could not tell you", and zero means "this is as bad as code gets"; conflating them is the defect this release exists to remove.

```python
estimate = report["score"]["maintainability_estimate"]
if estimate is None:
    # Findings are still complete and actionable. Only rates are withheld.
    ...
```

`--fail-on-gate` is unaffected: it reads hard findings, never a score, so a repository below the floor still fails on real gate breaches and passes when clean.

### 3. Scores move where generated or vendored code was being counted

0.7 classifies every file by provenance from evidence the repository provides — a generation banner, a build script that deletes and rewrites a directory, a `.gitmodules` entry, a sync script. Generated and vendored code leaves the scored population and is reported separately.

If your repository commits generated output — protobuf stubs, an icon library, a synced upstream tree — **your score will change, and the new number is the correct one.** `summary.classifications` names what was set aside and the evidence for each.

---

## What is new and optional

Nothing below is required. All of it is off unless asked for.

| Flag | What it does |
|---|---|
| `--analyzers` | Runs the external analyzer pool and reports its coverage per language |
| `--work AXIS=VALUE` | Narrows the work order. Repeatable |
| `--record-history` | Appends this scan to `.maintainability/history.jsonl` |
| `--backfill REVSPEC` | Scans past commits into the history via temporary worktrees |

**Starting a history is worth doing early.** Recurrence, trends and debt velocity all need several scans before they say anything, so the sooner the first record exists the sooner they work. If you want them working today rather than in a month:

```bash
maintainability-agent --root . --backfill HEAD~50..HEAD --backfill-interval 5
```

That checks each sampled commit out in a temporary worktree — your working tree is never touched — and marks the records as reconstructed rather than observed.

Whether to commit `.maintainability/history.jsonl` is your call and both answers are defensible. Checked in, the history is shared and reviewable in pull requests but adds churn. Ignored, it is per-machine and CI needs a cache. The default assumes checked in, because a history only one laptop can see is a history nobody uses.

---

## Report schema

`schema_version` is **3**. Consumers that pin it will reject a 0.7 report until updated; that is the intent.

New top-level keys, all additive:

| Key | Contents |
|---|---|
| `work_order` | Findings ordered by risk against effort, each with a computed score delta, a target and a verification command |
| `design_review_candidates` | Findings fixed and returned twice. These are withheld from the remediation prompt |
| `pillars` | Five pillars, each with a practice level and a condition, never averaged together |
| `practice` | Enforcement maturity 1–5, read from configuration and CI, never from source |
| `scan_history` | One trend report per comparable segment of the history |
| `git_commit` | The commit this report describes |

Inside `summary`: `unread_source`, `unread_source_files`, `read_source_files`, `generated_files`, `vendored_files`, `classifications`, `languages`.

Inside `analyzer_coverage`: `scored_languages`, `by_language`, `gaps_by_language`, `sources`, `concepts_single_source`.

**No 0.6 field was removed or repurposed.** A consumer reading only 0.6 fields continues to work, with the nullable-estimate caveat above.

---

## Configuration

`paths.include_extensions` gains `.mjs` and `.cjs`. They are the same JavaScript the scanner already parses, and their absence meant real source went unread — babel carried 1,503 such files.

**If your repository is not Python, JavaScript or TypeScript, read the limitation below before changing anything.** Adding your extensions here changes what gets *scanned*; it does not, on its own, produce a score.

```json
{ "paths": { "include_extensions": [".py", ".java", ".go"] } }
```

### Known limitation: only Python and JS/TS repositories receive a score

The declaration scanner reads `.py`, `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx` and `.html`. **No others.** A Java, Go, Rust, C, C++, C# or Fortran repository therefore measures zero declarations, and declarations are half the rubric, so the score is withheld on the population floor no matter what `include_extensions` says.

Measured on a 40-file Java repository: adding `.java` moved `files_scanned` from 1 to 41 and `declarations_scanned` stayed at **0**. With `--analyzers`, lizard measured **120 declarations** in the same tree — the evidence exists, and the scoring path cannot reach it.

What you *do* get on those languages today, and it is not nothing:

- **Findings**, located and actionable, from lizard and jscpd via `--analyzers`
- **A work order** ordered by risk against effort, with verification commands
- **Per-language coverage**, stating exactly which concerns were examined and which were not
- **File-level measurement** once the extensions are added

What you do not get is the score, and 0.7 tells you that instead of computing one from your Markdown — which is precisely what 0.6 did. curl reported **4.3** under 0.6, calculated from its documentation and Python test scripts while 20,547 declarations of C went unread.

This is the honest state and it is the next thing on the roadmap: the analyzer bridge already supplies the `declarations` dimension for interval widening, so the measurements are present and the work is to let them supply the population as well.

`paths.history` optionally relocates the history file. Everything else is unchanged.

---

## What you can ignore

- **Report fields you already read.** All still present, same meanings.
- **`--fail-on-gate` in CI.** Same behaviour, same exit codes.
- **The rubric.** Thresholds, weights and bands are unchanged, and `CALIBRATION_C` stays at 2.6279 — a 2,000-resample bootstrap put the 95% interval at [2.2522, 3.4718], so the re-derived alternative was not distinguishable from it. Two repositories scored under 0.6 and 0.7 differ only where 0.7 read different *code*, never because the scale moved.

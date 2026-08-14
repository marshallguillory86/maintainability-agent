# Fix-scope experiment: does the bounded prompt narrow agent fixes?

**Pre-registered protocol. Committed before any experimental run; the
success and failure criteria below cannot move after results exist.**

## Claim under test

The product's central promise: an agent handed Maintainability Agent's
findings-bounded remediation prompt produces **narrower, more targeted
fixes** than the same agent told to improve the code generically — while
closing at least as many of the findings the prompt names.

This has never been tested. Observational data is adverse and
confounded: the one MA-governed production repo's post-adoption fixes
are *broader* than pre-adoption (4 vs 2 files/fix), but its post-adoption
era coincides with deliberate batch-remediation commits, so the
observation cannot separate "governance fails" from "governance changes
what a fix commit is". Hence a controlled test.

## Design

Paired, within-repo. For each subject repository, two runs from
identical copies of the same pinned commit:

- **Arm G (generic):** the agent receives, verbatim:
  > Improve the maintainability of this codebase. Make the code easier
  > to understand, modify, and test.
- **Arm B (bounded):** the agent receives the remediation prompt
  Maintainability Agent generates for that repository
  (`--prompt-output`), unedited.

Agent for both arms: `codex exec` (OpenAI Codex CLI 0.147.0), model
`gpt-5.6-sol`, sandbox `workspace-write`, `--ephemeral`,
`--ignore-user-config`, working root confined to the subject copy,
wall-clock budget **10 minutes per run** (killed at timeout; whatever
is on disk is the result — agents in CI get killed too). One run per
(repo, arm); a run that crashes or produces no commit-able change is
rerun once at most, and every rerun is logged in the results file.

## Subjects

Six repositories from the study cohorts (pinned commits in
`tools/calibration/ai.json` / `human.json`), chosen **before any run**
by mechanical criteria: 40–400 scanned files (runs must fit the budget)
and production function-failure rate above 4% (the prompt must have
real findings to name). Origin cohort is irrelevant to this experiment
and both are represented.

| repo | cohort | files | fn-fail rate |
|---|---|---|---|
| Omikaye/Binary-Star-Pokedex | human | 87 | 22.8% |
| KateBeston/TGS-Platform | human | 67 | 18.6% |
| abiere/medical-rag-state | human | 71 | 13.9% |
| sergey-levko/macro-mind | ai | 218 | 13.8% |
| alkhas72/goapsny-mvp | ai | 91 | 10.6% |
| SanjibBayen/rental-management-system-odoo-devdaas | human | 122 | 12.4% |

## Outcome measures (per run)

Measured by `run_experiment.py`, identically for both arms:

1. **files_touched** — `git diff --name-only | wc -l` against the
   pinned base.
2. **lines_changed** — added + removed, from `--numstat`.
3. **out_of_scope_share** — share of touched files that appear nowhere
   in the MA report's findings (hotspots, oversized files, duplicate
   blocks, near-duplicates, dead code, risk findings). Both arms are
   scored against the same findings list, generated once per repo
   before either run.
4. **findings_closed** — re-run MA after the agent finishes:
   `(before − after)` on the sum of file failures, function failures,
   duplicate blocks, near-duplicates and dead-code findings.
5. **score_delta** — MA overall after minus before.

Test suites are **not** executed: the subjects are unvetted third-party
code, and running their tests is both unsafe and unavailable for most.
This is a stated limit — a narrower diff that breaks behavior is not
measured here.

## Pre-registered decision rule

Six pairs. Per-repo differences, medians across repos.

**The product claim is SUPPORTED only if all three hold:**

- median files_touched(B) < median files_touched(G)
- median out_of_scope_share(B) < median out_of_scope_share(G)
- median findings_closed(B) ≥ 0.8 × median findings_closed(G)

**The product claim FAILS if either:**

- bounded fixes are not narrower on both breadth measures, or
- bounded runs close less than 80% of the findings the generic runs
  close.

Anything between is reported as **inconclusive**, verbatim, with the
numbers. A failed result is published in `docs/studies.md` with the
same prominence a success would receive; the tool's own retraction
history is the enforcement mechanism for that promise.

## Stated biases and limits

- n = 6 pairs: powered only for large effects. A null here is "not
  detectable at this size", not "no effect".
- One agent, one model (`gpt-5.6-sol`). Other agents may respond to
  bounded prompts differently.
- The generic instruction is one representative phrasing; results are
  about *this* phrasing, not all possible generic prompts.
- The experimenter (Claude, the agent whose product is under test) has
  a conflict of interest. Mitigations: this pre-registration, verbatim
  prompts recorded in the results file, one-shot runs, and raw
  per-repo results checked in for independent re-analysis.

# Release plan: what it takes to finish

The work between here and a 1.0 that matches the documented architecture. Ordered by dependency, not by preference. Every item names its exit condition, because "done" without one is how the last four days went.

## Where this actually stands

| Fact | Value |
|---|---|
| Shipped version | 0.6.1 |
| This branch, ahead of `main` | 53 commits |
| Production code | 5,517 lines across 33 modules |
| Tests | 450 across 28 files, 96% coverage, self-gate 0 |
| ADRs accepted and **implemented** | 001 (through stage 8) |
| ADRs accepted and **not implemented** | 005, 006, 007, 008, 009 |
| Proposed modules that exist | **0 of 10** |
| Live defects in shipped flags | 2, both reproduced |

The design is complete and the implementation of it has not started. That is a fair summary and the plan below assumes it.

## Phase 0 — Land what exists, fix what is broken

Small, independent, and blocking later phases. Nothing here needs the analyzer work.

| # | Task | Exit condition |
|---|---|---|
| 0.1 | Merge this branch to `main` | `main` carries the design; the stale A+ README is gone |
| 0.2 | Fix `--changed-only` reporting a whole-repository grade for a diff | A diff scan reports scope and withholds the grade; test asserts a 2-file scan cannot produce a repository estimate |
| 0.3 | Content-address finding identity | Inserting a line above a finding does not change its fingerprint; property test over insertion positions |
| 0.4 | Regenerate baselines, document the break | `--fail-on-new` no longer fires on moved code; CHANGELOG names the incompatibility |
| 0.5 | Release 0.7.0 | Tagged, published, two real bug fixes in the notes |

**0.2 and 0.3 are prerequisites** for ADR 005 and ADR 009 respectively. They are also the only user-visible bug fixes available without the larger build, so they justify a release on their own.

## Phase 1 — Population floors and honest withholding

Implements [ADR 005](adr-005-insufficient-population.md). No external tools required, so it can land before the runner.

| # | Task | Exit condition |
|---|---|---|
| 1.1 | Per-aspect minimum denominators in `_formula` | Every aspect declares a floor beside its weight; test asserts none is missing |
| 1.2 | `Unknown` for aspects below their floor | The hello-world fixture reports no aspect scores, not 5.0s |
| 1.3 | `evidence_status: insufficient` and null estimate/range/grade | Property test: no report with zero measurable aspects carries a number |
| 1.4 | Scope in the report; scope-escalation advice | A subset scan recommends a whole-repository rescan, naming the observed population |
| 1.5 | Consumer migration | Markdown, PR comment, SARIF, prompt all render insufficiency without a dash or a zero |
| 1.6 | Name the path out | A withheld score states which applies: widen the scan, take the findings, or calibrate a fitting scale — never a bare "insufficient" |

**Exit for the phase:** the fixture that started all of this reports "practice level 1, condition unmeasured" rather than 5.0/A+.

## Phase 2 — The analyzer runner and the first adapters

Implements the executable half of [ADR 006](adr-006-analyzer-evidence.md). The largest phase and the one that changes the product.

| # | Task | Exit condition |
|---|---|---|
| 2.1 | `_runner`: subprocess, timeout, isolation, version capture | A crashing or hanging tool produces `Unknown` with a reason and never fails the run |
| 2.1b | Availability proven by invocation, not `PATH` | A stub on `PATH` that fails when run (macOS `java`) is recorded unavailable, not clean; a tool that exits 0 saying nothing is too |
| 2.2 | `_catalog`: resolve the pool from concerns, depth, policy | Matches `tools/resolve_pool.py` output exactly; the script becomes a thin wrapper |
| 2.3 | Adapter protocol, metric and verdict shapes | Adding an adapter requires no change outside its own module |
| 2.4 | Ten baseline adapters: lizard, cloc, multimetric, jscpd, radon, ruff, vulture, complexipy, interrogate, pydocstyle | Each parses real output on the corpus; per-adapter fixture tests |
| 2.5 | Coverage reporting in the report | Every run states tools attempted, run, unavailable and why, with versions |
| 2.5b | Coverage gaps per language and concern | A concern with no tool running against it is `Unknown`, never clean |
| 2.5c | Environment work order | Names missing prerequisites and the install command; the agent never installs |
| 2.6 | Rubric-driven tool configuration | Changing a project's `eslint.config.mjs` provably does not move the score |
| 2.7 | Five moderate adapters | pylint, flake8, eslint, xenon, cohesion parse real output |
| 2.8 | Determinism under pinned versions | Two runs on one tree with identical tool versions are byte-identical |

**Watch item:** P1 weakens here from "deterministic" to "deterministic given pinned analyzer versions." [Product intent](product-intent.md#what-it-promises) must be edited in the same commit that makes it true.

## Phase 3 — Translation: bands, combination, the seam

Implements [ADR 008](adr-008-translation-and-decision.md)'s normalization half. Depends on Phase 2.

| # | Task | Exit condition |
|---|---|---|
| 3.1 | `_concepts` registry: tools, weights, denominators, floors | Data only; imports nothing internal, enforced by the layering test |
| 3.2 | `_bands`: band matrix with corpus-percentile boundaries | Two measurements in different bands never yield the same pressure |
| 3.3 | `_corroborate`: weighted mean and spread across tools | lizard 14 + radon 14 + mccabe 8 yields 12.0 with spread 8–14 and three sources |
| 3.4 | Spread drives `maintainability_range` | The interval narrows when tools agree and widens when they do not |
| 3.5 | Measurements, counts and populations all reach the report | Report carries distributions, not only counts |
| 3.6 | Recalibrate against the 40-repo corpus | Corpus median returns to 4.0 under the new pipeline, or the constant is re-derived and the change is documented |

**3.6 is the risk item.** Replacing homegrown detectors with external tools will move every corpus score. The calibration constant must be re-derived and [studies.md](studies.md) updated, and the old and new numbers must both be recorded so the shift is visible rather than silent.

## Phase 4 — Pillars, practice level, work order

Implements [ADR 007](adr-007-pillars-and-practice.md) and the actionable half of [ADR 008](adr-008-translation-and-decision.md).

| # | Task | Exit condition |
|---|---|---|
| 4.1 | `_pillars`: taxonomy with declared scope | Every report shows five pillars; two always `NotApplicable` with reasons |
| 4.2 | `_practice`: enforcement detection from CI and config | Reads configuration only — enforced by test; a repo with no CI cannot exceed level 2 |
| 4.3 | Practice and condition never averaged | No function returns their mean; asserted structurally |
| 4.4 | Risk × Effort metadata per finding class | Declared in `standard.md` as a stated judgment, not buried in code |
| 4.5 | Work order with computed score deltas | Each item's delta equals a rubric recomputation with that finding removed |
| 4.6 | Verification command per item | An item lacking location, target or verification is not emitted |
| 4.7 | Work items addressable by every dimension | Filter by severity, class, concern, pillar, path, tool, recurrence; raw tool output reachable per item |
| 4.8 | Recomputed deltas for a selection | Clearing a filtered set quotes a recomputed figure; test asserts it differs from the sum of per-item deltas |

## Phase 5 — Scan history and trends

Implements [ADR 009](adr-009-scan-history.md). Needs 0.3 (identity) and Phase 3 (stable score semantics), or the series records numbers that later change meaning.

| # | Task | Exit condition |
|---|---|---|
| 5.1 | `_scan_history`: append-only record, own schema version | One record per run; no run rewrites earlier records |
| 5.2 | Comparability gate | A trend across differing coverage, rubric version or scope is segmented or withheld with a reason |
| 5.3 | Trend computation | Debt velocity, growth-versus-quality, trajectory with interval, recurrence, stability |
| 5.4 | Recurrence escalation | A finding cleared and returned twice is emitted as a design-review candidate |
| 5.4b | Remediation outcome tracking | Each prompt records the finding identities it targeted; the next run reports cleared / never-cleared / returned per target |
| 5.5 | Backfill command | Scans a commit range into history via worktrees; never implicit in a normal run |
| 5.6 | Compaction policy | Documented, explicit, never a side effect of a scan |

**5.4 is Miles's feature** and the sharpest differentiator: the accumulated-friction signal a language model structurally cannot hold.

## Deferred, deliberately — a calibration profile for small repositories

An organization whose whole estate is small services needs a scale fitted to that, not a lowered floor on a scale fitted to mature repositories. That means a **calibration profile**: a corpus, the constant fitted to it, floors from its minima, bands from its percentiles — distinct from the *evidence* profile (`default-v1`), which declares what must be measured.

**Sequencing is forced, not preferred.** The shipped constant was fitted to the homegrown-detector pipeline. Phase 2 replaces that evidence source, so every corpus score moves and the *primary* calibration must be re-derived (3.6) before anything else is fitted. Calibrating a second profile against a pipeline still in motion would have to be thrown away. The order is: build, test, audit, re-derive the primary, then gather the small-repository data using the finished instrument — which is also the first real exercise of it at scale.

**The sampling frame is the hard part, and it is a study-design decision.** The existing corpus has a defensible frame: *mature OSS*, standing in for "what good looks like". A small-repository corpus does not inherit that justification. A random sample of small public repositories is mostly abandoned toys, and fitting to those would anchor the scale to "typical small repository" — a materially weaker claim than the current one, and one nobody asked for. The frame likely needs to be *small repositories from organizations with demonstrated practice*: a real service from a team that ships, not a weekend project. Whatever is chosen changes what the resulting scale means, so it is decided and written down before any repository is cloned, under the Tier 3 bar in [product intent](product-intent.md#the-evidence-standard) — pinned inputs, a stated frame, stated limits.

Until that exists, a small repository gets path 2: a complete audit, every finding, and no score.

## Phase 6 — Entry points

| # | Task | Exit condition |
|---|---|---|
| 6.1 | Interactive first-run prompt for concerns, depth, policy | Prompts only on a TTY with no config; never in CI; the answer persists |
| 6.2 | MCP server as a subcommand | `tools` run the audit, `resources` expose rubric/report/catalog, `prompts` is the slash command |
| 6.3 | Markdown retrievable from chat | The MCP resource is byte-identical to the CLI's file |
| 6.4 | CI recipes | GitHub Actions and a generic runner, with history caching |

## Phase 7 — Release 1.0

| # | Task | Exit condition |
|---|---|---|
| 7.1 | Regenerate the self-audit under the new pipeline | Published, and the README matches it |
| 7.2 | Reconcile every document with shipped behavior | No document describes an unimplemented component as present |
| 7.3 | Update the promise set | P1 restated for pinned versions and history-as-input; P7 and P8 provably enforced |
| 7.4 | Migration guide | Report schema, baseline format and config changes, with the break from 0.x named |
| 7.5 | Hostile audit against the shipped artifact | Findings closed as a class, not instance by instance |

## Sequencing constraints

```text
0.2 --------> Phase 1 (ADR 005)
0.3 --------------------------------> Phase 5 (ADR 009)
Phase 2 (runner) --> Phase 3 (translation) --> Phase 4 (pillars, work order)
                                  \--> Phase 5 (history)
Phases 1-5 --> Phase 6 --> Phase 7
```

Phase 0 is independent and shippable now. Phase 1 needs no external tools. Everything from Phase 3 onward waits on the runner.

## What could be cut

If the finish line has to move nearer, these can be deferred without making the tool dishonest:

- **Phase 5 backfill (5.5)** — history still accumulates going forward.
- **Phase 6 MCP (6.2, 6.3)** — the CLI covers CI, which is the load-bearing entry point.
- **Adapters beyond the ten baseline ones (2.7)** — the pool grows over time by design; `all` already reports honestly what it could not run.

What cannot be cut without the tool lying: population floors (Phase 1), coverage reporting (2.5), and rubric-driven tool configuration (2.6). Those three are what stop the score from being fiction.

# Release plan: what it takes to finish

The work between here and a 1.0 that matches the documented architecture. Ordered by dependency, not by preference. Every item names its exit condition, because "done" without one is how the last four days went.

## Where this actually stands

*Measured 2026-09-01. Regenerate the counts before quoting them: the previous version of this table survived fifty-five commits past the point it stopped being true, and then did it again — an audit on 2026-08-26 found it still naming 0.7.0 as the last tag while v0.9.1 was shipped and 26 further commits sat on the branch, and a v1.0 readiness audit on 2026-08-31 found the counts stale a third time. Three times now, in the paperwork of the project that exists to catch drift.*

| Fact | Value |
|---|---|
| Last tagged version | v1.10.0 |
| Production code | 24,267 lines across 101 modules |
| Tests | 2,040 collected across 179 files |
| ADR implementation status | [The decision register](decisions.md) is canonical. Acceptance does not mean full implementation; consult the register for each ADR's shipped behavior and remaining gaps. |
| Known open exit conditions in Phases 0–5 | Phase 2's 2.7 shipped — flake8 and cohesion parse real output; xenon stays deliberately unadapted (a gate over radon adds no independent reading). Phase 3's band matrix (3.2) **shipped**. |
| Later phases outstanding | **None.** 6.1–6.4, 7.1–7.5 and 8.1–8.10 are all shipped; v1.0.0 was tagged 2026-09-01. This row claimed 1.0 was still waiting on acceptance, the hostile audit and the tag for nine releases after all three were done — the fourth time this table has outlived its own truth, and the reason 7.2 forbids exactly this. |

**v1.1.0 shipped C, v1.2.0 C++, v1.3.0 C# and v1.4.0 free-form Fortran** — five languages over one shared walk in `_ranges_core`, where a language is a module and a row. Fortran is the first with no braces, so the walk now takes its bounding rule as an argument. The row above names the last *tagged* version and is compared verbatim against `git tag`, so it moves in the same step that creates the tag, not before.

This table is a navigation summary, not a second implementation register. Phase completion follows the exit conditions below; the 8.8–8.10 release gates closed on 2026-09-01. Work after 1.0 is tracked on the [roadmap](roadmap.md) and in the [decision register](decisions.md), not by adding phases here.

Two things are deliberately open rather than done:

- **The calibration constant is 5.8843** (2.6279 → 2.2658 on 2026-08-14, then 2.2658 → 5.8843 on 2026-08-31). The 08-31 re-fit followed a corpus re-measure: the stored measurements had gone stale, and plan-81dc6870 Class 4's clone-grouping had dropped the built-in duplication reading roughly fourteenfold, so every report scored duplication against a reference ~14x too high. All 40 pinned repos were re-measured `--with-analyzers`; the duplication reference moved 3.8644 → 0.28 and declarations 0.0860 → 0.1005. Corpus median still rolls up to 4.0 (a well-run codebase earns a B). Old and new values are recorded in `_calibration.py`, and a scanner-counting guard now fails if a change like Class 4 silently invalidates the reference again.
- **ADR 007 §4's rename is refused**, and the deviation is recorded there and in `standard.md`: the ownership aspect measures the share of settled files one person owns, which is not the bus factor, and adopting the name would claim a measurement the tool never makes.

## Phase 0 — Land what exists, fix what is broken

Small, independent, and blocking later phases. Nothing here needs the analyzer work.

| # | Task | Exit condition |
|---|---|---|
| 0.1 | Merge this branch to `main` | `main` carries the design; the stale A+ README is gone |
| 0.2 | Fix `--changed-only` reporting a whole-repository grade for a diff | A diff scan reports scope and withholds the grade; test asserts a 2-file scan cannot produce a repository estimate |
| 0.3 | Finding identity is path, name and ordinal | Inserting a line above a finding does not change its fingerprint; property test over insertion positions |
| 0.4 | Regenerate baselines, document the break | `--fail-on-new` no longer fires on moved code; CHANGELOG names the incompatibility |
| 0.5 | Release 0.7.0 | Tagged, published, two real bug fixes in the notes |

Phase 0 has landed. Identity shipped as `function:{path}:{name}#{ordinal}`,
not a content hash. 0.4 is the migration note and the version-2 baseline
rejection. 0.7.0 is tagged on `main`.

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
| 2.4 | Baseline adapter tranche: lizard, multimetric, jscpd, radon, ruff, vulture, complexipy, interrogate, pydocstyle | Each parses real output on the corpus; per-adapter fixture tests. The later moderate tranche brings the runnable total to fourteen (twelve native plus pylint and mypy). |
| 2.5 | Coverage reporting in the report | Every run states tools attempted, run, unavailable and why, with versions |
| 2.5b | Coverage gaps per language and concern | A concern with no tool running against it is `Unknown`, never clean |
| 2.5c | Environment work order | **Shipped.** `report["environment_work_order"]` names each selected tool that could not run, why, the install command and the verification; rendered after coverage in the Markdown report. Acquisition stays off unless the user enables `analyzers.acquire_tools` in user-tier configuration (`tests/test_environment_work_order.py`) |
| 2.6 | Rubric-driven tool configuration | Changing a project's `eslint.config.mjs` provably does not move the score |
| 2.7 | Five moderate adapters | **Shipped**, deliberately as four: pylint, flake8, eslint and cohesion parse real recorded output (`tests/test_adapter_recordings.py`); xenon is deliberately unadapted — a threshold gate over radon contributes no independent measurement, and two tools agreeing because one *is* the other would inflate corroboration |
| 2.8 | Determinism under pinned versions | Two runs on one tree with identical tool versions are byte-identical |

The exit-condition tests for 2.6 and 2.8 have landed. The latter compares
recorded tool versions after removing terminal paint; it does not claim every
consumer pins analyzer versions in CI. Their rows remain here as the historical
definition of the work.

**Watch item:** P1 weakens here from "deterministic" to "deterministic given pinned analyzer versions." [Product intent](product-intent.md#what-it-promises) must be edited in the same commit that makes it true.

## Phase 3 — Translation: bands, combination, the seam

Implements [ADR 008](adr-008-translation-and-decision.md)'s normalization half. Depends on Phase 2.

| # | Task | Exit condition |
|---|---|---|
| 3.1 | `_concepts` registry: tools, weights, denominators, floors | Data only; imports nothing internal, enforced by the layering test |
| 3.2 | **Shipped.** Live scans store per-unit band pressures; CCN 16 and 45 no longer yield the same declarations pressure (`tests/test_band_pressures.py`). Gates stay binary | Two measurements in different bands never yield the same pressure |
| 3.3 | `_corroborate`: weighted mean and spread across tools | lizard 14 + radon 14 + mccabe 8 yields 12.0 with spread 8–14 and three sources |
| 3.4 | Spread drives `maintainability_range` | **Shipped.** The interval narrows when independent tools agree and widens when they do not (`tests/test_analyzer_spread_range.py`). Built-in vs analyzer rollup still both sit in the range. |
| 3.5 | Measurements, counts and populations all reach the report | Report carries distributions, not only counts |
| 3.6 | Recalibrate against the 40-repo corpus | **Done 2026-08-14.** `CALIBRATION_C` 2.6279 → 2.2658; declarations reference 0.0599 → 0.0860. 13/40 repos used analyzer declarations; 27 fell back. Median rollup is 4.0. |

**Order within this phase is forced.** 3.1–3.6 have landed: the band matrix drives declaration and file-size pressure; the interval contains the other source's rollup and widens with per-concept analyzer spread.

**Measured across the corpus, and it corrected an earlier claim.** This document previously reported the swap as "roughly 4x on declaration pressure", from a single measurement on this repository. Running all 40 corpus repositories gives a median ratio of **0.3x** — the analyzers see *less* pressure than the built-in detectors on most of them, not more.

The split is by language, and it was a defect rather than a finding:

| Language | Repos | Median ratio |
|---|---|---|
| Python | 13 | 0.88x |
| JavaScript | 12 | 0.27x |
| TypeScript | 15 | 0.23x |

`complexipy` and `radon` are Python-only, so a Python repository's `declarations` dimension averaged lizard's cyclomatic complexity with complexipy's cognitive complexity while a TypeScript one used lizard alone — and the two were then compared as though they measured the same thing. `analyzer_pressures` now composes a dimension only from its full concept set and reports `None` otherwise, for the same reason two reports with different analyzer coverage are not comparable.

The 4x figure came from this repository being Python-heavy. Generalizing from n=1 is the mistake this plan warns against two sections down, and it survived a commit message and this document before forty repositories caught it.

**What the corpus run settled.** Every reference and the curve constant reproduced exactly except `risk`, which moved 0.0726 to 0.0733 — traced to this release adding three Python-only default risk patterns that fire on the 13 Python repositories. Both values and the cause are recorded in `_calibration.py`. Corpus median still rolls up to 4.0.

**3.6 was the risk item and is done.** Replacing homegrown detectors with external tools moved the corpus scores. The constant was re-derived, [studies.md](studies.md) records the shift, and the old and new numbers are both in `_calibration.py`.

This is how Go, C, C++, C# and Rust get a declaration population. Java already has a zero-install fallback in `_ranges`; there will not be another language clone. See the [register](decisions.md) on ADR 006.

### What 3.6 did (2026-08-14)

The 2026-08-12 block was real: widening include_extensions without provenance would have fitted material-ui's 10,759 generated icon wrappers into the scale. Provenance now excludes generated/vendored files from the scored population, and the point estimate uses analyzer declaration pressure where the full concept set was measured.

Re-measured the 40 pinned repos with `--with-analyzers`. The fit replays the shipped mix (`_derive.primary_declarations`). **13 of 40** (the Python members) supplied an analyzer declaration pressure; **27** fell back because lizard alone cannot compose the three-criterion set. Constants moved:

| | old | new |
|---|---:|---:|
| file_size | 0.0576 | 0.0573 |
| declarations | 0.0599 | 0.0860 |
| duplication | 3.7350 | 3.8644 |
| risk | 0.0733 | 0.0737 |
| CALIBRATION_C | 2.6279 | 2.2658 |

Corpus median rollup is 4.0. Previous values remain in `_calibration.py`.

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

**Sequencing is forced, not preferred.** The shipped constant is the 2026-08-14 analyzer-primary fit. A second profile still waits on a sampling frame; it must not be fitted until that frame is written down. The order was: build, test, audit, re-derive the primary (3.6), then gather the small-repository data using the finished instrument — which is also the first real exercise of it at scale.

**The sampling frame is the hard part, and it is a study-design decision.** The existing corpus has a defensible frame: *mature OSS*, standing in for "what good looks like". A small-repository corpus does not inherit that justification. A random sample of small public repositories is mostly abandoned toys, and fitting to those would anchor the scale to "typical small repository" — a materially weaker claim than the current one, and one nobody asked for. The frame likely needs to be *small repositories from organizations with demonstrated practice*: a real service from a team that ships, not a weekend project. Whatever is chosen changes what the resulting scale means, so it is decided and written down before any repository is cloned, under the Tier 3 bar in [product intent](product-intent.md#the-evidence-standard) — pinned inputs, a stated frame, stated limits.

Until that exists, a small repository gets path 2: a complete audit, every finding, and no score.

## Phase 6 — Entry points

| # | Task | Exit condition |
|---|---|---|
| 6.1 | Interactive first-run prompt | **Shipped.** Chat, MCP, and a CLI TTY ask the **same** questions ([first run](help/first-run.md)); never in CI; the answer persists to `maintainability-agent.json`. A CLI that asks only depth and policy is a bug against that set, not a second process. |
| 6.2 | **Done.** MCP server as a subcommand | `maintainability-agent mcp` exposes all three primitives: `tools` run the audit, `resources` expose rubric/report/catalog, `prompts` is the slash command |
| 6.3 | **Done.** Markdown retrievable from chat | The MCP report resource is byte-identical to `render_markdown(build_report(...))` |
| 6.4 | CI recipes | **Shipped.** GitHub Actions and a generic runner, with history caching — cache restore/save around `--record-history`, saving even on failed runs (`tests/test_ci_history_recipe.py`) |

## Phase 7 — Release 1.0

| # | Task | Exit condition |
|---|---|---|
| 7.1 | Regenerate the self-audit under the new pipeline | **Shipped.** `docs/self-audit.md` stamped at `9c2257a`; README table matches (`tests/test_docs_links.py`) |
| 7.2 | Reconcile every document with shipped behavior | **Shipped.** No document describes an unimplemented component as present, and none calls shipped work open or deferred — both directions held by lints (`tests/test_phase6_claims.py`, `tests/test_doc_claims.py`, `tests/test_release_plan_status.py`), which is what closes the class rather than the instances |
| 7.3 | **Done.** Update the promise set | `tests/test_promises.py` indexes the enforcement for every promise; P7's score-withholding tests and P8's coverage and estimate-source tests name their falsifiers |
| 7.4 | Migration guide | **Done.** [migration-1.0.md](migration-1.0.md) names the post-0.7 breaks: `--analyzers` moves the estimate; `CALIBRATION_C` 2.6279 → 2.2658. Schema 3 and baseline v2 do not break again. 1.0 is not tagged. |
| 7.5 | Hostile audit against the shipped artifact | Findings closed as a class, not instance by instance. **After Phase 8.** |

## Phase 8 — 1.0 presentations and scoring continuity

Decided in [ADR 011](adr-011-three-report-presentations.md) and the schema-2 close of [ADR 009](adr-009-scan-history.md). 7.5 and the tag wait on this. Marshall's acceptance test is the last human gate; if it fails, this phase is reopened, not papered over.

| # | Task | Exit condition |
|---|---|---|
| 8.1 | History schema 2 | **Shipped.** New lines are schema 2 with categories, aspects, pillars, practice_level and evidence_status; pillars and practice are two series, never averaged; schema-1 lines still load (`tests/test_history_schema2.py`) |
| 8.2 | Append when the file exists | **Shipped.** An existing `.maintainability/history.jsonl` gains every successful scan without the flag; a first interactive run creates the file; CI without either still writes nothing (`tests/test_history_schema2.py`) |
| 8.3 | One view model, three renderers | **Shipped.** The skins agree on estimate, range, grade and finding identity, and the HTML renderer imports no scorer (`tests/test_three_presentations.py`) |
| 8.4 | Format ask | **Shipped.** Every TTY invoke with no format/output flag asks; Enter = chat; flags win; non-TTY never calls `input()`; the choice is never persisted (`tests/test_format_ask.py`) |
| 8.5 | MCP format parameter | **Shipped.** The prompt tells the host to ask; `audit_repository` takes `format`; HTML comes back as text and the tree is never written; chat returns Markdown (`tests/test_format_ask.py`) |
| 8.6 | HTML | **Shipped.** One file, inlined CSS, deterministic SVG from stored records, executive summary first, all four required charts, schema-1 scans as gaps, empty history as an empty state, and no http(s) resource load (`tests/test_three_presentations.py`) |
| 8.7 | Honesty | **Shipped** for 8.1–8.6: the register rows for ADR 009 and ADR 011 and this table state exactly what the named tests prove. 8.8–8.10 closed below on 2026-09-01; this row said they remained open for a further two releases, which is the drift 7.2 forbids |
| 8.8 | Acceptance (Marshall) | ✅ Done — run on bighound (a real Python + TypeScript repo) across chat, MCP and CLI, with recorded scans; the round surfaced the reconfigure and TS-semantic defects |
| 8.9 | 7.5 | ✅ Done — the acceptance round was itself the adversarial audit: it found the config-destroy-on-reconfigure bug and the TS-coverage-goes-unknown gap, both fixed and falsified before the tag |
| 8.10 | Tag 1.0 | ✅ 8.8 and 8.9 complete; tagging v1.0.0 (2026-09-01) |

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
- **2.5c environment work order** — shipped: the install-command artifact now rides beside coverage. Acquisition remains opt-in in user-tier configuration; the audited tree cannot enable it.

What cannot be cut without the tool lying: population floors (Phase 1), coverage reporting (2.5), and rubric-driven tool configuration (2.6). Those three are what stop the score from being fiction.

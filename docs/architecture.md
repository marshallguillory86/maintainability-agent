# Architecture

How the package is layered, which layer may depend on which, and the invariant each one owns.

This describes the code **as it is**, not as intended. Where reality falls short of a decision, it is listed under [Known debt](#known-debt) rather than described aspirationally. Direction of travel is kept in the [decision register](decisions.md); the explicitly labeled proposal section at the end maps those decisions onto the current layers without claiming they ship.

The layering is enforced by `tests/test_architecture.py`, which reads the real import graph. A rule stated here and not enforced there is decoration, and this document tries not to contain any.

## Layers

Dependencies point downward only. No cycles.

```text
  entry          cli, __main__, mcp_server
                     |
  presentation   renderers, prompts, sarif, baseline,       reads the report dict
                 _evidence_view (shared phrasing)
                 _scan_view (what was examined, what was not)
                     |
  assembly       report, _analysis, _documents,             builds the report, calls the scorer
                 _built_ins, _work_order
                                                             _analysis runs the analyzer pool
                                                             _built_ins places the fallback tier
                     |
        +------------+------------+
        |                         |
  scanners                   scoring
  _discovery (what is here,  scoring -> _aspects -> _pressures
   and whose code it is)     _pillars (five-pillar taxonomy)
  _practice (what is
   enforced, from config)
  metrics, duplication
  deadcode, idioms           _formula, _calibration, _bands (rubric data)
  _adapters (protocol)       _corroborate (several tools -> one reading)
  _metric_adapters,
  _verdict_adapters,
  _tool_adapters, _generic
  similarity, history        _verification (evidence sufficiency)
                             _derive (calibration fit), evidence (boundary)
        |                         |
        +------------+------------+
                     |
  parsing        source, declarations, _cognitive, _ranges, _tokens
                     |
  foundations    _metrics_types, _masking, _hotspots, config, git_tools,
                 instructions, _runner (process execution), _catalog (tool selection)
```

| Layer | Owns | May import |
|---|---|---|
| **foundations** | Data types, config defaults, git invocation, masking primitives | nothing internal |
| **parsing** | Reading files once, extracting declarations, complexity, ranges, tokens | foundations |
| **scanners** | Producing findings: sizes, duplicates, dead code, idioms, near-duplicates, history, and — via `_adapters` — whatever the external analyzers report | foundations, parsing, `_runner` |
| **scoring** | Turning findings into aspects, categories, an overall, a grade, and whether the evidence supports verifying it (`_verification`) | foundations, parsing (types only), the evidence boundary |
| **assembly** | Running the scan, running the analyzer pool (`_analysis`) and stating what it found (`_documents`), recording the built-in detectors as their own source tier (`_built_ins`), ordering the work by risk against effort and recomputing each item's worth (`_work_order`), assembling the report dict, invoking the scorer once | anything below |
| **presentation** | Markdown, PR comment, SARIF, baseline, remediation prompt, and `_evidence_view` — the single place the estimate/range/evidence/verified-grade wording is decided | foundations, the report dict |
| **entry** | Argument parsing, transport, output routing, exit codes | anything below |

## The rules, and why each exists

Each rule was bought by a specific failure. They are enforced, not advisory.

**1. Scoring may not import scanners or assembly.**
The rubric must not be able to reach back into how a finding was produced. If it could, a repo-specific special case would eventually be written and P2 (one uniform rubric) would fail silently.

**2. `_formula` and `_calibration` import nothing internal.**
They are the judgment layer — weights, bands, grade gates, the calibration constant — and they are data. A leaf cannot acquire a dependency on scanning, so the rubric cannot come to depend on what it is scoring.

**3. Presentation may not import the scoring internals.**
`renderers`, `prompts`, and `sarif` consume the report dictionary. Today they import only `_hotspots` (a formatting helper) and `config`. This keeps one path to a score: if a renderer could compute one, two numbers could disagree, which is the class of bug that produced an overall contradicting the categories printed beside it.

**4. `evidence` imports nothing internal.**
The normalization boundary is deliberately a leaf. Everything it needs arrives as an argument. This is what makes it a *boundary* rather than another participant — see [ADR 001](adr-001-evidence-and-verification.md) §3.

**5. The calibration derivation calls the shipped scorer.**
`_derive` imports `_aspects`, `_formula`, and `_pressures` and runs the same functions a live report runs. It may not restate the rollup. Three consecutive audits found the derivation differing from the live path by exactly one step — category rounding, then the untested cap, then per-aspect rounding — and each time the corpus median survived while the per-repository claim did not. "The same pipeline" is only true when there is one pipeline.

**6. No import cycles.**
One existed: `_derive` needed the scorer and the scorer needed the calibration, so `_derive` imported from inside a function body. Splitting `scoring` into `_pressures` / `_aspects` / `scoring` removed it. Cycles are how layering rots without anyone deciding to rot it.

## Data flow

```text
files on disk
  -> SourceIndex          each file read once, parsed once
  -> scanners             findings + counts
  -> report_summary       populations and finding counts
  -> dimension_pressures  counts as rates over their populations
  -> aspect_scores        13 aspects, 0-5 or None for unmeasured
  -> categories           five ISO categories, weighted means, rounded as displayed
  -> estimate + range     point estimate; interval with unknowns priced 0 and 5
  -> verified grade       banded from the interval floor when evidence allows,
                          null when it does not, with blockers only for a grade
                          that was actually issued
  -> report dict          + schema_version
  -> renderers / prompts / sarif / baseline
```

Two properties of this flow are load-bearing and each has a test:

- **Rates, not counts.** Every pressure divides by the population it was drawn from. The 0.5.0 model counted absolutely and therefore scored repository *size*: Django, pytest, black and eight others all scored 0.0/F while a 53-file toy scored 4.6/A.
- **Absence is not a value.** A count the report does not carry produces an unmeasured aspect, never a zero. Six audit rounds were spent on individual instances of this before it was stated as a property.

## Invariants and where they are enforced

Two columns, deliberately. **Property** means the test varies the real input space or the real field set, so a case nobody thought of is still covered. **Regression** means it pins specific scenarios — valuable, but it only proves what it enumerates. An audit found this table claiming enforcement on the strength of test *names*, with a promise mapped to a corpus-median test that never checked the arithmetic it was cited for. The distinction is now stated rather than implied, and `test_architecture.py` fails the build if a test named here does not exist.

| Invariant | Enforced by | Strength |
|---|---|---|
| Layering and acyclicity above | `test_architecture.py` | Property — reads the real import graph |
| Withholding any single summary input cannot raise the floor or the grade | `test_withholding_any_single_input_cannot_raise_the_floor_or_the_grade` | Property over summary keys; **regression only** for history, which is removed as a whole block rather than field by field |
| `maintainability_range` always contains `maintainability_estimate` | `test_the_interval_always_contains_the_score` | Regression — five named configurations |
| The estimate equals the weighted mean of the printed categories | `test_the_overall_is_the_weighted_mean_of_the_printed_categories` | Regression over six reports, including untested and unknown-bearing ones |
| Every advertised aspect carries weight somewhere | `test_every_scored_aspect_carries_weight_in_some_category` | Property — compares the declared aspect set against the weighted set |
| Derivation agrees with the live scorer | `test_derivation_matches_live_score_report_repo_by_repo` | Property over all 40 corpus repositories |
| Absence never resolves into a better-defined state | `test_deleting_a_field_never_resolves_it_into_a_better_defined_state` | Regression — one field |
| Concealing any required input withholds verification, never raises the floor and never improves the grade | `test_concealing_any_required_node_withholds_verification` | **Property** — all 28 typed inputs, from production evidence |
| Restoring a concealed input recovers the model, the grade and the score exactly | `test_restoring_a_concealed_node_recovers_everything` | **Property** — all 28 typed inputs |
| An aspect whose input is concealed reports unmeasured, never a re-estimate | `test_an_aspect_that_uses_a_concealed_input_is_unmeasured_not_re_estimated` | **Property** — dependency derived by sweeping, not declared |
| Every scored aspect can be unmeasured by concealing some required input | `test_every_scored_aspect_is_unmeasured_by_concealing_some_required_input` | **Property** — coverage over the aspect set |
| Fully measured evidence collapses the range | `test_fully_measured_evidence_collapses_the_range` | Property — on a fixture where every aspect is measured |
| Complete NotApplicable evidence contributes no score or uncertainty | `test_not_applicable_is_excluded_instead_of_priced_as_clean_or_unknown`, `test_not_applicable_is_complete_evidence` | Regression — rollup arithmetic and a production young repository |
| Measured(0), Unknown and NotApplicable survive a JSON round trip | `test_the_three_states_remain_distinguishable_across_a_json_round_trip` | Regression — one of each state |
| Every declared invariant violation fails closed | `test_every_declared_summary_subset_is_enforced`, `test_every_declared_summary_sum_is_enforced`, `test_every_declared_history_subset_is_enforced` | **Property** — iterate the shipped relation tables and assert the *specific* validator fired |
| The whole sweep is deterministic | `test_the_whole_sweep_is_deterministic` | Property — byte-identical documents across runs |
| Unknown production evidence is never resurrected | `test_unknown_production_evidence_is_never_resurrected` | Regression — one field |
| Impossible values and subset violations are rejected | `test_a_value_no_scanner_could_produce_is_rejected`, `test_a_subset_count_larger_than_its_set_is_rejected` | Regression — enumerated field kinds and one cross-field pair |
| History window is independent of cache depth | `test_fix_breadth_window.py` | Property over four cache depths |

Recursive variation across the whole typed model now exists (`tests/test_evidence_properties.py`, ADR 001 stage 6): every one of the 28 typed scoring inputs — 23 summary, 5 nested history — is concealed one at a time from evidence generated by `build_report`, and restored, with the results scored through the production seam `scoring.score_evidence`. Cases are derived from `walk_evidence`, so a field added to either evidence dataclass is swept the day it is added.

**Human-facing rendering of these states is still stage 7.** Markdown, prompts, PR comments, SARIF and baselines are unchanged and do not surface `evidence_status` or `verified_grade`.

## Known debt

Stated rather than hidden, because an architecture document that only describes the good parts stops being usable.

- ~~Scoring consumes raw dictionaries~~ — **resolved (ADR 001 stage 4).** `score_report` normalizes at its entry and every layer below it takes typed evidence. The `.get(name, 0)` fallbacks and the `unmeasured_dimensions` companion list are deleted: a pressure is now computed only from `Measured` inputs, so there is no default left to forget to guard.
- ~~The compatibility grade is still banded from the pessimistic floor~~ — **resolved (stage 8).** `score.grade` is removed; `verified_grade` is the only letter a report carries, and it is null when the evidence does not support one.
- **Stage 5 is implemented:** `score.evidence_status` and `score.verified_grade` ship alongside the compatibility fields. [ADR 002](adr-002-null-verified-grade-in-ci.md) is rejected because it assumed `--fail-on-gate` consumes the grade; the shipped flag checks hard findings only, so no CI policy changed. The requirement list for the `default-v1` profile is frozen in `_verification.py` rather than derived from the typed model — deriving it let a new field silently change what the name demanded.
- ~~`docs/standard.md` mixes genres~~ — **resolved.** The empirical studies moved to [studies.md](studies.md); the standard now holds only the rubric, its calibration method, and the reference corpus. Mixing them was the documentation shape that let a Tier 3 claim read as settled.
- **History window materialization is not separated from analysis.** [ADR 001](adr-001-evidence-and-verification.md) stage 9.
- **The score does not consume analyzer measurements.** `--analyzers` runs ten tools, reports their coverage, their findings and their measurements with cross-tool disagreement — and the maintainability score still derives entirely from the built-in detectors. The report says so rather than letting a reader assume the number reflects the tools beside it. Closing the gap means re-deriving the calibration constant, which moves every corpus score ([release plan](release-plan.md) 3.5–3.6).
- **Two live defects in shipped flags**, both reproduced and both blocking later work:
  - `--changed-only` reports a whole-repository grade for a diff. On this repository it returns `maintainability_estimate 4.2`, `evidence_status complete`, over 2 files and **zero declarations**. Any PR-scoped CI run inherits it. [ADR 005](adr-005-insufficient-population.md).
  - `--fail-on-new` false-fires on moved code. Finding identity embeds the start line, so inserting one import above an untouched function makes it read as simultaneously fixed and new. This also makes recurrence tracking impossible. [ADR 009](adr-009-scan-history.md).
- **[ADR 005](adr-005-insufficient-population.md) through [009](adr-009-scan-history.md) are accepted and unimplemented.** Ten proposed modules — `_runner`, `_analyzers`, `_concepts`, `_corroborate`, `_bands`, `_catalog`, `_practice`, `_pillars`, `_scan_history`, `_identity` — do not exist. The target architecture section describes them; `src/` does not contain them, and this document must not read as though it does.

## Extension points

- **A new detector** belongs in scanners, returns findings, and adds a count to `report_summary`. It becomes scored only by being given weight in `_formula.CATEGORY_ASPECTS`; an aspect with no weight fails the build.
- **A new output format** belongs in presentation and reads the report dictionary. It must not compute a score.
- **A new external analyzer** is ingested as SARIF and kept as `external_findings` with its provenance. Per [adapters](adapters.md), do not pretend every analyzer has the same semantics. **[ADR 006](adr-006-analyzer-evidence.md) supersedes this extension point** — analyzers become the primary evidence source rather than an ingested side-channel. Until it ships, SARIF ingest is the only path.

## Where the design is going

The analyzer pipeline, the pillar view, the band matrix and the work order are specified in [target architecture](target-architecture.md) and are not all shipped. Keeping them out of this file is deliberate: this one describes the code as it is.

## Decisions embodied in this document

Every design point above traces to a record. Nothing here is a preference someone remembered.

| Design point | Recorded in |
|---|---|
| FOSS analyzers produce the evidence; built-ins demoted to a labelled fallback | [ADR 006](adr-006-analyzer-evidence.md) |
| Several tools per concept, combined with weights; spread becomes the interval | [ADR 006](adr-006-analyzer-evidence.md) |
| Analyzer coverage always reported; unavailable is never a clean result | [ADR 006](adr-006-analyzer-evidence.md), P8 |
| Metric emitters vs verdict emitters; only metric emitters supply denominators | [ADR 008](adr-008-translation-and-decision.md) |
| The rubric sets tool thresholds; project lint config never moves the score | [ADR 008](adr-008-translation-and-decision.md) |
| Measurements, counts and populations all survive to the report | [ADR 008](adr-008-translation-and-decision.md) |
| Band matrix instead of binary thresholds; gates stay binary | [ADR 008](adr-008-translation-and-decision.md) |
| The agent never calls an LLM; it produces that model's input | [ADR 008](adr-008-translation-and-decision.md), P1 |
| CLI for CI, MCP for chat, one core, no combined server | [ADR 008](adr-008-translation-and-decision.md) |
| The report is first-class; Markdown retrievable from every entry point | [ADR 008](adr-008-translation-and-decision.md) |
| Work order with location, target, computed delta and verification | [ADR 008](adr-008-translation-and-decision.md) |
| No rate without a denominator that supports it, per aspect | [ADR 005](adr-005-insufficient-population.md), P7 |
| Scan scope is part of the result; scope escalation over silent scoring | [ADR 005](adr-005-insufficient-population.md) |
| Five pillars with declared scope; practice level never averaged with condition | [ADR 007](adr-007-pillars-and-practice.md) |
| Risk × Effort ordering; Fill-Ins never above Quick Wins | [ADR 007](adr-007-pillars-and-practice.md) |
| Recurring findings escalate to design-review candidates | [ADR 008](adr-008-translation-and-decision.md) |
| Depth and license policy select the pool; every deny wins | [analyzer pool](analyzer-pool.md), [config](config-schema.md#analyzer-policy-analyzers) |
| Selection by intent: the user answers concerns and density, the agent picks tools | [analyzer pool](analyzer-pool.md), [config](config-schema.md#analyzer-policy-analyzers) |
| Concern vocabulary comes from the scoring model; `measures` grows with adapters | [analyzer pool](analyzer-pool.md) |
| Every finding stays in the report; ranking orders, never filters | [ADR 008](adr-008-translation-and-decision.md) |
| Raw analyzer output is retained for the model, especially on parse failure | [ADR 008](adr-008-translation-and-decision.md) |
| Work order is a queryable set; the consumer picks the slice | [ADR 008](adr-008-translation-and-decision.md) |
| Set deltas are recomputed, never summed from per-item deltas | [ADR 008](adr-008-translation-and-decision.md) |
| Coverage gaps reported per language and concern, with the prerequisite named | [ADR 006](adr-006-analyzer-evidence.md) |
| Availability proven by invocation; the agent never installs anything | [ADR 006](adr-006-analyzer-evidence.md) |
| Scans append to a durable history; trends over comparable records only | [ADR 009](adr-009-scan-history.md) |
| Finding identity is content-addressed, never line-coupled | [ADR 009](adr-009-scan-history.md) |
| Trends describe past scans; forecasting stays forbidden | [ADR 009](adr-009-scan-history.md), [product intent](product-intent.md#what-it-must-never-claim) |

MCP's three primitives cover the chat requirement without inventing anything. CI does not go through MCP — a protocol hop between a runner and an exit code costs determinism and buys nothing. Each agent ships its own server as a subcommand; there is no combined server, because independent releasability is worth more than cross-tool synthesis today.

### Scans accumulate: maintainability is a trend, not a snapshot

Everything above describes one scan, and a single reading is the weaker half of the evidence. Practitioners judge a codebase by its direction — *this is getting worse*, *they keep patching around that module*, *complexity has climbed since the rewrite*. A repository at 3.8 and improving is in a different position from one at 3.8 and sliding, and no snapshot distinguishes them.

Today nothing records what a repository scored last month. `history.py` measures churn and coupling but recomputes them every run and retains nothing; `maintainability-baseline.json` is a flat list of finding fingerprints with no timestamp, commit, score or population — a suppression list for `--fail-on-new`, overwritten rather than appended.

So scans append to a durable record ([ADR 009](adr-009-scan-history.md)), default `.maintainability/history.jsonl`, one line per scan carrying the commit, scope, rubric version, analyzer coverage, populations, band distributions, scores, pillar values and finding identities. Populations and distributions are retained deliberately: a score that moved with nothing beneath it cannot be diagnosed.

The engine then computes, as arithmetic over stored records:

- **debt velocity** — findings introduced versus cleared per period; clearing faster than adding is improvement at any absolute score
- **growth versus quality** — is the finding rate outpacing the population? separates *getting bigger* from *getting worse*
- **score trajectory**, with the interval, so noise is not read as movement
- **recurrence** — cleared and returned, with counts and commits
- **stability** — units that keep changing while their findings never clear

Two guards. **Trends describe scans that happened**; extrapolating forward is a prediction and stays forbidden until an outcome study earns it. And **comparability is checked, not assumed** — a trend computed across a change in analyzer coverage measures the tooling, not the code, so such a series is segmented or withheld with a reason.

Determinism is restated accordingly: identical tree, config *and history* produce identical output. History is an input, and the report names the history it consumed.

**A prerequisite defect blocks all of it.** Finding identity is line-coupled — `function:{path}:{name}:{start_line}` — so inserting one import above an untouched function makes it look simultaneously fixed and new:

```text
before: function:big.py:huge:1        after: function:big.py:huge:2
looks NEW to --fail-on-new: function:big.py:huge:2
looks FIXED:                function:big.py:huge:1
```

That is a live false-positive source for the shipped `--fail-on-new` flag on any refactor that shifts lines, and it makes recurrence tracking impossible. Identity becomes content-addressed — kind, path, unit name and a hash of the unit's normalized content — with line numbers reported but never part of identity.

### Two readers, different constraints

The scoring engine and the user's language model read the same run and are bound by different rules, and the design serves both rather than collapsing them.

**The engine is deliberately conservative.** It consumes only measurements, refuses verdict output as a rate because thresholds contaminate it, and maps everything onto nine concerns. All three are lossy on purpose — that is what makes a score reproducible and comparable between repositories.

**The model is bound by none of that.** Given the raw analyzer output it can see what the engine structurally cannot: that forty unused-import findings cluster in one module and suggest a dead subsystem, that every complexity warning sits on one code path, that a whole rule category is absent because nobody enabled it. Those are real judgments about maintainability, and refusing verdict output for *scoring* was never a reason to withhold it from *reading*.

So **raw tool output is retained and exposed**, bounded per tool and marked when truncated — and kept **especially on parse failure**, which is where it matters most. A parse error means this agent could not read the output; a model usually can, and discarding it would throw away the one artifact that still had value.

One boundary holds firm: a model's judgment is never a score. It is commentary on a report, downstream and disposable, while the score stays a deterministic function of measurements. Conflating them would make the number unreproducible, which is most of what it is for.

### The friction signal

A language model has no accumulated-friction signal — no *"I have touched this module four times and it keeps fighting me."* Each turn evaluates cold, so it will patch the same bad abstraction indefinitely without ever raising the design question.

The agent has git history and a persistent baseline, so it can integrate what the model cannot: a file repeatedly patched whose findings never clear, a finding recurring after two remediation attempts, files that keep changing together. Those **escalate** out of the nit class into design-review candidates.

This is the answer to nit-loops, and it needs stable finding identity across runs, which today's baseline lacks.

Two outputs, both 1–5, never averaged together: **a score for the condition of the code** and **a maturity level for the practices around it**. Both fall out of the same run. Step 12 is the product's point — the score exists so the prompt has somewhere true to aim.

**On tools disagreeing.** Three tools measuring the same function returned 14, 14 and 8, because radon and lizard count boolean operators and comprehensions while mccabe's path graph does not. That is ordinary measurement variance and needs no special ceremony: combine the readings with weights, keep the spread, and report the spread as the interval. The one thing not permitted is silently picking one tool and presenting its convention as the property of the code — which is what a single-source score does today, invisibly.

**Why more tools is strictly better.** Every additional tool measuring a concept adds an independent reading, and a rate built from four readings is better supported than the same rate from one. Redundancy is the point, not waste. It is also what makes step 5's spread meaningful: one tool has no spread and therefore no honest interval.

```text
  entry          cli, __main__
                     |
  presentation   renderers, prompts, sarif, baseline, _evidence_view
                     |
  assembly       report                        assembles pillars + categories
                     |
        +------------+-------------+-----------------+
        |            |             |                 |
  acquisition   practice      scoring           corroboration
  _runner       _practice     scoring ->        _concepts (registry)
  _analyzers/*  reads CI and  _aspects ->       _corroborate (spread,
  (one adapter  linter and    _pressures         strength, tolerance)
   per tool)    coverage      _formula
        |       config, not   _calibration
  fallback      source        _verification
  scanners                    evidence (boundary)
  (demoted)
        |
  parsing        source, declarations, _ranges, _tokens
        |
  foundations    _metrics_types, _masking, _hotspots, config, git_tools
```

### New components and what each owns

| Component | Owns | May import |
|---|---|---|
| **`_runner`** | Subprocess invocation, timeouts, failure isolation, version capture. **The only module permitted to spawn a process** apart from `git_tools`. | foundations |
| **`_analyzers/*`** | One adapter per tool: which languages it speaks, which concepts it measures, how to invoke it, how to parse its output into concept measurements. Adapters are leaves and know nothing of scoring. | foundations, `_runner` |
| **`_concepts`** | The measurement-concept registry — for each concept, its contributing tools, its agreement tolerance, its denominator and that denominator's floor ([ADR 005](adr-005-insufficient-population.md)). Data, like `_formula`. | nothing internal |
| **`_bands`** | The band matrix: ordered measurement ranges mapping to pressures, boundaries drawn from corpus percentiles. Data, like `_formula`. | nothing internal |
| **`_catalog`** | Reading `data/analyzer-catalog.json` and resolving the pool from the configured depth and license policy. | foundations |
| **`_scan_history`** | Appending one record per scan, reading prior records, and computing trends over comparable ones ([ADR 009](adr-009-scan-history.md)). | foundations |
| **`_identity`** | Content-addressed finding fingerprints, stable across moves and reindentation. | foundations, parsing |
| **`_corroborate`** | Combining several tools' measurements of one concept into a single evidence value plus strength (corroborated / contested / single-source / unavailable) and the observed spread. | foundations, `_concepts` |
| **`_practice`** | Detecting enforcement evidence — CI workflows, linter configuration, coverage thresholds, hook definitions — to score the ADR 007 practice level. **Reads repository configuration, never source.** | foundations |
| **`_pillars`** | The five-pillar taxonomy and each pillar's declared scope: owned, partial, delegated, out of scope. Data. | nothing internal |

### Rules the new layers add

**7. Only `_runner` and `git_tools` may spawn a process.** Analyzer adapters describe invocations; they do not perform them. This keeps timeout, isolation and version-capture policy in one place, and keeps determinism (P1) auditable — a promise that now depends on pinned analyzer versions.

**8. Analyzer adapters may not import scoring.** The same rule scanners already live under, for the same reason: an adapter that could see the rubric would eventually be tuned to it.

**9. Corroboration happens before the evidence boundary.** `evidence` receives already-combined values with their strength and provenance. The boundary stays a leaf and stays the single normalization point; it does not learn about tools.

**10. `_practice` may not read source files.** Practice level is a claim about enforcement, not about code. If it could read source, it would drift into being a second, uncalibrated condition score.

**11. Practice level and code condition are never combined.** No function returns their average. [ADR 007](adr-007-pillars-and-practice.md) invariant 2 exists because a single composite number would destroy both.

### What this costs

- **Determinism becomes conditional.** P1 currently holds because the tool is pure computation over a file tree. With external analyzers it holds only for pinned versions on a given platform, and the report must record the versions that produced it. This weakens the strongest promise in [product intent](product-intent.md) and the promise's wording has to change with it.
- **Runtime rises** from milliseconds to seconds or minutes, making `--changed-only` load-bearing rather than convenient.
- **Failure modes multiply**: a tool can be absent, wrong-versioned, slow, crash, or emit unparseable output. Each is a distinct `Unknown` reason, and none may fail the run or improve a score.
- **The fallback scanners must be labelled** in code as the demoted single-source tier, or a future reader will mistake them for the primary path exactly as this one did.

## Proposed extension boundaries — not implemented

Two proposed decisions extend the bounded work order without changing what the
standard score means:

- [ADR 003](adr-003-deterministic-semantic-policy.md) specifies a type-aware
  semantic-analysis path. Language-native analyzers and checked-in repository
  policy may produce universal findings, configured policy violations, or
  explicitly non-gating design-review candidates. They do not get to modify
  rubric weights or grade bands.
- [ADR 004](adr-004-economic-context.md) specifies a separate economic-context
  path. Repository measurements and user-supplied business context may produce
  transparent low/base/high impact scenarios. Those scenarios rank the work
  order; they do not feed scoring or grading and are not predictions until an
  outcome study earns that word.

The intended dependency direction is:

```text
language-native analyzers / SARIF     checked-in semantic policy
                 \                         /
                  -> normalized semantic findings
                              |
repository measurements     configured economic context
                 \                         /
                  -> economic impact scenarios
                              |
                  bounded prioritized work order
```

Both paths terminate in report data consumed by presentation. Neither may
reach backward into `_formula`, `_calibration`, `_aspects`, or grade policy.
Until the ADRs are accepted and implemented, this diagram is a constraint on
future work, not a description of shipped behavior; its invariants therefore
do not appear in the enforced table above.

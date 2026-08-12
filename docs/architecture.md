# Architecture

How the package is layered, which layer may depend on which, and the invariant each one owns.

This describes the code **as it is**, not as intended. Where reality falls short of a decision, it is listed under [Known debt](#known-debt) rather than described aspirationally. Direction of travel is kept in the [decision register](decisions.md); the explicitly labeled proposal section at the end maps those decisions onto the current layers without claiming they ship.

The layering is enforced by `tests/test_architecture.py`, which reads the real import graph. A rule stated here and not enforced there is decoration, and this document tries not to contain any.

## Layers

Dependencies point downward only. No cycles.

```text
  entry          cli, __main__
                     |
  presentation   renderers, prompts, sarif, baseline,       reads the report dict
                 _evidence_view (shared phrasing)
                     |
  assembly       report                                     builds the report, calls the scorer
                     |
        +------------+------------+
        |                         |
  scanners                   scoring
  metrics, duplication       scoring -> _aspects -> _pressures
  deadcode, idioms           _formula, _calibration (rubric data)
  _verification (evidence sufficiency)
  similarity, history        _derive (calibration fit), evidence (boundary)
        |                         |
        +------------+------------+
                     |
  parsing        source, declarations, _cognitive, _ranges, _tokens
                     |
  foundations    _metrics_types, _masking, _hotspots, config, git_tools, instructions
```

| Layer | Owns | May import |
|---|---|---|
| **foundations** | Data types, config defaults, git invocation, masking primitives | nothing internal |
| **parsing** | Reading files once, extracting declarations, complexity, ranges, tokens | foundations |
| **scanners** | Producing findings: sizes, duplicates, dead code, idioms, near-duplicates, history | foundations, parsing |
| **scoring** | Turning findings into aspects, categories, an overall, a grade, and whether the evidence supports verifying it (`_verification`) | foundations, parsing (types only), the evidence boundary |
| **assembly** | Running the scan, assembling the report dict, invoking the scorer once | anything below |
| **presentation** | Markdown, PR comment, SARIF, baseline, remediation prompt, and `_evidence_view` — the single place the estimate/range/evidence/verified-grade wording is decided | foundations, the report dict |
| **entry** | Argument parsing, output routing, exit codes | anything below |

## The rules, and why each exists

Each rule was bought by a specific failure. They are enforced, not advisory.

**1. Scoring may not import scanners or assembly.**
The rubric must not be able to reach back into how a finding was produced. If it could, a repo-specific special case would eventually be written and P2 (one uniform rubric) would fail silently.

**2. `_formula` and `_calibration` import nothing internal.**
They are the judgment layer — weights, bands, grade gates, the calibration constant — and they are data. A leaf cannot acquire a dependency on scanning, so the rubric cannot come to depend on what it is scoring.

**3. Presentation may not import the scoring internals.**
`renderers`, `prompts`, and `sarif` consume the report dictionary. Today they import only `_hotspots` (a formatting helper) and `config`. This keeps one path to a score: if a renderer could compute one, two numbers could disagree, which is the class of bug that produced an overall contradicting the categories printed beside it.

**4. `evidence` imports nothing internal.**
The normalization boundary is deliberately a leaf. Everything it needs arrives as an argument. This is what makes it a *boundary* rather than another participant — see ADR 001 §3.

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
- **History window materialization is not separated from analysis.** ADR 001 stage 9.

## Extension points

- **A new detector** belongs in scanners, returns findings, and adds a count to `report_summary`. It becomes scored only by being given weight in `_formula.CATEGORY_ASPECTS`; an aspect with no weight fails the build.
- **A new output format** belongs in presentation and reads the report dictionary. It must not compute a score.
- **A new external analyzer** is ingested as SARIF and kept as `external_findings` with its provenance. Per [adapters](adapters.md), do not pretend every analyzer has the same semantics. **[ADR 006](adr-006-analyzer-evidence.md) supersedes this extension point** — analyzers become the primary evidence source rather than an ingested side-channel. Until it ships, SARIF ingest is the only path.

## Target architecture — ADR 006 and 007, not implemented

The layer model above is what the code does today. [ADR 006](adr-006-analyzer-evidence.md) and [ADR 007](adr-007-pillars-and-practice.md) change it materially, and the shape is recorded here so the work has a target rather than a direction.

The current design inverts its own stated principle. The README says *"pair this tool with mature analyzers … don't replace them"*, and `src/` contains six homegrown reimplementations of exactly those analyzers, with external tools relegated to optional SARIF ingest. ADR 006 turns that the right way up.

### The pipeline, plainly

This is not complicated, and the rest of this section is detail on top of it. End to end:

```text
1.  a commit, or a working tree
2.  run every quality tool that is available and speaks one of its languages
       -- twenty-four tools is fine; more sources is better, not worse
       -- the agent sets each tool's thresholds from the rubric, ignoring
          project-local lint config, so no tool's opinion moves the score
3.  each tool emits its own findings and metrics, in its own format
4.  normalize each output onto shared measurement concepts
       -- "cyclomatic complexity", "duplication ratio", "dead code", "docstring coverage"
5.  where several tools measured one concept, combine them with weights
       -- a weighted mean, and record the spread; disagreement is variance, not a crisis
6.  the agent attributes each unit as production or test -- tools don't know
7.  apply the RUBRIC's thresholds to the measurements   -> counts
8.  divide counts by the population they came from, so the result is a rate, not a size
9.  apply the rubric's aspect weights          -> aspect scores    (0-5)
10. apply the rubric's category weights        -> category scores  (0-5)
11. weighted mean of categories                -> OVERALL SCORE    (1-5)
12. separately, detect enforcement evidence    -> MATURITY LEVEL   (1-5)
       -- linter wired to CI? coverage gate? complexity thresholds configured?
13. rank the weak areas by risk x effort, escalating recurring findings
14. emit the REPORT -- scan results, scores, coverage, evidence  (the record)
15. hand the rubric + scores + ranked areas + real findings to the user's LLM
       -> improvement prompts aimed at what actually scored badly  (the action)
```

Steps 14 and 15 are both first-class. The **report** is the record of what was examined and what was found; the **prompt** is one thing you can do with it. A user who only wants to read the findings never has to invoke a model.

Step 7 is the seam. **Everything above it is tool-shaped; everything below it is rubric-shaped.** No tool's threshold survives it — only its measurements.

The agent itself never calls a language model. Step 14 hands structured input to *the user's* model, which keeps the audit deterministic and offline (promise **P1**) and keeps everything the agent asserts reproducible from a pinned run.

### Two kinds of tool, and why the difference decides everything

Auditing the scoring contract against what real tools emit produced one finding that constrains the whole design:

| Kind | Reports | Can supply | Examples |
|---|---|---|---|
| **Metric emitter** | A value for *every* unit, threshold-free | Numerators **and denominators** | lizard, radon, multimetric, jscpd statistics |
| **Verdict emitter** | Only units breaching *its own* threshold | Located findings only | eslint, ruff, pylint, most linters |

Two measurements make this concrete. The same one-function file, cyclomatic complexity 11, through eslint:

```text
eslint threshold  5 -> 1 finding
eslint threshold 10 -> 1 finding
eslint threshold 15 -> 0 findings     <- identical code
eslint threshold 20 -> 0 findings
```

Consume those verdicts and the score becomes a function of the repository's `eslint.config.mjs`, which falsifies **P2** — one uniform rubric for every repository. And at threshold 15 the output is *empty*: nothing reveals that a function exists, so no denominator can be formed. lizard on the same file reports one function at CCN 11 — numerator and denominator together.

That is why rates may come only from metric emitters. Feeding verdict-only output into a rate would reintroduce the 0.5.0 bug — counting absolutely and therefore scoring repository *size* — from a new direction.

A further wrinkle: eslint's JSON carries no metric field. The value 11 exists **only inside the human-readable message string**, so recovering it means parsing prose that changes between releases. Pinned versions and tests, or the tool stays verdict-only.

### What no tool can supply

- `idiom_concern_count` and `risk_findings` have no FOSS equivalent and stay native permanently.
- Production/test attribution is the agent's path classification. Tools measure; the agent attributes. Eleven of the 23 summary inputs are production-only variants that depend on it.

### The scoring contract is exact

The scorer consumes 28 typed inputs — 23 on `SummaryEvidence`, 5 on `HistoryEvidence` — and every one is read by `_pressures` or `_aspects`. No dead inputs, none undeclared. Each is a count or a population; **none accepts a measurement**, which is precisely why step 7 exists.

### Outputs: the report is the product, the prompt is one use of it

The tool already emits a Markdown report, a JSON report, a PR comment, SARIF and a baseline. Those stay. What changes is what the report has to *say* once analyzers, pillars and population floors exist — a report that shows scores without showing what produced them is the same failure as the A+, one layer out.

Every report gains:

| Section | Answers |
|---|---|
| **Analyzer coverage** | Which tools ran, which were unavailable and why, their versions, the depth and license policy in force |
| **Score with attribution** | Each measurement's contributing tools, their spread, and its evidence strength |
| **Pillar view** | All five pillars with scope status; practice level and code condition side by side, never averaged |
| **Withheld measures** | Every aspect suppressed for insufficient population, naming the observed count and the floor |
| **Findings** | Unchanged — locations, severities, the existing tables |
| **Recurrence** | Findings that have returned after remediation, escalated as design-review candidates |
| **Ranked work** | Risk × Effort ordering: Quick Wins first, Fill-Ins never above them |

Two reports with different analyzer coverage are not comparable, so coverage is not an appendix — it belongs beside the score.

### Entry points

| Entry point | For | Contract |
|---|---|---|
| **CLI** | CI runners, Makefiles, merge gates | Exit codes, files on disk, never prompts, deterministic |
| **MCP server** | Chat, slash commands, agentic loops | `tools` run the audit, `resources` expose rubric and report, `prompts` are the slash command |

**Getting the Markdown out.** From the CLI it is already a file: `--format markdown --output report.md`. From chat the same document is exposed as an MCP resource with a Markdown media type, so the client can display it inline *and* the user can save it — one rendering, two ways to reach it. The chat path must never produce a summary that the downloadable file does not contain; if the two disagree, the file is authoritative and the summary is the bug.

MCP's three primitives cover the chat requirement without inventing anything. CI does not go through MCP — a protocol hop between a runner and an exit code costs determinism and buys nothing. Each agent ships its own server as a subcommand; there is no combined server, because independent releasability is worth more than cross-tool synthesis today.

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

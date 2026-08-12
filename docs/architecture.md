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
                     |
  assembly       report, _analysis                          builds the report, calls the scorer
                                                             _analysis runs the analyzer pool
                     |
        +------------+------------+
        |                         |
  scanners                   scoring
  metrics, duplication       scoring -> _aspects -> _pressures
  deadcode, idioms           _formula, _calibration, _bands (rubric data)
  _adapters (external)       _corroborate (several tools -> one reading)
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
| **assembly** | Running the scan, running the analyzer pool (`_analysis`), assembling the report dict, invoking the scorer once | anything below |
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
- **Two live defects in shipped flags**, both reproduced and both blocking later work:
  - `--changed-only` reports a whole-repository grade for a diff. On this repository it returns `maintainability_estimate 4.2`, `evidence_status complete`, over 2 files and **zero declarations**. Any PR-scoped CI run inherits it. [ADR 005](adr-005-insufficient-population.md).
  - `--fail-on-new` false-fires on moved code. Finding identity embeds the start line, so inserting one import above an untouched function makes it read as simultaneously fixed and new. This also makes recurrence tracking impossible. [ADR 009](adr-009-scan-history.md).
- **[ADR 005](adr-005-insufficient-population.md) through [009](adr-009-scan-history.md) are accepted and unimplemented.** Ten proposed modules — `_runner`, `_analyzers`, `_concepts`, `_corroborate`, `_bands`, `_catalog`, `_practice`, `_pillars`, `_scan_history`, `_identity` — do not exist. The target architecture section describes them; `src/` does not contain them, and this document must not read as though it does.

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
7.  normalize measurements through the RUBRIC's band matrix -> per-unit pressure
       -- bands, not a binary threshold; CCN 14 and CCN 45 must not
          both collapse into "1 failure"
       -- measurements, counts and populations all survive this step;
          the report carries all three, the score reads what it needs
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

### Three kinds of data, all kept

Counts, populations and measurements are different taxonomies of fact about the code, and forcing them into one shape destroys information the reader needs.

| Kind | Example | Who needs it |
|---|---|---|
| **Measurement** | this function has CCN 14; this file has MI 42.23 | The band matrix, the report, and any model reading the report |
| **Count** | 7 declarations exceed the complexity band | The rate, and the finding tables |
| **Population** | 629 declarations across 123 files | The denominator, and the sufficiency check |

The scoring inputs are counts and populations because that is what a *rate* needs. That is a fact about the score, not a reason to throw the measurements away. All three travel to the report; the score reads the two it needs.

The raw distribution is the part a language model can actually reason with. "Seven functions failed" supports one sentence. "Seven functions failed, worst at CCN 45, median 6, and they cluster in two modules" supports a plan.

### Bands, not binary thresholds

A threshold turns CCN 14 and CCN 45 into the same fact — one failure each — and the difference between a function that needs a guard clause extracted and one that needs redesigning is exactly the information the reader wanted.

So a measurement is normalized through a **band matrix**: ordered ranges, each mapping to a normalized pressure between 0 and 1, weighted and averaged across the population.

```text
cyclomatic complexity      band     pressure
    1 - 5                  clean       0.00
    6 - 10                 mild        0.25
   11 - 15                 elevated    0.50
   16 - 25                 high        0.75
   26 +                    severe      1.00
```

Band boundaries are corpus percentiles rather than invented numbers, which is the grounding this project already uses elsewhere — the cognitive-complexity thresholds sit at the 94th and 97th percentiles of 21,300 corpus declarations. Boundaries are rubric data, visible in `_formula`, arguable by changing one row.

Hard gates keep their binary character: a gate is a policy line, and a line is meant to be crossed or not. Bands drive the *score*; gates drive the *exit code*.

### Scan scope is part of the result

A five-line function and a 4,500-line multi-module commit are not the same measurement problem. The small one reaches a high score trivially, and saying so is common sense that the tool must encode rather than assume the reader supplies.

Every report therefore states its **scope** — whole repository, changed-only, or a path subset — and when the scanned population is small relative to the repository, the report says so and recommends a whole-repository rescan for a meaningful reading. Withholding a score ([ADR 005](adr-005-insufficient-population.md)) is the floor case; **scope escalation is the useful case**, because the user usually can get a real answer by widening the scan.

This is a live defect, not a hypothetical. Today `--changed-only HEAD~1` on this repository reports **estimate 4.2, evidence status complete, over 2 files and zero declarations**, against a scale calibrated on whole repositories. Any PR-scoped CI run inherits it.

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

### The product, in one paragraph

A user should not have to know which of 444 analyzers exist, write scripts to invoke them, or reconcile their output formats. They answer two questions — **what do you want examined** and **how deep** — inside a license policy their organization sets once. The agent resolves the toolset, runs it, and returns two things: the compiler-style errors (located, specific, fixable) and the scores (compact, comparable, trendable). Both go in the report; neither replaces the other.

That is the whole value proposition, and every mechanism below exists to serve it.

### Selection by intent: concerns, then density, then policy

Three independent selectors, answered once and persisted so CI is reproducible:

| Selector | Question it answers | Values |
|---|---|---|
| **concerns** | What do you want examined? | `complexity`, `duplication`, `dead-code`, `documentation`, `structure`, `testing`, `style`, `types`, `metrics`, or `all` |
| **depth** | How thorough? | `baseline`, `moderate`, `heavy`, `all` |
| **license policy** | What may we legally run? | `permissive` … `unverified` |

The pool is the intersection, resolved automatically:

```text
$ resolve_pool --concerns duplication,dead-code
  jscpd     measures duplication
  lizard    measures complexity,duplication,metrics,structure
  ruff      measures complexity,dead-code,style
  vulture   measures dead-code

$ resolve_pool --concerns documentation
  interrogate  measures documentation
  pydocstyle   measures documentation,style
```

**The concern vocabulary is the scoring model's, not an invented one**, so an answer to "what do you care about?" maps onto aspects that actually exist and can actually move a score.

It also cannot be sourced from the catalog's upstream data, and that is worth stating plainly: the upstream tags are languages, ecosystems and frameworks — `rails`, `nodejs`, `spring` — and **367 of the 444 eligible tools carry no concern tag at all**. What a tool measures can only be known by running it, so the `measures` field is populated exactly as fast as adapters are written, and the upstream tags are kept separately as `upstream_tags` rather than dressed up as concerns.

### Which tools run: the catalog, depth and license policy

The pool is not hardcoded. [`data/analyzer-catalog.json`](../data/analyzer-catalog.json) holds **759 tools** — 755 from the analysis-tools.dev database pinned at a recorded commit, plus 4 verified locally — each with its license, license class, languages and source. **444 are eligible**: open-source class, current, language-targeting, not security-only.

Two independent selectors narrow it, because *how much work* and *what may we legally run* are different questions:

- **depth** — `baseline`(4) / `moderate`(10) / `heavy`(14) / `all`(444). A tier below `all` is a promise the tool works; nothing enters one until it has been installed, run and parsed.
- **license policy** — `permissive`(366) / `copyleft-weak`(400) / `copyleft-any`(444) / `commercial-free-tier`(476) / `unverified`. Some organizations forbid copyleft outright, so the policy is enforceable rather than advisory.

Both are set in the `analyzers` block of the config file, or answered interactively on first run at a terminal, and both are **recorded in the report** — a score from four tools and a score from forty are not the same measurement and must not be silently comparable. Individual tools and whole license classes can be denied; **every deny wins, including over an explicit allow**, because an organization's prohibition must not be overridable per repository.

Full inventory and the classification rules: [the analyzer pool](analyzer-pool.md). Config fields: [config schema](config-schema.md#analyzer-policy-analyzers).

### The five pillars, and the two axes that are never averaged

Reporting is organized by the five-pillar framework ([ADR 007](adr-007-pillars-and-practice.md)), with each pillar's scope declared rather than left silent:

| Pillar | Position |
|---|---|
| **Readability** | Partial — linter conformance, docstring coverage, declaration size |
| **Maintainability** | Owned — the existing ISO 25010 decomposition is this pillar's detail view |
| **Efficiency & Scalability** | Out of scope permanently — needs profiling and runtime telemetry |
| **Security** | Delegated to `secure-code-agent`, named so silence is not read as safety |
| **Testability** | Partial — test presence, declaration size, policy gates |

Each pillar reports **two values that are never combined**:

- **Practice level (1–5)** — is the standard *enforced*? Detected from CI configuration, linter configuration, coverage gates and thresholds. `_practice` reads configuration, never source.
- **Code condition** — what the analyzers found, as rates over populations.

The hello-world that scored 5.0/A+ is *practice level 1, condition unmeasured*. That is the truth, and no single composite number can express it. This is the concept the six original promises lacked, and why [product intent](product-intent.md#what-it-promises) gained **P7** (a score only where enough was examined) and **P8** (every report states what examined it).

### Coverage gaps, and telling the user how to close them

Detecting what the repository is written in, knowing which tools cover it, and knowing which of those can actually run are three facts the agent already has. Composed, they answer a question no current tool answers: **what part of this codebase did nobody look at, and what would it take to look?**

The gap is rarely "no coverage." Multi-language tools reach almost everything, so the honest gap is *depth per concern*. On a tree that is 60% Java:

```text
  complexity     lizard, multimetric
  duplication    jscpd, lizard
  dead-code      NONE -- 58 cataloged tools could cover it
  documentation  cloc, multimetric
  structure      lizard
  testing        NONE -- 58 cataloged tools could cover it
  style          NONE -- 58 cataloged tools could cover it
  types          NONE -- 58 cataloged tools could cover it
```

Four of nine concerns unexamined on the majority language. Without this section a reader sees scores and assumes they were earned across the board.

So every report carries a coverage gap list, and each gap says what would close it: the tools, and the prerequisite runtime — a JDK for PMD and Checkstyle, Node for the JS toolchain, the Go or Rust toolchain, the .NET SDK.

**The agent never installs anything.** Installing is a network and privilege action and it is the user's decision. What the agent emits is an *environment work order* in the same shape as the code work order — what is missing, why it matters, and the exact command — so a human can run it or hand it to their own AI agent to run. Same artifact, either consumer.

**Availability is proven by invocation, never by `PATH`.** Measured here: `/usr/bin/java` exists and `command -v java` succeeds, but it is the macOS stub with no JDK behind it, so PMD refused to run through it. Presence on `PATH` says nothing about whether a tool works.

Exit codes are no better a signal on their own — many linters exit non-zero to report findings, and a launcher can exit zero having done nothing. So a tool counts as available only when it has been invoked and its output validated against an expected shape. A tool that would otherwise be recorded as having run, found nothing, and contributed a clean result is the hello-world A+ arriving through a new door.

A language or concern with nothing running against it is `Unknown` in the score, never clean.

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

### What a compiler outputs, and what this must output

A compiler is useful because of what it emits, and it is worth being precise about what that is: **`file:line:col`, a specific defect, and a check you can re-run.** It never says "your code is 4.2 out of 5." It says *this, here, is wrong* — and when you fix it and recompile, the message is gone or it is not. That loop is the entire value.

Scores do not close a loop. "Modularity 3.8" tells nobody what to change, and a bare finding list produces nit loops because nothing says which items matter. So the agent's primary actionable artifact is a **work order**: every entry locatable, measured, targeted and verifiable.

Each work item carries:

| Field | Example | Why it is there |
|---|---|---|
| **Location** | `src/maintainability_audit/history.py:217` | A compiler's first token. Without it nothing is actionable |
| **Unit** | `history_section` | What to open |
| **Measurement** | cyclomatic complexity 14 | The fact, not a grade |
| **Band and target** | `elevated`; clears below 10 | **The definition of done** |
| **Attribution** | lizard 14, radon 14, mccabe 8 | How well supported, and by what |
| **Score delta** | modularity 3.1 → 3.4 if cleared | Computed, not predicted — see below |
| **Class** | Quick Win / Major Project / Fill-In | Risk × Effort, so ordering is not by count |
| **Recurrence** | cleared twice, returned twice | Escalates to design-review candidate |
| **Verification** | `lizard src/maintainability_audit/history.py` | Re-run this and check. The compiler loop |

**The score delta is arithmetic, not prophecy.** Removing a finding and re-running the rubric gives the exact resulting score, because the rubric is a deterministic function of counts over populations. So "fixing this one function moves modularity from 3.1 to 3.4" is a computed fact, and it is what makes prioritization honest: work sorts by measured impact rather than by severity labels or by whatever produced the most rows.

This is also what makes the output usable by a language model rather than merely readable. "Reduce complexity" invites slop. *"`history_section` at `history.py:217` measures CCN 14 across three tools, target is below 10, clearing it moves modularity 3.1 → 3.4, verify with `lizard …`"* is a bounded task with a stated finish line and its own test — which is precisely the bounded-prompt shape this project already has evidence for.

Two audiences, two artifacts, and they must not be conflated:

- The **score and pillar view** answer *should we invest here?* — for a lead or a stakeholder. Compact, comparable across repositories, and trendable across scans ([ADR 009](adr-009-scan-history.md)). This is what makes pattern recognition possible: one number per category, tracked over time.
- The **work order and full findings** answer *what exactly do I change, and how will I know it worked?* — for whoever or whatever does the work. Located, specific, verifiable.

**Every finding stays in the report**, whatever its rank. The work order is an *ordering* over findings, not a filter that hides them — a low-ranked item is still a fact about the code, and suppressing it would make the report a summary rather than a record. Ranking decides what leads; it never decides what exists.

The scores are the layer a model or a human uses for comparison and pattern recognition. The findings are the layer that changes code. Prompt generation draws on the findings; comparison draws on the scores; neither substitutes for the other.

An item with no verification command does not belong in the work order. If the tool cannot state how to check the fix, it has not finished thinking about the finding.

### The output is a queryable set, not a narrative

Because a run produces *all three* layers — every raw tool output, every work item, and the scores — the consumer chooses the slice. *"Fix all severity 1."* *"Just the Quick Wins."* *"Everything in the payments module."* *"Only what recurred."* None of those need a different scan; they are selections over one dataset.

So work items are **structured records with orthogonal dimensions**, and the agent does not pre-bake a single narrative:

| Dimension | Slice it enables |
|---|---|
| severity | "all sev 1" |
| Risk × Effort class | "just the Quick Wins" |
| concern | "only duplication" |
| pillar and aspect | "whatever is hurting testability" |
| path and module | "everything under `payments/`" |
| producing tool | "what did semgrep say" |
| recurrence count | "only what we've already tried to fix" |
| score delta | "the ten items that move the number most" |

Raw tool output is retained and addressable alongside, so a reader can always get back to what the analyzer actually said rather than the agent's summary of it.

**Deltas do not add, and this is the trap.** The score impact of clearing a *set* of findings is not the sum of their individual deltas: they share denominators, the pressure-to-score curve is non-linear, and the aspect → category → overall rollup rounds at each step. Ten items each worth "+0.05" do not make "+0.5."

So a selection's delta is computed by **recomputing the rubric with that whole selection removed** — same mechanism as the single-item delta, applied to the set. Any interface that lets a user pick a slice must quote the recomputed figure for that slice, never a sum of per-item numbers. Summing would be fabrication of exactly the kind [P7](product-intent.md#what-it-promises) forbids, arriving through arithmetic instead of absence.

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

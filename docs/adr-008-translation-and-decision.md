# ADR 008: The translation layer, the decision engine, and the two entry points

- Status: Accepted. Implementation progress is tracked in the [decision register](decisions.md), which is the single place it is stated
- Date: 2026-08-12
- Scope: How tool output becomes scoring input, who calls the LLM, and how the agent is invoked
- Related: [ADR 006](adr-006-analyzer-evidence.md), [ADR 005](adr-005-insufficient-population.md), [ADR 007](adr-007-pillars-and-practice.md)

## Context: what the audit found

[ADR 006](adr-006-analyzer-evidence.md) decided that external analyzers produce the evidence. Before writing a line of connector code, the existing scoring contract was audited against what real tools actually emit. Six findings, four of them load-bearing.

### 1. The input contract is fully wired

The scorer consumes exactly 28 typed inputs — 23 on `SummaryEvidence`, 5 on `HistoryEvidence`. Every one is read by `_pressures` or `_aspects`. There are no dead inputs and no undeclared ones, so the target the translation layer must hit is exact and small.

### 2. The scoring inputs are count-shaped; tools emit measurements

Every scoring input is a **count** (`function_failures`, `duplicate_blocks`, `dead_code_count`) or a **population** (`declarations_scanned`). No input accepts a measurement — because a *rate* needs a numerator and a denominator, and that is what the score is built from.

That is a fact about the score's needs, not a reason to discard the measurements. See "All three data kinds survive" below.

Tools emit one of two very different things, and conflating them is the trap:

- **Metric emitters** report a value for *every* unit: lizard gives cyclomatic complexity, NLOC and parameter count for every function; radon gives a Maintainability Index per file. Threshold-free, complete, and therefore able to supply both numerator and denominator.
- **Verdict emitters** report only units that violated *the tool's own configured threshold*: eslint, ruff, pylint, most linters. A pass produces no output at all.

### 3. Verdict emitters import their thresholds into the score — measured

The same file, one function, cyclomatic complexity 11, run through eslint at four thresholds:

| eslint `complexity` threshold | findings reported |
|---|---|
| 5 | 1 |
| 10 | 1 |
| 15 | 0 |
| 20 | 0 |

Consuming those verdicts makes the score a function of the repository's `eslint.config.mjs`. Two repositories with identical code and different lint configs would score differently, which falsifies promise **P2** — one uniform rubric applied to every repository. The rubric's threshold must be the only threshold that decides a count.

Worse, the value itself is not machine-readable. eslint's JSON carries `ruleId`, `severity`, `line`, `column` and a human sentence — *"Function 'tangled' has a complexity of 11"*. **The number 11 exists only inside the message string.** Recovering it means regex-parsing prose that changes between releases.

### 4. Verdict emitters cannot supply a denominator — measured

The same one-function file at eslint threshold 15 produces **zero messages**. Nothing in that output reveals that a function exists. lizard on the identical file reports one function with CCN 11 — numerator and denominator together.

This matters more than it looks. Rates-not-counts is the property that fixed the 0.5.0 model, where Django, pytest and black all scored 0.0/F while a 53-file toy scored 4.6/A because the model counted absolutely and therefore scored repository *size*. Feeding verdict-only output into a rate would reintroduce exactly that bug from a new direction.

### 5. Two inputs have no FOSS equivalent

`idiom_concern_count` (competing libraries for one concern) and `risk_findings` (repository-configured regex patterns) are not measured by any catalogued tool. They stay native, permanently, and should be stated as such rather than left looking like a gap.

### 6. Production/test classification belongs to the agent

Eleven of the 23 summary inputs are production-only variants. No analyzer knows which files are tests — that is the agent's path classification. Tools measure; the agent attributes.

## Decision

### Every tool is classified, and the classification constrains its use

The catalog gains a required `emits` field: `metric`, `verdict`, or `both`.

- **Only metric emitters may supply populations or feed rate-based aspects.** They are the sole source of denominators.
- **Verdict emitters may contribute findings** — a named problem at a location — and may never contribute a rate or a population.
- **A tool with a rubric-drivable threshold is promoted to metric-equivalent** for that concept, by the next rule.

### The rubric drives the tools, not the reverse

Where a tool's threshold is configurable from the command line or a generated config, the agent **sets it from the rubric** and ignores any project-local configuration for scoring purposes. eslint invoked with the rubric's complexity limit produces counts that mean what the rubric says they mean.

Where a threshold cannot be forced, the tool is verdict-only for that concept and its output never becomes a rate.

Project-local lint configuration is still honored for the developer's own workflow; it simply does not get to move the score. A score that moves with a config file is not a measurement of the code.

### All three data kinds survive; bands do the normalizing

An earlier draft of this record described step 7 as "apply the rubric's thresholds to the measurements, producing counts." That is lossy in two ways, and both matter.

**It discards the measurements.** Counts, populations and measurements are distinct, useful taxonomies. The score needs counts and populations because a rate needs a numerator and a denominator; that is a fact about the *score*, not a licence to throw the underlying values away. All three reach the report. The distribution is the part a model can reason with: *"seven functions failed"* supports a sentence, *"seven failed, worst CCN 45, median 6, clustered in two modules"* supports a plan.

**It flattens severity.** A binary threshold makes CCN 14 and CCN 45 the same fact. The difference between extracting a guard clause and redesigning a module is precisely the information the reader wanted.

So measurements are normalized through a **band matrix** — ordered ranges, each mapping to a pressure between 0 and 1, weighted and averaged over the population — with boundaries drawn from corpus percentiles rather than invented. Hard gates stay binary: bands drive the score, gates drive the exit code.

### Scan scope is part of the result

A five-line function and a 4,500-line multi-module commit are different measurement problems, and the small one reaches a high score trivially. The tool must encode that rather than assume the reader supplies it.

Every report states its scope, and a scope-limited run with a small population recommends a whole-repository rescan. Withholding is the floor case; **scope escalation is the useful case**, because widening the scan usually yields a real answer.

### Normalization is a pipeline with one shape

```text
tool process output (JSON/CSV/XML/text)
  -> adapter            parse into per-unit measurements or located findings
  -> concept            "cyclomatic complexity" on this function, from this tool
  -> combine            several tools measuring one concept -> weighted mean + spread
  -> attribute          agent classifies each unit as production or test
  -> band               RUBRIC band matrix maps each measurement to a pressure
                        (measurements, counts and populations all retained)
  -> populate           the 28 typed inputs, each Measured / Unknown / NotApplicable
  -> score              unchanged from here down
```

The seam is deliberate: **everything above `band` is tool-shaped, everything below is rubric-shaped.** No tool's opinion survives the seam, only its measurements.

Combination happens *before* banding, and only among measurements. Averaging a verdict with a number is meaningless and is not attempted.

**`attribute` is not optional, and skipping it was measured.** The scorer keeps two populations — every declaration scanned, and production declarations only — because `analyzability`, `testability` and `declaration_size` ask about the production code, and growing a test suite must not change the answer. The first bridge produced only one number and the scorer substituted it into **both** slots, so production aspects were charged for the state of the test suite. The compromise was written down in a code comment and then forgotten, which is what a compromise written in a code comment does.

The gap it papered over is not small. On flask, 1,494 of the 2,206 declarations the analyzers see are test code, and the reading moves 0.0049 → 0.0138; on scrapy, 5,938 of 9,143. Left alone, the alternative rollup was pessimistic on exactly the repositories that test themselves well.

So the bridge now produces both readings, and they are passed together in one `ExternalPressures` value rather than as a dict a caller can use twice. Supplying one and getting the old behaviour is no longer expressible.

This is the same defect class as the three wrong formulas before it: a bridge that describes itself rather than the code. The defence is the same too — `test_analyzer_production_pressure_excludes_test_declarations` fixes the population, `test_analyzer_pressures_are_a_drop_in_for_the_built_in_ones` fixes the formula, and `test_each_population_is_substituted_from_its_own_reading` fixes the wiring between them.

### The report is a first-class output, not a by-product of the prompt

The tool already emits Markdown, JSON, a PR comment, SARIF and a baseline, and those remain. But a design that describes the pipeline as ending in an improvement prompt gets built as one, and the reader who simply wants to know *what is wrong with this repository* is left invoking a language model to find out.

So the pipeline has two terminal outputs, both first-class: the **report** is the record of what was examined and found; the **prompt** is one action taken from it. Neither depends on the other, and a user who never invokes a model still gets the full record.

What the report must gain, because the new architecture produces information the current report has no place for:

- **Analyzer coverage** — tools attempted, ran, unavailable-and-why, their versions, and the depth and license policy in force. Two reports with different coverage are not comparable, so this sits beside the score, not in an appendix.
- **Attribution and spread** — per measurement, which tools produced it and how far apart they were.
- **The pillar view** — five pillars with scope status, practice level and code condition side by side and never averaged.
- **Withheld measures** — each aspect suppressed for insufficient population, with the observed count and the floor.
- **Recurrence** — findings that returned after remediation, escalated as design-review candidates.
- **Ranked work** — Risk × Effort ordering.

**Markdown delivery.** From the CLI this exists: `--format markdown --output report.md`. From chat, the identical document is exposed as an MCP resource with a Markdown media type, so a client can render it inline and the user can save it. One rendering reached two ways — the chat summary may never contain a claim the downloadable file does not, and if they disagree the file is authoritative.

### The work order is the actionable artifact

A compiler is useful because of exactly what it emits: `file:line:col`, a specific defect, and a check you can re-run. It never reports "your code is 4.2 out of 5." Fix, recompile, the message is gone or it is not — that loop is the value.

Scores close no loop, and an unranked finding list produces nit loops. So alongside the report the agent emits a **work order**, every entry locatable, measured, targeted and verifiable: location, unit, measurement, band and clearing target, tool attribution, computed score delta, Risk × Effort class, recurrence count, and a verification command.

**The score delta is arithmetic, not prophecy.** The rubric is a deterministic function of counts over populations, so removing a finding and recomputing yields the exact resulting score. "Clearing this function moves modularity 3.1 → 3.4" is computed. That makes prioritization honest — work sorts by measured impact rather than by severity labels or row counts.

It is also what makes the output usable by a language model rather than merely readable. "Reduce complexity" invites slop; *"`history_section` at `history.py:217`, CCN 14 across three tools, target below 10, clears modularity 3.1 → 3.4, verify with `lizard …`"* is a bounded task with a finish line and its own test.

An item with no verification command does not belong in the work order. If the tool cannot say how to check the fix, it has not finished thinking about the finding.

**The work order is a queryable set, not a narrative.** A run produces all three layers — raw tool output, work items, scores — so the consumer chooses the slice: *all severity 1*, *just the Quick Wins*, *everything under `payments/`*, *only what recurred*. Work items are therefore structured records with orthogonal dimensions (severity, Risk × Effort class, concern, pillar, aspect, path, producing tool, recurrence count, score delta), and raw tool output is retained and addressable so a reader can reach what the analyzer actually said.

**Set deltas are recomputed, never summed.** The impact of clearing a *selection* is not the sum of its items' individual deltas: findings share denominators, the pressure-to-score curve is non-linear, and the aspect → category → overall rollup rounds at each step. Ten items each worth "+0.05" do not make "+0.5". Any interface offering a slice must quote the rubric recomputed with that whole slice removed.

### Raw analyzer output is retained, for a reader with different constraints

The engine consumes only measurements, refuses verdicts as rates, and maps output onto nine concerns — lossy by design, and that is what makes a score reproducible.

A language model reading the report is bound by none of those rules. It can observe that forty unused-import findings cluster in one module, that every complexity warning sits on one code path, or that a rule category is missing because nobody enabled it. Refusing verdict output for *scoring* was never a reason to withhold it from *reading*.

So every tool's raw output is retained, bounded per tool and marked when truncated, and kept **especially when the adapter failed to parse it** — a parse error means this agent could not read the output, not that nobody can.

The boundary that holds: a model's judgment is never a score. It is commentary on a report, downstream and disposable; the score stays a deterministic function of measurements.

### The agent never calls an LLM

The audit stays deterministic, offline, and LLM-free — promise **P1** is unchanged. What the agent produces is the *input* to a language model:

- the rubric that was applied,
- the scores and the maturity level,
- the ranked target areas, ordered by Risk × Effort per [ADR 007](adr-007-pillars-and-practice.md),
- the real findings backing each area, with locations.

The **user's** model consumes that and writes the improvement prompt. This keeps the boundary that makes the tool trustworthy: everything the agent asserts is reproducible from a pinned run, and everything a model says about it is downstream and disposable.

### Two entry points over one core

| Entry point | For | Contract |
|---|---|---|
| **CLI** | CI runners, Makefiles, pre-merge gates | Exit codes, files on disk, no prompting, fully deterministic |
| **MCP server** | Chat, slash commands, agentic loops | Model Context Protocol: `tools` to run the audit, `resources` for the rubric and report, `prompts` for the slash command |

MCP's three primitives map onto the requirement without inventing anything: a slash command *is* an MCP prompt, "let the model read the rubric and scores" *is* MCP resources, and "run the audit" *is* an MCP tool.

The MCP server ships as a subcommand of this package rather than a separate distribution, and `secure-code-agent` does the same for itself. **No combined server.** Two independent servers keep the two tools independently releasable, which is the property that just survived a release cycle. An aggregator that synthesizes both is a reasonable later idea and a bad first one.

CI does not go through MCP. A protocol hop between a runner and an exit code buys nothing and costs determinism.

### Recurrence is tracked, because the model cannot

A finding that has been fixed and returned is not a nit; it is evidence that the abstraction is wrong. Language models have no accumulated-friction signal — no "I have touched this module four times and it keeps fighting me" — so each turn re-evaluates cold and will patch the same bad shape indefinitely.

The agent has git history and a persistent baseline and can integrate what the model cannot:

- a file repeatedly modified whose findings never clear,
- a finding recurring after two or more remediation attempts,
- files that keep changing together.

Such findings **escalate** out of the nit class into a design-review candidate, and the remediation input says so. This requires stable finding identity across runs, which today's baseline does not have; that is the prerequisite work.

## Consequences

- The catalog needs an `emits` classification per tool, and it cannot be inferred from the database — it requires running each tool. Another reason tiers grow one verified tool at a time.
- Adapters are not uniform. A metric adapter parses a table; a verdict adapter parses located findings. Two adapter shapes, not one.
- Invoking tools with generated configuration is now a requirement, not an optimization, which enlarges `_runner`.
- Message-string parsing is accepted for verdict emitters where no structured value exists, and must be pinned to a tool version and tested, because it breaks silently on upgrade.
- The remediation prompt gains ordering and escalation metadata it does not have today.
- Recurrence tracking needs stable finding fingerprints — new persistent state, and a migration for the existing baseline.

## Invariants

1. No scoring input is derived from a tool's own threshold verdict unless the agent set that threshold from the rubric.
2. Populations and rates come only from tools classified `metric` or `both`.
3. A verdict-only tool can contribute findings and can never change a denominator.
4. Combination across tools happens on measurements, before banding, never on verdicts.
5. Production/test attribution is performed by the agent, never taken from a tool.
6. The audit performs no network access and invokes no language model.
7. The CLI path never prompts and never varies its pool between runs given the same configuration.
8. A finding's identity is stable across runs, so recurrence is a fact rather than a coincidence of formatting.
9. A full report is produced on every run, whether or not a remediation prompt is generated or a model is ever invoked.
10. Every report states its analyzer coverage, and no score is presented without it.
11. The Markdown report is retrievable as a file from every entry point, and any chat-rendered summary is a strict subset of it.
12. Measurements, counts and populations all reach the report; the score consumes counts and populations without the measurements being discarded.
13. Two measurements in different bands never produce the same pressure.
14. Every report states its scan scope, and a scope-limited run whose population falls short recommends a whole-repository rescan.
15. Every work item carries a location, a clearing target and a verification command; an item missing any of the three is not emitted.
16. A work item's score delta equals the score obtained by recomputing the rubric with that finding removed.
17. A selection's score delta is obtained by recomputing the rubric with the whole selection removed, and is never a sum of per-item deltas.
18. Work items are addressable by severity, class, concern, pillar, aspect, path, tool and recurrence, and the raw tool output behind each is retrievable.
19. A tool's raw output is retained whether or not its adapter parsed it, bounded and marked when truncated.
20. No judgment produced by a language model becomes part of a score.

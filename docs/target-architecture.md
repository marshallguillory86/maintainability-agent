# Target architecture

Where the design is going, and why. Separate from [architecture.md](architecture.md) because that document describes the code **as it is** — a three-hundred-line "not implemented" section inside it contradicted its own first sentence, and the audit flagged the combined file at 632 lines against this project's 500-line limit.

Nothing here ships. Implementation status lives in the [decision register](decisions.md) and the [release plan](release-plan.md).

The layer model above is what the code does today. [ADR 006](adr-006-analyzer-evidence.md) and [ADR 007](adr-007-pillars-and-practice.md) change it materially, and the shape is recorded here so the work has a target rather than a direction.

The current design inverts its own stated principle. The README says *"pair this tool with mature analyzers … don't replace them"*, and `src/` contains six homegrown reimplementations of exactly those analyzers, with external tools relegated to optional SARIF ingest. ADR 006 turns that the right way up.

## Planned companion boundary

**Planned; not implemented.** The [product intent](product-intent.md#planned-product-split-and-companion-workflow)
separates the existing deterministic audit, to be named `maintainability-audit`,
from the new `maintainability-agent` companion. The companion operates inside
human-controlled agent chat and uses the host's reasoning and coding tools.
It does not add a model to the audit pipeline.

```text
Human direction in agent chat
  -> companion requests audit -> audit report and work orders
  -> human selects scope and limits
  -> companion retains original task contract
  -> host performs authorized work
  -> authorized tests + independent audit verification
  -> continue within limits / request direction / present for review
```

The task contract must retain repository identity, starting revision and
relevant working-tree state, the original report and selected finding
identities, allowed paths, verification commands and attempt limits. Task
state records attempts, inspected revisions, evidence and remaining work.
A rescan must not overwrite the original selection; a scope change requires
an explicit human amendment. Resume must validate repository and revision
context, and stale evidence must not close a newer attempt.

The companion consumes the audit's public interfaces rather than importing
scoring internals or changing thresholds to obtain a pass. Existing work
orders, finding identity, recurrence, conformance and regression checks are
building blocks; they do not constitute a shipped task lifecycle. The
original-selection verification contract and chat access to the required
checks must be implemented and tested before claiming the loop works.

The host owns execution permissions and edits. Task state is separate from
audit scan history and does not grant additional access. The verifier's
inputs and configuration must be recorded, with changes made visible rather
than silently accepted. Separate processes alone do not establish an
independent verification boundary.

A host skill plus durable state is the first candidate. The supported hosts,
state schema and storage location, public operation names, and installation
and compatibility plan remain design decisions. No standalone runtime,
background scheduler, fleet orchestration or model-routing system is included
in this increment. The remaining sections describe audit-pipeline design.

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

A user should not have to know which of 448 analyzers exist, write scripts to invoke them, or reconcile their output formats. They answer two questions — **what do you want examined** and **how deep** — inside a license policy their organization sets once. The agent resolves the toolset, runs it, and returns two things: the compiler-style errors (located, specific, fixable) and the scores (compact, comparable, trendable). Both go in the report; neither replaces the other.

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

It also cannot be sourced from the catalog's upstream data, and that is worth stating plainly: the upstream tags are languages, ecosystems and frameworks — `rails`, `nodejs`, `spring` — and **only 5 of the 448 eligible tools carry an upstream tag naming one of this project's concerns**. What a tool measures can only be known by running it, so the `measures` field is populated exactly as fast as adapters are written, and the upstream tags are kept separately as `upstream_tags` rather than dressed up as concerns.

### Which tools run: the catalog, depth and license policy

The pool is not hardcoded. [`src/maintainability_audit/_assets/analyzer-catalog.json`](../src/maintainability_audit/_assets/analyzer-catalog.json) holds **760 tools** — 755 from the analysis-tools.dev database pinned at a recorded commit, plus 5 verified locally — each with its license, license class, languages and source. **448 are eligible**: open-source class, current, language-targeting, not security-only.

Two independent selectors narrow it, because *how much work* and *what may we legally run* are different questions:

- **depth** — `baseline`(9) / `moderate`(17) / `heavy`(17) / `all`(448). A tier below `all` is a promise the tool works; nothing enters one until it has been installed, run and parsed.
- **license policy** — `permissive`(368) / `copyleft-weak`(403) / `copyleft-any`(448) / `commercial-free-tier`(474) / `unverified`. Some organizations forbid copyleft outright, so the policy is enforceable rather than advisory.

Both are set in the `analyzers` block of the config file, or answered on first run — the **same** questions on chat, MCP, and a CLI TTY — and both are **recorded in the report** — a score from four tools and a score from forty are not the same measurement and must not be silently comparable. Individual tools and whole license classes can be denied; **every deny wins, including over an explicit allow**, because an organization's prohibition must not be overridable per repository.

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

**Acquisition is a user-tier decision.** Installing is a network and privilege action and it is off by default. A user may enable `analyzers.acquire_tools`; the audited tree cannot enable it. What the agent emits is an *environment work order* in the same shape as the code work order — what is missing, why it matters, and the exact command — so a human can run it or hand it to their own AI agent to run. Same artifact, either consumer.

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
| **CLI** | CI runners, Makefiles, merge gates; interactive TTY is the same first-run as chat | Exit codes, files on disk, deterministic once configured. CI never prompts. A TTY with no config asks the same questions as MCP/chat, not a shorter set. |
| **MCP server** | Chat, slash commands, agentic loops | `tools` run the audit, `resources` expose rubric and report, `prompts` are the slash command. Setup questions are the same as an interactive CLI TTY. |

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

# Product intent

The governing document. When another document, a code comment, or a release note disagrees with this one, this one is right and the other is a bug.

## What this is

A deterministic maintainability audit that produces a **bounded work order** for an AI coding agent.

Not a linter (those exist and are better at it), not an AI reviewer, not a quality dashboard. The scanner and the score exist to aim the remediation prompt. If the prompt were removed, the rest would be a worse version of tools that already ship.

**The primary surface is an AI chat host** — an IDE assistant or chat
window driving the MCP server. The CLI is the automation surface for CI
and scripts. Almost no user runs the audit at a bare terminal, so a
capability that exists only behind a terminal prompt does not exist for
most users. The individual wiring defects found when this contract first met a
real host—and their closing tests—are recorded in the
[chat-surface defect register](defect-register-chat-surface.md).

## The job it does

Agents write code faster than humans can read it. The ratio of code-written to code-reviewed has collapsed, and unmaintainable code that used to accumulate over years can now accumulate in an afternoon. The same speed is the way out: an agent pointed at specific, deterministic findings can fix them at the same rate they appear.

The loop this product closes:

1. Measure pressure points deterministically, with no LLM involved.
2. Apply one uniform standard, so "better" and "worse" are not an argument.
3. Emit a prompt scoped to *those findings only*, with explicit instructions not to refactor beyond them.
4. Hand it to the agent. Review a scoped diff instead of a speculative rewrite.

Step 3 is the product. Steps 1 and 2 are in service of it.

### Semantic judgment and economic priority

The next useful boundary is not a larger generic smell catalog. It is a way to
make repository knowledge explicit enough that a deterministic tool can act on
it. Source code alone can observe that the same bare strings are repeated in
dispatch, validation and capability checks. It cannot universally know whether
those strings should be constants, an enum, a value object, or reified
operations with behavior and generic result types. That choice contains domain
intent.

[ADR 003](adr-003-deterministic-semantic-policy.md) accepts three honestly
different outputs: facts established by a language type system, violations of
checked-in repository policy, and design-review candidates inferred from
structural or historical friction. Determinism means that the same tree,
analyzer versions and policy produce the same result; it does not require the
tool to pretend that one universal rule contains every repository's semantics.
The current increment is TypeScript only. These results aim the bounded prompt;
they do not change the standard score, range, grade, or evidence status.

[ADR 004](adr-004-economic-context.md) v1 is **shipped**. Change history
supplies recurrence and hotspot churn; the user may supply loaded labor
cost (low/base/high) and optional horizon, reliability tier, review
burden and incident cost. The result is a labeled scenario range in a
separate report block and a reordered work order, not a modification of
the uniform score and not a prediction.
The product direction is:

> deterministic finding + explicit repository semantics + configured economic
> context -> a bounded work order ordered by estimated exposure

ADR 003 option C is accepted and its TypeScript precision increment is current
work. Both paths preserve the offline, no-LLM audit path and the evidence
standard below.

## Who it is for

- Teams running agents in the dev loop who are tired of unbounded cleanup PRs.
- Repos that want a maintainability gate without a SaaS analyzer or shipping code to a third party.
- Solo developers who want one deterministic audit pinnable in a Makefile or CI script.

## What it promises

Each promise is falsifiable, and named so a failure can be reported against it.

| # | Promise | Falsified by |
|---|---|---|
| P1 | The audit is deterministic: same tree, config, pinned analyzer versions **and scan history** in, same *evidence, findings and score* out — **at a fixed point in time.** The history window is relative to the wall clock (see below), so the same tree audited on two different days can report different history rates. Three further fields describe the run rather than the repository and are recorded without being compared — the absolute `root`, `git_status_short`, and each analyzer's wall-clock `seconds`; see below. History is an input, not decoration — a finding that cleared and returned twice is different information from one seen for the first time, so an identical tree reports differently against different histories, and that is the feature working. **The analysis itself performs no network access and invokes no language model.** Tool acquisition is opt-in through `analyzers.acquire_tools` and defaults off; when enabled, it may fetch a missing tool and records the acquired version | Two runs disagreeing on identical tree, config, versions and history, or any network access during analysis |
| P2 | The score applies the same rubric to every repository, and the rubric is readable in source | A repo-specific code path changing a weight or band |
| P3 | Withholding evidence cannot improve the reported grade | Any input whose removal raises the graded field |
| P4 | The overall equals the weighted mean of the categories printed beside it | A report where the arithmetic does not check |
| P5 | The remediation prompt names only findings the audit actually produced | A prompt instruction with no corresponding finding |
| P6 | Every empirical claim in this repo is reproducible from checked-in pinned inputs | A quoted number that cannot be re-derived offline |
| P7 | A score is issued only where enough was examined to support it, and never as a consequence of not looking | A number a reader with the repository in front of them would call absurd |
| P8 | Every report states what examined it — which analyzers ran, which did not, and what measured each value | A reported value with no attributable source, or a run whose coverage cannot be recovered from its output |

### Why P1 was amended

P1 read "no network, no LLM" when the tool was pure computation over a file tree. Under [ADR 006](adr-006-analyzer-evidence.md) it invokes external analyzers, and some of those live in ecosystems whose normal installation path is a fetch — `npx` for the Node tools most obviously.

Two honest options existed: refuse to acquire tools, which makes the multi-language story depend on every user hand-installing a dozen ecosystems; or provide an explicit acquisition choice and disclose it. The latter was chosen, so the promise separates **analysis** from **acquisition**. Analysis still touches no network and no model: **this agent does not transmit the audited source.** Acquisition defaults off. When a user enables `analyzers.acquire_tools`, a missing tool may be fetched and its version is recorded in the report so the run remains reproducible.

**Why P1 names three excepted fields.** An audit ran the same tree
twice and found the reports differing by one millisecond, on an
analyzer's `seconds`. The promise said "same report out" and the
determinism check had been quietly stripping `root`,
`git_status_short` and every `seconds` for as long as it had existed —
so the promise was false of the JSON a consumer actually diffs, and
true only of the test's own projection.

The exceptions are legitimate: a duration is a fact about the run, not
about the repository, and an absolute path is not portable. What was
wrong was that they were undisclosed, which is exactly the shape this
table exists to prevent — a promise kept green by a check narrower than
the promise. They are named above now, and
`test_the_determinism_exceptions_are_exactly_the_disclosed_ones` fails
if the strip list grows without this page growing with it.

**Why P1 names the history window.** The three excepted fields above
are recorded and not compared. The history window is a fourth exception
of a different kind, and it went undisclosed longer: `DEFAULT_SINCE` is
`12 months ago`, which git resolves against the wall clock at the moment
the audit runs. It is not configurable.

So "same tree, config, pinned analyzer versions and scan history in,
same score out" is true within a run and false across days. A commit
ages out of the window overnight and the churn, hotspot, coupling and
ownership rates move underneath an unchanged tree — no input changed,
and the grade did. That is a real determinism limit, not a rounding
one, and it is the same shape as the three fields above: legitimate
behaviour kept invisible by a check narrower than the promise. The
determinism test compares two runs seconds apart, which is precisely
the interval over which this cannot fail.

Named rather than removed, because a fixed absolute window would make
every report a different question over time, and pinning the window per
repository is a config decision nobody has asked for.
`test_the_history_window_is_disclosed_as_clock_relative` fails if the
window changes without this paragraph changing with it.

**What P1 does not police.** External analyzers run as local child processes (`_runner`). This package does not wrap them in a network sandbox, and it does not inspect whether *they* open sockets. A future SaaS CLI adapter would be a different product. The host that prints a report into an IDE chat (Grok, Claude, …) is also outside this process. P1 is enforced as determinism plus no HTTP client in `src/` that uploads the tree — not as “no packet can leave the box.”

The prerequisites this creates are listed in [the analyzer pool](analyzer-pool.md#runtime-prerequisites) rather than left for a user to discover from a failure.

### Why P7 and P8 were added

P1–P6 are all **self-consistency** promises: the machine agrees with itself, the arithmetic checks, nothing is concealed. A repository holding one function and one test passed all six while being reported as **5.0 / A+, evidence complete, verified** — deterministically, under the same rubric, with the arithmetic correct and nothing withheld. Six for six, and the result was worthless.

Nothing in P1–P6 asks whether a number corresponds to anything about the code, so four days of hostile audits could not see it. Worse, the [evidence standard](#the-evidence-standard) classifies the rubric as Tier 2 — a judgment that "needs no validation study and no apology" — which is right for *weights* and became a principled-sounding reason never to ask whether a specific score was defensible.

P7 is that missing question, stated as a falsifiable property. P8 makes it checkable: a score cannot be judged sufficient unless the report says what produced it. See [ADR 005](adr-005-insufficient-population.md) and [ADR 006](adr-006-analyzer-evidence.md).

## What it must never claim

This list exists because the project has already broken it once and retracted. Adding a claim in these shapes requires deleting it from this list first, with the evidence that earns it.

- **That it detects AI-written code**, or that any metric distinguishes AI authorship. Tested with a matched control and [retracted](studies.md#does-this-detect-ai-written-code). Any revival needs a pre-registered design with commit-level authorship.
- **That the score predicts business outcomes** — defect rates, delivery speed, cost. No outcome study has been run. The rubric is a standard, not a model of the future.
- **That a configured economic scenario is a prediction or observed saving.** User inputs make assumptions explicit; they do not validate the model. Scenario ranges must remain separate from the score until held-out outcomes establish predictive performance.
- **That a heuristic can recover experienced engineering judgment.** A repeated string dispatch or repeatedly patched abstraction can justify a design-review candidate. It does not prove which abstraction is correct.
- **That a passing grade means the code is maintainable.** It means nothing this tool measures is out of band.
- **That the architecture, or any ADR, is "fully implemented"** while its consumers and invariants have not migrated.
- **That a bug class is closed** because the reported instance stopped reproducing. See the closure rules below.
- **That third-party tools cannot use the network**, or that a run is kernel-air-gapped. This agent does not transmit the audited source; it does not sandbox children.

## The evidence standard

Six audit rounds went in circles for one reason: claims of different kinds were held to the same loose bar. A judgment was defended as if it needed a study, and a study was asserted as if it were a judgment. Every claim in this repository is exactly one of these, and its type determines what it needs.

### Tier 1 — Deterministic property

*"The overall is the mean of the printed categories."* A statement about what the code does.

**Requires:** a test that fails if it stops being true. Not an example — a property over the real field set or input space. No study, no debate.

### Tier 2 — Standard (judgment)

*"Duplication is 25% of modularity."* *"A file over 400 lines warns."*

**Requires:** that it be explicit, deterministic, uniform across repositories, and readable in source. **It requires no validation study, and no apology.** Every standard — ISO 25010, a building code, a style guide — is judgment made explicit and applied uniformly. Anyone may disagree with a weight; they can read it and argue. Legitimacy comes from being stated and applied evenly, not from being proven optimal.

Calibration against the reference corpus is what keeps these judgments *anchored* to real code. It does not convert them into Tier 3 facts.

### Tier 3 — Empirical claim

*"AI-assisted fixes touch more files."* A statement about the world.

**Requires:** pinned inputs checked in, a matched control, a pre-registered primary outcome, correction for multiple comparisons, and re-derivation offline. Absent any of those, it is reported as an **exploratory direction** and never as a finding. A result that crosses significance depending on a specification choice is *fragile by demonstration* and must be labeled so.

**The failure mode this prevents:** stating a Tier 3 claim in a document whose genre implies Tier 1 or 2. That is precisely how the retracted claim reached the README headline.

## When a finding is closed

Adapted from [ADR 001](adr-001-evidence-and-verification.md), which earned these the hard way. All conditions, not a majority:

1. The original reproduction no longer fails.
2. The governing invariant is stated **independently of that reproduction**.
3. Tests exercise the production model, not a hand-built fixture that happens to carry the right keys.
4. The equivalent missing, invalid, zero, and not-applicable states are all covered.
5. Public claims do not exceed what the invariant and tests establish.
6. Any changed empirical result is re-derived from pinned inputs and corrected **everywhere it is quoted**.

Passing the test suite and the self-audit is necessary and is not sufficient. Two consecutive audit rounds were rejected for fixing the demonstrated instance and leaving structurally identical paths untouched.

## What success looks like

- An agent handed the bounded work order acts on the standard instead of wandering.
- A maintainer can explain any grade by pointing at a named measurement.
- A hostile audit finds nothing that a stated invariant did not already cover.

### What the evidence currently supports

**[studies.md](studies.md) is the source of record.** This section holds no table and no interpretation — an earlier revision duplicated both and the copies promptly disagreed. What it does hold is the single approved public sentence, because a document whose job is to say what the product may claim cannot do that job while quoting nothing. Every figure below also appears in `studies.md`, and a test enforces that.

One pre-registered experiment has been run: [does the bounded prompt work?](studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered). Its registered verdict is **INCONCLUSIVE** and stays recorded that way; the registered hypothesis was that bounded prompts produce narrower diffs, and they did not.

**The defensible public sentence**, and the only one:

> Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count.

An earlier revision read "bounded ones did not", which concealed the bounded arm's own failure; an audit flagged it as a misleading public claim and it is corrected here rather than quietly rewritten. Two limits travel with that sentence wherever it goes: the bounded arm is told which findings to close and then scored on closing them, and "improved" means "closed the findings this tool names", which no outcome study has yet connected to real maintenance cost.

## What failure looks like

- The score becomes something to game rather than something to act on.
- The tool grows into a worse SonarQube.
- A claim outruns its evidence tier — the single failure this project has actually committed.

## Non-goals

Replacing mature analyzers; rewriting repositories automatically; sending code to an LLM by default; treating maintainability as purely numeric; preserving undocumented behavior for hypothetical consumers.

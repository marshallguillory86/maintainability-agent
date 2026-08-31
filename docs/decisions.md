# Decision register

Every architectural decision, including the ones not yet made.

A decision recorded only as a sentence inside a design document is a decision that gets re-litigated. This register exists so that "why is it like this?" and "what are we still arguing about?" both have one answer, and so an open question is visibly *open* rather than dissolved into prose in three files.

## Register

| ID | Decision | Status | Affects |
|---|---|---|---|
| [001](adr-001-evidence-and-verification.md) | Separate maintainability scoring from evidence verification | **Accepted** — stages 1–8 implemented, 9 pending | Report schema, scoring, grading, history studies |
| [002](adr-002-null-verified-grade-in-ci.md) | Whether null `verified_grade` needs a CI policy before stage 5 | **Rejected** — premise assumed a grade gate that does not exist | CLI exit codes, ADR 001 stage 5 |
| [003](adr-003-deterministic-semantic-policy.md) | Add deterministic, repository-aware semantic findings without changing the uniform rubric | **Accepted** — option C; this increment is TypeScript only: type-backed universal facts, checked-in policy violations, and prompt-only design-review candidates. The pre-registered corpus and precision bar are in [semantic-prototype.md](semantic-prototype.md). No semantic result changes the score | Analyzers, configuration, findings, remediation prompts |
| [004](adr-004-economic-context.md) | Add configured economic-impact scenarios without turning the score into a cost prediction | **Accepted** — v1 **shipped** (`tests/test_economic_context.py`): optional TTY ask once, persist `economic_context`, env overrides; labeled scenario range; work order reorders by recurrence + churn; score/grade untouched. Ladder 2–4 (prediction language) still unearned | Configuration, report schema, prioritization, studies |
| [005](adr-005-insufficient-population.md) | Withhold rates, per aspect, where the denominator is too small to support one | **Accepted** — implemented | Scoring, grade profile, report contract, every consumer |
| [006](adr-006-analyzer-evidence.md) | External analyzers produce the evidence; the agent orchestrates and corroborates across tools | **Accepted** — implemented; the point estimate uses analyzer pressures for every dimension measured on the full concept set, with the built-in detectors as the fallback. Calibration (3.6) was re-derived 2026-08-14 against that mix (`CALIBRATION_C` 2.6279 → 2.2658). Java has a built-in range fallback; **we will not write more range detectors** for Go/C/C++/C#/Rust. Remaining population work is analyzer-supplied measurements for languages the built-ins cannot range. 2.5c shipped: the environment work order rides beside coverage; acquisition remains opt-in in user-tier configuration and unavailable to the audited tree. | Whole evidence layer, determinism promise, installation, CI, report contract |
| [007](adr-007-pillars-and-practice.md) | Adopt the five-pillar framework; separate practice maturity from code condition | **Accepted** — implemented; the §4 vocabulary rename was **refused**, recorded in the ADR and [standard.md](standard.md#shared-vocabulary-and-where-this-tools-terms-differ) | Reporting taxonomy, scope boundaries, remediation prioritization |
| [008](adr-008-translation-and-decision.md) | Translation layer from tool output to scoring input; the LLM boundary; CLI and MCP entry points | **Accepted** — band matrix **shipped (3.2)**: live declaration and file-size pressures use `_bands` so values in different bands are not one failure (`tests/test_band_pressures.py`); gates stay binary. MCP tools, resources and prompt ship through `maintainability-agent mcp`, with `maintainability-agent-mcp` retained for IDEs | Evidence normalization, thresholds, remediation, entry points |
| [009](adr-009-scan-history.md) | Persist a scan history so the engine can measure change over time | **Accepted** — implemented. Schema 3 stores structured identities (`kind`, path, name, ordinal, `body_digest`, fingerprint) beside labels; schema-1/2 lines still load and remain label-equality comparisons. Baseline v3 and recurrence use `_finding_match`, including git-attested rename following and same-name reorder resolution. The human label remains `function:{path}:{name}#{ordinal}`. Append-when-file-exists and the separate pillar/practice series remain shipped | Persistence, finding identity, determinism, report, `--fail-on-new`, HTML/MD trend charts |
| [010](adr-010-repository-discovery.md) | Classify every file by language and provenance from evidence the repository provides | **Accepted** — implemented | Scanned population, scored population, analyzer applicability, coverage |
| [011](adr-011-three-report-presentations.md) | Three user-facing skins of one report dict: chat/CLI text (default), Markdown file, one self-contained HTML file; ask every interactive invoke | **Accepted** — implemented except acceptance: the three skins render from one report dict and never disagree on the headline (`tests/test_three_presentations.py`), the TTY ask and MCP format argument shipped (`tests/test_format_ask.py`), and the HTML file is one self-contained deterministic page. 8.8 acceptance, then 7.5 and the tag, remain | Presentation, CLI, MCP prompt, HTML |
| [012](adr-012-spotbugs-build-boundary.md) | The agent never builds: SpotBugs analyzes bytecode that already exists, absence becomes a build-then-rerun work-order remedy, and every run records staleness evidence (source mtime vs class mtime) | **Accepted** (2026-08-19, decision 11) — implemented in slice 3 behind `tests/test_spotbugs_adapter.py`; D15 composition of source-read and artifact-read shapes is `tests/test_d15_composition.py` | Analyzer pool, environment work order, JVM adapters |
| [013](adr-013-hostile-audit-prompt.md) | Emit a deterministic, report-seeded hostile-audit prompt so the adversarial audit that builds this tool becomes a repeatable step; the LLM does the reasoning outside, the core never performs it | **Proposed** (2026-08-30) — a third emitter on the prompt seam beside `render_ai_prompt` / `render_agent_instructions`; non-gating, non-scoring. The deterministic adversarial-properties *detection* dimension (auditing a target for the same hardening classes) is deferred to a future release ([roadmap](roadmap.md)) and its own ADR | Prompt seam, CLI, MCP prompt, QA methodology |

## Recorded operating decisions

These choices settle cross-cutting behavior discovered while closing the chat
surface. They do not create new ADRs or silently amend the numbered decisions
above; they record Marshall's answers so a pull request is never the only place
the choice exists.

### Decision 4 — History consent

- Recorded: 2026-08-17

First-run setup asks whether to record scan history in the repository, with
**yes** as the disclosed default and **no** as the alternative. The answer is
persisted like the other setup choices. Client capability alone does not start
a series.

### Decision 5 — Three-way root grant, session default

- Recorded: 2026-08-17

An out-of-roots audit elicitation offers **this session**, **always**, and
**no**, with **this session** pre-selected. Always persists a user-tier
`allowed_roots` entry; a session grant changes only the running process; no
returns the static `--allow-root` and environment-variable remedies.
How that refusal survives MCP is the entry-layer transport rule in
[architecture.md](architecture.md#the-rules-and-why-each-exists): only the
transport declares the named anticipated refusals that may carry their text to
the caller.

### Decision 6 — Verification-audit L scope stays in one slice

- Recorded: 2026-08-17

The TOCTOU repair (resolve once and grant exactly what was asked), the
`write_user_config` caller-class lint, and the stale D10 register citation land
together before the documentation sweep.

### Decision 7 — Config wins over terminal interactivity

- Recorded: 2026-08-17

Written consent outranks the terminal: `history.record: false` suppresses
recording even on a TTY. The terminal may start a series only when no consent is
written, and the CLI and MCP doors apply the same rule.

### Decision 8 — Flat allowed_roots stands

- Recorded: 2026-08-17

`get_agent_info` keeps the honest flat `allowed_roots` list. Provenance labels
are not added to that response.

Decisions 005–007 were written together after a repository containing one production function was reported as 5.0 / A+, evidence complete, verified. They address three distinct causes of that single result: no rate has a minimum population (005), the evidence comes from six homegrown detectors rather than the mature analyzers the README says to pair with (006), and nothing distinguishes *a clean scan* from *an enforced standard* (007).

### Decision 9 — The line is executing code

- Recorded: 2026-08-25

**This agent never executes the audited repository's code, and its
configuration is code.** An eslint flat config is a JavaScript program; a
pylint or mypy plugin is a Python module. Loading either to produce a
finding is executing the tree, so the boundary is drawn at execution
rather than at a judgment about whether a given repository is
trustworthy.

This answers the question `security-queue.md` recorded as *"the one
decision that is not mine"* — are repositories trusted? — by making it
moot. The agent does not need to decide; it does not run their code
either way.

**A pillar that can only be measured by running the code waits for a
future version.** It is not approximated, not half-measured, and not
shipped behind a caveat. `test_effectiveness` was already `unscored` for
exactly this reason ("requires running the suite (mutation/coverage);
this audit never executes code"), and that entry now reflects a rule
rather than a limitation.

Consequences: `SECURITY.md`'s existing claim becomes true rather than
aspirational. D39 stops being an accepted residual and becomes a defect
— the promise was right and the code drifted from it. Analyzers that
require the tree's own configuration leave the default pool; analyzers
that merely *may* load configured plugins (mypy, pylint) run with that
loading disabled. Child sandboxing stays refused and this does not
reopen it: not executing the tree is a narrower and cheaper guarantee
than containing it while it runs.

### Decision 10 — v1.0 ships Python and Java

- Recorded: 2026-08-25

**v1.0 is the current language capability with an empty defect ledger,
not a larger language matrix.** Python (`ast`, exact declaration ranges)
and Java (dedicated scanner) are the two languages with real declaration
parsers, and they are what v1.0 claims.

Further languages — Fortran, C#, C, Rust, then JavaScript and the rest —
arrive **one adapter per release**, not as a batch. Marshall's reason,
in his words: he is an agilist, and a six-language batch is the opposite
of that. The catalog already carries analyzer coverage for those
ecosystems, so each release adds a declaration parser to a pool that can
already measure something.

Consequences: v1.0's remaining work is the defect ledger, not new
adapters. Every language outside Python and Java gets file length,
duplication and risk, with declaration rates **withheld** and the
missing parser named, which is what P7 requires.

**Amended 2026-08-26.** The paragraph above said every language
outside Python and Java has declaration rates withheld. That was never
true: the brace scanner reads JS, TS, JSX and HTML, so a JavaScript
repository was handed a declaration population, `evidence_status:
complete` and a verified grade while this decision claimed two
languages. An audit found the contradiction and the sentence was mine.

The resolution is that the claim follows the capability, not the
reverse. Marshall, on being shown that lizard, jscpd and multimetric
are baseline-tier adapters that read JavaScript: *"keep JS in since we
have a detector and can score it."*

**Corrected 2026-08-26, on the same page's own evidence.** The sentence
above got the *supporting* fact wrong even though the decision is
right. The detector that scores JavaScript declarations is this
project's own brace scanner (`_ranges`, `_cognitive.brace_cognitive`),
not the analyzer pool. `DECLARATION_CRITERIA` requires cyclomatic
complexity, declaration lines **and** cognitive complexity, because the
built-in path fails a declaration on any of the three and a rate built
from a narrower set is not comparable to it. lizard emits the first
two. So for a JavaScript repository with lizard installed and nothing
else, `_declaration_pressure` returns `None` and the built-in tier
scores the dimension -- every time, by construction, not by accident.

Marshall's ruling stands unchanged: *we have a detector and can score
it* is exactly true of the brace scanner, and `language-support.md`
already names brace/paren depth as the mechanism. What was wrong was
this page crediting the pool for work the pool cannot do here. The
analyzers that read JavaScript still contribute duplication (jscpd) and
file metrics (multimetric); they do not drive the declarations
dimension, and PMD is the only catalogued tool that could.

So v1.0's declaration languages are **Python, Java, JS, TS, JSX and
HTML** — everything this project can detect and score — and
`docs/language-support.md` says exactly that. The one-adapter-per-
release cadence is unchanged and applies to languages nothing here
reads yet: Go, Rust, C, C# and Fortran, which are absent from the
default extensions rather than scanned and unscored.

The rule the falsifier holds is the narrow one that was actually
broken: a declaration population must never come from a language the
tool can neither parse nor hand to an adapter, and the page and the
parser must name the same set.
`test_the_parsed_languages_are_exactly_the_documented_languages` fails
in either direction.

## Statuses

- **Proposed** — written up with options; not yet decided. May be edited freely.
- **Accepted** — decided. The text is frozen except to record implementation progress or to mark it superseded.
- **Superseded by NNN** — replaced. Left in place; never deleted, because the reasoning explains code that still exists.
- **Rejected** — considered and declined, with the reason. Worth keeping so it is not proposed again.

## When to write one

Write an ADR when a choice would be expensive to reverse, when it constrains code that has not been written yet, or when it has already been argued about more than once. Do not write one for a preference a reviewer could simply request a change to.

The bar is deliberately low for **Proposed**. An open question sitting in a register is cheap; the same question sitting in someone's head is what produces a sixth audit round.

## Template

```markdown
# ADR NNN: <decision in a few words>

- Status: Proposed | Accepted | Superseded by NNN | Rejected
- Date: YYYY-MM-DD
- Scope: <what this constrains>

## Context

What is true today, and what forces the choice. Facts, not preferences.

## Options

Each with its consequence. Include the one that will be rejected — an ADR
listing only the chosen path is a rationalization.

## Decision

The choice, in the active voice. For Proposed, state the recommendation
and what is needed to settle it.

## Consequences

What becomes easier, what becomes harder, and what has to migrate.

## Invariants

The properties that must hold afterwards, phrased so a test can check
them — see [product intent](product-intent.md#the-evidence-standard).
```

An ADR that states no invariant is usually describing a preference rather than a decision.

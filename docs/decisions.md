# Decision register

Every architectural decision, including the ones not yet made.

A decision recorded only as a sentence inside a design document is a decision that gets re-litigated. This register exists so that "why is it like this?" and "what are we still arguing about?" both have one answer, and so an open question is visibly *open* rather than dissolved into prose in three files.

## Register

| ID | Decision | Status | Affects |
|---|---|---|---|
| [001](adr-001-evidence-and-verification.md) | Separate maintainability scoring from evidence verification | **Accepted** — stages 1–9 implemented. Stage 9 (1.9.0) split history materialization from measurement: `tools/calibration/history_manifest.py` fetches and pins, `measure_fix_breadth` reads the manifest and never touches the network, and a cache that has drifted is refused rather than measured (`tests/test_history_manifest.py`). The checked-in `history_manifest.json` pins 33 subjects, 6,120 commit ids and 293 required parent objects | Report schema, scoring, grading, history studies |
| [002](adr-002-null-verified-grade-in-ci.md) | Whether null `verified_grade` needs a CI policy before stage 5 | **Rejected** — premise assumed a grade gate that does not exist | CLI exit codes, ADR 001 stage 5 |
| [003](adr-003-deterministic-semantic-policy.md) | Add deterministic, repository-aware semantic findings without changing the uniform rubric | **Accepted** — option C; this increment is TypeScript only: type-backed universal facts, checked-in policy violations, and prompt-only design-review candidates. The pre-registered corpus and precision bar are in [semantic-prototype.md](semantic-prototype.md). No semantic result changes the score | Analyzers, configuration, findings, remediation prompts |
| [004](adr-004-economic-context.md) | Add configured economic-impact scenarios without turning the score into a cost prediction | **Accepted** — v1 **shipped** (`tests/test_economic_context.py`): optional TTY ask once, persist `economic_context`, env overrides; labeled scenario range; work order reorders by recurrence + churn; score/grade untouched. Ladder 2–4 (prediction language) still unearned | Configuration, report schema, prioritization, studies |
| [005](adr-005-insufficient-population.md) | Withhold rates, per aspect, where the denominator is too small to support one | **Accepted** — implemented | Scoring, grade profile, report contract, every consumer |
| [006](adr-006-analyzer-evidence.md) | External analyzers produce the evidence; the agent orchestrates and corroborates across tools | **Accepted** — implemented; the point estimate uses analyzer pressures for every dimension measured on the full concept set, with the built-in detectors as the fallback. Calibration (3.6) was re-derived 2026-08-14 against that mix (`CALIBRATION_C` 2.6279 → 2.2658). Java has a built-in range fallback. This entry read **"we will not write more range detectors" for Go/C/C++/C#/Rust** until 1.6.0; five were written — C (1.1.0), C++ (1.2.0), C# (1.3.0), free-form Fortran (1.4.0), fixed-form Fortran (1.6.0) — each as its own minor release, which is the cadence recorded below. The rule the original wording protected still holds and is the price of admission: a language is claimed only when it has a scanner of its own, a documented list of what it misses, and tests that pin them. Go and Rust remained unwritten on exactly those terms until 2.11.0, which wrote them along with PHP and Ruby — and paid the price of admission twice, since an audit of that release found four defects whose constructs were in no fixture (D125–D129). Remaining population work is analyzer-supplied measurements for languages the built-ins cannot range. 2.5c shipped: the environment work order rides beside coverage; acquisition remains opt-in in user-tier configuration and unavailable to the audited tree. | Whole evidence layer, determinism promise, installation, CI, report contract |
| [007](adr-007-pillars-and-practice.md) | Adopt the five-pillar framework; separate practice maturity from code condition | **Accepted** — implemented; the §4 vocabulary rename was **refused**, recorded in the ADR and [standard.md](standard.md#shared-vocabulary-and-where-this-tools-terms-differ) | Reporting taxonomy, scope boundaries, remediation prioritization |
| [008](adr-008-translation-and-decision.md) | Translation layer from tool output to scoring input; the LLM boundary; CLI and MCP entry points | **Accepted** — band matrix **shipped (3.2)**: live declaration and file-size pressures use `_bands` so values in different bands are not one failure (`tests/test_band_pressures.py`); gates stay binary. MCP tools, resources and prompt ship through `maintainability-agent mcp`, with `maintainability-agent-mcp` retained for IDEs | Evidence normalization, thresholds, remediation, entry points |
| [009](adr-009-scan-history.md) | Persist a scan history so the engine can measure change over time | **Accepted** — implemented. Schema 3 stores structured identities (`kind`, path, name, ordinal, `body_digest`, fingerprint) beside labels; schema-1/2 lines still load and remain label-equality comparisons. Baseline v3 and recurrence use `_finding_match`, including git-attested rename following and same-name reorder resolution. The human label remains `function:{path}:{name}#{ordinal}`. Append-when-file-exists and the separate pillar/practice series remain shipped | Persistence, finding identity, determinism, report, `--fail-on-new`, HTML/MD trend charts |
| [010](adr-010-repository-discovery.md) | Classify every file by language and provenance from evidence the repository provides | **Accepted** — implemented | Scanned population, scored population, analyzer applicability, coverage |
| [011](adr-011-three-report-presentations.md) | Three user-facing skins of one report dict: chat/CLI text (default), Markdown file, one self-contained HTML file; ask every interactive invoke | **Accepted** — implemented except acceptance: the three skins render from one report dict and never disagree on the headline (`tests/test_three_presentations.py`), the TTY ask and MCP format argument shipped (`tests/test_format_ask.py`), and the HTML file is one self-contained deterministic page. Amended 2026-09-20 (D201): `json` is offered at the question too — both doors already accepted it per call, so it was a shipped capability nobody was ever shown. 8.8 acceptance, then 7.5 and the tag, remain | Presentation, CLI, MCP prompt, HTML |
| [012](adr-012-spotbugs-build-boundary.md) | The agent never builds: SpotBugs analyzes bytecode that already exists, absence becomes a build-then-rerun work-order remedy, and every run records staleness evidence (source mtime vs class mtime) | **Accepted** (2026-08-19, decision 11) — implemented in slice 3 behind `tests/test_spotbugs_adapter.py`; D15 composition of source-read and artifact-read shapes is `tests/test_d15_composition.py` | Analyzer pool, environment work order, JVM adapters |
| [013](adr-013-hostile-audit-prompt.md) | Emit a deterministic, report-seeded hostile-audit prompt so the adversarial audit that builds this tool becomes a repeatable step; the LLM does the reasoning outside, the core never performs it | **Accepted** — implemented in 1.10.0: `render_hostile_audit_prompt` is the third emitter on the prompt seam, surfaced as CLI `--hostile-prompt-output` and the MCP `maintainability-hostile-audit` prompt. It seeds the audit from one run — commit, evidence already computed, P1-P8 with each stated falsifier, and the audit contract — and does not gate or score (`tests/test_hostile_prompt.py`). The promise table lives in code so the brief works offline, held to `product-intent.md` in both directions. A third emitter on the prompt seam beside `render_ai_prompt` / `render_agent_instructions`; non-gating, non-scoring. The deterministic adversarial-properties *detection* dimension (auditing a target for the same hardening classes) is deferred to a future release ([roadmap](roadmap.md)) and its own ADR | Prompt seam, CLI, MCP prompt, QA methodology |
| [014](adr-014-absence-as-evidence.md) | Adversarial-properties detection takes the evidence-integrity half only — code that reads an absent, empty or failed measurement as a passing result — and leaves every exploitability class to `secure-code-agent` | **Accepted** (2026-09-10) — the *scope* decision only; **nothing is built**. The boundary is a rule rather than a list: a candidate is MA's when it would still be a defect on a machine no attacker can reach, and the delegate's when its harm requires someone hostile; where it is genuinely both, MA yields, because [ADR 007](adr-007-pillars-and-practice.md) already gave that pillar away. Non-gating and non-scoring on [ADR 003](adr-003-deterministic-semantic-policy.md)'s terms. Implementation is gated on a frozen precision bar pre-registered before any result exists, as [semantic-prototype.md](semantic-prototype.md) did; a measured precision below it supersedes this ADR rather than lowering the bar | Findings, remediation prompts, the `secure-code-agent` boundary, QA methodology |

## Recorded operating decisions

These choices settle cross-cutting behavior discovered while closing the chat
surface. They do not create new ADRs or silently amend the numbered decisions
above; they record the answers so a pull request is never the only place
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

**Amended 2026-08-31 (Class 5 — opt-in suite execution).** The pillar
`test_effectiveness` named above no longer waits unconditionally. The one
exception to "never executes the audited repository's code" is an
explicit, per-repository operator opt-in: setup asks — defaulting to
**no** — whether to run the tree's *own documented* test command, and
only a `yes` together with a recorded command lets the audit spawn it.
The default is unchanged and total: with no opt-in the agent never runs
the tree, and every report produced without it keeps the original
guarantee verbatim. This is consent to run one operator-named command,
not a retreat from the boundary — it does not load the tree's
configuration as code (Decision 9's actual target), does not reopen child
sandboxing, and runs nothing the operator did not name. Coverage from
that run scores `test_effectiveness` as `coverage / 20`; without it the
aspect is `NotApplicable`, scored exactly as if the pillar were still
deferred.

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
arrive **one adapter per release**, not as a batch: small increments
rather than a six-language batch. The catalog already carries analyzer coverage for those
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
reverse. lizard, jscpd and multimetric are baseline-tier adapters that
read JavaScript, so JavaScript stays in the claim: there is a detector and
it can be scored.

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

The ruling stands unchanged: *there is a detector and it can be scored* is
exactly true of the brace scanner, and `language-support.md`
already names brace/paren depth as the mechanism. What was wrong was
this page crediting the pool for work the pool cannot do here. The
analyzers that read JavaScript still contribute duplication (jscpd) and
file metrics (multimetric); they do not drive the declarations
dimension, and PMD is the only catalogued tool that could.

So v1.0's declaration languages were **Python, Java, JS, TS, JSX and
HTML** — everything this project could detect and score at that release —
and `docs/language-support.md` said exactly that. It now names seven
languages, C through Fortran having arrived one per minor release since,
and it is still the page the parser is held to in both directions. The one-adapter-per-
release cadence is unchanged and applies to languages nothing here
reads yet. That list was **Go, Rust, C, C# and Fortran** when this was
written; C (1.1.0), C# (1.3.0) and Fortran (1.4.0, fixed-form 1.6.0) have
since been written and are in the default extensions. **Go and Rust**
remain absent from them rather than scanned and unscored, which is the
condition this paragraph exists to state.

The rule the falsifier holds is the narrow one that was actually
broken: a declaration population must never come from a language the
tool can neither parse nor hand to an adapter, and the page and the
parser must name the same set.
`test_the_parsed_languages_are_exactly_the_documented_languages` fails
in either direction.

### Decision 12: Writable oracle, three homes

- Recorded: 2026-09-26
- The contract-floor condition — a deterministic check is only evidence
  when the work under review could not author the record — is credited to
  **Michael Eakins**, who raised it in a public discussion of this project
  on 2026-09-26.
- Status: **Accepted. Home 1 authorized by the maintainer, 2026-09-27.
  Built in 3.11.0**: `_oracle`,
  held to the precision bar frozen first in
  `tests/test_oracle_weakening_precision_bar.py` (zero false alarms on its
  legitimate edits; every labelled weakening caught). Homes 2 and 3 are
  unchanged. Numbered 12 because ADR 012 was accepted as decision 11.

A deterministic check is only evidence when the unit under review could
not author the record. An agent that aliases a matcher, replaces an
assertion with `assert True`, or deletes the assertion, then watches
the suite go green, is writing the oracle. The pairing rule already
lets that file into the remediating diff.

Three homes, not one product:

1. **`--conformance` `clean` (this package).** Oracle-weakening in the
   remediating diff is the same second verdict as a skipped test.
   Shipped: a suppression directive added to a *named* file fails
   `clean`. Built in 3.11.0: any test file in the diff made unable to
   fail — skip or suppression, tautology, replaced assertion API,
   swallowed failure, deleted assertion — fails `clean` too. Still
   shape, never correctness. Deleting a whole test is reported as
   `test deleted` and is not `clean` either; removing one of two
   identical assertions is read as a deletion, a declared limit of
   reading the diff rather than the file.

2. **`tools/prove_falsifiers.py` (this repository).** Already first-order
   here: keep `tests/` from this commit, restore everything else to the
   base, those tests must fail. It stays this repository's gate. It
   does not become a first-order step in the customer product loop.
   Generalizing it to a stranger's suite remains the unscheduled
   capability named under [roadmap § the test that defends nothing](roadmap.md#3-the-test-that-defends-nothing).
   It does not license a claim that tests would catch a regression.

3. **Freeze, a fresh seat, a human on the test hunk (outside this
   package).** This auditor does not sequence remediation, freeze the
   suite before an agent writes, or launch a review that never saw the
   work. Those stay with the seats that split test-writing,
   implementation, and audit, and with the operator reading the test
   diff. This package's job at that seam is `clean` on the diff. This
   decision does not describe a successor, rename, or execution layer.

Governing text: [product intent](product-intent.md#the-writable-oracle).
Architecture records the unshipped `clean` cases as known debt.
CLI `--conformance` names what is shipped versus recorded.

### Decision 13: The ask beside the diff

- Recorded: 2026-09-27
- Status: **Accepted, authorized by the maintainer 2026-09-27, built in
  3.11.0** (`--ask`).

Found in the same exchange as Decision 12, from the other side. The
frozen tests were wrong before the agent saw them; the agent rewrote
production code until they passed; the test file was byte for byte the
one frozen. Nothing weakened a test, the record was one the agent could
not write, and the diff was still the wrong diff — because nobody had
asked for that code. What caught it was reading the diff against the
original ask.

`--conformance` already reads a diff against an ask when the ask is this
tool's own work order: a change outside the named targets is out of
scope. It could not do that for work this tool did not order, which is
most work.

1. **Conformance accepts an ask it did not write**, supplied beside the
   diff, and reports every change outside it as out of scope — so
   "every frozen test passed and the diff touched code nobody asked
   for" is a statement the report can make. The form of the ask and of
   the report is design work for the build, not part of this decision.
2. **Still shape, never correctness.** Whether code *inside* the ask is
   what was wanted is a judgment, and this package runs no model. A
   wrong assertion written before the work began leaves no trace in the
   diff and stays with the freeze, the fresh seat and the person, as
   Decision 12's third home says.
3. **The ask is the operator's.** A manifest the audited tree supplies
   about itself is the writable-oracle problem again, so it is read from
   the operator's path, never discovered in the tree.

Governing text: [product intent](product-intent.md#the-writable-oracle).

### Decision 14: secure-code-agent's behaviour is built there

- Recorded: 2026-10-02
- Status: **Accepted, stated by the maintainer 2026-10-02.**

The security pillar is a delegate call, not a second copy of
secure-code-agent. 4.0.1 began re-authoring the delegate inside this
package — remedy text for a required scanner its config switches off, and a
hand-written neutral config so preflight would not read the tree's. Two
copies of scanner knowledge drift, which is the reason this project reads
`--preflight --json` rather than keeping its own install table.

1. **Anything that knows about scanners is built in secure-code-agent
   first**: remedies, which config is trusted, preflight modes, what a
   disabled required scanner means. It is released there, the supported
   floor here is raised to it, and this package passes it through.
2. **An urgent fix may land here first only as a call to the delegate's
   public interface**, with the delegate-side work named as its follow-up.
   D222's neutral `--config` is that case: it uses a flag the delegate
   already has, and the delegate gains a mode of its own to replace it.

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

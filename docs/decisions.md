# Decision register

Every architectural decision, including the ones not yet made.

A decision recorded only as a sentence inside a design document is a decision that gets re-litigated. This register exists so that "why is it like this?" and "what are we still arguing about?" both have one answer, and so an open question is visibly *open* rather than dissolved into prose in three files.

## Register

| ID | Decision | Status | Affects |
|---|---|---|---|
| [001](adr-001-evidence-and-verification.md) | Separate maintainability scoring from evidence verification | **Accepted** — stages 1–8 implemented, 9 pending | Report schema, scoring, grading, history studies |
| [002](adr-002-null-verified-grade-in-ci.md) | Whether null `verified_grade` needs a CI policy before stage 5 | **Rejected** — premise assumed a grade gate that does not exist | CLI exit codes, ADR 001 stage 5 |
| [003](adr-003-deterministic-semantic-policy.md) | Add deterministic, repository-aware semantic findings without changing the uniform rubric | **Proposed** — TypeScript precision prototype required | Analyzers, configuration, findings, remediation prompts |
| [004](adr-004-economic-context.md) | Add configured economic-impact scenarios without turning the score into a cost prediction | **Accepted — not implemented.** v1 decided 2026-08-15: optional TTY ask once, persist `economic_context`, env/flags override; $ only as a labeled scenario range (labor low/base/high required); work order reorders by recurrence + churn; score/grade untouched. Historical validation (ladder 2–4) still required before prediction language | Configuration, report schema, prioritization, studies |
| [005](adr-005-insufficient-population.md) | Withhold rates, per aspect, where the denominator is too small to support one | **Accepted** — implemented | Scoring, grade profile, report contract, every consumer |
| [006](adr-006-analyzer-evidence.md) | External analyzers produce the evidence; the agent orchestrates and corroborates across tools | **Accepted** — implemented; the point estimate uses analyzer pressures for every dimension measured on the full concept set, with the built-in detectors as the fallback. Calibration (3.6) was re-derived 2026-08-14 against that mix (`CALIBRATION_C` 2.6279 → 2.2658). Java has a built-in range fallback; **we will not write more range detectors** for Go/C/C++/C#/Rust. Remaining population work is analyzer-supplied measurements for languages the built-ins cannot range. 2.5c shipped: the environment work order rides beside coverage and the agent still never installs. | Whole evidence layer, determinism promise, installation, CI, report contract |
| [007](adr-007-pillars-and-practice.md) | Adopt the five-pillar framework; separate practice maturity from code condition | **Accepted** — implemented; the §4 vocabulary rename was **refused**, recorded in the ADR and [standard.md](standard.md#shared-vocabulary-and-where-this-tools-terms-differ) | Reporting taxonomy, scope boundaries, remediation prioritization |
| [008](adr-008-translation-and-decision.md) | Translation layer from tool output to scoring input; the LLM boundary; CLI and MCP entry points | **Accepted** — implemented except the band matrix; `_bands` exists and is unused, and binary warn/fail rates still ship (see architecture [Known debt](architecture.md#known-debt)); MCP tools, resources and prompt ship through `maintainability-agent mcp`, with `maintainability-agent-mcp` retained for IDEs | Evidence normalization, thresholds, remediation, entry points |
| [009](adr-009-scan-history.md) | Persist a scan history so the engine can measure change over time | **Accepted** — implemented. Schema 2 shipped: each new line stores categories, aspects, pillars, practice level and evidence status, with pillar condition and practice/maturity as **two series**, never averaged; schema-1 lines still load (`tests/test_history_schema2.py`). Append-when-file-exists shipped: an existing history gains every successful scan without the flag, and a first interactive run starts the series. Identity is `function:{path}:{name}#{ordinal}` | Persistence, finding identity, determinism, report, `--fail-on-new`, HTML/MD trend charts |
| [010](adr-010-repository-discovery.md) | Classify every file by language and provenance from evidence the repository provides | **Accepted** — implemented | Scanned population, scored population, analyzer applicability, coverage |
| [011](adr-011-three-report-presentations.md) | Three user-facing skins of one report dict: chat/CLI text (default), Markdown file, one self-contained HTML file; ask every interactive invoke | **Accepted** — implemented except acceptance: the three skins render from one report dict and never disagree on the headline (`tests/test_three_presentations.py`), the TTY ask and MCP format argument shipped (`tests/test_format_ask.py`), and the HTML file is one self-contained deterministic page. 8.8 acceptance, then 7.5 and the tag, remain | Presentation, CLI, MCP prompt, HTML |

Decisions 005–007 were written together after a repository containing one production function was reported as 5.0 / A+, evidence complete, verified. They address three distinct causes of that single result: no rate has a minimum population (005), the evidence comes from six homegrown detectors rather than the mature analyzers the README says to pair with (006), and nothing distinguishes *a clean scan* from *an enforced standard* (007).

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

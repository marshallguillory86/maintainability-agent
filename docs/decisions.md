# Decision register

Every architectural decision, including the ones not yet made.

A decision recorded only as a sentence inside a design document is a decision that gets re-litigated. This register exists so that "why is it like this?" and "what are we still arguing about?" both have one answer, and so an open question is visibly *open* rather than dissolved into prose in three files.

## Register

| ID | Decision | Status | Affects |
|---|---|---|---|
| [001](adr-001-evidence-and-verification.md) | Separate maintainability scoring from evidence verification | **Accepted** — stages 1–8 implemented, 9 pending | Report schema, scoring, grading, history studies |
| [002](adr-002-null-verified-grade-in-ci.md) | Whether null `verified_grade` needs a CI policy before stage 5 | **Rejected** — premise assumed a grade gate that does not exist | CLI exit codes, ADR 001 stage 5 |
| [003](adr-003-deterministic-semantic-policy.md) | Add deterministic, repository-aware semantic findings without changing the uniform rubric | **Proposed** — TypeScript precision prototype required | Analyzers, configuration, findings, remediation prompts |
| [004](adr-004-economic-context.md) | Add configured economic-impact scenarios without turning the score into a cost prediction | **Proposed** — historical validation design required | Configuration, report schema, prioritization, studies |
| [005](adr-005-insufficient-population.md) | Withhold rates, per aspect, where the denominator is too small to support one | **Accepted** — implemented | Scoring, grade profile, report contract, every consumer |
| [006](adr-006-analyzer-evidence.md) | External analyzers produce the evidence; the agent orchestrates and corroborates across tools | **Accepted** — implemented; the point estimate uses analyzer pressures for every dimension measured on the full concept set, with the built-in detectors as the fallback. Calibration (3.6) was re-derived 2026-08-14 against that mix (`CALIBRATION_C` 2.6279 → 2.2658). Java has a built-in range fallback; **we will not write more range detectors** for Go/C/C++/C#/Rust. Remaining population work is analyzer-supplied measurements for languages the built-ins cannot range. 2.5c deferred to 1.0. | Whole evidence layer, determinism promise, installation, CI, report contract |
| [007](adr-007-pillars-and-practice.md) | Adopt the five-pillar framework; separate practice maturity from code condition | **Accepted** — implemented; the §4 vocabulary rename was **refused**, recorded in the ADR and [standard.md](standard.md#shared-vocabulary-and-where-this-tools-terms-differ) | Reporting taxonomy, scope boundaries, remediation prioritization |
| [008](adr-008-translation-and-decision.md) | Translation layer from tool output to scoring input; the LLM boundary; CLI and MCP entry points | **Accepted** — implemented except the band matrix; `_bands` exists and is unused; binary warn/fail rates still ship (see architecture [Known debt](architecture.md#known-debt)) | Evidence normalization, thresholds, remediation, entry points |
| [009](adr-009-scan-history.md) | Persist a scan history so the engine can measure change over time | **Accepted** — implemented. Finding identity shipped as `function:{path}:{name}#{ordinal}` in `_identity`, not a content hash | Persistence, finding identity, determinism, report, `--fail-on-new` |
| [010](adr-010-repository-discovery.md) | Classify every file by language and provenance from evidence the repository provides | **Accepted** — implemented | Scanned population, scored population, analyzer applicability, coverage |

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

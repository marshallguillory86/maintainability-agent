# Decision register

Every architectural decision, including the ones not yet made.

A decision recorded only as a sentence inside a design document is a decision that gets re-litigated. This register exists so that "why is it like this?" and "what are we still arguing about?" both have one answer, and so an open question is visibly *open* rather than dissolved into prose in three files.

## Register

| ID | Decision | Status | Affects |
|---|---|---|---|
| [001](adr-001-evidence-and-verification.md) | Separate maintainability scoring from evidence verification | **Accepted** — stages 1–4 implemented, 5–9 pending | Report schema, scoring, grading, history studies |
| [002](adr-002-null-verified-grade-in-ci.md) | What a CI gate does when `verified_grade` is null | **Proposed** — blocks ADR 001 stage 5 | CLI exit codes, badges, API consumers |

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

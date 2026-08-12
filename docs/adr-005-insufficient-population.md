# ADR 005: Report no score when the population is too small to measure

- Status: Accepted
- Date: 2026-08-12
- Scope: Grade profile, the public score contract, every consumer
- Depends on: [ADR 001](adr-001-evidence-and-verification.md) — implementation status in the [register](decisions.md)
- Related: [ADR 006](adr-006-analyzer-evidence.md), [ADR 007](adr-007-pillars-and-practice.md)

## Context

A repository containing one production function, one test, a README and a changelog currently scores **5.0 / A+, evidence complete, verified**. Every finding count is genuinely zero, every rate is zero over a tiny denominator, and every aspect lands on 5.0.

The arithmetic is right. The number is meaningless, and the tool says it with full confidence.

This is the same family of mistake the evidence model was built to remove, one level up. [ADR 001](adr-001-evidence-and-verification.md) separated *measured zero* from *could not measure* from *does not apply*. It never introduced **measured, but over a population too small to support a conclusion**. `evidence_status: complete` today asserts that every required measurement was resolved. It asserts nothing about whether resolving them told us anything.

Two consequences, both bad:

- A new repository earns A+ on its first commit and gets *worse* as real code arrives. The scale rewards emptiness.
- The verified grade — the field stage 5 introduced specifically so that a grade means something — is issued in exactly the case where it cannot.

The scale is calibrated against 40 mature repositories. The smallest carries **39 files and 139 declarations** (36 production declarations). Below that, the tool is extrapolating outside the range it was calibrated on, and saying so is cheaper than pretending otherwise.

## Options

**A. Do nothing; document the limitation.** Rejected. The number is published, machine-readable, and flattering. A caveat in `docs/standard.md` does not reach a CI badge or a JSON consumer, and "the tool gives new repos an A+" is the kind of result that discredits a scale.

**B. Withhold only the verified grade.** Rejected as insufficient. It was the author's first proposal and it is half a fix: `maintainability_estimate: 5.0` is fabricated whether or not a letter accompanies it, and consumers that read the estimate — the PR comment, the prompt, SARIF — would still carry it.

**C. Suppress the rolled-up score below a repository-wide population floor, keep every aspect.** Rejected on review, and the reasoning is worth keeping because it was the author's second mistake in the same hour. The claim was that "the aspects are still true statements about what was seen." They are not. `dead_code: 5.0` computed over one production declaration is the identical fabrication one level down, and a reader of the aspect table draws the identical false conclusion. Suppressing the rollup while publishing thirteen unsupported aspects fixes the symptom and keeps the disease.

**D. Scale confidence continuously with population.** Rejected for now. It needs a model of how rate variance falls with denominator, which is an empirical claim this project has no evidence for, and inventing one would breach the evidence standard in a decision about not inventing numbers.

**E. Apply the rule per aspect, at the denominator each aspect actually divides by.** Accepted. An aspect whose denominator is too small to support a rate reports **not measurable** instead of a number, using the `Unknown` state ADR 001 already built and every consumer already renders. The rollup then falls out for free: a score over mostly-unmeasurable aspects has nothing to roll up, and the existing "withholding cannot improve a grade" property does the rest.

This is strictly better than a repository-wide floor because denominators differ per aspect. A repository with 400 declarations in one enormous file has ample material to judge `declaration_size` and none to judge `file_size`; a single repository-level gate cannot express that, and per-aspect denominators can.

## Decision

An aspect is scored only where its own denominator supports a rate. Below that, the aspect is `Unknown` with a reason naming the population and the floor, and the rollup withholds the score.

```text
maintainability_estimate  null
maintainability_range     null
verified_grade            null
verified_grade_blockers   []
evidence_status.status    "insufficient"
evidence_status.reasons   names the population and the floor
```

Each aspect declares the minimum denominator at which its rate is meaningful, in the same rubric table that declares its weight. The floors are anchored on the reference corpus, whose smallest member carries **39 files, 139 declarations and 36 production declarations** — the scale's meaning derives from that corpus, so extrapolating beneath it is unsupported by construction. They are thresholds, not measurements: a Tier 2 judgment under [product intent](product-intent.md#the-evidence-standard), stated explicitly, applied identically everywhere, and arguable by changing one visible number.

Findings are never suppressed. A two-file repository with a 300-line function still reports it, because that is an observation about a specific line of code and needs no population to be true. What is withheld is every *rate* — the aspect scores and the rollup — because a rate over a denominator of one is arithmetic, not evidence.

## Consequences

- A new or tiny repository gets findings and no grade, instead of an A+ it did not earn.
- `maintainability_estimate` and `maintainability_range` become nullable. This is a public contract change and rides with the schema-version bump it requires.
- `evidence_status.status` gains a third value. Consumers that branch on `complete`/`incomplete` must handle it; the shared presentation helper does this in one place.
- Partial suppression becomes normal and must render well: a mid-sized repository may measure eight aspects and withhold five, and the report has to make that legible rather than alarming.
- CI is unaffected: `--fail-on-gate` reads hard findings, never a score, so a repository below the floor still fails on real gate breaches and passes when clean.
- The floors are visible and arguable. Someone who thinks 139 declarations is the wrong line changes one constant and says why.
- This interacts with [ADR 006](adr-006-analyzer-evidence.md): population insufficiency and analyzer unavailability are different causes of the same `Unknown`, and the reason string must distinguish them. "Nothing measured it" and "it was measured over three declarations" call for different responses.

## Invariants

1. An aspect whose denominator is below its declared floor is `Unknown`, never a number.
2. When no aspect in a category is measurable, the category is `Unknown`; when the rollup has no measurable categories, `maintainability_estimate`, `maintainability_range` and `verified_grade` are all null and `evidence_status.status == "insufficient"`.
3. An aspect at or above its floor is unaffected — same value as before this decision.
4. Findings are never suppressed by insufficiency, only rates.
5. No consumer renders a suppressed score as a number, a dash, or a zero.
6. `--fail-on-gate` exit codes are unchanged by insufficiency.
7. Every insufficiency reason names both the observed population and the floor, and is distinguishable from an analyzer-unavailability reason.

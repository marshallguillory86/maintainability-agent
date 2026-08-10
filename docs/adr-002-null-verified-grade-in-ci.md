# ADR 002: What a CI gate does when `verified_grade` is null

- Status: **Proposed** — awaiting a decision from the maintainers
- Date: 2026-08-10
- Scope: CLI exit codes, `--fail-on-gate`, badges, and any API consumer reading the grade
- Blocks: [ADR 001](adr-001-evidence-and-verification.md) stage 5

## Context

[ADR 001 §1](adr-001-evidence-and-verification.md) decides that insufficient evidence must produce `verified_grade: null` plus explicit reasons, rather than a pessimistic letter grade. The reasoning holds: grading the floor conflates *missing evidence* with *demonstrated poor maintainability*, and forces every domain rule to participate correctly in imputation.

Today the grade is banded from the evidence floor, with unknowns priced at zero. This makes concealment unprofitable — hiding an aspect can only push the floor down — at the cost of telling a repository with a shallow clone that it is a C when nobody has established anything of the kind.

The ADR did not say what `--fail-on-gate` should do with a null. That is not a detail. It is the difference between a safety property and a hole:

- **Fail open** (null passes) means a repository can turn its gate green by withholding evidence. `actions/checkout` defaults to `fetch-depth: 1`, so this is not even adversarial — it is the default configuration.
- **Fail closed** (null fails) means every repository that has not opted into full history has a red build on upgrade.

Whichever is chosen, the current floor-grade behavior is strictly safer than fail-open, so stage 5 must not ship until this is settled. Shipping it undecided would replace a working safety property with a hole, in the name of an architectural improvement.

## Options

**A. Fail closed — null is a gate failure.**
Preserves the concealment property exactly. Upgrading breaks builds for every shallow-clone repository until they set `fetch-depth: 0`, which is a one-line fix but an unannounced one. Honest, noisy, and safe by default.

**B. Fail open — null passes, reasons are reported.**
Never breaks an upgrade. Reintroduces the exploit the last three audit rounds were spent closing, in its worst form: silence becomes success. Rejected on those grounds unless someone can show the exploit is not reachable.

**C. Configurable, defaulting to fail closed.**
`require_verified_grade: true` by default; a repository may opt into passing on null. Preserves the default safety property, gives large repositories an escape hatch, and makes the choice visible in config where a reviewer can see it. Costs one config key and one more code path.

**D. Fail on the estimate when the grade is null.**
Gate on `maintainability_estimate` against a configured threshold, ignoring evidence completeness. Keeps builds meaningful without full history, but reintroduces anchor-imputed unknowns into the gating decision — which is precisely the coupling ADR 001 §1 separates. Rejected as a default; acceptable only as an explicit opt-in under C.

## Decision

**Recommended: C, defaulting to fail closed.**

The default must preserve the property that withholding evidence cannot produce a better CI outcome, because that property was bought with three audit rounds and is the one thing a CI consumer actually relies on. The opt-in exists because "we cannot fetch full history in this pipeline" is a legitimate constraint, and a tool that ignores it gets disabled entirely — which is a worse outcome than a documented, visible relaxation.

The upgrade break is real and is handled by release notes plus a blocker message naming `fetch-depth: 0`, not by weakening the default.

Needed to settle this: a maintainer decision on whether the opt-in key exists at all, or whether B-style behavior should simply never be reachable.

## Consequences

- `--fail-on-gate` gains one input: whether a verified grade is required.
- The upgrade to stage 5 becomes a breaking change for shallow-clone CI and must be released as one.
- Badges and API consumers need a rendering for "ungraded" that is not mistaken for a passing grade or for an F.
- The blocker that currently explains a floor-graded demotion becomes the explanation for a null grade, and keeps naming the specific missing evidence.

## Invariants

Whatever is chosen must satisfy these, and each is checkable:

1. Replacing any `Measured` evidence node with `Unknown` cannot improve the CI outcome — not the exit code, not the grade, not the badge.
2. A null grade is never rendered as, or serialized as, a passing grade.
3. The reasons for a null grade name specific missing measurements, never a bare "insufficient evidence".
4. If the opt-in of option C exists, enabling it is visible in the report, so a reader can tell which contract produced the result.

Invariant 1 is the one that makes this a decision rather than a preference: option B fails it, which is why it is listed and rejected rather than quietly omitted.

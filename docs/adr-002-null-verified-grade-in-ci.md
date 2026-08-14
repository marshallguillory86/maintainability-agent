# ADR 002: Do not couple `verified_grade` to the existing CI gate

- Status: **Rejected** — the proposed decision assumed a grade gate that does not exist
- Date: 2026-08-10
- Scope: CLI exit codes and ADR 001 stage 5

## Context

[ADR 001](adr-001-evidence-and-verification.md) stage 5 introduces
`evidence_status` and `verified_grade` alongside the existing compatibility
fields. Insufficient evidence produces `verified_grade: null` with specific
reasons instead of pretending that unknown quality is demonstrated poor
quality.

The original proposal treated `--fail-on-gate` as a consumer of the letter
grade and asked whether a null grade should fail open or fail closed. That
premise is false. The shipped CLI exits nonzero for `--fail-on-gate` only when
`report["hard_gate_failures"]` is non-empty. It does not inspect `score.grade`,
an overall threshold, or any grade field. The CLI documentation describes the
same contract.

No shipped badge or API consumer that gates on the grade was identified.
Designing null-grade behavior for those hypothetical consumers would violate
ADR 001's staged migration: introduce the fields first, then migrate actual
consumers deliberately.

## Options considered

**A. Make null fail through `--fail-on-gate`.**
Rejected because it changes an existing hard-finding gate into an
evidence-completeness gate. That is a new CLI contract, not a consequence of
adding a report field.

**B. Make null pass through `--fail-on-gate`.**
Rejected because the flag never reads the grade. Calling the unchanged behavior
"fail open" would falsely imply that a grade gate exists today.

**C. Add configuration for null-grade behavior now.**
Rejected because no current consumer needs it. It would add a speculative code
path before ADR 001 stage 5 has established the field being configured.

**D. Preserve existing behavior while Stage 5 adds shadow fields.**
Accepted as the bounded migration path in ADR 001; it requires no separate CI
policy decision.

## Decision

Reject this ADR's proposed CI policy decision. Its premise does not match the
shipped CLI.

ADR 001 stage 5 is not blocked. It may add `evidence_status` and
`verified_grade` alongside compatibility fields without changing exit codes,
`--fail-on-gate`, or existing rendered fields. Consumer migration remains ADR
001 stage 7 work.

If a real consumer later needs to gate on `verified_grade`, that behavior must
be designed from that consumer's explicit contract. This ADR does not invent a
flag, configuration key, badge, API, or threshold for it.

## Consequences

- Stage 5 remains a backward-compatible schema addition.
- `--fail-on-gate` keeps its documented meaning: fail on hard-gate findings.
- No speculative `require_verified_grade` setting is added.
- Stage 7 must inventory actual consumers before changing how any of them use
  `verified_grade`.

## Invariants

1. Adding Stage 5 fields does not change CLI exit codes for an otherwise
   identical report.
2. `--fail-on-gate` continues to depend only on hard-gate findings unless a
   later accepted decision explicitly changes its contract.
3. `verified_grade: null` carries specific evidence reasons and is never
   represented as a passing verified grade.

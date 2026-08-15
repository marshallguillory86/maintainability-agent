# TypeScript semantic-policy prototype

**Genre: pre-registered prototype contract.** This document fixes the inputs,
signals, labels, and acceptance bar before any implementation result exists.
It is not a precision result.

## Scope

This increment is TypeScript only. It uses recorded, versioned type-analysis
facts and checked-in repository policy. It does not call an LLM, install a
compiler, or infer a repository convention from a name.

The reviewed corpus is [`tests/fixtures/semantic_ts/`](../tests/fixtures/semantic_ts/):

- `labels.json` separates labeled true positives from benign lookalikes;
- `recordings/typescript-5.9.2.json` is the fixed type-analysis input;
- `maintainability-agent.json` supplies exact-path semantic policy; and
- `src/` and `benign/` hold the TypeScript examples under review.

Missing or unsupported type analysis is `Unknown` coverage. It is never a
successful run with zero violations, and no test skips that state into green.

## The three signals

No fourth signal is part of this prototype:

1. **Typed domain boundary:** typed analysis proves that a plain `string` is
   used where an existing declared domain type such as `OrderStatus` is
   required. This is a universal fact.
2. **Repeated public-boundary validation:** the checked-in `semantic_policy`
   names an exact boundary and required type; typed analysis proves that the
   same primitive is re-validated or converted there. This is a policy
   violation and must name the policy entry.
3. **Repeated operation set:** one operation-name set appears across dispatch,
   capability, and description roles, or its history moves in lockstep. This is
   a design-review candidate only. It does not prove an enum, value object, or
   operation hierarchy is the right design.

Bare strings without a declared domain type are candidates or nothing, never a
universal violation. In particular, a suffix such as `_id` is not a policy.

## Frozen acceptance bar

Precision and recall are reported separately. Before implementation results:

- emitted results must reach **at least 0.95 precision** against the labeled
  corpus;
- recall has no minimum for this increment—low recall is accepted in exchange
  for high precision; and
- universal, policy, and candidate results are counted separately as well as
  together, so candidate volume cannot conceal an actionable false positive.

The corpus and bar may not be changed in the same change that reports a result.
Expanding the corpus is welcome; weakening labels after seeing output is not.

## Scoring and gates

Semantic results do not appear in `_formula.CATEGORY_ASPECTS`, do not enter
`_calibration.py`, and cannot change `maintainability_estimate`,
`maintainability_range`, `verified_grade`, or `evidence_status`. A candidate is
prompt-only and must never fail `--fail-on-gate`. Its prompt language names the
evidence and asks for design review without claiming “replace with an enum” is
proven.

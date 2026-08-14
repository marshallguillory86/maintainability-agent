# ADR 003: Add deterministic semantic policy without changing the rubric

- Status: Proposed
- Date: 2026-08-11
- Scope: Type-aware analyzers, repository policy, finding classification and
  remediation prompts

## Context

The native scanner deliberately under-reports when syntax alone cannot support
a finding. That is the right failure mode for generic structural checks, but it
leaves out a class of maintenance problems experienced developers recognize
through domain meaning.

A representative case defines operations as bare strings and repeats those
strings across dispatch and capability checks. Replacing the literals with
method names or an enum removes misspelling risk but may leave the real design
problem intact: an operation can be a domain object carrying behavior, and
different operations may have different result types expressed through a
generic contract. The source contains observable symptoms; it does not contain
enough universal information to prove the intended abstraction.

There is also a temporal signal that a one-shot scan cannot see. A developer
feels the same module resist the fourth change and recognizes that repeated
local patches have crossed a design threshold. An agent evaluating isolated
requests can keep patching indefinitely. Git history can measure repeated
touches, synchronized edits and recurring validation or dispatch changes, but
those observations still do not prove a particular redesign.

The product must preserve P1: no LLM, no network and identical results for the
same inputs. It must also preserve P2: repository knowledge cannot silently
change the uniform score.

## Options

### A. Treat bare primitives as a universal defect

Flag strings used in dispatch, identifiers or closed value sets and recommend
one replacement abstraction.

This is simple and deterministic, but wrong in both directions. Many strings
are appropriate, and syntax cannot decide whether the right replacement is a
literal union, enum, value object, protocol or operation object.

### B. Add an LLM semantic reviewer to the audit

Ask a model to infer the domain and recommend an abstraction.

This may produce useful review commentary, but it breaks the offline,
repeatable audit contract. It cannot be the source of a deterministic finding
or gate.

### C. Combine type-backed facts, checked-in policy and labeled candidates

Use language-native type information where it proves a fact, explicit policy
where maintainers have supplied domain intent, and conservative heuristics only
to nominate design-review candidates.

This preserves determinism while admitting that not every design judgment is
derivable from source.

## Proposed decision

Choose option C, subject to a TypeScript precision prototype.

Every semantic result has exactly one class:

1. **Universal finding.** A compiler or analyzer establishes the violation
   without repository-specific meaning. An example is passing a plain `string`
   where an existing declared `OrderStatus` is required.
2. **Configured policy violation.** A checked-in semantic policy declares the
   repository's boundary or domain concept, and typed analysis establishes a
   violation. An example is a public order API accepting `string` where policy
   requires `OrderStatus`.
3. **Design-review candidate.** Structural or historical evidence suggests a
   missing abstraction but cannot prove the intended design. An example is one
   closed set of operation names repeated across dispatch, permission and
   validation sites, or repeatedly changed together over time.

Universal findings and configured violations may become gateable after their
precision is measured. Candidates are prompt-only and never hard-gating.
Nothing in this path changes rubric weights, aspect scores, grade bands or the
meaning of the standard score. A future decision may consider scoring only
after an evidence-backed rule has a repository-independent meaning.

## Design

### Analysis boundary

```text
source + compiler/type checker + analyzer version
                         |
checked-in semantic policy
                         |
        normalized semantic finding
        - class
        - rule identifier and version
        - exact locations and symbols
        - observed type facts
        - policy provenance, when applicable
        - suggested review boundary
                         |
       report -> bounded remediation prompt
```

Language-native analysis is preferred when a language exposes a stable type
API. External analyzers may enter through SARIF if their provenance and rule
identity survive normalization. The normalized result must not imply that two
tools have identical semantics. TypeScript ESLint documents custom rules that
consume TypeScript type information, and Semgrep documents typed metavariables;
both are candidate implementation mechanisms, not evidence that a proposed
rule is accurate.

### Initial TypeScript signals

The discovery prototype should test a small number of high-precision signals:

- a `string` parameter or field constrained by comparisons to one finite
  literal set across multiple sites;
- the same primitive repeatedly validated or converted at module or API
  boundaries;
- an existing domain type bypassed by a primitive at a typed boundary;
- one operation-name set repeated across dispatch, capability and description
  logic;
- history showing the same operation set or validation convention changed in
  lockstep repeatedly.

The last two are candidates, not proof that an enum or operation hierarchy is
correct. The prompt must name the evidence and ask the implementer to preserve
operation-specific input and result types. It must not mechanically prescribe
an enum when behavior-bearing objects or a generic operation contract may be
the actual design.

### Policy shape

Policy is explicit, versioned and checked in. Initial configuration should
prefer exact concepts and boundaries over broad naming conventions:

```yaml
semantic_policy:
  version: 1
  domain_types:
    - paths: ["src/orders/**"]
      boundary: public
      symbol: status
      required_type: OrderStatus
  operations:
    - paths: ["src/session/**"]
      capability_type: SessionCapability
      operation_contract: "Op[TResult]"
```

A convention such as “every name ending in `_id` must be a value object” is too
broad for the first version. Configuration supplies intent; it does not get to
declare its own score weights or relabel a candidate as a universal fact.

### Discovery and acceptance bar

Build a reviewed corpus of true and benign examples before implementation is
made gateable. The prototype should:

1. run on TypeScript only;
2. implement two or three signals through the compiler API or a typed analyzer;
3. compare findings with human labels and report precision and recall
   separately;
4. target high precision and accept low recall;
5. emit findings and prompts without score weight or hard gates; and
6. test that the generated work order names exact evidence and does not widen
   the requested refactor.

The precision threshold and corpus must be pre-registered before results are
known. A useful candidate stream does not by itself earn a universal finding.

## Consequences

- Repository maintainers can encode domain facts the generic scanner cannot
  infer while keeping analysis offline and reproducible.
- The work order can surface design pressure that grep and token counting miss.
- Every supported language needs a type-aware implementation or a provenanced
  adapter; coverage will therefore be uneven and explicitly reported.
- Policy authoring adds configuration cost and can encode a bad local decision.
  The report must identify configured policy rather than laundering it into a
  universal recommendation.
- Historical friction becomes visible, but remains a review trigger rather
  than a claim that the tool possesses experienced judgment.

## Invariants

1. Identical source, history window, analyzer versions and semantic policy
   produce byte-identical semantic findings.
2. A configured policy violation identifies the exact policy entry and source
   evidence that produced it.
3. Removing semantic policy cannot create a configured violation.
4. A design-review candidate cannot fail a gate or alter any score or grade.
5. No semantic finding changes `_formula`, `_calibration`, category weights or
   grade bands through a repository-specific path.
6. Unsupported or unavailable type analysis is reported as unknown coverage,
   never as zero violations.
7. The remediation prompt distinguishes an observed symptom from the proposed
   abstraction and does not claim that one replacement design was proven.

## References

- [typescript-eslint: Custom Rules](https://typescript-eslint.io/developers/custom-rules/)
- [Semgrep: Type awareness in semantic grep](https://semgrep.dev/blog/2020/type-awareness-in-semantic-grep/)

# ADR 001: Separate Maintainability Scoring from Evidence Verification

- Status: Accepted. Implementation progress is tracked in the [decision register](decisions.md), which is the single place it is stated
- Date: 2026-08-09
- Owners: Maintainability Agent maintainers
- Scope: Report schema, scoring, grading, legacy-report handling, and history-based studies

## Context

The current scorer receives nested, untyped dictionaries and uses missing keys to represent several different states:

- a measurement was taken and the result was zero;
- a measurement could not be taken;
- a measurement does not apply;
- an older report did not contain the field;
- a malformed or selectively incomplete report omitted the field.

Those states are not interchangeable. They are nevertheless interpreted independently in pressure calculations, aspect scoring, caps, evidence blockers, interval construction, and grading. Defaults such as `get(name, 0)` can turn "not reported" into "measured clean"; direct indexing can turn incomplete evidence into a crash. Repeated fixes have corrected individual fields while leaving structurally identical paths elsewhere.

The current grade also combines two separate questions:

1. What does the measured evidence suggest about maintainability?
2. Is enough evidence present to issue a verified letter grade?

Pricing unknown aspects into an interval is useful for an estimate, but using that interval to manufacture a letter grade makes evidence completeness part of the maintainability number. It also creates interactions among imputation, grade bands, testability caps, and missing-field behavior that are difficult to reason about and easy to overclaim in tests.

History-based studies have the same boundary problem in a different form. Clone acquisition, cache repair, window selection, diff measurement, and statistical analysis currently share one execution path. A pinned commit is not a sufficient reproducibility boundary if selected commits lack parents or the selected population changes with cache state.

## Decision

### 1. Quality and evidence sufficiency are separate outputs

The report will expose four distinct concepts:

```text
maintainability_estimate   numeric point estimate from available evidence
maintainability_range      lower and upper estimate under unknown evidence
evidence_status            complete, incomplete, or invalid, with reasons
verified_grade             letter grade, or null when evidence is insufficient
```

`maintainability_estimate` and `maintainability_range` describe quality. `evidence_status` describes whether the inputs support a grade. `verified_grade` is issued only when the configured grade profile's required evidence is complete and valid.

Missing required evidence will not produce a pessimistic letter grade. It will produce `verified_grade: null` plus explicit reasons. This makes concealment unprofitable without pretending that unknown quality is known to be bad.

Reports may retain `score.overall`, `score.overall_range`, and `score.grade` during a documented compatibility period, but `score.grade` must not silently change meaning. A schema-versioned migration will either map it to `verified_grade` or deprecate it explicitly.

### 2. Evidence states are explicit and typed

Every scoring input will be normalized at one boundary into exactly one of:

```text
Measured(value, provenance)
Unknown(reason, provenance)
NotApplicable(reason, provenance)
```

These states apply recursively to summary and history evidence. Missing dictionary keys are an input-format concern, not a scoring state. Scoring functions must not use `get(name, 0)` to decide that missing evidence is clean, and they must not index optional evidence directly.

`Measured(0)` means the scanner looked and found none. `Unknown` means it could not establish a value. `NotApplicable` means the measurement has no meaningful population for this repository. Only `Measured` contributes a measured value to an aspect.

### 3. Validation and migration happen before scoring

Reports will carry an explicit schema version. A single normalization layer will:

1. validate the report structure;
2. migrate supported older versions;
3. attach evidence state and provenance;
4. reject invalid combinations;
5. produce the typed model consumed by scoring.

Scoring code will not contain compatibility fallbacks for older dictionary shapes. Each supported migration will be named, versioned, and tested independently. Unsupported versions will fail with a clear error rather than being silently interpreted under the latest rubric.

Before implementing migrations, confirm which historical artifacts are actually rescored. Compatibility code will not be retained for hypothetical consumers.

### 4. Scoring consumes normalized evidence only

The scoring pipeline will have these boundaries:

```text
raw scan/report
    -> schema validation and version migration
    -> typed evidence model
    -> aspect measurements
    -> category and overall estimate/range
    -> evidence-policy evaluation
    -> verified grade or indeterminate result
```

Aspect functions will not inspect raw report dictionaries. Grade policy will not infer evidence completeness from numeric scores. Testability and other domain rules will consume explicit evidence states rather than adding caps conditionally on key presence.

### 5. Grade profiles declare required evidence

Evidence requirements belong to a named grade profile. The default profile will state which measurements are required for any verified grade and which additional gates apply to A and A+.

A profile may allow estimates when evidence is incomplete, but it may not issue a verified grade while required evidence is `Unknown` or invalid. Reports will name the profile used so CI, badges, and APIs do not confuse different evidence contracts.

### 6. Concealment resistance is an invariant, not an example

The implementation must satisfy these properties:

- Replacing any `Measured` evidence node with `Unknown` cannot improve `verified_grade`.
- Removing required evidence changes a verified grade to indeterminate.
- `Measured(0)`, `Unknown`, and `NotApplicable` remain distinguishable through rendering and serialization.
- Invalid partial structures produce validation errors, not clean scores or uncaught exceptions.
- The point estimate lies within the reported range.
- Complete evidence collapses the range where no other uncertainty remains.
- Adding evidence may narrow the range and may establish a verified grade; it must not change the meaning of already measured values.

Tests will generate the production evidence model and recursively vary evidence states. Hand-maintained summary dictionaries and one-off field deletions may remain as regression tests, but they are not proof of these properties.

### 7. History-window materialization is separate from analysis

History-based measurements, including fix breadth, will use four explicit stages:

```text
resolve pinned repository and commit
    -> materialize and validate an immutable commit window
    -> emit a manifest of selected commits and required parent objects
    -> measure and analyze only that manifest
```

The manifest will record the pinned head, selection rule, selected commit IDs, parent IDs needed for diffs, tool version, and acquisition result. Materialization fails if a selected non-root commit's parent is unavailable. Once the manifest is valid, cache depth and clone history must no longer affect measurement.

Statistical outputs will identify the manifest or its digest. Re-running analysis against the same manifest must not perform network access or Git-history discovery.

## Closure criteria for future audit findings

A finding is closed only when all applicable conditions hold:

1. The original reproduction no longer fails.
2. The governing invariant is stated independently of that reproduction.
3. Tests exercise the production schema or typed model, including nested evidence.
4. Equivalent missing, invalid, zero, and not-applicable states are covered.
5. Public claims do not exceed what the invariant and tests establish.
6. A changed empirical result is re-derived from pinned inputs and corrected wherever quoted.

Passing the ordinary test suite or self-audit is necessary but is not evidence that these closure conditions hold.

## Implementation sequence

The redesign will be delivered in bounded stages:

1. Inventory current report consumers and supported historical versions.
2. Define the versioned raw-report schema and typed evidence model.
3. Add normalization and migration tests without changing scoring output.
4. Move aspect scoring behind the typed boundary.
5. Introduce `evidence_status` and `verified_grade` alongside compatibility fields.
6. Add invariant/property tests over the complete nested evidence model.
7. Migrate CI, Markdown, JSON, SARIF, badges, and prompt consumers.
8. Deprecate and later remove ambiguous compatibility fields and raw-dictionary fallbacks.
9. Separate history-window materialization from fix-breadth measurement and pin manifests in the repository.

Each stage must remain reviewable and preserve unrelated scanner behavior. No stage may claim the architecture is complete before its consumers and invariants have migrated.

## Consequences

### Positive

- Missing evidence has one meaning throughout the system.
- A maintainability estimate no longer masquerades as a verified grade.
- CI and API consumers can distinguish poor quality from insufficient evidence.
- Legacy compatibility becomes visible, bounded, and removable.
- Concealment resistance can be tested as a property of the model.
- History studies become reproducible from explicit manifests rather than cache state.

### Costs and tradeoffs

- The report schema and downstream integrations must migrate.
- Some repositories that currently receive a low letter grade from incomplete evidence will instead receive no verified grade.
- Typed evidence and migrations add code, but replace scattered defensive branches and repeated audit repairs.
- Maintaining estimates alongside verified grades requires careful naming during the compatibility period.

## Rejected alternatives

### Continue patching missing keys individually

Rejected because six audit rounds have demonstrated that field-by-field repairs do not establish the class-level property.

### Keep grading from the pessimistic interval floor

Rejected as the long-term contract because it conflates missing evidence with demonstrated poor maintainability and requires every domain-specific rule to participate correctly in imputation.

### Treat missing values as zero

Rejected because it rewards withheld evidence whenever zero means clean and cannot distinguish an old report from a measured result.

### Renormalize missing aspects away

Rejected because removing evidence removes its weight and can improve the score.

### Require full Git history everywhere

Rejected as the only solution because history can be unavailable legitimately and reproducible studies need an explicit selected window, not an unbounded environmental dependency.

## Non-goals

- Changing aspect weights or calibration constants as part of the architecture migration.
- Claiming that the maintainability rubric predicts business outcomes.
- Re-running the fix-scope experiment.
- Broad scanner refactoring unrelated to evidence normalization.
- Preserving undocumented behavior for arbitrary historical dictionaries.


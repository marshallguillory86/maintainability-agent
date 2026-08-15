# The report contract

Inventory and versioning policy for the dictionary `build_report` returns.

This document exists because [ADR 001](adr-001-evidence-and-verification.md) requires the report's producers and consumers to be *named* before any migration is written: "Compatibility code will not be retained for hypothetical consumers." Everything below was traced in the source, not assumed.

**Status:** see the [decision register](decisions.md), which is the single place ADR 001's implementation status is stated. This document describes the report contract as it stands today.

## The single producer

[`report.build_report`](../src/maintainability_audit/report.py) is the only function that constructs a report. It assembles the scan results, calls `scoring.score_report(report)` on the in-memory dictionary, attaches the result as `report["score"]`, and returns it.

`scoring.score_report` has exactly one caller: that line. **No code path rescores a report loaded from disk.**

## Consumers

Classified as the task requires: *current* reports only, *persisted* historical reports, reliance on undocumented dictionary fallbacks, and whether migration is needed.

| Consumer | Reads | Class | Fallbacks | Migration |
|---|---|---|---|---|
| [`scoring.score_report`](../src/maintainability_audit/scoring.py) | normalizes the report at entry | current only | none — migrated | done |
| [`_pressures`](../src/maintainability_audit/_pressures.py) | `SummaryEvidence` states | current only | none — migrated | done |
| [`_aspects`](../src/maintainability_audit/_aspects.py) | `NormalizedEvidence` | current only | none — migrated | done |
| [`renderers.render_markdown`](../src/maintainability_audit/renderers.py) | `summary`, `score`, `history`, finding lists | current only | minor | **migrated (stage 7)** — estimate, range, evidence status, verified grade, and a table of unavailable measurements with provenance |
| [`renderers.render_pr_comment`](../src/maintainability_audit/renderers.py) | `summary`, `score`, `hard_gate_failures`, `function_hotspots` | current only | minor | **migrated (stage 7)** — same four concepts, condensed |
| [`prompts.render_ai_prompt`](../src/maintainability_audit/prompts.py) | `summary`, `score`, all finding lists | current only | minor | **migrated (stage 7)** — plus an evidence section stating that incomplete evidence is not a code defect and must not widen the work order |
| [`prompts.render_agent_instructions`](../src/maintainability_audit/prompts.py) | canonical score fields, four `summary` counts | current only | none | **migrated** — reads `maintainability_estimate` and `verified_grade`; there is no other letter to substitute |
| [`sarif.report_to_sarif`](../src/maintainability_audit/sarif.py) | finding lists, and `score` for run properties | current only | `.get(key, [])` on finding lists | **migrated (stage 7)** — evidence at run level only; results, rule ids and levels unchanged, and missing evidence never becomes a result |
| [`baseline.write_baseline`](../src/maintainability_audit/baseline.py) | root, git commit, and finding lists | current only (write side) | none | baseline v3 |
| [`baseline.load_baseline_identities`](../src/maintainability_audit/baseline.py) | **persisted file**, `identities` plus labels | **persisted** | a hand-added bare label matches that exact label only | versions 1/2 rejected; regenerate |
| [`cli`](../src/maintainability_audit/cli.py) | orchestrates; passes the report through | current only | none | **no change (stage 7)** — `--fail-on-gate` still reads hard findings only, per ADR 002 |
| [`tools/calibration/measure.py`](../tools/calibration/measure.py) | `summary` of a live `build_report` | current only | none | stage 4 |
| [`tools/calibration/measure_cohorts.py`](../tools/calibration/measure_cohorts.py) | `summary`, `score.maintainability_estimate` of a live `build_report` | current only | none | **migrated (stage 8)** |
| [`_derive._corpus_overall`](../src/maintainability_audit/_derive.py) | a **synthesized** summary from `measurements.json` `evidence` blocks | persisted *measurements*, not reports | builds its own dict | stage 4 |

Tests and fixtures that construct or consume report shapes: `test_audit_components.py`, `test_scanning.py`, `test_cli.py`, `test_sarif.py`, `test_near_duplicates.py`, `test_declaration_grading.py` (all via `build_report`), plus `test_scoring_calibration.py` and `test_calibration_corpus.py` (hand-built summary dictionaries passed directly to `score_report`). The hand-built ones are the reason ADR 001 §6 requires production-model tests: they carry whichever keys the scorer needs and cannot demonstrate a property of real reports. `test_evidence_normalization.py` starts from `build_report` for exactly that reason.

### The persisted baseline contract

Baseline version 3 stores two views of the same finding population:

```json
{
  "version": 3,
  "commit": "<git commit>",
  "findings": ["function:{path}:{name}#{ordinal}"],
  "identities": [{
    "kind": "declaration",
    "path": "path/to/file.py",
    "name": "name",
    "ordinal": 0,
    "body_digest": "<scan-time digest>",
    "fingerprint": "function:path/to/file.py:name#0"
  }]
}
```

`findings` remains the sorted human-label list. `identities` carries the
structured matching inputs: kind, path, name, ordinal, `body_digest`, and
fingerprint. `findings_not_in_baseline` compares current identities against
those records and applies git's old-path-to-new-path rename map between the
stored commit and the audited commit. A copy is not a rename; a declaration
name change is not rescued by a matching digest.

Baseline versions 1 and 2 cannot be migrated because labels do not contain a
body digest or the commit needed for rename evidence. They are rejected with a
specific `--write-baseline` regeneration instruction. This remains separate
from report-schema normalization: no persisted report is rescored.

## The stage 5 fields

`score.evidence_status` reports `complete` or `incomplete` against the named profile `default-v1`, with one reason per unresolved measurement carrying its typed-model path and provenance. `score.verified_grade` is the letter when the evidence supports one and `null` when it does not.

The profile's required measurements are **frozen by name** in `_verification.DEFAULT_V1_REQUIRED`. Adding a scoring input does not silently change what `default-v1` demands: it fails a test until the input is required under a new profile name or recorded as not required. Editing v1's set in place is a v2.

`Measured(0)` and `NotApplicable` are both **complete** evidence — the scanner looked and found none, and the measurement has no population here. Only `Unknown` withholds a grade. In the rollup, `NotApplicable` removes the corresponding aspect from the category denominator under the point estimate and both interval endpoints; it is neither a clean score nor unresolved uncertainty.

**What stage 8 changed.** `score.grade` is gone; `verified_grade` is the only letter a report carries. `verified_grade_blockers` explains an *issued* grade and is empty when none was issued — what is missing is named in `evidence_status.reasons` instead. Adding optional fields does not bump the schema version, but removing or renaming public fields does, which is why stage 8 became version 2. ADR 005 then made the estimate nullable as version 3. Invalid input still raises `EvidenceValidationError` or `UnsupportedReportSchema`: there is no serialized `invalid` status, because a malformed report must not flow onward carrying numbers nobody should trust.

## Schema version

**Version 3 (ADR 005).** `maintainability_estimate` and `maintainability_range` are nullable, and `evidence_status.status` gains `insufficient`. A scan whose scope is not a whole repository carries no score: the scale is calibrated over whole repositories, so a diff is a different kind of object rather than a small one. Consumers that assumed a number must handle null; the shared presentation helper renders `Not scored`, never a dash or a zero.

Findings, aspects, categories and dimensions are unaffected — only the rolled-up judgment is withheld.


New reports carry a top-level integer:

```json
{ "schema_version": 3, "root": "...", "summary": { ... } }
```

**Version 2 (ADR 001 stage 8)** removed the ambiguous compatibility score fields. **Version 3 (ADR 005)** made the estimate and range nullable. The public `score` object is now:

| Field | Type |
|---|---|
| `standard` | string |
| `maintainability_estimate` | number or `null` |
| `maintainability_range` | `[number, number]` or `null` |
| `evidence_status` | `{status, profile, reasons[]}` |
| `verified_grade` | string or `null` |
| `verified_grade_blockers` | string[] — empty whenever no grade was issued |
| `categories`, `aspects`, `rubric`, `dimensions`, `reference` | unchanged structures |
| `worst_dimension` | string or `null` |
| `analyzer_scored_dimensions` | string[] — dimensions whose analyzer reading set the estimate; empty when none did |

`overall`, `overall_range`, `grade` and `grade_blockers` are gone, with no aliases. **Version 1 is rejected, not migrated** — the inventory below established that nothing rescores a persisted report, so a migration would serve no caller.

- **Owner.** `build_report` stamps it. The constant lives in [`evidence.py`](../src/maintainability_audit/evidence.py) as `REPORT_SCHEMA_VERSION`, next to the code that validates it.
- **Not the baseline version.** `baseline.write_baseline` writes its own
  `"version": 3`. That numbers a different artifact with a different lifecycle;
  it does not change report schema 3.
- **What forces a bump.** Removing or renaming a scoring input, or changing the meaning of an existing field. Adding a new optional field does not, because absent inputs already normalize to `Unknown` rather than to a value.
- **Compatibility policy.** `normalize_report_evidence` accepts version 3 only. An unsupported or absent version raises `UnsupportedReportSchema`. Nothing is silently interpreted under the latest rubric.
- **Non-normalizing consumers are unaffected.** Renderers, SARIF, prompts and baselines read named keys; an added top-level key is inert to them. Verified by comparing a full report before and after this slice: `score`, `summary` and `history` are byte-identical.

## Evidence states

[`evidence.py`](../src/maintainability_audit/evidence.py) defines exactly three, per ADR 001 §2:

| State | Meaning |
|---|---|
| `Measured(value, provenance)` | the scanner looked and established this value; `Measured(0)` is a finding |
| `Unknown(reason, provenance)` | no value could be established, with the reason |
| `NotApplicable(reason, provenance)` | the measurement has no population in this repository |

`SummaryEvidence` and `HistoryEvidence` name every scoring input currently drawn from `summary` and `history`. `walk_evidence` recurses the model, so tests sweep the real field set instead of a hand-maintained list.

Two behaviors worth recording because they are decisions, not details:

- **History is always a structure.** When a report carries no history, every field is `Unknown` with a reason naming the shallow clone, rather than the object being absent. A caller cannot reach a history number without passing a state that says whether it exists.
- **The state is the only authority after normalization.** Raw history presence is used only while constructing `Measured`, `Unknown`, and `NotApplicable`; no companion `history_present` flag survives into `NormalizedEvidence` or grading. Two representations can disagree, and one did: an `Unknown` ownership count inherited the `NotApplicable` grade exemption merely because a history object existed.
- **Absence is never upgraded.** `single_author_files` becomes `NotApplicable` when no file has three commits — but only if the count was actually recorded. A deleted field stays `Unknown` even when the population is empty, because deleting evidence must not resolve it into a *better-defined* state than leaving it in. This was a live bug in the first draft of the module, caught by its own tests.

## Deliberate no-ops

Confirmed in source during stage 7 rather than assumed:

- **No badge consumer exists.** Nothing in this repository renders or publishes a grade badge, so there was nothing to migrate. One was not created to satisfy the ADR's wording.
- **No API consumer exists.** The JSON report is the API; it already carries both fields.
- **The gate does not compare label sets.** `load_baseline` remains available to
  string consumers, but `--fail-on-new` calls `findings_not_in_baseline`, which
  loads structured identities and applies the shared matcher.

## Remaining work

The contract migration is done; see the [decision register](decisions.md) for where the ADR stands. One stage remains:

**Stage 9 — separate history-window materialization from measurement.** Fix-breadth still resolves, fetches, repairs and measures in one path. The ADR calls for an explicit manifest — pinned head, selection rule, selected commit ids, required parent objects, tool version — checked in, with analysis reading only the manifest and performing no network access.

Older notes on the work those stages cover:

ADR 001 is **partially implemented**: stage 8 shipped; stage 9 remains. Nothing here should be read as claiming otherwise.

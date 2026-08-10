# The report contract

Inventory and versioning policy for the dictionary `build_report` returns.

This document exists because [ADR 001](adr-001-evidence-and-verification.md) requires the report's producers and consumers to be *named* before any migration is written: "Compatibility code will not be retained for hypothetical consumers." Everything below was traced in the source, not assumed.

**Status: ADR 001 is not implemented.** This slice adds a schema version, a typed evidence model, and one normalization boundary. Scoring still reads raw dictionaries and is unchanged. `evidence_status` and `verified_grade` do not exist yet. See [Remaining work](#remaining-work).

## The single producer

[`report.build_report`](../src/maintainability_audit/report.py) is the only function that constructs a report. It assembles the scan results, calls `scoring.score_report(report)` on the in-memory dictionary, attaches the result as `report["score"]`, and returns it.

`scoring.score_report` has exactly one caller: that line. **No code path rescores a report loaded from disk.**

## Consumers

Classified as the task requires: *current* reports only, *persisted* historical reports, reliance on undocumented dictionary fallbacks, and whether migration is needed.

| Consumer | Reads | Class | Fallbacks | Migration |
|---|---|---|---|---|
| [`scoring.score_report`](../src/maintainability_audit/scoring.py) | `summary`, `history`, whole report | current only | **yes** — `_pressures`, `_aspects` | stage 4 |
| [`_pressures`](../src/maintainability_audit/_pressures.py) | `summary` counts | current only | **yes** — `.get(name, 0)`, guarded by `unmeasured_dimensions` | stage 4 |
| [`_aspects`](../src/maintainability_audit/_aspects.py) | `summary`, `history` | current only | **yes** — `.get(key)`, `history.get(key)` | stage 4 |
| [`renderers.render_markdown`](../src/maintainability_audit/renderers.py) | `summary`, `score`, `history`, finding lists | current only | minor — `score.get("grade_blockers")`, `report.get("history")` | stage 7 |
| [`renderers.render_pr_comment`](../src/maintainability_audit/renderers.py) | `summary`, `score`, `hard_gate_failures`, `function_hotspots` | current only | minor — `report.get("mode", "full")` | stage 7 |
| [`prompts.render_ai_prompt`](../src/maintainability_audit/prompts.py) | `summary`, `score`, all finding lists | current only | minor — `report.get("dead_code") or []` and siblings | stage 7 |
| [`prompts.render_agent_instructions`](../src/maintainability_audit/prompts.py) | `score.overall`, `score.grade`, four `summary` counts | current only | none (direct indexing) | stage 7 |
| [`sarif.report_to_sarif`](../src/maintainability_audit/sarif.py) | `largest_files`, `function_hotspots`, `risk_findings`, `duplicate_blocks` | current only | `.get(key, [])` on finding lists; does **not** read `summary`/`score` | stage 7 |
| [`baseline.write_baseline`](../src/maintainability_audit/baseline.py) | `root`, `score`, finding lists | current only (write side) | `report.get("score", {})` | none |
| [`baseline.load_baseline`](../src/maintainability_audit/baseline.py) | **persisted file**, `data["findings"]` only | **persisted** | reads a string list, never evidence | **none — see below** |
| [`cli`](../src/maintainability_audit/cli.py) | orchestrates; passes the report through | current only | none | stage 7 |
| [`tools/calibration/measure.py`](../tools/calibration/measure.py) | `summary` of a live `build_report` | current only | none | stage 4 |
| [`tools/calibration/measure_cohorts.py`](../tools/calibration/measure_cohorts.py) | `summary`, `score.overall` of a live `build_report` | current only | none | stage 4 |
| [`_derive._corpus_overall`](../src/maintainability_audit/_derive.py) | a **synthesized** summary from `measurements.json` `evidence` blocks | persisted *measurements*, not reports | builds its own dict | stage 4 |

Tests and fixtures that construct or consume report shapes: `test_audit_components.py`, `test_scanning.py`, `test_cli.py`, `test_sarif.py`, `test_near_duplicates.py`, `test_declaration_grading.py` (all via `build_report`), plus `test_scoring_calibration.py` and `test_calibration_corpus.py` (hand-built summary dictionaries passed directly to `score_report`). The hand-built ones are the reason ADR 001 §6 requires production-model tests: they carry whichever keys the scorer needs and cannot demonstrate a property of real reports. `test_evidence_normalization.py` starts from `build_report` for exactly that reason.

### The only persisted-report consumer, and why nothing needs migrating

`load_baseline` is the sole reader of a file this tool previously wrote. It reads one key:

```python
data = json.loads(baseline_path.read_text(encoding="utf-8"))
return set(data.get("findings", []))
```

`findings` is a sorted list of fingerprint **strings** (`file-lines:<path>`, `function:<path>:<name>:<line>`, …). The baseline file also stores a `score` snapshot, but **no code reads it back** — it is informational. No evidence, no summary, and no history is ever re-read, so no historical report is ever rescored under a newer rubric.

Consequence, and it is the main decision this inventory drives: **there are no legacy reports to migrate.** The normalizer therefore supports exactly one version and refuses everything else, including unversioned reports, rather than shipping a migration path for a consumer that does not exist. If a genuine rescoring consumer appears later, it arrives with a named, versioned, separately tested migration — which is what ADR 001 §3 asks for.

## Schema version

New reports carry a top-level integer:

```json
{ "schema_version": 1, "root": "...", "summary": { ... } }
```

- **Owner.** `build_report` stamps it. The constant lives in [`evidence.py`](../src/maintainability_audit/evidence.py) as `REPORT_SCHEMA_VERSION`, next to the code that validates it.
- **Not the baseline version.** `baseline.write_baseline` writes its own `"version": 1`. That numbers a different artifact with a different lifecycle and is deliberately left alone; overloading it would tie the report structure to the baseline format.
- **What forces a bump.** Removing or renaming a scoring input, or changing the meaning of an existing field. Adding a new optional field does not, because absent inputs already normalize to `Unknown` rather than to a value.
- **Compatibility policy.** `normalize_report_evidence` accepts version 1 only. An unsupported or absent version raises `UnsupportedReportSchema`. Nothing is silently interpreted under the latest rubric.
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
- **Absence is never upgraded.** `single_author_files` becomes `NotApplicable` when no file has three commits — but only if the count was actually recorded. A deleted field stays `Unknown` even when the population is empty, because deleting evidence must not resolve it into a *better-defined* state than leaving it in. This was a live bug in the first draft of the module, caught by its own tests.

## Remaining work

ADR 001's stages 4-9 are untouched: migrating aspect scorers behind the boundary, `evidence_status` and `verified_grade`, invariant tests over the nested model, consumer migration, removing the raw-dictionary fallbacks in `_pressures`/`_aspects`, and separating history-window materialization from fix-breadth measurement.

Nothing in this repository should be read as claiming the ADR is implemented.

# Architecture

How the package is layered, which layer may depend on which, and the invariant each one owns.

This describes the code **as it is**, not as intended. Where reality falls short of a decision, it is listed under [Known debt](#known-debt) rather than described aspirationally. Direction of travel is in [ADR 001](adr-001-evidence-and-verification.md).

The layering is enforced by `tests/test_architecture.py`, which reads the real import graph. A rule stated here and not enforced there is decoration, and this document tries not to contain any.

## Layers

Dependencies point downward only. No cycles.

```text
  entry          cli, __main__
                     |
  presentation   renderers, prompts, sarif, baseline        reads the report dict
                     |
  assembly       report                                     builds the report, calls the scorer
                     |
        +------------+------------+
        |                         |
  scanners                   scoring
  metrics, duplication       scoring -> _aspects -> _pressures
  deadcode, idioms           _formula, _calibration (rubric data)
  similarity, history        _derive (calibration fit), evidence (boundary)
        |                         |
        +------------+------------+
                     |
  parsing        source, declarations, _cognitive, _ranges, _tokens
                     |
  foundations    _metrics_types, _masking, _hotspots, config, git_tools, instructions
```

| Layer | Owns | May import |
|---|---|---|
| **foundations** | Data types, config defaults, git invocation, masking primitives | nothing internal |
| **parsing** | Reading files once, extracting declarations, complexity, ranges, tokens | foundations |
| **scanners** | Producing findings: sizes, duplicates, dead code, idioms, near-duplicates, history | foundations, parsing |
| **scoring** | Turning findings into aspects, categories, an overall, and a grade | foundations, parsing (types only) |
| **assembly** | Running the scan, assembling the report dict, invoking the scorer once | anything below |
| **presentation** | Markdown, PR comment, SARIF, baseline, remediation prompt | foundations, the report dict |
| **entry** | Argument parsing, output routing, exit codes | anything below |

## The rules, and why each exists

Each rule was bought by a specific failure. They are enforced, not advisory.

**1. Scoring may not import scanners or assembly.**
The rubric must not be able to reach back into how a finding was produced. If it could, a repo-specific special case would eventually be written and P2 (one uniform rubric) would fail silently.

**2. `_formula` and `_calibration` import nothing internal.**
They are the judgment layer — weights, bands, grade gates, the calibration constant — and they are data. A leaf cannot acquire a dependency on scanning, so the rubric cannot come to depend on what it is scoring.

**3. Presentation may not import the scoring internals.**
`renderers`, `prompts`, and `sarif` consume the report dictionary. Today they import only `_hotspots` (a formatting helper) and `config`. This keeps one path to a score: if a renderer could compute one, two numbers could disagree, which is the class of bug that produced an overall contradicting the categories printed beside it.

**4. `evidence` imports nothing internal.**
The normalization boundary is deliberately a leaf. Everything it needs arrives as an argument. This is what makes it a *boundary* rather than another participant — see ADR 001 §3.

**5. The calibration derivation calls the shipped scorer.**
`_derive` imports `_aspects`, `_formula`, and `_pressures` and runs the same functions a live report runs. It may not restate the rollup. Three consecutive audits found the derivation differing from the live path by exactly one step — category rounding, then the untested cap, then per-aspect rounding — and each time the corpus median survived while the per-repository claim did not. "The same pipeline" is only true when there is one pipeline.

**6. No import cycles.**
One existed: `_derive` needed the scorer and the scorer needed the calibration, so `_derive` imported from inside a function body. Splitting `scoring` into `_pressures` / `_aspects` / `scoring` removed it. Cycles are how layering rots without anyone deciding to rot it.

## Data flow

```text
files on disk
  -> SourceIndex          each file read once, parsed once
  -> scanners             findings + counts
  -> report_summary       populations and finding counts
  -> dimension_pressures  counts as rates over their populations
  -> aspect_scores        13 aspects, 0-5 or None for unmeasured
  -> categories           five ISO categories, weighted means, rounded as displayed
  -> overall + range      point estimate; interval with unknowns priced 0 and 5
  -> grade                banded from the interval floor, with named blockers
  -> report dict          + schema_version
  -> renderers / prompts / sarif / baseline
```

Two properties of this flow are load-bearing and each has a test:

- **Rates, not counts.** Every pressure divides by the population it was drawn from. The 0.5.0 model counted absolutely and therefore scored repository *size*: Django, pytest, black and eight others all scored 0.0/F while a 53-file toy scored 4.6/A.
- **Absence is not a value.** A count the report does not carry produces an unmeasured aspect, never a zero. Six audit rounds were spent on individual instances of this before it was stated as a property.

## Invariants and where they are enforced

| Invariant | Enforced by |
|---|---|
| Layering and acyclicity above | `tests/test_architecture.py` |
| Withholding any input cannot raise the floor or the grade | `test_withholding_any_single_input_cannot_raise_the_floor_or_the_grade` |
| `overall_range` always contains `overall` | `test_the_interval_always_contains_the_score` |
| Overall equals the mean of the printed categories | `test_corpus_median_rolls_up_to_exactly_four_through_the_rounded_path` |
| Every advertised aspect carries weight somewhere | `test_every_scored_aspect_carries_weight_in_some_category` |
| Derivation agrees with the live scorer per repository | `test_derivation_matches_live_score_report_repo_by_repo` |
| Absence never resolves into a better-defined state | `test_deleting_a_field_never_resolves_it_into_a_better_defined_state` |
| History window is independent of cache depth | `tests/test_fix_breadth_window.py` |

## Known debt

Stated rather than hidden, because an architecture document that only describes the good parts stops being usable.

- **Scoring still consumes raw dictionaries.** `_pressures` and `_aspects` read `summary` and `history` with `.get`, guarded by `unmeasured_dimensions` rather than by types. The typed boundary in `evidence.py` exists and is tested, but nothing consumes it yet. ADR 001 stage 4.
- **`evidence_status` and `verified_grade` do not exist.** The grade is still banded from the pessimistic floor, which ADR 001 rejects as the long-term contract because it conflates missing evidence with demonstrated poor maintainability.
- **An open decision blocks stage 5:** what CI does when `verified_grade` is null. A null grade that silently passes `--fail-on-gate` would be worse than today's floor grade. Not yet recorded in the ADR.
- **`docs/standard.md` mixes genres** — normative rubric, empirical studies, and audit history in one file, which is the documentation shape that let a Tier 3 claim read as settled. See [product intent](product-intent.md#the-evidence-standard).
- **History window materialization is not separated from analysis.** ADR 001 stage 9.

## Extension points

- **A new detector** belongs in scanners, returns findings, and adds a count to `report_summary`. It becomes scored only by being given weight in `_formula.CATEGORY_ASPECTS`; an aspect with no weight fails the build.
- **A new output format** belongs in presentation and reads the report dictionary. It must not compute a score.
- **A new external analyzer** is ingested as SARIF and kept as `external_findings` with its provenance. Per [adapters](adapters.md), do not pretend every analyzer has the same semantics.

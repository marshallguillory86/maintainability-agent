<!--
Generated from the tree at commit b290b17f6b2747363a7fc0182306cc7a4272a588 plus the staged release
changes. This is a **provenance record, not a promise of currency**: it
states the exact source commit it was generated against, and says
nothing about how far that is from the current HEAD.

An earlier version promised a fixed distance from HEAD — that it trailed
by a single commit. That could not survive a merge — a merge commit puts it two or
more behind, a squash makes the stamped commit not an ancestor at all,
and a rebase rewrites the hash entirely. Worse, defending the claim
meant regenerating the report every time anything landed on top of it,
which is a loop with no end. Compare the stamp against the commit you
care about instead. Regenerate for the current tree with:

    maintainability-agent --config maintainability-agent.json \
        --output /tmp/self-audit.md \
        && sed "s|$(pwd)|.|g" /tmp/self-audit.md > docs/self-audit.md
-->

# Maintainability CI Report

Root: `.`
Branch: `corpus/expand-and-report`

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.3 / 5 |
| Range (unmeasured evidence priced 0..5) | 4.3 (no unmeasured evidence) |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 184 |
| File warnings | 52 |
| File failures | 0 |
| Function warnings | 25 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Scoring standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based.

## Pillars

**Practice level 4 of 5** — CI holds a numeric quality gate.

| Pillar | Scope | Practice | Condition | Reading |
|---|---|---:|---:|---|
| readability | partial | 4 | 4.9 | healthy: enforced, and the code reflects it |
| maintainability | owned | 4 | 3.7 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 4 | — | not measured — see below |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — delegated to secure-code-agent; this tool catalogues security analyzers and never runs them, so silence here is not safety

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

1 of 126 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.sh` | Shell | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 3.5 |
| reusability | 4.7 |
| analyzability | 4.5 |
| modifiability | 3.7 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 3.2 |
| declaration size | 4.7 |
| duplication | 5.0 |
| risk patterns | 5.0 |
| policy gates | 5.0 |
| test presence | 5.0 |
| dead code | 5.0 |
| near duplication | 5.0 |
| idiom consistency | 5.0 |
| documentation | 5.0 |
| churn hotspots | 4.5 |
| change coupling | 2.0 |
| knowledge concentration | 1.0 |

## Not Scored — no measurement exists

| Aspect | Why |
|---|---|
| test effectiveness | requires running the suite (mutation/coverage); this audit never executes code |
| naming quality | no static proxy survives contact; a wrong-name detector needs semantics |
| comment accuracy | comments are deliberately unparsed; staleness needs meaning, not structure |
| indirection depth | call-graph construction is not implemented for the supported languages |
| architectural coherence | no measurement distinguishes a wrong boundary from an unusual one statically |

## Largest Files

| File | Lines | Status |
|---|---|---|
| `tests/test_adapters.py` | 473 | warn |
| `tests/test_consumer_migration.py` | 466 | warn |
| `src/maintainability_audit/_work_order.py` | 460 | warn |
| `tests/test_evidence_properties.py` | 456 | warn |
| `tests/test_analyzer_bridge.py` | 446 | warn |
| `tools/build_catalog.py` | 444 | warn |
| `src/maintainability_audit/scoring.py` | 441 | warn |
| `tests/test_scoring_calibration.py` | 440 | warn |
| `src/maintainability_audit/evidence.py` | 439 | warn |
| `tests/test_discovery.py` | 432 | warn |
| `tests/test_evidence_normalization.py` | 416 | warn |
| `tests/test_analysis_coverage.py` | 405 | warn |
| `src/maintainability_audit/_scan_view.py` | 402 | warn |
| `tests/test_trends.py` | 402 | warn |
| `tests/test_pillars_and_practice.py` | 394 | warn |
| `src/maintainability_audit/_analysis.py` | 388 | warn |
| `tests/test_verified_grade.py` | 387 | warn |
| `src/maintainability_audit/_discovery.py` | 386 | warn |
| `tests/test_recurrence.py` | 384 | warn |
| `src/maintainability_audit/_metric_adapters.py` | 381 | warn |
| `src/maintainability_audit/prompts.py` | 381 | warn |
| `tests/test_scan_history.py` | 375 | warn |
| `src/maintainability_audit/report.py` | 373 | warn |
| `src/maintainability_audit/_formula.py` | 367 | warn |
| `tests/test_work_order.py` | 358 | warn |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `tools/build_catalog.py` | `build` | 373 | 31 | 15 | 0 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 14 | 10 | warn |
| `src/maintainability_audit/prompts.py` | `prompt_work_order` | 80 | 53 | 14 | 11 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 235 | 48 | 14 | 3 | warn |
| `src/maintainability_audit/idioms.py` | `divergent_idioms` | 152 | 51 | 13 | 15 | warn |
| `src/maintainability_audit/_scan_view.py` | `pillars_markdown` | 278 | 49 | 13 | 12 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 169 | 37 | 13 | 4 | warn |
| `src/maintainability_audit/cli.py` | `main` | 137 | 64 | 12 | 19 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 233 | 72 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 372 | 70 | 10 | 13 | warn |
| `src/maintainability_audit/_scan_view.py` | `analyzer_coverage_markdown` | 61 | 72 | 9 | 10 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 308 | 66 | 8 | 1 | warn |
| `src/maintainability_audit/_discovery.py` | `discover` | 321 | 38 | 8 | 16 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `src/maintainability_audit/_discovery.py` | `_generated_directories` | 246 | 25 | 8 | 17 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `src/maintainability_audit/renderers.py` | `render_markdown` | 105 | 70 | 6 | 5 | warn |
| `src/maintainability_audit/_runner.py` | `run` | 196 | 65 | 6 | 10 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |
| `src/maintainability_audit/report.py` | `_assemble` | 229 | 77 | 5 | 1 | warn |
| `src/maintainability_audit/scoring.py` | `score_evidence` | 263 | 63 | 3 | 0 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/scoring.py` | 21 | 1473 | 47 | 2 | 987 |
| `src/maintainability_audit/renderers.py` | 23 | 1074 | 30 | 2 | 690 |
| `tests/test_architecture.py` | 23 | 383 | 27 | 1 | 621 |
| `src/maintainability_audit/_scan_view.py` | 8 | 634 | 65 | 1 | 520 |
| `src/maintainability_audit/cli.py` | 13 | 1868 | 38 | 2 | 494 |
| `src/maintainability_audit/_analysis.py` | 12 | 848 | 35 | 1 | 420 |
| `src/maintainability_audit/metrics.py` | 8 | 1026 | 49 | 2 | 392 |
| `src/maintainability_audit/_aspects.py` | 8 | 470 | 46 | 1 | 368 |
| `src/maintainability_audit/evidence.py` | 9 | 519 | 36 | 1 | 324 |
| `src/maintainability_audit/_pressures.py` | 9 | 709 | 34 | 1 | 306 |
| `tests/test_docs_links.py` | 6 | 366 | 47 | 1 | 282 |
| `src/maintainability_audit/prompts.py` | 9 | 395 | 30 | 1 | 270 |
| `tools/build_catalog.py` | 6 | 676 | 42 | 1 | 252 |
| `tools/calibration/measure_fix_breadth.py` | 5 | 409 | 47 | 1 | 235 |
| `src/maintainability_audit/history.py` | 4 | 357 | 55 | 1 | 220 |
| `src/maintainability_audit/declarations.py` | 5 | 203 | 38 | 1 | 190 |
| `src/maintainability_audit/_work_order.py` | 3 | 464 | 58 | 1 | 174 |
| `tools/calibration/measure_cohorts.py` | 4 | 341 | 40 | 1 | 160 |
| `tools/calibration/measure.py` | 6 | 274 | 26 | 1 | 156 |
| `src/maintainability_audit/_scan_history.py` | 5 | 307 | 30 | 1 | 150 |
| `src/maintainability_audit/_adapters.py` | 12 | 1478 | 12 | 1 | 144 |
| `src/maintainability_audit/_generic.py` | 3 | 281 | 46 | 1 | 138 |
| `src/maintainability_audit/_metric_adapters.py` | 3 | 391 | 45 | 1 | 135 |
| `src/maintainability_audit/_evidence_view.py` | 7 | 372 | 18 | 1 | 126 |
| `src/maintainability_audit/sarif.py` | 5 | 193 | 24 | 2 | 120 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `README.md` | `docs/self-audit.md` | 20 | 95% |
| `CHANGELOG.md` | `README.md` | 20 | 54% |
| `docs/architecture.md` | `tests/test_architecture.py` | 19 | 86% |
| `CHANGELOG.md` | `docs/standard.md` | 17 | 63% |
| `README.md` | `docs/standard.md` | 17 | 63% |
| `docs/README.md` | `docs/architecture.md` | 13 | 72% |
| `docs/architecture.md` | `docs/decisions.md` | 12 | 100% |
| `CHANGELOG.md` | `src/maintainability_audit/scoring.py` | 12 | 63% |
| `CHANGELOG.md` | `docs/self-audit.md` | 12 | 57% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 12 | 57% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 11 | 85% |
| `docs/standard.md` | `src/maintainability_audit/scoring.py` | 11 | 58% |
| `docs/standard.md` | `src/maintainability_audit/report.py` | 11 | 55% |
| `docs/self-audit.md` | `docs/standard.md` | 11 | 52% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 11 | 52% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 77% |
| `src/maintainability_audit/_adapters.py` | `tests/test_adapters.py` | 9 | 90% |
| `src/maintainability_audit/prompts.py` | `src/maintainability_audit/renderers.py` | 8 | 89% |
| `docs/README.md` | `docs/decisions.md` | 8 | 67% |
| `docs/architecture.md` | `docs/report-contract.md` | 8 | 67% |
| `docs/architecture.md` | `docs/roadmap.md` | 8 | 62% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `docs/standard.md` | `tests/test_scoring_calibration.py` | 7 | 100% |
| `docs/README.md` | `docs/product-intent.md` | 7 | 88% |
| `CHANGELOG.md` | `src/maintainability_audit/_formula.py` | 7 | 78% |


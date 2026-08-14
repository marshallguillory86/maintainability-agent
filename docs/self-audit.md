<!--
Generated from the tree at commit 4966d1c579211bb0464d8a57ffc29f4cf9c7b06b. This is a **provenance record, not a promise of currency**: it
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
Branch: `docs/readme-0.7-honest`

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.7 / 5 |
| Range (unmeasured evidence priced 0..5) | 4.7 (no unmeasured evidence) |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 196 |
| File warnings | 56 |
| File failures | 0 |
| Function warnings | 28 |
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
| maintainability | owned | 4 | 4.6 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 4 | — | not measured — see below |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — delegated to secure-code-agent; this tool catalogues security analyzers and never runs them, so silence here is not safety

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

1 of 136 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.sh` | Shell | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Why the verified grade is not higher

- file_warn_rate 0.286 exceeds the A ceiling of 0.05

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.2 |
| reusability | 4.7 |
| analyzability | 4.8 |
| modifiability | 4.7 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 3.2 |
| declaration size | 4.6 |
| duplication | 5.0 |
| risk patterns | 5.0 |
| policy gates | 5.0 |
| test presence | 5.0 |
| dead code | 5.0 |
| near duplication | 5.0 |
| idiom consistency | 5.0 |
| documentation | 5.0 |
| churn hotspots | 4.5 |
| change coupling | 4.5 |
| knowledge concentration | 5.0 |

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
| `tests/test_unread_code.py` | 487 | warn |
| `tests/test_adapters.py` | 473 | warn |
| `tests/test_docs_links.py` | 470 | warn |
| `tests/test_consumer_migration.py` | 466 | warn |
| `tests/test_evidence_properties.py` | 456 | warn |
| `tests/test_analyzer_bridge.py` | 446 | warn |
| `tools/build_catalog.py` | 444 | warn |
| `src/maintainability_audit/evidence.py` | 443 | warn |
| `src/maintainability_audit/scoring.py` | 441 | warn |
| `tests/test_scoring_calibration.py` | 441 | warn |
| `src/maintainability_audit/_scan_view.py` | 439 | warn |
| `tests/test_discovery.py` | 435 | warn |
| `src/maintainability_audit/_work_order.py` | 433 | warn |
| `src/maintainability_audit/prompts.py` | 423 | warn |
| `tests/test_evidence_normalization.py` | 416 | warn |
| `tests/test_analysis_coverage.py` | 405 | warn |
| `tests/test_trends.py` | 402 | warn |
| `tests/test_pillars_and_practice.py` | 394 | warn |
| `tests/test_recurrence.py` | 389 | warn |
| `src/maintainability_audit/_analysis.py` | 388 | warn |
| `tests/test_verified_grade.py` | 387 | warn |
| `src/maintainability_audit/_discovery.py` | 386 | warn |
| `src/maintainability_audit/report.py` | 384 | warn |
| `src/maintainability_audit/_metric_adapters.py` | 381 | warn |
| `tests/test_scan_history.py` | 375 | warn |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `tools/build_catalog.py` | `build` | 373 | 31 | 15 | 0 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 14 | 10 | warn |
| `src/maintainability_audit/prompts.py` | `prompt_work_order` | 117 | 53 | 14 | 11 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 235 | 48 | 14 | 3 | warn |
| `tests/test_unread_code.py` | `test_the_language_table_does_not_market_a_detector_that_never_runs` | 431 | 57 | 13 | 3 | warn |
| `src/maintainability_audit/idioms.py` | `divergent_idioms` | 152 | 51 | 13 | 15 | warn |
| `src/maintainability_audit/_scan_view.py` | `pillars_markdown` | 315 | 49 | 13 | 12 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 169 | 37 | 13 | 4 | warn |
| `src/maintainability_audit/cli.py` | `main` | 138 | 64 | 12 | 19 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 233 | 72 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 372 | 70 | 10 | 13 | warn |
| `src/maintainability_audit/_scan_view.py` | `analyzer_coverage_markdown` | 61 | 72 | 9 | 10 | warn |
| `src/maintainability_audit/_discovery.py` | `discover` | 321 | 38 | 8 | 16 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `src/maintainability_audit/_discovery.py` | `_generated_directories` | 246 | 25 | 8 | 17 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 320 | 65 | 7 | 1 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `src/maintainability_audit/renderers.py` | `render_markdown` | 106 | 71 | 6 | 5 | warn |
| `src/maintainability_audit/_runner.py` | `run` | 196 | 65 | 6 | 10 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |
| `src/maintainability_audit/_work_order.py` | `work_order` | 233 | 62 | 6 | 7 | warn |
| `src/maintainability_audit/report.py` | `_assemble` | 241 | 77 | 5 | 1 | warn |
| `src/maintainability_audit/scoring.py` | `score_evidence` | 263 | 63 | 3 | 0 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/metrics.py` | 7 | 1067 | 57 | 2 | 399 |
| `src/maintainability_audit/renderers.py` | 9 | 756 | 30 | 2 | 270 |
| `src/maintainability_audit/scoring.py` | 5 | 785 | 47 | 2 | 235 |
| `src/maintainability_audit/cli.py` | 6 | 1799 | 38 | 2 | 228 |
| `src/maintainability_audit/declarations.py` | 5 | 212 | 38 | 2 | 190 |
| `src/maintainability_audit/prompts.py` | 5 | 431 | 32 | 2 | 160 |
| `src/maintainability_audit/_ranges.py` | 2 | 263 | 51 | 2 | 102 |
| `src/maintainability_audit/idioms.py` | 3 | 220 | 34 | 2 | 102 |
| `src/maintainability_audit/sarif.py` | 4 | 191 | 24 | 2 | 96 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/config.py` | 11 | 218 | 8 | 2 | 88 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |
| `tools/calibration/measure.py` | 2 | 252 | 26 | 2 | 52 |
| `src/maintainability_audit/deadcode.py` | 2 | 173 | 22 | 1 | 44 |
| `src/maintainability_audit/report.py` | 7 | 466 | 5 | 2 | 35 |
| `src/maintainability_audit/_derive.py` | 2 | 209 | 14 | 2 | 28 |
| `tests/test_audit_components.py` | 4 | 704 | 5 | 2 | 20 |
| `src/maintainability_audit/_hotspots.py` | 2 | 60 | 9 | 1 | 18 |
| `tests/test_calibration_corpus.py` | 2 | 364 | 6 | 2 | 12 |
| `src/maintainability_audit/_metrics_types.py` | 4 | 173 | 2 | 2 | 8 |
| `src/maintainability_audit/baseline.py` | 2 | 88 | 3 | 2 | 6 |
| `tests/test_scoring_calibration.py` | 2 | 469 | 3 | 2 | 6 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `CHANGELOG.md` | `README.md` | 13 | 87% |
| `README.md` | `docs/self-audit.md` | 10 | 100% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 100% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 90% |
| `README.md` | `docs/standard.md` | 8 | 100% |
| `README.md` | `src/maintainability_audit/renderers.py` | 8 | 100% |
| `CHANGELOG.md` | `docs/self-audit.md` | 8 | 80% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `CHANGELOG.md` | `docs/standard.md` | 7 | 88% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 7 | 88% |
| `src/maintainability_audit/config.py` | `src/maintainability_audit/renderers.py` | 7 | 88% |
| `CHANGELOG.md` | `src/maintainability_audit/__init__.py` | 6 | 86% |
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 6 | 86% |
| `docs/self-audit.md` | `docs/standard.md` | 6 | 75% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 6 | 75% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 6 | 75% |
| `docs/self-audit.md` | `src/maintainability_audit/config.py` | 6 | 60% |
| `README.md` | `docs/config-schema.md` | 5 | 100% |
| `README.md` | `maintainability-agent.schema.json` | 5 | 100% |
| `README.md` | `src/maintainability_audit/cli.py` | 5 | 100% |
| `README.md` | `tests/test_cli.py` | 5 | 100% |
| `docs/config-schema.md` | `maintainability-agent.schema.json` | 5 | 100% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 5 | 83% |
| `README.md` | `src/maintainability_audit/metrics.py` | 5 | 83% |
| `README.md` | `src/maintainability_audit/report.py` | 5 | 83% |


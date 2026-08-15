<!--
Generated from the tree at commit 9c2257a9f2dc81b05ca5ba836dc6499b387c65e6. This is a **provenance record, not a promise of currency**: it
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
Branch: `main`

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.6 / 5 |
| Estimate source | Built-in detectors (fallback tier) |
| Range (unmeasured evidence priced 0..5) | 4.6 (no unmeasured evidence) |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 235 |
| File warnings | 65 |
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
| maintainability | owned | 4 | 4.4 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 4 | — | not measured — see below |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — delegated to secure-code-agent; this tool catalogues security analyzers and never runs them, so silence here is not safety

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

1 of 160 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.sh` | Shell | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Why the verified grade is not higher

- file_warn_rate 0.277 exceeds the A ceiling of 0.05

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.0 |
| reusability | 4.7 |
| analyzability | 4.8 |
| modifiability | 4.5 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 3.1 |
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
| change coupling | 4.0 |
| knowledge concentration | 4.0 |

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
| `tests/test_unread_code.py` | 500 | warn |
| `tests/test_docs_links.py` | 494 | warn |
| `src/maintainability_audit/_scan_view.py` | 487 | warn |
| `tests/test_adapters.py` | 468 | warn |
| `tests/test_calibration_corpus.py` | 468 | warn |
| `tests/test_consumer_migration.py` | 466 | warn |
| `tests/test_analyzer_provenance_exclusions.py` | 463 | warn |
| `src/maintainability_audit/_analysis.py` | 462 | warn |
| `tests/test_analyzer_bridge.py` | 462 | warn |
| `src/maintainability_audit/_metric_adapters.py` | 460 | warn |
| `tests/test_evidence_properties.py` | 456 | warn |
| `tools/build_catalog.py` | 456 | warn |
| `tests/test_scoring_calibration.py` | 447 | warn |
| `src/maintainability_audit/evidence.py` | 443 | warn |
| `tests/test_discovery.py` | 435 | warn |
| `src/maintainability_audit/_work_order.py` | 433 | warn |
| `src/maintainability_audit/prompts.py` | 430 | warn |
| `src/maintainability_audit/scoring.py` | 419 | warn |
| `src/maintainability_audit/_discovery.py` | 418 | warn |
| `tests/test_evidence_normalization.py` | 416 | warn |
| `tests/test_analysis_coverage.py` | 405 | warn |
| `tests/test_mcp_server.py` | 404 | warn |
| `tests/test_trends.py` | 402 | warn |
| `CHANGELOG.md` | 397 | warn |
| `src/maintainability_audit/report.py` | 396 | warn |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `tools/build_catalog.py` | `build` | 385 | 31 | 15 | 0 | warn |
| `src/maintainability_audit/cli.py` | `main` | 140 | 76 | 14 | 22 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 14 | 10 | warn |
| `src/maintainability_audit/prompts.py` | `prompt_work_order` | 124 | 53 | 14 | 11 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 235 | 48 | 14 | 3 | warn |
| `tests/test_unread_code.py` | `test_the_language_table_does_not_market_a_detector_that_never_runs` | 444 | 57 | 13 | 3 | warn |
| `src/maintainability_audit/idioms.py` | `divergent_idioms` | 152 | 51 | 13 | 15 | warn |
| `src/maintainability_audit/_scan_view.py` | `pillars_markdown` | 339 | 49 | 13 | 12 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 169 | 37 | 13 | 4 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 234 | 77 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_discovery.py` | `discover` | 348 | 43 | 11 | 16 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 350 | 70 | 10 | 13 | warn |
| `src/maintainability_audit/_scan_view.py` | `analyzer_coverage_markdown` | 61 | 72 | 9 | 10 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `src/maintainability_audit/_discovery.py` | `_generated_directories` | 273 | 25 | 8 | 17 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 331 | 66 | 7 | 1 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `src/maintainability_audit/renderers.py` | `render_markdown` | 114 | 75 | 6 | 7 | warn |
| `src/maintainability_audit/_runner.py` | `run` | 196 | 65 | 6 | 10 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |
| `src/maintainability_audit/_work_order.py` | `work_order` | 233 | 62 | 6 | 7 | warn |
| `src/maintainability_audit/report.py` | `_assemble` | 251 | 78 | 5 | 1 | warn |
| `src/maintainability_audit/scoring.py` | `score_evidence` | 269 | 71 | 3 | 0 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/renderers.py` | 12 | 770 | 35 | 2 | 420 |
| `src/maintainability_audit/metrics.py` | 7 | 1067 | 57 | 2 | 399 |
| `src/maintainability_audit/cli.py` | 9 | 1817 | 41 | 2 | 369 |
| `src/maintainability_audit/scoring.py` | 7 | 991 | 37 | 2 | 259 |
| `src/maintainability_audit/_ranges.py` | 3 | 403 | 84 | 2 | 252 |
| `src/maintainability_audit/declarations.py` | 6 | 227 | 39 | 2 | 234 |
| `src/maintainability_audit/_scan_view.py` | 3 | 505 | 70 | 1 | 210 |
| `src/maintainability_audit/prompts.py` | 6 | 460 | 35 | 2 | 210 |
| `src/maintainability_audit/_metric_adapters.py` | 3 | 462 | 54 | 1 | 162 |
| `src/maintainability_audit/_discovery.py` | 2 | 418 | 75 | 1 | 150 |
| `tests/test_docs_links.py` | 2 | 494 | 70 | 1 | 140 |
| `tools/build_catalog.py` | 3 | 468 | 42 | 1 | 126 |
| `src/maintainability_audit/_pressures.py` | 3 | 308 | 35 | 1 | 105 |
| `src/maintainability_audit/_verdict_adapters.py` | 3 | 299 | 34 | 1 | 102 |
| `src/maintainability_audit/idioms.py` | 3 | 220 | 34 | 2 | 102 |
| `src/maintainability_audit/config.py` | 12 | 220 | 8 | 2 | 96 |
| `src/maintainability_audit/sarif.py` | 4 | 191 | 24 | 2 | 96 |
| `src/maintainability_audit/_generic.py` | 2 | 283 | 46 | 1 | 92 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/_analysis.py` | 2 | 476 | 42 | 1 | 84 |
| `src/maintainability_audit/_derive.py` | 3 | 312 | 27 | 2 | 81 |
| `tests/test_architecture.py` | 3 | 376 | 27 | 1 | 81 |
| `tools/calibration/measure.py` | 3 | 260 | 26 | 2 | 78 |
| `tests/test_phase6_claims.py` | 3 | 275 | 25 | 1 | 75 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `CHANGELOG.md` | `README.md` | 16 | 73% |
| `README.md` | `docs/self-audit.md` | 13 | 100% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 91% |
| `CHANGELOG.md` | `docs/self-audit.md` | 10 | 77% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 82% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 9 | 82% |
| `README.md` | `src/maintainability_audit/renderers.py` | 9 | 82% |
| `CHANGELOG.md` | `docs/standard.md` | 8 | 89% |
| `README.md` | `docs/standard.md` | 8 | 89% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 8 | 80% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/cli.py` | 7 | 88% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 7 | 64% |
| `src/maintainability_audit/config.py` | `src/maintainability_audit/renderers.py` | 7 | 64% |
| `README.md` | `tests/test_cli.py` | 6 | 100% |
| `docs/architecture.md` | `docs/decisions.md` | 6 | 100% |
| `docs/config-schema.md` | `maintainability-agent.schema.json` | 6 | 100% |
| `CHANGELOG.md` | `docs/config-schema.md` | 6 | 86% |
| `CHANGELOG.md` | `src/maintainability_audit/__init__.py` | 6 | 86% |
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 6 | 86% |
| `CHANGELOG.md` | `src/maintainability_audit/cli.py` | 6 | 75% |
| `docs/architecture.md` | `docs/release-plan.md` | 6 | 75% |
| `docs/self-audit.md` | `docs/standard.md` | 6 | 67% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 6 | 67% |
| `README.md` | `src/maintainability_audit/report.py` | 6 | 60% |


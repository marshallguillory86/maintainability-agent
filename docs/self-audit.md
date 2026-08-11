<!--
Generated from the tree at commit 2410ae9428e9148ab6da4ebc91b2242f22aa8138 plus the staged release
changes; the commit that ships this file postdates that tree by
construction, so this report is always exactly one commit behind the
HEAD it travels with. That is a property of checking in a self-report,
not a promise of currency — regenerate for the current tree with:

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
| Maintainability estimate | 4.4 / 5 |
| Range (unmeasured evidence priced 0..5) | 4.4 (no unmeasured evidence) |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Compatibility grade | B (compatibility, evidence-floor) |
| Files scanned | 117 |
| File warnings | 16 |
| File failures | 0 |
| Function warnings | 8 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Scoring standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based.

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 3.9 |
| reusability | 4.8 |
| analyzability | 4.6 |
| modifiability | 3.9 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 3.9 |
| declaration size | 4.8 |
| duplication | 5.0 |
| risk patterns | 5.0 |
| policy gates | 5.0 |
| test presence | 5.0 |
| dead code | 5.0 |
| near duplication | 5.0 |
| idiom consistency | 5.0 |
| documentation | 5.0 |
| churn hotspots | 5.0 |
| change coupling | 2.0 |
| knowledge concentration | 2.0 |

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
| `tests/test_scoring_calibration.py` | 489 | warn |
| `tests/test_evidence_properties.py` | 459 | warn |
| `tests/test_evidence_normalization.py` | 409 | warn |
| `src/maintainability_audit/evidence.py` | 383 | warn |
| `tests/test_verified_grade.py` | 373 | warn |
| `src/maintainability_audit/scoring.py` | 368 | warn |
| `tools/calibration/select_authored.py` | 336 | warn |
| `tools/calibration/measure_cohorts.py` | 321 | warn |
| `src/maintainability_audit/renderers.py` | 319 | warn |
| `src/maintainability_audit/history.py` | 309 | warn |
| `tools/calibration/measure_fix_breadth.py` | 307 | warn |
| `tests/test_consumer_migration.py` | 300 | warn |
| `src/maintainability_audit/_formula.py` | 289 | warn |
| `src/maintainability_audit/prompts.py` | 280 | warn |
| `docs/standard.md` | 269 | warn |
| `README.md` | 267 | warn |
| `src/maintainability_audit/similarity.py` | 250 | ok |
| `tools/experiments/fix_scope/run_experiment.py` | 244 | ok |
| `src/maintainability_audit/_aspects.py` | 243 | ok |
| `tests/test_architecture.py` | 243 | ok |
| `src/maintainability_audit/_ranges.py` | 232 | ok |
| `tests/test_audit_components.py` | 224 | ok |
| `docs/adr-004-economic-context.md` | 221 | ok |
| `.github/workflows/quality-gates.yml` | 212 | ok |
| `tests/test_cli.py` | 212 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 217 | 48 | 14 | 3 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 115 | 78 | 10 | 3 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/scoring.py` | 17 | 1350 | 31 | 2 | 527 |
| `src/maintainability_audit/renderers.py` | 13 | 735 | 28 | 2 | 364 |
| `src/maintainability_audit/metrics.py` | 7 | 952 | 41 | 2 | 287 |
| `tools/calibration/measure_fix_breadth.py` | 5 | 409 | 47 | 1 | 235 |
| `tests/test_docs_links.py` | 5 | 334 | 46 | 1 | 230 |
| `src/maintainability_audit/evidence.py` | 5 | 451 | 35 | 1 | 175 |
| `src/maintainability_audit/_aspects.py` | 5 | 407 | 33 | 1 | 165 |
| `src/maintainability_audit/history.py` | 3 | 331 | 54 | 1 | 162 |
| `src/maintainability_audit/declarations.py` | 4 | 197 | 38 | 1 | 152 |
| `tools/calibration/measure_cohorts.py` | 3 | 339 | 40 | 1 | 120 |
| `src/maintainability_audit/_derive.py` | 8 | 289 | 14 | 1 | 112 |
| `tests/test_architecture.py` | 5 | 255 | 21 | 1 | 105 |
| `src/maintainability_audit/sarif.py` | 4 | 191 | 24 | 2 | 96 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/cli.py` | 5 | 1680 | 18 | 2 | 90 |
| `tools/calibration/analyze_cohorts.py` | 3 | 185 | 27 | 1 | 81 |
| `src/maintainability_audit/prompts.py` | 5 | 284 | 16 | 1 | 80 |
| `tools/experiments/fix_scope/run_experiment.py` | 2 | 268 | 36 | 1 | 72 |
| `src/maintainability_audit/idioms.py` | 2 | 178 | 34 | 1 | 68 |
| `src/maintainability_audit/config.py` | 11 | 134 | 6 | 2 | 66 |
| `tools/calibration/measure.py` | 3 | 175 | 22 | 1 | 66 |
| `src/maintainability_audit/_pressures.py` | 4 | 344 | 15 | 1 | 60 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |
| `tools/experiments/fix_scope/analyze.py` | 2 | 206 | 29 | 1 | 58 |
| `src/maintainability_audit/_formula.py` | 8 | 447 | 6 | 1 | 48 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `CHANGELOG.md` | `README.md` | 19 | 70% |
| `README.md` | `docs/standard.md` | 17 | 71% |
| `README.md` | `docs/self-audit.md` | 16 | 100% |
| `CHANGELOG.md` | `docs/standard.md` | 16 | 67% |
| `CHANGELOG.md` | `docs/self-audit.md` | 12 | 75% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 11 | 92% |
| `docs/self-audit.md` | `docs/standard.md` | 11 | 69% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 91% |
| `README.md` | `src/maintainability_audit/renderers.py` | 10 | 83% |
| `docs/standard.md` | `src/maintainability_audit/report.py` | 10 | 83% |
| `CHANGELOG.md` | `src/maintainability_audit/scoring.py` | 10 | 62% |
| `docs/standard.md` | `src/maintainability_audit/scoring.py` | 10 | 62% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 82% |
| `README.md` | `src/maintainability_audit/report.py` | 9 | 75% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 9 | 75% |
| `README.md` | `src/maintainability_audit/scoring.py` | 9 | 56% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 8 | 67% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 8 | 67% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `docs/architecture.md` | `docs/decisions.md` | 7 | 100% |
| `docs/standard.md` | `src/maintainability_audit/_formula.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/self-audit.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/standard.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/architecture.md` | `docs/report-contract.md` | 7 | 78% |


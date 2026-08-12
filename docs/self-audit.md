<!--
Generated from the tree at commit 1a867b158f35b8c0307ffb9686698e2e4c4f5b54 plus the staged release
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
| Maintainability estimate | 4.4 / 5 |
| Range (unmeasured evidence priced 0..5) | 4.4 (no unmeasured evidence) |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 117 |
| File warnings | 17 |
| File failures | 0 |
| Function warnings | 9 |
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
| `tests/test_scoring_calibration.py` | 498 | warn |
| `tests/test_evidence_properties.py` | 456 | warn |
| `tests/test_consumer_migration.py` | 455 | warn |
| `tests/test_evidence_normalization.py` | 409 | warn |
| `src/maintainability_audit/evidence.py` | 393 | warn |
| `tests/test_verified_grade.py` | 387 | warn |
| `src/maintainability_audit/scoring.py` | 371 | warn |
| `tools/calibration/select_authored.py` | 336 | warn |
| `src/maintainability_audit/renderers.py` | 322 | warn |
| `tools/calibration/measure_cohorts.py` | 321 | warn |
| `src/maintainability_audit/history.py` | 309 | warn |
| `tools/calibration/measure_fix_breadth.py` | 307 | warn |
| `tests/test_architecture.py` | 290 | warn |
| `src/maintainability_audit/_formula.py` | 289 | warn |
| `src/maintainability_audit/prompts.py` | 283 | warn |
| `docs/standard.md` | 269 | warn |
| `README.md` | 268 | warn |
| `src/maintainability_audit/similarity.py` | 250 | ok |
| `tools/experiments/fix_scope/run_experiment.py` | 244 | ok |
| `src/maintainability_audit/_aspects.py` | 243 | ok |
| `tests/test_docs_links.py` | 234 | ok |
| `src/maintainability_audit/_ranges.py` | 232 | ok |
| `tests/test_audit_components.py` | 226 | ok |
| `CHANGELOG.md` | 223 | ok |
| `docs/adr-004-economic-context.md` | 221 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 217 | 48 | 14 | 3 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 115 | 78 | 10 | 3 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 309 | 63 | 8 | 9 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/scoring.py` | 18 | 1361 | 33 | 2 | 594 |
| `src/maintainability_audit/renderers.py` | 14 | 752 | 27 | 2 | 378 |
| `src/maintainability_audit/metrics.py` | 7 | 952 | 41 | 2 | 287 |
| `tests/test_docs_links.py` | 6 | 366 | 47 | 1 | 282 |
| `tools/calibration/measure_fix_breadth.py` | 5 | 409 | 47 | 1 | 235 |
| `src/maintainability_audit/evidence.py` | 6 | 465 | 35 | 1 | 210 |
| `src/maintainability_audit/_aspects.py` | 5 | 407 | 33 | 1 | 165 |
| `src/maintainability_audit/history.py` | 3 | 331 | 54 | 1 | 162 |
| `tests/test_architecture.py` | 6 | 302 | 27 | 1 | 162 |
| `tools/calibration/measure_cohorts.py` | 4 | 341 | 40 | 1 | 160 |
| `src/maintainability_audit/declarations.py` | 4 | 197 | 38 | 1 | 152 |
| `src/maintainability_audit/sarif.py` | 5 | 193 | 24 | 2 | 120 |
| `src/maintainability_audit/_derive.py` | 8 | 289 | 14 | 1 | 112 |
| `tools/experiments/fix_scope/run_experiment.py` | 3 | 272 | 36 | 1 | 108 |
| `src/maintainability_audit/prompts.py` | 7 | 295 | 15 | 1 | 105 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/cli.py` | 5 | 1680 | 18 | 2 | 90 |
| `tools/calibration/analyze_cohorts.py` | 3 | 185 | 27 | 1 | 81 |
| `tests/test_consumer_migration.py` | 4 | 491 | 19 | 1 | 76 |
| `src/maintainability_audit/idioms.py` | 2 | 178 | 34 | 1 | 68 |
| `src/maintainability_audit/config.py` | 11 | 134 | 6 | 2 | 66 |
| `tools/calibration/measure.py` | 3 | 175 | 22 | 1 | 66 |
| `src/maintainability_audit/_pressures.py` | 4 | 344 | 15 | 1 | 60 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |
| `tools/experiments/fix_scope/analyze.py` | 2 | 206 | 29 | 1 | 58 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `README.md` | `docs/self-audit.md` | 19 | 100% |
| `CHANGELOG.md` | `README.md` | 19 | 66% |
| `CHANGELOG.md` | `docs/standard.md` | 17 | 68% |
| `README.md` | `docs/standard.md` | 17 | 68% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 12 | 92% |
| `CHANGELOG.md` | `docs/self-audit.md` | 12 | 63% |
| `CHANGELOG.md` | `src/maintainability_audit/scoring.py` | 11 | 65% |
| `docs/standard.md` | `src/maintainability_audit/scoring.py` | 11 | 65% |
| `docs/self-audit.md` | `docs/standard.md` | 11 | 58% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 91% |
| `docs/standard.md` | `src/maintainability_audit/report.py` | 10 | 83% |
| `README.md` | `src/maintainability_audit/renderers.py` | 10 | 77% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 10 | 77% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 82% |
| `README.md` | `src/maintainability_audit/report.py` | 9 | 75% |
| `README.md` | `src/maintainability_audit/scoring.py` | 9 | 53% |
| `docs/architecture.md` | `docs/decisions.md` | 8 | 100% |
| `docs/architecture.md` | `docs/report-contract.md` | 8 | 73% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 8 | 67% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 8 | 62% |
| `CHANGELOG.md` | `src/maintainability_audit/prompts.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `docs/standard.md` | `src/maintainability_audit/_formula.py` | 7 | 100% |
| `docs/standard.md` | `tests/test_scoring_calibration.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |


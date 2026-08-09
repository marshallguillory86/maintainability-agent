<!--
Generated from the tree at commit 01e8a5c44418e3f18cc57606bdc8c16ac1b8c05b plus the staged release
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
| Overall score | 4.7 / 5 (B) |
| Files scanned | 92 |
| File warnings | 9 |
| File failures | 0 |
| Function warnings | 6 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Scoring standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based.

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.2 |
| reusability | 4.9 |
| analyzability | 4.9 |
| modifiability | 4.4 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 4.2 |
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
| change coupling | 3.0 |
| knowledge concentration | 3.0 |

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
| `src/maintainability_audit/scoring.py` | 499 | warn |
| `tools/calibration/select_authored.py` | 336 | warn |
| `tools/calibration/measure_cohorts.py` | 321 | warn |
| `src/maintainability_audit/history.py` | 309 | warn |
| `tests/test_scoring_calibration.py` | 291 | warn |
| `docs/standard.md` | 290 | warn |
| `src/maintainability_audit/prompts.py` | 275 | warn |
| `src/maintainability_audit/renderers.py` | 272 | warn |
| `README.md` | 254 | warn |
| `src/maintainability_audit/similarity.py` | 250 | ok |
| `tools/experiments/fix_scope/run_experiment.py` | 244 | ok |
| `tools/calibration/measure_fix_breadth.py` | 239 | ok |
| `src/maintainability_audit/_ranges.py` | 232 | ok |
| `tests/test_cli.py` | 212 | ok |
| `tests/test_audit_components.py` | 201 | ok |
| `tests/test_declaration_ranges.py` | 190 | ok |
| `docs/ide-agent-integration.md` | 188 | ok |
| `tests/test_near_duplicates.py` | 187 | ok |
| `src/maintainability_audit/report.py` | 185 | ok |
| `src/maintainability_audit/_derive.py` | 177 | ok |
| `tests/test_calibration_corpus.py` | 177 | ok |
| `tests/test_declaration_grading.py` | 177 | ok |
| `docs/self-audit.md` | 175 | ok |
| `src/maintainability_audit/declarations.py` | 173 | ok |
| `tools/calibration/measure.py` | 173 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 217 | 48 | 14 | 3 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 114 | 72 | 9 | 3 | warn |
| `src/maintainability_audit/scoring.py` | `score_report` | 240 | 72 | 8 | 6 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/scoring.py` | 9 | 802 | 48 | 2 | 432 |
| `src/maintainability_audit/metrics.py` | 7 | 952 | 41 | 2 | 287 |
| `src/maintainability_audit/renderers.py` | 10 | 669 | 24 | 2 | 240 |
| `src/maintainability_audit/history.py` | 3 | 331 | 54 | 1 | 162 |
| `src/maintainability_audit/declarations.py` | 4 | 197 | 38 | 1 | 152 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/cli.py` | 5 | 1680 | 18 | 2 | 90 |
| `tools/calibration/analyze_cohorts.py` | 3 | 185 | 27 | 1 | 81 |
| `tools/calibration/measure_cohorts.py` | 2 | 337 | 40 | 1 | 80 |
| `tools/calibration/measure_fix_breadth.py` | 2 | 274 | 38 | 1 | 76 |
| `tools/experiments/fix_scope/run_experiment.py` | 2 | 268 | 36 | 1 | 72 |
| `src/maintainability_audit/idioms.py` | 2 | 178 | 34 | 1 | 68 |
| `src/maintainability_audit/config.py` | 11 | 134 | 6 | 2 | 66 |
| `tools/calibration/measure.py` | 3 | 175 | 22 | 1 | 66 |
| `src/maintainability_audit/_derive.py` | 5 | 203 | 13 | 1 | 65 |
| `src/maintainability_audit/prompts.py` | 4 | 275 | 16 | 1 | 64 |
| `src/maintainability_audit/sarif.py` | 3 | 155 | 21 | 2 | 63 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |
| `tools/experiments/fix_scope/analyze.py` | 2 | 206 | 29 | 1 | 58 |
| `src/maintainability_audit/deadcode.py` | 2 | 173 | 22 | 1 | 44 |
| `src/maintainability_audit/report.py` | 10 | 249 | 3 | 1 | 30 |
| `src/maintainability_audit/_hotspots.py` | 2 | 60 | 9 | 1 | 18 |
| `tools/calibration/select_corpus.py` | 2 | 165 | 9 | 1 | 18 |
| `tests/test_calibration_corpus.py` | 3 | 179 | 4 | 1 | 12 |
| `tests/test_audit_components.py` | 5 | 615 | 2 | 2 | 10 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `CHANGELOG.md` | `README.md` | 16 | 76% |
| `README.md` | `docs/self-audit.md` | 13 | 100% |
| `README.md` | `docs/standard.md` | 13 | 93% |
| `CHANGELOG.md` | `docs/standard.md` | 11 | 79% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 91% |
| `CHANGELOG.md` | `docs/self-audit.md` | 10 | 77% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 9 | 90% |
| `README.md` | `src/maintainability_audit/renderers.py` | 9 | 90% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 82% |
| `docs/self-audit.md` | `docs/standard.md` | 9 | 69% |
| `README.md` | `src/maintainability_audit/report.py` | 8 | 80% |
| `docs/standard.md` | `src/maintainability_audit/report.py` | 8 | 80% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/scoring.py` | 7 | 78% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 7 | 70% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 7 | 70% |
| `docs/self-audit.md` | `src/maintainability_audit/report.py` | 7 | 70% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 7 | 70% |
| `src/maintainability_audit/config.py` | `src/maintainability_audit/renderers.py` | 7 | 70% |
| `CHANGELOG.md` | `src/maintainability_audit/__init__.py` | 6 | 86% |
| `README.md` | `maintainability-agent.json` | 6 | 86% |
| `README.md` | `src/maintainability_audit/_calibration.py` | 6 | 86% |
| `docs/self-audit.md` | `src/maintainability_audit/_calibration.py` | 6 | 86% |
| `docs/standard.md` | `src/maintainability_audit/_calibration.py` | 6 | 86% |
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 6 | 86% |


<!--
Generated from the tree at commit e947e7cb8763db034a7238e7629b3befb9250985 plus the staged release
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
| Overall score | 4.6 / 5 (B) |
| Files scanned | 107 |
| File warnings | 13 |
| File failures | 0 |
| Function warnings | 8 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Scoring standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based.

## Why the grade is capped

- file_warn_rate 0.121 exceeds the A ceiling of 0.05

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.2 |
| reusability | 4.8 |
| analyzability | 4.7 |
| modifiability | 4.2 |
| testability | 4.9 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 4.0 |
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
| `tests/test_scoring_calibration.py` | 492 | warn |
| `tools/calibration/select_authored.py` | 336 | warn |
| `tools/calibration/measure_cohorts.py` | 321 | warn |
| `src/maintainability_audit/history.py` | 309 | warn |
| `tools/calibration/measure_fix_breadth.py` | 307 | warn |
| `tests/test_evidence_normalization.py` | 294 | warn |
| `src/maintainability_audit/renderers.py` | 292 | warn |
| `src/maintainability_audit/scoring.py` | 278 | warn |
| `src/maintainability_audit/prompts.py` | 275 | warn |
| `docs/standard.md` | 268 | warn |
| `README.md` | 267 | warn |
| `src/maintainability_audit/evidence.py` | 263 | warn |
| `src/maintainability_audit/_formula.py` | 253 | warn |
| `src/maintainability_audit/similarity.py` | 250 | ok |
| `tools/experiments/fix_scope/run_experiment.py` | 244 | ok |
| `src/maintainability_audit/_ranges.py` | 232 | ok |
| `tests/test_audit_components.py` | 224 | ok |
| `src/maintainability_audit/_aspects.py` | 218 | ok |
| `tests/test_cli.py` | 212 | ok |
| `docs/adr-001-evidence-and-verification.md` | 203 | ok |
| `src/maintainability_audit/report.py` | 192 | ok |
| `tests/test_declaration_ranges.py` | 190 | ok |
| `docs/ide-agent-integration.md` | 188 | ok |
| `tests/test_near_duplicates.py` | 187 | ok |
| `CHANGELOG.md` | 186 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 217 | 48 | 14 | 3 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 115 | 78 | 10 | 3 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 135 | 34 | 8 | 17 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 52 | 16 | 7 | 17 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 74 | 65 | 6 | 6 | warn |
| `src/maintainability_audit/scoring.py` | `score_report` | 201 | 76 | 5 | 5 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/renderers.py` | 12 | 694 | 27 | 2 | 324 |
| `src/maintainability_audit/metrics.py` | 7 | 952 | 41 | 2 | 287 |
| `src/maintainability_audit/scoring.py` | 12 | 1196 | 21 | 2 | 252 |
| `tools/calibration/measure_fix_breadth.py` | 5 | 409 | 47 | 1 | 235 |
| `src/maintainability_audit/history.py` | 3 | 331 | 54 | 1 | 162 |
| `src/maintainability_audit/declarations.py` | 4 | 197 | 38 | 1 | 152 |
| `tools/calibration/measure_cohorts.py` | 3 | 339 | 40 | 1 | 120 |
| `src/maintainability_audit/similarity.py` | 2 | 264 | 46 | 1 | 92 |
| `src/maintainability_audit/_derive.py` | 7 | 261 | 13 | 1 | 91 |
| `src/maintainability_audit/cli.py` | 5 | 1680 | 18 | 2 | 90 |
| `tools/calibration/analyze_cohorts.py` | 3 | 185 | 27 | 1 | 81 |
| `tools/experiments/fix_scope/run_experiment.py` | 2 | 268 | 36 | 1 | 72 |
| `src/maintainability_audit/idioms.py` | 2 | 178 | 34 | 1 | 68 |
| `src/maintainability_audit/config.py` | 11 | 134 | 6 | 2 | 66 |
| `tools/calibration/measure.py` | 3 | 175 | 22 | 1 | 66 |
| `src/maintainability_audit/prompts.py` | 4 | 275 | 16 | 1 | 64 |
| `src/maintainability_audit/sarif.py` | 3 | 155 | 21 | 2 | 63 |
| `src/maintainability_audit/_aspects.py` | 2 | 244 | 31 | 1 | 62 |
| `src/maintainability_audit/duplication.py` | 2 | 107 | 30 | 1 | 60 |
| `tools/experiments/fix_scope/analyze.py` | 2 | 206 | 29 | 1 | 58 |
| `src/maintainability_audit/deadcode.py` | 2 | 173 | 22 | 1 | 44 |
| `tests/test_scoring_calibration.py` | 5 | 502 | 8 | 1 | 40 |
| `src/maintainability_audit/report.py` | 12 | 258 | 3 | 1 | 36 |
| `src/maintainability_audit/_formula.py` | 7 | 381 | 4 | 1 | 28 |
| `src/maintainability_audit/_hotspots.py` | 2 | 60 | 9 | 1 | 18 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `CHANGELOG.md` | `README.md` | 19 | 79% |
| `README.md` | `docs/standard.md` | 16 | 84% |
| `README.md` | `docs/self-audit.md` | 15 | 100% |
| `CHANGELOG.md` | `docs/standard.md` | 14 | 74% |
| `CHANGELOG.md` | `docs/self-audit.md` | 12 | 80% |
| `docs/self-audit.md` | `docs/standard.md` | 11 | 73% |
| `CHANGELOG.md` | `src/maintainability_audit/renderers.py` | 10 | 91% |
| `README.md` | `src/maintainability_audit/config.py` | 10 | 91% |
| `README.md` | `src/maintainability_audit/renderers.py` | 10 | 91% |
| `docs/standard.md` | `src/maintainability_audit/report.py` | 10 | 83% |
| `CHANGELOG.md` | `src/maintainability_audit/config.py` | 9 | 82% |
| `README.md` | `src/maintainability_audit/scoring.py` | 9 | 82% |
| `README.md` | `src/maintainability_audit/report.py` | 9 | 75% |
| `CHANGELOG.md` | `src/maintainability_audit/scoring.py` | 8 | 73% |
| `docs/self-audit.md` | `src/maintainability_audit/renderers.py` | 8 | 73% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 8 | 73% |
| `docs/standard.md` | `src/maintainability_audit/scoring.py` | 8 | 73% |
| `CHANGELOG.md` | `src/maintainability_audit/report.py` | 8 | 67% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 100% |
| `README.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/self-audit.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/standard.md` | `src/maintainability_audit/_calibration.py` | 7 | 88% |
| `docs/self-audit.md` | `src/maintainability_audit/scoring.py` | 7 | 64% |
| `src/maintainability_audit/config.py` | `src/maintainability_audit/renderers.py` | 7 | 64% |
| `docs/self-audit.md` | `src/maintainability_audit/report.py` | 7 | 58% |


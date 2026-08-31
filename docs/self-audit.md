<!--
Generated from the tree at commit dabdcb84f61447dcc8399eba2c98393fe0d5bca3. This is a **provenance record, not a promise of currency**: it
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
| Maintainability estimate | 4.1 / 5 |
| Estimate source | Built-in detectors (fallback tier) |
| Range (unmeasured evidence priced 0..5) | 4.0 – 4.2 |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 379 |
| File warnings | 117 |
| File failures | 0 |
| Function warnings | 66 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Scoring standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based.

## Trend

7 separate series. Scans either side of a break were produced by different instruments and cannot be compared, so they are reported apart rather than joined into one line.

**Series 1** — 7 scans, 2026-08-15T20:46:31Z to 2026-08-16T06:01:10Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** grew without getting worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers, scored_languages changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 2** — 48 scans, 2026-08-17T15:38:29Z to 2026-08-19T22:06:38Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 38 introduced, 39 cleared (clearing faster than adding).
- **Growth:** grew without getting worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 3** — 6 scans, 2026-08-19T22:59:02Z to 2026-08-19T23:50:01Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.10.
- **Debt velocity:** 0 introduced, 2 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 4** — 27 scans, 2026-08-20T16:20:52Z to 2026-08-21T18:18:13Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.20.
- **Debt velocity:** 6 introduced, 32 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 5** — 1 scans, 2026-08-21T18:32:29Z to 2026-08-21T18:32:29Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** analyzers, scope changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 6** — 3 scans, 2026-08-28T13:05:26Z to 2026-08-28T13:07:10Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** calibration, analyzers, scope changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 7** — 3 scans, 2026-08-31T20:47:54Z to 2026-08-31T20:51:00Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 1 introduced, 1 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

Every figure above describes scans that happened. This tool does not forecast, and no number here should be read as one.

## Work Order

Ordered by what it costs to leave against what it costs to fix (see the standard). `Worth` is what clearing the whole class moves the score, recomputed through the rubric rather than estimated.

| # | Band | Item | Worth | Target |
|---:|---|---|---:|---|
| 1 | quick-win | unpaired file in src/maintainability_audit/_discovery.py (`src/maintainability_audit/_discovery.py`) | — | add a paired test for `_discovery.py` |
| 2 | quick-win | unpaired file in src/maintainability_audit/_metric_adapters.py (`src/maintainability_audit/_metric_adapters.py`) | — | add a paired test for `_metric_adapters.py` |
| 3 | quick-win | unpaired file in src/maintainability_audit/_ranges.py (`src/maintainability_audit/_ranges.py`) | — | add a paired test for `_ranges.py` |
| 4 | quick-win | unpaired file in src/maintainability_audit/config.py (`src/maintainability_audit/config.py`) | — | add a paired test for `config.py` |
| 5 | quick-win | unpaired file in src/maintainability_audit/evidence.py (`src/maintainability_audit/evidence.py`) | — | add a paired test for `evidence.py` |
| 6 | quick-win | unpaired file in src/maintainability_audit/report.py (`src/maintainability_audit/report.py`) | — | add a paired test for `report.py` |
| 7 | quick-win | unpaired file in src/maintainability_audit/_html_view.py (`src/maintainability_audit/_html_view.py`) | — | add a paired test for `_html_view.py` |
| 8 | quick-win | unpaired file in src/maintainability_audit/_work_order.py (`src/maintainability_audit/_work_order.py`) | — | add a paired test for `_work_order.py` |
| 9 | quick-win | unpaired file in src/maintainability_audit/prompts.py (`src/maintainability_audit/prompts.py`) | — | add a paired test for `prompts.py` |
| 10 | quick-win | unpaired file in src/maintainability_audit/_adapters.py (`src/maintainability_audit/_adapters.py`) | — | add a paired test for `_adapters.py` |
| 11 | quick-win | unpaired file in src/maintainability_audit/_analysis.py (`src/maintainability_audit/_analysis.py`) | — | add a paired test for `_analysis.py` |
| 12 | quick-win | unpaired file in src/maintainability_audit/_mcp_setup.py (`src/maintainability_audit/_mcp_setup.py`) | — | add a paired test for `_mcp_setup.py` |
| 13 | quick-win | unpaired file in tools/build_catalog.py (`tools/build_catalog.py`) | — | add a paired test for `build_catalog.py` |
| 14 | quick-win | unpaired file in src/maintainability_audit/_scan_view.py (`src/maintainability_audit/_scan_view.py`) | — | add a paired test for `_scan_view.py` |
| 15 | quick-win | unpaired file in src/maintainability_audit/renderers.py (`src/maintainability_audit/renderers.py`) | — | add a paired test for `renderers.py` |
| 16 | quick-win | unpaired file in src/maintainability_audit/scoring.py (`src/maintainability_audit/scoring.py`) | — | add a paired test for `scoring.py` |
| 17 | quick-win | unpaired file in src/maintainability_audit/_mcp_audit.py (`src/maintainability_audit/_mcp_audit.py`) | — | add a paired test for `_mcp_audit.py` |
| 18 | quick-win | unpaired file in src/maintainability_audit/_scan_history.py (`src/maintainability_audit/_scan_history.py`) | — | add a paired test for `_scan_history.py` |
| 19 | quick-win | unpaired file in src/maintainability_audit/_runner.py (`src/maintainability_audit/_runner.py`) | — | add a paired test for `_runner.py` |
| 20 | quick-win | unpaired file in src/maintainability_audit/_formula.py (`src/maintainability_audit/_formula.py`) | — | add a paired test for `_formula.py` |

...and 24 more. A list longer than 20 is a backlog, not a plan.

Verify with: `python -m maintainability_audit --root . --format json`

## TDD-shaped tests

TDD-shaped tests: detected beside 5 of 104 production source files (path pairing). Constructs: pytest in 172 file(s), unittest in 1 file(s), describe_it in 10 file(s), parametrize in 68 file(s), given_when_then in 1 file(s).
Chronology is not measured. Effectiveness is unscored unless the operator opted into suite execution.

## Test Suite

- The operator opted in to running the repository's test command; it did not run (exit None).
- Command: PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92
- Coverage: no coverage reported by the run
- Detail: PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92 could not be executed: [Errno 2] No such file or directory: 'PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92'

## Semantic Findings (ADR 003)

TypeScript semantic coverage: **unknown** — no recorded type analysis and no local type checker: semantic coverage for TypeScript is unknown. Absence of analysis is not absence of findings.

- **Design-review candidate**: `tests/fixtures/semantic_ts/src/operations.ts` — one operation-name set recurs across dispatch, capability and description roles. That is an observed symptom; the intended abstraction is not proven by this evidence. Review whether these operations should carry their own behavior and result types, and preserve operation-specific input and result types in any redesign.

## Pillars

**Practice level 4 of 5** — CI holds a numeric quality gate.

| Pillar | Scope | Practice | Condition | Reading |
|---|---|---:|---:|---|
| readability | partial | 4 | 4.8 | healthy: enforced, and the code reflects it |
| maintainability | owned | 4 | 3.6 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 4 | — | not measured — see below |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — delegated to secure-code-agent; this tool catalogues security analyzers and never runs them, so silence here is not safety

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `types-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

1 of 281 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.sh` | Shell | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Analyzer Coverage

2 of 12 tools contributed — concerns `all`, depth `moderate`, license policy `permissive`.

Plus 8 built-in detectors, which always run and whose measurements are single-source.

| Source | Tier | Outcome | Version | Measurements | Findings | Note |
|---|---|---|---|---|---|---|
| `eslint` | analyzer | not-applicable | — | — | — | reads javascript, jsx, typescript; this tree is Python, Shell, so it had nothing |
| `complexipy` | analyzer | not-installed | — | — | — | complexipy is not installed or not on PATH |
| `interrogate` | analyzer | not-installed | — | — | — | interrogate is not installed or not on PATH |
| `lizard` | analyzer | not-installed | — | — | — | lizard is not installed or not on PATH |
| `multimetric` | analyzer | not-installed | — | — | — | multimetric is not installed or not on PATH |
| `mypy` | analyzer | not-installed | — | — | — | mypy is not installed or not on PATH |
| `pydocstyle` | analyzer | not-installed | — | — | — | pydocstyle is not installed or not on PATH |
| `radon` | analyzer | not-installed | — | — | — | radon is not installed or not on PATH |
| `ruff` | analyzer | not-installed | — | — | — | ruff is not installed or not on PATH |
| `vulture` | analyzer | not-installed | — | — | — | vulture is not installed or not on PATH |
| `jscpd` | analyzer | ran | cpd 5.1.1 | 1 | 122 |  |
| `pmd` | analyzer | ran | PMD 7.26.0 (8fd38edf285a33e1164f66205ebe243441db9557, 2026-06-29T08:22:36Z) | 0 | 0 |  |
| `competing-libraries` | built-in | ran | — | 379 | 0 | two libraries doing one job; no adapter emits idioms |
| `dead-code` | built-in | ran | — | 2876 | 2 | vulture, ruff and eslint cover this |
| `declaration-size` | built-in | ran | — | 2876 | 66 | lizard and complexipy cover these; the only source when neither runs |
| `duplicate-blocks` | built-in | ran | — | 379 | 0 | jscpd covers this; the only source when Node is unavailable |
| `file-size` | built-in | ran | — | 379 | 117 | per-file line counts; no adapter emits file_lines |
| `history` | built-in | ran | — | 376 | 32 | git history; no adapter emits churn, coupling or ownership |
| `near-duplicates` | built-in | ran | — | 2876 | 2 | token-shingle near-matches, which jscpd's exact-block scan misses |
| `risk-patterns` | built-in | ran | — | 379 | 0 | regex policy from this repository's own config; nothing external can hold a proj |

### Coverage by language

| Language | Scored | Examined | Unexamined |
|---|---|---|---|
| Python | yes | `duplication` | `complexity`, `dead-code`, `documentation`, `metrics`, `structure`, `style`, `testing`, `types` |
| Shell | not read | `duplication` | `complexity`, `dead-code`, `documentation`, `metrics`, `structure`, `style`, `testing`, `types` |

The score is drawn from the scored languages only. Anything marked `not read` is listed under Source Not Read with its file count.

**One source only:** `complexity`, `dead-code`, `metrics`.

A built-in detector examined these and no external tool did, so nothing corroborates them. Install a tool covering the concern to get a second opinion.

**`declarations` measured by built-in detectors:** no analyzer supplied cyclomatic_complexity, declaration_lines, cognitive_complexity, and a declaration rate built from a narrower criterion set is not comparable to the rubric's, which fails a declaration on any of the three.

**Nothing examined:** `documentation`, `structure`, `style`, `testing`, `types`.

These concerns are unmeasured, not clean. Install a tool that covers them, or widen `analyzers.depth`, to have them reported.

## Environment Work Order

Selected analyzers that could not run, and what it would take. These commands are for **you** to run — the agent never installs anything.

| Tool | Why it did not run | Install | Verify |
|---|---|---|---|
| `complexipy` | complexipy is not installed or not on PATH | `pip install complexipy` | `complexipy --version` |
| `interrogate` | interrogate is not installed or not on PATH | `pip install interrogate` | `interrogate --version` |
| `lizard` | lizard is not installed or not on PATH | `pip install lizard` | `lizard --version` |
| `multimetric` | multimetric is not installed or not on PATH | `pip install multimetric` | `pip show multimetric` |
| `mypy` | mypy is not installed or not on PATH | `pip install mypy` | `mypy --version` |
| `pydocstyle` | pydocstyle is not installed or not on PATH | `pip install pydocstyle` | `pydocstyle --version` |
| `radon` | radon is not installed or not on PATH | `pip install radon` | `radon --version` |
| `ruff` | ruff is not installed or not on PATH | `pip install ruff` | `ruff --version` |
| `vulture` | vulture is not installed or not on PATH | `pip install vulture` | `vulture --version` |

## Measurements

| Concept | Units | Sources | Tool disagreement | Min | Median | p90 | Max |
|---|---|---|---|---|---|---|---|
| duplication | 1 | jscpd | single source | 1.54 | 1.54 | 1.54 | 1.54 |

*The analyzers ran but measured none of the dimensions the rubric scores, so the estimate comes from the built-in detectors. Treat an analyzer finding as evidence about the code, never as a change to the score.*

## Analyzer Findings

122 findings from external analyzers — 122 duplication.

| File | Line | Concern | Tool | Rule | Finding |
|---|---|---|---|---|---|
| `.github/workflows/quality-gates.yml` | 52 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 275 | duplication | `jscpd` | — | 9 duplicated lines |
| `README.md` | 168 | duplication | `jscpd` | — | 50 duplicated lines |
| `README.md` | 168 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 168 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 170 | duplication | `jscpd` | — | 47 duplicated lines |
| `docs/pr-and-baseline-workflows.md` | 38 | duplication | `jscpd` | — | 9 duplicated lines |
| `docs/standard.md` | 172 | duplication | `jscpd` | — | 7 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 92 | duplication | `jscpd` | — | 44 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 139 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 302 | duplication | `jscpd` | — | 7 duplicated lines |
| `src/maintainability_audit/_generic.py` | 146 | duplication | `jscpd` | — | 9 duplicated lines |
| `src/maintainability_audit/_html_report_sections.py` | 183 | duplication | `jscpd` | — | 8 duplicated lines |
| `src/maintainability_audit/_jvm_adapters.py` | 79 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_mcp_audit.py` | 157 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_recurrence.py` | 3 | duplication | `jscpd` | — | 9 duplicated lines |
| `src/maintainability_audit/_work_order.py` | 72 | duplication | `jscpd` | — | 8 duplicated lines |
| `tests/_analyzer_fixtures.py` | 29 | duplication | `jscpd` | — | 7 duplicated lines |
| `tests/_mcp_fixtures.py` | 35 | duplication | `jscpd` | — | 18 duplicated lines |
| `tests/_mcp_fixtures.py` | 41 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/_mcp_fixtures.py` | 70 | duplication | `jscpd` | — | 10 duplicated lines |
| `tests/_scoring_fixtures.py` | 113 | duplication | `jscpd` | — | 8 duplicated lines |
| `tests/test_analyzer_config_isolation.py` | 255 | duplication | `jscpd` | — | 10 duplicated lines |
| `tests/test_analyzer_estimate_claims.py` | 202 | duplication | `jscpd` | — | 14 duplicated lines |
| `tests/test_analyzer_estimate_claims.py` | 208 | duplication | `jscpd` | — | 10 duplicated lines |
| `tests/test_analyzer_provenance.py` | 50 | duplication | `jscpd` | — | 7 duplicated lines |
| `tests/test_artifact_write_route_class.py` | 50 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/test_audit_components.py` | 67 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/test_backfill.py` | 257 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/test_chat_primary_docs.py` | 327 | duplication | `jscpd` | — | 19 duplicated lines |
| `tests/test_chat_primary_docs.py` | 327 | duplication | `jscpd` | — | 7 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 30 | duplication | `jscpd` | — | 11 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 35 | duplication | `jscpd` | — | 12 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 52 | duplication | `jscpd` | — | 11 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 85 | duplication | `jscpd` | — | 22 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 88 | duplication | `jscpd` | — | 9 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 88 | duplication | `jscpd` | — | 9 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 102 | duplication | `jscpd` | — | 13 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 106 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/test_checkstyle_adapter.py` | 106 | duplication | `jscpd` | — | 9 duplicated lines |

Showing 40 of 122. The complete list is in the JSON report under `analyzer_findings`.

## Why the verified grade is not higher

- graded on the evidence floor 4.0 (point estimate 4.1, ceiling 4.2): unmeasured aspects price at 0 for the grade
- unpaired fail-band production unit: testability capped at 4.0

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 3.8 |
| reusability | 4.6 |
| analyzability | 4.2 |
| modifiability | 4.0 |
| testability | 4.0 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 3.5 |
| declaration size | 4.5 |
| duplication | 5.0 |
| risk patterns | 5.0 |
| policy gates | 5.0 |
| test presence | 5.0 |
| dead code | 3.5 |
| near duplication | 4.5 |
| idiom consistency | 5.0 |
| documentation | 5.0 |
| churn hotspots | 4.0 |
| change coupling | 3.0 |
| knowledge concentration | 2.0 |
| test effectiveness | not measurable |

## Not Scored — no measurement exists

| Aspect | Why |
|---|---|
| naming quality | no static proxy survives contact; a wrong-name detector needs semantics |
| comment accuracy | comments are deliberately unparsed; staleness needs meaning, not structure |
| indirection depth | call-graph construction is not implemented for the supported languages |
| architectural coherence | no measurement distinguishes a wrong boundary from an unusual one statically |

## Largest Files

| File | Lines | Status |
|---|---|---|
| `src/maintainability_audit/_discovery.py` | 500 | warn |
| `src/maintainability_audit/_metric_adapters.py` | 500 | warn |
| `src/maintainability_audit/_ranges.py` | 500 | warn |
| `src/maintainability_audit/config.py` | 500 | warn |
| `src/maintainability_audit/evidence.py` | 500 | warn |
| `src/maintainability_audit/report.py` | 500 | warn |
| `tests/test_unread_code.py` | 500 | warn |
| `tests/test_calibration_corpus.py` | 499 | warn |
| `src/maintainability_audit/_html_view.py` | 497 | warn |
| `src/maintainability_audit/_work_order.py` | 496 | warn |
| `src/maintainability_audit/prompts.py` | 496 | warn |
| `tests/test_docs_links.py` | 494 | warn |
| `tests/test_evidence_properties.py` | 494 | warn |
| `src/maintainability_audit/_adapters.py` | 492 | warn |
| `tests/test_written_record.py` | 492 | warn |
| `tests/test_adapters.py` | 491 | warn |
| `src/maintainability_audit/_analysis.py` | 485 | warn |
| `tests/test_mcp_history.py` | 482 | warn |
| `src/maintainability_audit/_mcp_setup.py` | 481 | warn |
| `tools/build_catalog.py` | 479 | warn |
| `src/maintainability_audit/_scan_view.py` | 477 | warn |
| `tests/test_grant_only_user_tier.py` | 475 | warn |
| `tests/test_consumer_migration.py` | 470 | warn |
| `tests/test_analyzer_provenance_exclusions.py` | 464 | warn |
| `src/maintainability_audit/renderers.py` | 463 | warn |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 15 | 8 | warn |
| `tests/test_platform_claim.py` | `test_the_macos_runner_actually_runs_the_suite` | 100 | 53 | 15 | 8 | warn |
| `tools/build_catalog.py` | `build` | 397 | 36 | 15 | 0 | warn |
| `tests/test_verified_grade.py` | `test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor` | 245 | 70 | 14 | 0 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 14 | 10 | warn |
| `src/maintainability_audit/prompts.py` | `prompt_work_order` | 175 | 53 | 14 | 11 | warn |
| `src/maintainability_audit/_discovery.py` | `discover` | 404 | 51 | 14 | 17 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 288 | 51 | 14 | 3 | warn |
| `tests/test_written_record.py` | `test_every_closing_citation_names_a_test_that_exists` | 101 | 75 | 13 | 3 | warn |
| `tests/test_unread_code.py` | `test_the_language_table_does_not_market_a_detector_that_never_runs` | 444 | 57 | 13 | 3 | warn |
| `src/maintainability_audit/idioms.py` | `divergent_idioms` | 152 | 51 | 13 | 15 | warn |
| `src/maintainability_audit/_html_report_sections.py` | `_pillars_section` | 173 | 49 | 13 | 12 | warn |
| `src/maintainability_audit/_scan_view.py` | `pillars_markdown` | 329 | 49 | 13 | 12 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `tests/test_anticipated_refusals.py` | `test_the_transport_excepts_the_named_tuple_not_a_copy` | 179 | 40 | 13 | 2 | warn |
| `src/maintainability_audit/duplication.py` | `duplicate_blocks` | 50 | 35 | 13 | 10 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 262 | 34 | 13 | 4 | warn |
| `src/maintainability_audit/cli.py` | `add_arguments` | 47 | 65 | 12 | 0 | warn |
| `tests/test_written_record.py` | `test_no_document_says_a_register_entry_is_open_that_the_register_closed` | 275 | 45 | 12 | 16 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 12 | 20 | warn |
| `tests/test_git_argv.py` | `test_every_git_command_disables_gits_own_housekeeping` | 396 | 66 | 11 | 20 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 243 | 61 | 11 | 5 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_ranges.py` | `js_declaration_ranges` | 323 | 38 | 11 | 24 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 274 | 79 | 10 | 5 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 423 | 78 | 10 | 3 | warn |
| `src/maintainability_audit/_mcp_audit.py` | `audit_repository` | 157 | 74 | 10 | 11 | warn |
| `src/maintainability_audit/cli.py` | `main` | 255 | 73 | 10 | 15 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 389 | 70 | 10 | 13 | warn |
| `src/maintainability_audit/_skill_install.py` | `install_skill` | 48 | 67 | 10 | 13 | warn |
| `src/maintainability_audit/_practice.py` | `practice_level` | 288 | 48 | 10 | 16 | warn |
| `src/maintainability_audit/_masking.py` | `_mask_code` | 68 | 47 | 10 | 20 | warn |
| `tools/prove_falsifiers.py` | `main` | 226 | 40 | 10 | 16 | warn |
| `src/maintainability_audit/_selection.py` | `select_runnable` | 58 | 79 | 9 | 20 | warn |
| `tests/test_determinism.py` | `test_the_history_window_is_disclosed_as_clock_relative` | 225 | 71 | 9 | 4 | warn |
| `tests/conftest.py` | `_git_ignores_developer_configuration` | 150 | 68 | 9 | 4 | warn |
| `src/maintainability_audit/_scan_history.py` | `record_of` | 358 | 64 | 9 | 19 | warn |
| `tests/conftest.py` | `_git_never_maintains_the_fixtures` | 85 | 62 | 9 | 5 | warn |
| `tests/_ast_reading.py` | `reachable_names` | 204 | 44 | 9 | 17 | warn |
| `src/maintainability_audit/_work_order.py` | `_items_from_semantic` | 308 | 43 | 9 | 19 | warn |
| `tests/test_authorship_gates.py` | `_step_scripts` | 41 | 42 | 9 | 23 | warn |
| `tests/test_anticipated_refusals.py` | `_named_exceptions` | 88 | 26 | 9 | 16 | warn |
| `tests/test_network_disclosure.py` | `test_no_module_imports_an_http_client` | 69 | 24 | 9 | 16 | warn |
| `src/maintainability_audit/_analysis.py` | `_attempt` | 398 | 80 | 8 | 12 | warn |
| `tests/test_first_run_elicitation.py` | `test_one_native_elicitation_configures_and_then_asks_before_auditing` | 303 | 78 | 8 | 0 | warn |
| `src/maintainability_audit/instructions.py` | `instruction_body` | 15 | 67 | 8 | 1 | warn |
| `src/maintainability_audit/_derive.py` | `_corpus_overall` | 172 | 63 | 8 | 6 | warn |
| `src/maintainability_audit/history.py` | `_commits` | 160 | 34 | 8 | 17 | warn |
| `src/maintainability_audit/_discovery.py` | `_generated_directories` | 282 | 25 | 8 | 17 | warn |
| `tests/test_promises.py` | `_paths_the_audit_produced` | 129 | 25 | 8 | 20 | warn |

## Near-Duplicate Declarations

| Location | Declaration | Duplicates | Named | Similarity | Scope |
|---|---|---|---|---|---|
| `src/maintainability_audit/_semantic_policy.py:30` | `_domain_type` | `src/maintainability_audit/_semantic_policy.py:42` | `_operation` | 90% | same file |
| `src/maintainability_audit/_pressures.py:97` | `dimension_pressures` | `src/maintainability_audit/_pressures.py:142` | `production_pressures` | 81% | same file |

## Unreferenced Private Declarations

| Location | Declaration | Kind | Lines |
|---|---|---|---|
| `src/maintainability_audit/_pressures.py:263` | `_breach_counts` | function | 24 |
| `src/maintainability_audit/_grant_ledger.py:44` | `_grant_still_names_what_was_granted` | function | 6 |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/config.py` | 33 | 638 | 72 | 2 | 2376 |
| `src/maintainability_audit/cli.py` | 25 | 2140 | 52 | 2 | 1300 |
| `src/maintainability_audit/renderers.py` | 22 | 901 | 38 | 2 | 836 |
| `src/maintainability_audit/_mcp_audit.py` | 17 | 980 | 48 | 2 | 816 |
| `src/maintainability_audit/_ranges.py` | 7 | 536 | 114 | 2 | 798 |
| `tests/test_architecture.py` | 26 | 481 | 28 | 2 | 728 |
| `src/maintainability_audit/metrics.py` | 10 | 1119 | 67 | 2 | 670 |
| `src/maintainability_audit/_html_view.py` | 8 | 613 | 79 | 1 | 632 |
| `src/maintainability_audit/prompts.py` | 12 | 536 | 48 | 2 | 576 |
| `src/maintainability_audit/_work_order.py` | 5 | 600 | 104 | 1 | 520 |
| `tests/test_first_run_elicitation.py` | 8 | 810 | 65 | 1 | 520 |
| `src/maintainability_audit/_analysis.py` | 13 | 855 | 39 | 2 | 507 |
| `src/maintainability_audit/mcp_server.py` | 24 | 1791 | 21 | 2 | 504 |
| `tests/test_written_record.py` | 12 | 590 | 42 | 2 | 504 |
| `src/maintainability_audit/_mcp_setup.py` | 8 | 591 | 54 | 2 | 432 |
| `tests/test_git_argv.py` | 9 | 683 | 48 | 1 | 432 |
| `src/maintainability_audit/scoring.py` | 10 | 1084 | 43 | 2 | 430 |
| `tools/build_catalog.py` | 10 | 531 | 42 | 1 | 420 |
| `src/maintainability_audit/_metric_adapters.py` | 6 | 544 | 59 | 2 | 354 |
| `src/maintainability_audit/_skill_install.py` | 6 | 543 | 58 | 1 | 348 |
| `src/maintainability_audit/_scan_view.py` | 5 | 559 | 69 | 1 | 345 |
| `src/maintainability_audit/report.py` | 23 | 694 | 15 | 2 | 345 |
| `src/maintainability_audit/_verdict_adapters.py` | 10 | 776 | 34 | 1 | 340 |
| `tests/_ast_reading.py` | 5 | 317 | 63 | 1 | 315 |
| `src/maintainability_audit/declarations.py` | 8 | 255 | 39 | 2 | 312 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `docs/architecture.md` | `tests/test_architecture.py` | 21 | 96% |
| `docs/architecture.md` | `docs/decisions.md` | 19 | 79% |
| `docs/architecture.md` | `src/maintainability_audit/cli.py` | 15 | 62% |
| `docs/architecture.md` | `src/maintainability_audit/mcp_server.py` | 13 | 62% |
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 12 | 92% |
| `docs/architecture.md` | `docs/release-plan.md` | 11 | 55% |
| `docs/architecture.md` | `src/maintainability_audit/report.py` | 11 | 55% |
| `docs/cli.md` | `src/maintainability_audit/cli.py` | 10 | 77% |
| `README.md` | `src/maintainability_audit/renderers.py` | 10 | 53% |
| `README.md` | `docs/ide-agent-integration.md` | 9 | 82% |
| `docs/architecture.md` | `docs/cli.md` | 9 | 69% |
| `docs/config-schema.md` | `maintainability-agent.schema.json` | 8 | 80% |
| `README.md` | `docs/standard.md` | 8 | 73% |
| `docs/architecture.md` | `docs/product-intent.md` | 8 | 73% |
| `docs/architecture.md` | `docs/config-schema.md` | 8 | 53% |
| `src/maintainability_audit/mcp_server.py` | `tests/test_mcp_server.py` | 7 | 78% |
| `maintainability-agent.schema.json` | `src/maintainability_audit/config.py` | 7 | 70% |
| `src/maintainability_audit/prompts.py` | `src/maintainability_audit/report.py` | 7 | 70% |
| `docs/standard.md` | `src/maintainability_audit/renderers.py` | 7 | 64% |
| `README.md` | `src/maintainability_audit/__init__.py` | 7 | 54% |
| `README.md` | `tests/test_cli.py` | 6 | 100% |
| `src/maintainability_audit/_skill_install.py` | `tests/test_skill_install.py` | 6 | 100% |
| `docs/analyzer-pool.md` | `tools/build_catalog.py` | 6 | 86% |
| `src/maintainability_audit/_mcp_audit.py` | `tests/test_grant_only_user_tier.py` | 6 | 75% |
| `docs/architecture.md` | `tests/test_mcp_server.py` | 6 | 67% |


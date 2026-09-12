<!--
Generated from the tree at commit 934f7739bd176d3e0fc5313624c361c7a50eb77c. This is a **provenance record, not a promise of currency**: it
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

- Generated: 2026-09-12T00:53:47+00:00
- Commit: `934f7739bd176d3e0fc5313624c361c7a50eb77c` · Branch: `docs/define-done`
- Root: `/Users/marshallguillory/repos/maintainability-agent`
- Standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.5 / 5 |
| Estimate source | Analyzer readings for declarations (completed by built-in detectors); built-in detectors for remaining dimensions |
| Range (unmeasured evidence priced 0..5) | 4.2 – 4.8 |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 511 |
| File warnings | 2 |
| File failures | 0 |
| Function warnings | 72 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

*COBOL is parsed but is not in the reference corpus, so a grade reported for code in it is provisional: the findings are as good as the parser, the rate they are compared against was measured on other languages.*


## Trend

54 separate series. Scans either side of a break were produced by different instruments and cannot be compared, so they are reported apart rather than joined into one line. The current series is given in full; the earlier ones are summarized, because a reader deciding what to do today is acting on the instrument in use today.

**This series begins at a break:** the tool version, a delegated pillar's producer or its version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Current series** — 4 scans, 2026-09-12T00:17:35Z to 2026-09-12T00:53:48Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

### Earlier series (53 series)

| Window | Scans | Direction | Change | Began at a break in |
|---|---|---|---|---|
| 2026-09-12T00:03:02Z to 2026-09-12T00:03:02Z | 1 | unknown | — | the tool version, a delegated pillar's producer or its version changed |
| 2026-09-11T23:21:19Z to 2026-09-11T23:43:19Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-11T22:43:02Z to 2026-09-11T23:05:25Z | 4 | indistinguishable | +0.00 | a delegated pillar's producer or its version changed |
| 2026-09-11T21:08:33Z to 2026-09-11T21:29:07Z | 2 | indistinguishable | +0.00 | the tool version, a delegated pillar's producer or its version changed |
| 2026-09-10T23:35:05Z to 2026-09-11T19:24:09Z | 26 | indistinguishable | +0.10 | the tool version changed |
| 2026-09-10T22:48:20Z to 2026-09-10T23:22:21Z | 6 | indistinguishable | +0.00 | the tool version, the configured thresholds changed |
| 2026-09-09T16:26:16Z to 2026-09-09T16:26:16Z | 1 | unknown | — | the tool version, which analyzers contributed changed |
| 2026-09-09T16:03:21Z to 2026-09-09T16:03:21Z | 1 | unknown | — | which analyzers contributed changed |
| 2026-09-09T15:57:18Z to 2026-09-09T15:57:18Z | 1 | unknown | — | which analyzers contributed changed |
| 2026-09-09T15:51:34Z to 2026-09-09T15:51:34Z | 1 | unknown | — | which analyzers contributed changed |
| 2026-09-09T15:45:03Z to 2026-09-09T15:45:03Z | 1 | unknown | — | which analyzers contributed changed |
| 2026-09-09T15:28:08Z to 2026-09-09T15:28:08Z | 1 | unknown | — | which analyzers contributed changed |
| 2026-09-08T19:04:32Z to 2026-09-08T19:04:32Z | 1 | unknown | — | the tool version changed |
| 2026-09-08T07:43:59Z to 2026-09-08T17:45:09Z | 5 | indistinguishable | +0.00 | the tool version, the calibration constant changed |
| 2026-09-07T18:48:35Z to 2026-09-08T00:14:00Z | 7 | indistinguishable | +0.00 | the tool version, which analyzers contributed changed |
| 2026-09-06T18:48:06Z to 2026-09-06T18:55:57Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-06T14:42:34Z to 2026-09-06T18:28:54Z | 9 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-05T21:35:57Z to 2026-09-06T04:02:48Z | 6 | indistinguishable | +0.00 | the tool version, which analyzers contributed, the scored languages, the scan scope changed |
| 2026-09-05T20:49:08Z to 2026-09-05T20:53:53Z | 2 | unknown | — | which analyzers contributed, the scored languages changed |
| 2026-09-05T20:44:46Z to 2026-09-05T20:44:46Z | 1 | unknown | — | the scan scope changed |
| 2026-09-05T19:52:45Z to 2026-09-05T19:52:45Z | 1 | unknown | — | the tool version changed |
| 2026-09-05T00:59:02Z to 2026-09-05T18:15:54Z | 23 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-04T22:42:23Z to 2026-09-05T00:47:24Z | 6 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-04T19:52:42Z to 2026-09-04T22:33:54Z | 16 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-04T19:08:33Z to 2026-09-04T19:08:33Z | 1 | unknown | — | the tool version changed |
| 2026-09-04T16:40:06Z to 2026-09-04T17:56:04Z | 2 | indistinguishable | +0.00 | the tool version, which analyzers contributed changed |
| 2026-09-04T07:53:46Z to 2026-09-04T07:53:46Z | 1 | unknown | — | the tool version changed |
| 2026-09-04T07:11:36Z to 2026-09-04T07:40:48Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-04T05:56:43Z to 2026-09-04T06:58:47Z | 4 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-04T04:25:28Z to 2026-09-04T05:44:00Z | 6 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-03T22:26:06Z to 2026-09-04T04:12:38Z | 11 | indistinguishable | +0.00 | the tool version, the calibration constant changed |
| 2026-09-03T16:43:03Z to 2026-09-03T19:57:41Z | 15 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-03T14:19:51Z to 2026-09-03T15:38:52Z | 5 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-03T04:32:13Z to 2026-09-03T14:04:41Z | 10 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-03T03:14:36Z to 2026-09-03T03:26:28Z | 3 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-03T01:50:55Z to 2026-09-03T01:50:55Z | 1 | unknown | — | the tool version, which analyzers contributed changed |
| 2026-09-02T21:22:31Z to 2026-09-02T21:22:31Z | 1 | unknown | — | the tool version, which analyzers contributed changed |
| 2026-09-02T20:57:23Z to 2026-09-02T20:57:23Z | 1 | unknown | — | the tool version changed |
| 2026-09-02T19:48:51Z to 2026-09-02T20:10:01Z | 4 | indistinguishable | +0.00 | which analyzers contributed changed |
| 2026-09-02T19:09:34Z to 2026-09-02T19:09:34Z | 1 | unknown | — | the tool version, which analyzers contributed changed |
| 2026-09-02T16:49:38Z to 2026-09-02T18:17:31Z | 5 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-02T15:53:44Z to 2026-09-02T16:09:57Z | 4 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-02T05:07:33Z to 2026-09-02T05:21:56Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-02T04:13:12Z to 2026-09-02T04:32:59Z | 5 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-02T02:37:15Z to 2026-09-02T03:10:30Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-02T00:13:53Z to 2026-09-02T02:55:46Z | 3 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-01T22:50:04Z to 2026-09-01T23:57:58Z | 4 | indistinguishable | +0.00 | the tool version, the calibration constant, which analyzers contributed, the scan scope changed |
| 2026-08-28T13:05:26Z to 2026-08-28T13:07:10Z | 3 | unknown | — | which analyzers contributed, the scan scope changed |
| 2026-08-21T18:32:29Z to 2026-08-21T18:32:29Z | 1 | unknown | — | the tool version changed |
| 2026-08-20T16:20:52Z to 2026-08-21T18:18:13Z | 27 | indistinguishable | +0.20 | the tool version changed |
| 2026-08-19T22:59:02Z to 2026-08-19T23:50:01Z | 6 | indistinguishable | +0.10 | which analyzers contributed changed |
| 2026-08-17T15:38:29Z to 2026-08-19T22:06:38Z | 48 | indistinguishable | +0.00 | the tool version, which analyzers contributed, the scored languages changed |
| 2026-08-15T20:46:31Z to 2026-08-16T06:01:10Z | 7 | indistinguishable | +0.00 | the first recorded scan |

Every figure above describes scans that happened. This tool does not forecast, and no number here should be read as one.

## TDD-shaped tests

TDD-shaped tests: detected beside 121 of 150 production source files (path pairing). Constructs: pytest in 228 file(s), unittest in 1 file(s), describe_it in 16 file(s), parametrize in 80 file(s), given_when_then in 2 file(s).
Chronology is not measured. Effectiveness is unscored unless the operator opted into suite execution.

## Test Suite

- The operator opted in to running the repository's test command; it did not run (exit None).
- Command: PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92
- Coverage: no coverage reported by the run
- Detail: opted in, but no test command is recorded in the user tier; the repository's documented command is not run on its own say-so

## Semantic Findings (ADR 003)

TypeScript semantic coverage: **unknown** — no recorded type analysis and no local type checker: semantic coverage for TypeScript is unknown. Absence of analysis is not absence of findings.

- **Design-review candidate**: `tests/fixtures/semantic_ts/src/operations.ts` — one operation-name set recurs across dispatch, capability and description roles. That is an observed symptom; the intended abstraction is not proven by this evidence. Review whether these operations should carry their own behavior and result types, and preserve operation-specific input and result types in any redesign.

## Pillars

**Practice level 4 of 5** — CI holds a numeric quality gate.

| Pillar | Scope | Practice | Condition | Reading |
|---|---|---:|---:|---|
| readability | partial | 4 | 4.8 | healthy: enforced, and the code reflects it |
| maintainability | owned | 4 | 4.1 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 5 | — | unverified: clean scan, but nothing prevents tomorrow's regression |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — secure-code-agent owns the security pillar: it runs the scanner floor, reports coverage as a separate axis, and withholds a grade when the evidence cannot support one

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `types-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

12 of 396 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.sh` | Shell | 2 |
| `.c` | C | 1 |
| `.cpp` | C++ | 1 |
| `.cs` | C# | 1 |
| `.f90` | Fortran | 1 |
| `.go` | Go | 1 |
| `.js` | JavaScript | 1 |
| `.php` | PHP | 1 |
| `.rb` | Ruby | 1 |
| `.rs` | Rust | 1 |
| `.swift` | Swift | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Analyzer Coverage

11 of 13 tools contributed — concerns `all`, depth `moderate`, license policy `permissive`.

Plus 8 built-in detectors, which always run and whose measurements are single-source.

| Source | Tier | Outcome | Version | Measurements | Findings | Note |
|---|---|---|---|---|---|---|
| `eslint` | analyzer | not-applicable | — | — | — | reads javascript, jsx, typescript; this tree is Python, Shell, so it had nothing |
| `fortitude` | analyzer | not-applicable | — | — | — | reads fortran; this tree is Python, Shell, so it had nothing to examine |
| `complexipy` | analyzer | ran | 7.0.1 | 3678 | 0 |  |
| `interrogate` | analyzer | ran | interrogate, version 1.7.0 | 1 | 0 |  |
| `jscpd` | analyzer | ran | cpd 5.1.1 | 1 | 137 |  |
| `lizard` | analyzer | ran | 1.24.0 | 11823 | 0 |  |
| `multimetric` | analyzer | ran | multimetric 2.4.4 | 1620 | 0 |  |
| `mypy` | analyzer | ran | mypy 2.3.1 (compiled: yes) | 0 | 0 |  |
| `pmd` | analyzer | ran | PMD 7.26.0 (8fd38edf285a33e1164f66205ebe243441db9557, 2026-06-29T08:22:36Z) | 0 | 0 |  |
| `pydocstyle` | analyzer | ran | 6.3.0 | 0 | 546 |  |
| `radon` | analyzer | ran | 6.0.1 | 384 | 0 |  |
| `ruff` | analyzer | ran | ruff 0.16.5 | 0 | 1 |  |
| `vulture` | analyzer | ran | vulture 2.16 | 0 | 9 |  |
| `competing-libraries` | built-in | ran | — | 511 | 0 | two libraries doing one job; no adapter emits idioms |
| `dead-code` | built-in | ran | — | 3908 | 0 | vulture, ruff and eslint cover this |
| `declaration-size` | built-in | ran | — | 3908 | 72 | lizard and complexipy cover these; the only source when neither runs |
| `duplicate-blocks` | built-in | ran | — | 511 | 0 | jscpd covers this; the only source when Node is unavailable |
| `file-size` | built-in | ran | — | 511 | 2 | per-file line counts; no adapter emits file_lines |
| `history` | built-in | ran | — | 507 | 58 | git history; no adapter emits churn, coupling or ownership |
| `near-duplicates` | built-in | ran | — | 3908 | 0 | token-shingle near-matches, which jscpd's exact-block scan misses |
| `risk-patterns` | built-in | ran | — | 511 | 0 | regex policy from this repository's own config; nothing external can hold a proj |

### Coverage by language

| Language | Scored | Examined | Unexamined |
|---|---|---|---|
| Python | yes | `complexity`, `dead-code`, `documentation`, `duplication`, `metrics`, `structure`, `style`, `types` | `testing` |
| Shell | not read | `duplication` | `complexity`, `dead-code`, `documentation`, `metrics`, `structure`, `style`, `testing`, `types` |

The score is drawn from the scored languages only. Anything marked `not read` is listed under Source Not Read with its file count.

**`declarations` measured by analyzers, completed by built-in detectors:** no analyzer supplies cognitive_complexity for C, C#, C++, Fortran, Go, Java, JavaScript, PHP, Ruby, Rust, Swift, TypeScript, so the built-in scanner supplied it for those declarations and the analyzers supplied the rest; the criterion set is complete per declaration, which is what makes the rate comparable to the rubric's.

**Nothing examined:** `testing`.

These concerns are unmeasured, not clean. Install a tool that covers them, or widen `analyzers.depth`, to have them reported.

**Analyzer children are not network-isolated.** 11 external tools ran as local child processes. This agent does not transmit the audited source and opens no socket of its own, but it does not sandbox what it spawns: a third-party analyzer that reaches the network is outside what this run controls or observes. Determinism and no upload are the promise; a kernel air-gap is not.

## Measurements

| Concept | Units | Sources | Tool disagreement | Min | Median | p90 | Max |
|---|---|---|---|---|---|---|---|
| cognitive_complexity | 3678 | complexipy | single source | 0.0 | 1.0 | 6.0 | 27.0 |
| cyclomatic_complexity | 3941 | lizard | single source | 1.0 | 2.0 | 6.0 | 15.0 |
| declaration_lines | 3941 | lizard | single source | 1.0 | 13.0 | 33.0 | 80.0 |
| documentation | 406 | interrogate, multimetric | no shared units | 0.0 | 37.35 | 57.52 | 92.26 |
| duplication | 1 | jscpd | single source | 1.17 | 1.17 | 1.17 | 1.17 |
| file_cyclomatic_complexity | 405 | multimetric | single source | 0.0 | 2.0 | 27.0 | 68.0 |
| halstead_difficulty | 405 | multimetric | single source | 0.67 | 52.28 | 98.5 | 155.32 |
| maintainability_index | 405 | multimetric, radon | 38% | 21.47 | 54.28 | 73.18 | 135.29 |
| parameters | 3941 | lizard | single source | 0.0 | 1.0 | 2.0 | 18.0 |

Where two tools measured the same thing, their disagreement is shown rather than averaged away — it is the uncertainty a single-tool number hides.

*The maintainability estimate uses the analyzer readings for declarations (completed by built-in detectors) — external tools are the primary evidence there. Dimensions no analyzer measured kept the fallback tier. Where the two sources disagree the range widens to contain both; they are never averaged.*

## Analyzer Findings

693 findings from external analyzers — 9 dead-code, 546 documentation, 137 duplication, 1 style.

| File | Line | Concern | Tool | Rule | Finding |
|---|---|---|---|---|---|
| `.github/workflows/quality-gates.yml` | 52 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 208 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 312 | duplication | `jscpd` | — | 9 duplicated lines |
| `README.md` | 154 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 154 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 154 | duplication | `jscpd` | — | 7 duplicated lines |
| `docs/cli.md` | 77 | duplication | `jscpd` | — | 11 duplicated lines |
| `docs/pr-and-baseline-workflows.md` | 38 | duplication | `jscpd` | — | 9 duplicated lines |
| `docs/standard.md` | 248 | duplication | `jscpd` | — | 7 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 127 | duplication | `jscpd` | — | 44 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 174 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 64 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 82 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_adapters.py` | 209 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 213 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_adapters.py` | 302 | duplication | `jscpd` | — | 7 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 304 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 318 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 377 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_adapters.py` | 473 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_analysis.py` | 92 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_analysis.py` | 179 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_analysis.py` | 245 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_analysis.py` | 260 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_analyzer_sections.py` | 38 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_anchor.py` | 58 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_arguments.py` | 21 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'What') |
| `src/maintainability_audit/_arguments.py` | 77 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_arguments.py` | 111 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_arguments.py` | 186 | documentation | `pydocstyle` | D401 | First line should be in imperative mood (perhaps 'Flag', not 'Flags') |
| `src/maintainability_audit/_aspects.py` | 113 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'A') |
| `src/maintainability_audit/_aspects.py` | 160 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_attestation.py` | 89 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_attestation.py` | 126 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_bands.py` | 109 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_bands.py` | 163 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_banner.py` | 46 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
| `src/maintainability_audit/_banner.py` | 48 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_banner.py` | 48 | duplication | `jscpd` | — | 6 duplicated lines |
| `src/maintainability_audit/_banner.py` | 50 | duplication | `jscpd` | — | 9 duplicated lines |

Showing 40 of 693. The complete list is in the JSON report under `analyzer_findings`.

## Why the verified grade is not higher

- graded on the evidence floor 4.2 (point estimate 4.5, ceiling 4.8): unmeasured aspects price at 0 for the grade

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.2 |
| reusability | 4.9 |
| analyzability | 4.4 |
| modifiability | 4.0 |
| testability | 4.8 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 4.6 |
| declaration size | 4.3 |
| duplication | 5.0 |
| risk patterns | 5.0 |
| policy gates | 5.0 |
| test presence | 5.0 |
| dead code | 5.0 |
| near duplication | 5.0 |
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
| `tests/test_operator_named_reads.py` | 613 | warn |
| `src/maintainability_audit/_scan_history.py` | 601 | warn |
| `tests/test_docs_links.py` | 524 | ok |
| `.github/workflows/quality-gates.yml` | 522 | ok |
| `tests/test_mcp_server.py` | 520 | ok |
| `src/maintainability_audit/_discovery.py` | 518 | ok |
| `src/maintainability_audit/_work_order.py` | 508 | ok |
| `tests/test_calibration_corpus.py` | 499 | ok |
| `tests/test_evidence_properties.py` | 496 | ok |
| `src/maintainability_audit/scoring.py` | 495 | ok |
| `src/maintainability_audit/_adapters.py` | 492 | ok |
| `src/maintainability_audit/_mcp_audit.py` | 491 | ok |
| `tests/test_adapters.py` | 491 | ok |
| `src/maintainability_audit/report.py` | 489 | ok |
| `src/maintainability_audit/cli.py` | 488 | ok |
| `src/maintainability_audit/_analysis.py` | 485 | ok |
| `tests/test_mcp_history.py` | 482 | ok |
| `src/maintainability_audit/_masking.py` | 476 | ok |
| `tests/test_grant_only_user_tier.py` | 475 | ok |
| `src/maintainability_audit/_metrics_types.py` | 472 | ok |
| `tools/prove_falsifiers.py` | 472 | ok |
| `tests/test_consumer_migration.py` | 471 | ok |
| `src/maintainability_audit/_pressures.py` | 470 | ok |
| `README.md` | 467 | ok |
| `tests/test_analyzer_provenance_exclusions.py` | 464 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/build_catalog.py` | `build` | 327 | 36 | 15 | 0 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 198 | 35 | 15 | 20 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 298 | 51 | 14 | 3 | warn |
| `tools/build_catalog.py` | `_entry` | 257 | 46 | 14 | 15 | warn |
| `tests/_ast_reading.py` | `reachable_names` | 203 | 44 | 14 | 17 | warn |
| `src/maintainability_audit/_html_view.py` | `_chart_sections` | 193 | 39 | 14 | 4 | warn |
| `tests/test_identity_resolution.py` | `test_fail_on_new_uses_structured_matching_not_a_label_set_difference` | 278 | 33 | 14 | 13 | warn |
| `src/maintainability_audit/_ranges_core.py` | `scan_bounded` | 207 | 78 | 13 | 19 | warn |
| `src/maintainability_audit/_skill_install.py` | `install_skill` | 48 | 67 | 13 | 13 | warn |
| `tests/test_git_argv.py` | `test_every_git_command_disables_gits_own_housekeeping` | 396 | 66 | 13 | 20 | warn |
| `tests/test_language_coverage.py` | `test_every_parsed_language_can_reach_a_complexity_analyzer` | 212 | 58 | 13 | 3 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 13 | 10 | warn |
| `src/maintainability_audit/_metric_adapters.py` | `expand_files` | 46 | 47 | 13 | 6 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `tests/test_authorship_gates.py` | `_step_scripts` | 41 | 42 | 13 | 23 | warn |
| `tests/test_analysis_coverage.py` | `test_no_built_in_claims_to_be_unique_when_an_adapter_exists` | 302 | 36 | 13 | 2 | warn |
| `src/maintainability_audit/duplication.py` | `duplicate_blocks` | 50 | 35 | 13 | 10 | warn |
| `tests/test_ci_installs_the_analyzer_pool.py` | `_pip_installed_by_ci` | 73 | 35 | 13 | 15 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 262 | 34 | 13 | 4 | warn |
| `src/maintainability_audit/_semantic_view.py` | `semantic_markdown` | 36 | 33 | 13 | 12 | warn |
| `src/maintainability_audit/_jvm_adapters.py` | `_finding_of` | 367 | 27 | 13 | 12 | warn |
| `tests/test_promises.py` | `_paths_the_audit_produced` | 129 | 25 | 13 | 20 | warn |
| `tests/test_first_run_elicitation.py` | `_preferred_for` | 255 | 18 | 13 | 14 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 274 | 79 | 12 | 5 | warn |
| `src/maintainability_audit/_pressures.py` | `declined_dimensions` | 244 | 79 | 12 | 6 | warn |
| `src/maintainability_audit/_runner.py` | `run` | 356 | 79 | 12 | 12 | warn |
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 12 | 8 | warn |
| `src/maintainability_audit/_masking.py` | `_mask_code` | 68 | 47 | 12 | 20 | warn |
| `src/maintainability_audit/_ranges_js.py` | `js_declaration_ranges` | 202 | 38 | 12 | 24 | warn |
| `src/maintainability_audit/_test_execution.py` | `run_test_suite` | 133 | 66 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 225 | 66 | 11 | 6 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_masking.py` | `_blank_fstring_literals` | 353 | 44 | 11 | 18 | warn |
| `src/maintainability_audit/_ranges_fortran.py` | `_fortran_end` | 163 | 38 | 11 | 16 | warn |
| `tests/test_network_disclosure.py` | `test_no_module_imports_an_http_client` | 69 | 24 | 11 | 16 | warn |
| `src/maintainability_audit/_analysis.py` | `_attempt` | 398 | 80 | 10 | 12 | warn |
| `tests/test_verified_grade.py` | `test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor` | 255 | 80 | 10 | 0 | warn |
| `src/maintainability_audit/_mcp_audit.py` | `audit_repository` | 178 | 74 | 10 | 11 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 429 | 67 | 10 | 13 | warn |
| `tests/test_written_record.py` | `test_no_document_says_a_register_entry_is_open_that_the_register_closed` | 345 | 45 | 10 | 16 | warn |
| `tests/test_anticipated_refusals.py` | `_named_exceptions` | 95 | 26 | 10 | 16 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 82 | 16 | 9 | 17 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 410 | 80 | 8 | 3 | warn |
| `tests/test_release_plan.py` | `test_the_release_plan_table_is_measured_not_remembered` | 27 | 68 | 8 | 2 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 100 | 74 | 7 | 7 | warn |
| `tests/test_determinism.py` | `test_the_history_window_is_disclosed_as_clock_relative` | 230 | 71 | 7 | 4 | warn |
| `src/maintainability_audit/_pressures.py` | `_declaration_pressure` | 351 | 69 | 7 | 3 | warn |
| `src/maintainability_audit/_safe_write.py` | `_stage_and_replace` | 205 | 69 | 7 | 7 | warn |
| `src/maintainability_audit/_work_order.py` | `work_order` | 241 | 65 | 7 | 8 | warn |
| `src/maintainability_audit/_derive.py` | `_corpus_overall` | 173 | 63 | 7 | 6 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/config.py` | 77 | 1113 | 78 | 2 | 6006 |
| `src/maintainability_audit/cli.py` | 35 | 2756 | 84 | 2 | 2940 |
| `src/maintainability_audit/metrics.py` | 14 | 1261 | 79 | 2 | 1106 |
| `src/maintainability_audit/_mcp_audit.py` | 21 | 1031 | 50 | 2 | 1050 |
| `tests/test_architecture.py` | 35 | 736 | 28 | 2 | 980 |
| `src/maintainability_audit/_masking.py` | 7 | 490 | 120 | 2 | 840 |
| `src/maintainability_audit/_html_view.py` | 11 | 846 | 67 | 1 | 737 |
| `src/maintainability_audit/declarations.py` | 16 | 539 | 43 | 2 | 688 |
| `src/maintainability_audit/renderers.py` | 26 | 1222 | 26 | 2 | 676 |
| `src/maintainability_audit/scoring.py` | 15 | 1165 | 43 | 2 | 645 |
| `src/maintainability_audit/_work_order.py` | 6 | 666 | 102 | 1 | 612 |
| `tools/prove_falsifiers.py` | 9 | 724 | 65 | 1 | 585 |
| `src/maintainability_audit/_discovery.py` | 7 | 776 | 80 | 1 | 560 |
| `src/maintainability_audit/_mcp_setup.py` | 12 | 874 | 46 | 2 | 552 |
| `src/maintainability_audit/mcp_server.py` | 26 | 1819 | 21 | 2 | 546 |
| `src/maintainability_audit/report.py` | 28 | 841 | 19 | 2 | 532 |
| `src/maintainability_audit/_scan_history.py` | 10 | 717 | 52 | 2 | 520 |
| `tests/test_first_run_elicitation.py` | 8 | 810 | 65 | 1 | 520 |
| `src/maintainability_audit/_analysis.py` | 13 | 855 | 39 | 2 | 507 |
| `tests/test_written_record.py` | 13 | 810 | 36 | 2 | 468 |
| `src/maintainability_audit/_ranges_core.py` | 6 | 332 | 75 | 1 | 450 |
| `src/maintainability_audit/_verdict_adapters.py` | 12 | 933 | 37 | 1 | 444 |
| `tools/calibration/measure.py` | 7 | 534 | 63 | 2 | 441 |
| `tests/test_git_argv.py` | 9 | 683 | 48 | 1 | 432 |
| `src/maintainability_audit/_first_run.py` | 9 | 464 | 43 | 1 | 387 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 47 | 98% |
| `README.md` | `src/maintainability_audit/config.py` | 45 | 64% |
| `README.md` | `src/maintainability_audit/__init__.py` | 40 | 83% |
| `README.md` | `docs/release-plan.md` | 38 | 63% |
| `docs/release-plan.md` | `src/maintainability_audit/config.py` | 34 | 57% |
| `docs/release-plan.md` | `src/maintainability_audit/__init__.py` | 33 | 69% |
| `docs/architecture.md` | `tests/test_architecture.py` | 29 | 97% |
| `SECURITY.md` | `src/maintainability_audit/config.py` | 26 | 90% |
| `SECURITY.md` | `src/maintainability_audit/__init__.py` | 25 | 86% |
| `docs/architecture.md` | `docs/decisions.md` | 24 | 80% |
| `README.md` | `SECURITY.md` | 23 | 79% |
| `SECURITY.md` | `docs/release-plan.md` | 23 | 79% |
| `docs/architecture.md` | `src/maintainability_audit/cli.py` | 22 | 69% |
| `README.md` | `docs/roadmap.md` | 19 | 61% |
| `docs/cli.md` | `src/maintainability_audit/cli.py` | 18 | 86% |
| `docs/architecture.md` | `docs/cli.md` | 16 | 76% |
| `SECURITY.md` | `docs/architecture.md` | 15 | 52% |
| `docs/decisions.md` | `docs/release-plan.md` | 15 | 50% |
| `docs/architecture.md` | `src/maintainability_audit/mcp_server.py` | 14 | 61% |
| `docs/architecture.md` | `tests/_architecture_layers.py` | 13 | 100% |
| `docs/architecture.md` | `src/maintainability_audit/report.py` | 13 | 54% |
| `README.md` | `tests/_architecture_layers.py` | 12 | 92% |
| `docs/architecture.md` | `docs/product-intent.md` | 12 | 80% |
| `README.md` | `docs/cli.md` | 12 | 57% |
| `README.md` | `src/maintainability_audit/renderers.py` | 12 | 52% |


<!--
Generated from the tree at commit 0c57062302db1b0e2f3bbef9eeb25356586ddea8. This is a **provenance record, not a promise of currency**: it
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

- Generated: 2026-09-24T19:58:14+00:00
- Commit: `0c57062302db1b0e2f3bbef9eeb25356586ddea8` · Branch: `feat/shell`
- Root: `.`
- Standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.4 / 5 |
| Estimate source | Analyzer readings for declarations (completed by built-in detectors); built-in detectors for remaining dimensions |
| Range (unmeasured evidence priced 0..5) | 4.1 – 4.7 |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 558 |
| File warnings | 4 |
| File failures | 0 |
| Function warnings | 81 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

*Shell is parsed but is not in the reference corpus, so a grade reported for code in it is provisional: the findings are as good as the parser, the rate they are compared against was measured on other languages.*


## Trend

66 separate series. Scans either side of a break were produced by different instruments and cannot be compared, so they are reported apart rather than joined into one line. The current series is given in full; the earlier ones are summarized, because a reader deciding what to do today is acting on the instrument in use today.

**This series begins at a break:** the tool version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Current series** — 1 scan, 2026-09-24T20:02:45Z to 2026-09-24T20:02:45Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

### Earlier series (65 series)

| Window | Scans | Direction | Change | Began at a break in |
|---|---|---|---|---|
| 2026-09-24T19:14:06Z to 2026-09-24T19:30:54Z | 3 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-23T20:27:30Z to 2026-09-23T20:27:30Z | 1 | unknown | — | the tool version, the scan scope changed |
| 2026-09-21T18:30:16Z to 2026-09-21T18:40:04Z | 3 | unknown | — | the tool version changed |
| 2026-09-21T17:48:53Z to 2026-09-21T18:06:18Z | 4 | unknown | — | the tool version, the scan scope changed |
| 2026-09-21T01:07:06Z to 2026-09-21T01:07:06Z | 1 | unknown | — | the tool version changed |
| 2026-09-19T01:11:44Z to 2026-09-19T01:21:41Z | 2 | indistinguishable | +0.10 | the tool version changed |
| 2026-09-18T21:32:18Z to 2026-09-18T21:32:18Z | 1 | unknown | — | the tool version changed |
| 2026-09-18T20:50:09Z to 2026-09-18T20:50:09Z | 1 | unknown | — | the tool version, which analyzers contributed changed |
| 2026-09-18T19:59:49Z to 2026-09-18T20:03:00Z | 2 | indistinguishable | +0.10 | the tool version changed |
| 2026-09-12T00:17:35Z to 2026-09-12T02:12:33Z | 11 | indistinguishable | +0.00 | the tool version, a delegated pillar's producer or its scoring model changed |
| 2026-09-12T00:03:02Z to 2026-09-12T00:03:02Z | 1 | unknown | — | the tool version, a delegated pillar's producer or its scoring model changed |
| 2026-09-11T23:21:19Z to 2026-09-11T23:43:19Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-11T22:43:02Z to 2026-09-11T23:05:25Z | 4 | indistinguishable | +0.00 | a delegated pillar's producer or its scoring model changed |
| 2026-09-11T21:08:33Z to 2026-09-11T21:29:07Z | 2 | indistinguishable | +0.00 | the tool version, a delegated pillar's producer or its scoring model changed |
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
| 2026-09-02T03:10:30Z to 2026-09-02T03:10:30Z | 1 | unknown | — | the tool version changed |
| 2026-09-02T02:55:46Z to 2026-09-02T02:55:46Z | 1 | unknown | — | the tool version changed |
| 2026-09-02T02:37:15Z to 2026-09-02T02:37:15Z | 1 | unknown | — | the tool version changed |
| 2026-09-02T00:13:53Z to 2026-09-02T02:21:34Z | 2 | indistinguishable | +0.00 | the tool version changed |
| 2026-09-01T22:50:04Z to 2026-09-01T23:57:58Z | 4 | indistinguishable | +0.00 | the tool version, the calibration constant, which analyzers contributed, the scan scope changed |
| 2026-08-28T13:05:26Z to 2026-08-28T13:07:10Z | 3 | unknown | — | which analyzers contributed, the scan scope changed |
| 2026-08-21T18:32:29Z to 2026-08-21T18:32:29Z | 1 | unknown | — | the tool version changed |
| 2026-08-20T16:20:52Z to 2026-08-21T18:18:13Z | 27 | indistinguishable | +0.20 | the tool version changed |
| 2026-08-19T22:59:02Z to 2026-08-19T23:50:01Z | 6 | indistinguishable | +0.10 | which analyzers contributed changed |
| 2026-08-17T15:38:29Z to 2026-08-19T22:06:38Z | 48 | indistinguishable | +0.00 | the tool version, which analyzers contributed, the scored languages changed |
| 2026-08-15T20:46:31Z to 2026-08-16T06:01:10Z | 7 | indistinguishable | +0.00 | the first recorded scan |

Every figure above describes scans that happened. This tool does not forecast, and no number here should be read as one.

## Security Work Order

Written by secure-code-agent 0.12.9 and reproduced as it wrote it. It is that tool's work order, not this one's: its findings are not re-ranked or merged into the maintainability work order above.

### Security work order

**0 to fix · 0 to review · 5560 suppression candidates.**

Work the tiers in order. Everything in §FIX is a defect the scanner is confident about; everything in §REVIEW needs your judgement before you touch it, and the reason is stated per finding. This is a constrained task, not a refactor.

#### Hard constraints — MUST NOT violate

1. Fix only the findings listed. Touch nothing else.
2. Do not change crypto algorithms, key derivation, IV/nonce, padding or random sources unless a finding names them.
3. Do not change auth flows, sessions, token lifetime, cookie attributes or authorization gates unless a finding names them.
4. Do not weaken validation, encoding, sanitization, bounds checks, regex strictness or rate limits to make tests pass.
5. Do not disable, delete or skip security tests, or remove `@require_auth`-style decorators.
6. Do not silence warnings: no `# nosec`, `# noqa`, `# type: ignore`, `eslint-disable` or equivalent.
7. Do not add dependencies. If one is genuinely required, stop and ask.
8. Preserve behaviour. If a finding proves current behaviour unsafe, name the input → old/new output.
9. Add one focused test per fix that FAILS before and PASSES after. No "TODO: add test later".
10. Keep the patch small. If you are rewriting a function rather than patching it, stop and report why.

#### Protocol

Per finding: quote the lines you will change, state the minimum change and
the test you will add, apply it, then confirm the test fails on the pre-fix
code and passes after. Do not re-run this tool; CI will.

Report per finding: id · files changed (`file:line`) · test added · behaviour
change (yes/no, with input → old/new) · standards satisfied.

A false positive is a successful outcome: do not patch it. Emit a
`.scignore.yaml` suppression candidate with the justification and a proposed
`expires` date (90 days maximum) for the operator to review.

#### §ACCEPT — test tree and documentation

Findings outside the shipped source. A credential in a test fixture
or a tutorial is usually deliberate, and these do not grade the code
condition — but they are reported, because one of them may be a real
key committed to the wrong place.

**Do not patch these.** Decide per group: a genuine secret to rotate
and remove, or a fixture to record in `.scignore.yaml` with a reason
and an expiry. Propose, do not apply.

Grouped by rule, because the decision is per rule and not per line.

| rule | count | worst | example |
| --- | ---: | --- | --- |
| `B108` | 9 | medium | `tests/test_analyzer_config_isolation.py:139` |
| `B310` | 2 | medium | `tools/sonar_resolve.py:56` |
| `B314` | 1 | medium | `src/maintainability_audit/_xml.py:70` |
| `B101` | 4963 | low | `tests/_ast_reading.py:94` |
| `B603` | 251 | low | `src/maintainability_audit/_backfill.py:51` |
| `B607` | 212 | low | `src/maintainability_audit/_backfill.py:51` |
| `B404` | 117 | low | `src/maintainability_audit/_backfill.py:29` |
| `B405` | 3 | low | `src/maintainability_audit/_jvm_adapters.py:21` |
| _2 more rule(s)_ | 2 | | _see the report_ |

A suppression covering one of these groups looks like:

```yaml
- rule_id: B314
  paths: ["*/tests/*"]
  reason: "state why this is deliberate, and what you checked"
  expires: "YYYY-MM-DD"
```

---

End of findings. Apply the patch protocol above per finding. Report each one in the summary block format.

## Economic Context (scenario)

**0 – 0 USD** over 12 months (base 0 USD), across 0 work-order item(s).

Assumptions:

- each bound = affected changes/year × incremental hours/change × loaded labor rate × horizon/12
- no usable history; assumed one change per work-order item per year
- incremental hours/change of 0.25-2.0 (base 1.0) — a stated default unless configured
- loaded labor rate 130.0-275.0 USD/hour (base 165.0), as configured
- planning horizon of 12 months
- a scenario computed from these assumptions; change them and the range moves with them

## TDD-shaped tests

TDD-shaped tests: detected beside 131 of 162 production source files (path pairing). Constructs: pytest in 290 file(s), unittest in 1 file(s), describe_it in 20 file(s), parametrize in 93 file(s), given_when_then in 3 file(s).
Chronology is not measured. Effectiveness is unscored unless the operator opted into suite execution.

## Test Suite

- The operator opted in to running the repository's test command; it failed (exit 1).
- Command: pytest -n auto --cov=maintainability_audit --cov-report=xml:coverage.xml -q
- Program run: /Users/marshallguillory/Library/Python/3.11/bin/pytest
- Coverage: 71.7% line coverage

## Semantic Findings (ADR 003)

TypeScript semantic coverage: **unknown** — no recorded type analysis and no local type checker: semantic coverage for TypeScript is unknown. Absence of analysis is not absence of findings.

## Pillars

**Practice level 4 of 5** — CI holds a numeric quality gate.

| Pillar | Scope | Practice | Condition | Reading |
|---|---|---:|---:|---|
| readability | partial | 4 | 4.8 | healthy: enforced, and the code reflects it |
| maintainability | owned | 4 | 4.1 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | — | — | not measured — see below |
| security | delegated | 5 | 5.0 | healthy: enforced, and the code reflects it; findings: no findings |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `types-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

21 of 480 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.ts` | TypeScript | 9 |
| `.c` | C | 1 |
| `.cpp` | C++ | 1 |
| `.cs` | C# | 1 |
| `.f90` | Fortran | 1 |
| `.go` | Go | 1 |
| `.js` | JavaScript | 1 |
| `.kt` | Kotlin | 1 |
| `.php` | PHP | 1 |
| `.rb` | Ruby | 1 |
| `.rs` | Rust | 1 |
| `.sh` | Shell | 1 |
| `.swift` | Swift | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Analyzer Coverage

12 of 17 tools contributed — concerns `all`, depth `heavy`, license policy `copyleft-any`.

Plus 8 built-in detectors, which always run and whose measurements are single-source.

| Source | Tier | Outcome | Version | Measurements | Findings | Note |
|---|---|---|---|---|---|---|
| `cohesion` | analyzer | failed | — | — | — | /Users/marshallguillory/Library/Python/3.11/bin/cohesion exited 2: ['usage: cohe |
| `eslint` | analyzer | not-applicable | — | — | — | reads javascript, jsx, typescript; this tree is Python, Shell, so it had nothing |
| `fortitude` | analyzer | not-applicable | — | — | — | reads fortran; this tree is Python, Shell, so it had nothing to examine |
| `spotbugs` | analyzer | not-applicable | — | — | — | reads java; this tree is Python, Shell, so it had nothing to examine |
| `pylint` | analyzer | parse-error | pylint 4.0.7 | — | — | pylint ran but its output could not be read (JSONDecodeError: Expecting value: l |
| `checkstyle` | analyzer | ran | Checkstyle version: 14.0.0 | 0 | 119 |  |
| `complexipy` | analyzer | ran | 7.0.1 | 4211 | 0 |  |
| `interrogate` | analyzer | ran | interrogate, version 1.7.0 | 1 | 0 |  |
| `jscpd` | analyzer | ran | cpd 5.1.1 | 1 | 144 |  |
| `lizard` | analyzer | ran | 1.24.0 | 13494 | 0 |  |
| `multimetric` | analyzer | ran | multimetric 2.4.4 | 1928 | 0 |  |
| `mypy` | analyzer | ran | mypy 2.3.1 (compiled: yes) | 0 | 0 |  |
| `pmd` | analyzer | ran | PMD 7.26.0 (8fd38edf285a33e1164f66205ebe243441db9557, 2026-06-29T08:22:36Z) | 0 | 0 |  |
| `pydocstyle` | analyzer | ran | 6.3.0 | 0 | 240 |  |
| `radon` | analyzer | ran | 6.0.1 | 461 | 0 |  |
| `ruff` | analyzer | ran | ruff 0.16.5 | 0 | 1 |  |
| `vulture` | analyzer | ran | vulture 2.16 | 0 | 6 |  |
| `competing-libraries` | built-in | ran | — | 558 | 0 | two libraries doing one job; no adapter emits idioms |
| `dead-code` | built-in | ran | — | 4451 | 0 | vulture, ruff and eslint cover this |
| `declaration-size` | built-in | ran | — | 4451 | 81 | lizard and complexipy cover these; the only source when neither runs |
| `duplicate-blocks` | built-in | ran | — | 558 | 0 | jscpd covers this; the only source when Node is unavailable |
| `file-size` | built-in | ran | — | 558 | 4 | per-file line counts; no adapter emits file_lines |
| `history` | built-in | ran | — | 557 | 75 | git history; no adapter emits churn, coupling or ownership |
| `near-duplicates` | built-in | ran | — | 4451 | 0 | token-shingle near-matches, which jscpd's exact-block scan misses |
| `risk-patterns` | built-in | ran | — | 558 | 0 | regex policy from this repository's own config; nothing external can hold a proj |

### Coverage by language

| Language | Scored | Examined | Unexamined |
|---|---|---|---|
| Python | yes | `complexity`, `dead-code`, `documentation`, `duplication`, `metrics`, `structure`, `style`, `types` | `testing` |
| Shell | not read | `duplication` | `complexity`, `dead-code`, `documentation`, `metrics`, `structure`, `style`, `testing`, `types` |

The score is drawn from the scored languages only. Anything marked `not read` is listed under Source Not Read with its file count.

**`declarations` measured by analyzers, completed by built-in detectors:** no analyzer supplies cognitive_complexity for C, C#, C++, Fortran, Go, Java, JavaScript, Kotlin, PHP, Ruby, Rust, Swift, TypeScript, so the built-in scanner supplied it for those declarations and the analyzers supplied the rest; the criterion set is complete per declaration, which is what makes the rate comparable to the rubric's.

**Nothing examined:** `testing`.

These concerns are unmeasured, not clean. Install a tool that covers them, or widen `analyzers.depth`, to have them reported.

**Analyzer children are not network-isolated.** 12 external tools ran as local child processes. This agent does not transmit the audited source and opens no socket of its own, but it does not sandbox what it spawns: a third-party analyzer that reaches the network is outside what this run controls or observes. Determinism and no upload are the promise; a kernel air-gap is not.

## Measurements

| Concept | Units | Sources | Tool disagreement | Min | Median | p90 | Max |
|---|---|---|---|---|---|---|---|
| cognitive_complexity | 4211 | complexipy | single source | 0.0 | 1.0 | 6.0 | 34.0 |
| cyclomatic_complexity | 4498 | lizard | single source | 1.0 | 2.0 | 6.0 | 27.0 |
| declaration_lines | 4498 | lizard | single source | 1.0 | 13.0 | 32.0 | 80.0 |
| documentation | 483 | interrogate, multimetric | no shared units | 0.0 | 38.9 | 58.56 | 92.28 |
| duplication | 1 | jscpd | single source | 1.27 | 1.27 | 1.27 | 1.27 |
| file_cyclomatic_complexity | 482 | multimetric | single source | 0.0 | 2.0 | 26.0 | 70.0 |
| halstead_difficulty | 482 | multimetric | single source | 0.67 | 50.67 | 96.8 | 155.32 |
| maintainability_index | 482 | multimetric, radon | 36% | 21.47 | 57.17 | 76.43 | 135.29 |
| parameters | 4498 | lizard | single source | 0.0 | 1.0 | 2.0 | 18.0 |

Where two tools measured the same thing, their disagreement is shown rather than averaged away — it is the uncertainty a single-tool number hides.

*The maintainability estimate uses the analyzer readings for declarations (completed by built-in detectors) — external tools are the primary evidence there. Dimensions no analyzer measured kept the fallback tier. Where the two sources disagree the range widens to contain both; they are never averaged.*

## Analyzer Findings

510 findings from external analyzers — 6 dead-code, 263 documentation, 144 duplication, 97 style.

| File | Line | Concern | Tool | Rule | Finding |
|---|---|---|---|---|---|
| `.github/workflows/quality-gates.yml` | 75 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 138 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 250 | duplication | `jscpd` | — | 9 duplicated lines |
| `README.md` | 197 | duplication | `jscpd` | — | 6 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 129 | duplication | `jscpd` | — | 47 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 179 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 64 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 209 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 302 | duplication | `jscpd` | — | 7 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 304 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 318 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_adapters.py` | 377 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_analysis.py` | 92 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_arguments.py` | 111 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_bands.py` | 163 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_banner.py` | 48 | duplication | `jscpd` | — | 6 duplicated lines |
| `src/maintainability_audit/_banner.py` | 48 | duplication | `jscpd` | — | 9 duplicated lines |
| `src/maintainability_audit/_catalog.py` | 88 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_catalog.py` | 232 | documentation | `pydocstyle` | D205 | 1 blank line required between summary line and description (found 0) |
| `src/maintainability_audit/_catalog.py` | 232 | documentation | `pydocstyle` | D209 | Multi-line docstring closing quotes should be on a separate line |
| `src/maintainability_audit/_catalog.py` | 232 | documentation | `pydocstyle` | D400 | First line should end with a period (not 'y') |
| `src/maintainability_audit/_corroborate.py` | 55 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_corroborate.py` | 59 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_corroborate.py` | 73 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_discovery.py` | 169 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_discovery.py` | 201 | documentation | `pydocstyle` | D102 | Missing docstring in public method |
| `src/maintainability_audit/_discovery.py` | 513 | documentation | `pydocstyle` | D205 | 1 blank line required between summary line and description (found 0) |
| `src/maintainability_audit/_discovery.py` | 513 | documentation | `pydocstyle` | D209 | Multi-line docstring closing quotes should be on a separate line |
| `src/maintainability_audit/_discovery.py` | 513 | documentation | `pydocstyle` | D400 | First line should end with a period (not 'o') |
| `src/maintainability_audit/_evidence_view.py` | 84 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_evidence_view.py` | 88 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_evidence_view.py` | 112 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_evidence_view.py` | 126 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_finding_match.py` | 82 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_finding_match.py` | 86 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_finding_match.py` | 90 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_first_run.py` | 257 | documentation | `pydocstyle` | D205 | 1 blank line required between summary line and description (found 0) |
| `src/maintainability_audit/_first_run.py` | 257 | documentation | `pydocstyle` | D400 | First line should end with a period (not 'f') |
| `src/maintainability_audit/_gates.py` | 130 | documentation | `pydocstyle` | D103 | Missing docstring in public function |
| `src/maintainability_audit/_generic.py` | 146 | duplication | `jscpd` | — | 9 duplicated lines |

Showing 40 of 510. The complete list is in the JSON report under `analyzer_findings`.

## Why the verified grade is not higher

- graded on the evidence floor 4.1 (point estimate 4.4, ceiling 4.7): unmeasured aspects price at 0 for the grade

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.2 |
| reusability | 4.9 |
| analyzability | 4.4 |
| modifiability | 4.0 |
| testability | 4.6 |

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
| test effectiveness | 3.6 |

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
| `.github/workflows/quality-gates.yml` | 637 | warn |
| `tests/test_operator_named_reads.py` | 637 | warn |
| `src/maintainability_audit/_prompt_sections.py` | 628 | warn |
| `src/maintainability_audit/_scan_history.py` | 624 | warn |
| `src/maintainability_audit/cli.py` | 564 | ok |
| `src/maintainability_audit/_metrics_types.py` | 561 | ok |
| `src/maintainability_audit/_discovery.py` | 553 | ok |
| `src/maintainability_audit/_work_order.py` | 544 | ok |
| `src/maintainability_audit/report.py` | 540 | ok |
| `src/maintainability_audit/mcp_server.py` | 536 | ok |
| `src/maintainability_audit/_mcp_audit.py` | 532 | ok |
| `tests/test_docs_links.py` | 524 | ok |
| `tests/test_mcp_server.py` | 520 | ok |
| `tests/test_grammar_constructs.py` | 516 | ok |
| `README.md` | 513 | ok |
| `src/maintainability_audit/scoring.py` | 513 | ok |
| `tools/prove_falsifiers.py` | 500 | ok |
| `tests/test_calibration_corpus.py` | 499 | ok |
| `src/maintainability_audit/_mcp_setup.py` | 496 | ok |
| `tests/test_evidence_properties.py` | 496 | ok |
| `src/maintainability_audit/_scan_view.py` | 495 | ok |
| `src/maintainability_audit/_adapters.py` | 492 | ok |
| `tests/test_adapters.py` | 491 | ok |
| `tests/test_mcp_history.py` | 486 | ok |
| `src/maintainability_audit/_analysis.py` | 485 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/build_catalog.py` | `build` | 335 | 36 | 15 | 0 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 198 | 35 | 15 | 20 | warn |
| `tests/test_operator_named_reads.py` | `test_the_operator_read_resolves_the_name_exactly_once` | 402 | 67 | 14 | 12 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 298 | 51 | 14 | 3 | warn |
| `tools/build_catalog.py` | `_entry` | 265 | 46 | 14 | 15 | warn |
| `tests/_ast_reading.py` | `reachable_names` | 203 | 44 | 14 | 17 | warn |
| `src/maintainability_audit/_html_view.py` | `_chart_sections` | 196 | 39 | 14 | 4 | warn |
| `tests/test_identity_resolution.py` | `test_fail_on_new_uses_structured_matching_not_a_label_set_difference` | 278 | 33 | 14 | 13 | warn |
| `src/maintainability_audit/_ranges_core.py` | `scan_bounded` | 207 | 78 | 13 | 19 | warn |
| `src/maintainability_audit/_skill_install.py` | `install_skill` | 48 | 67 | 13 | 13 | warn |
| `tests/test_git_argv.py` | `test_every_git_command_disables_gits_own_housekeeping` | 396 | 66 | 13 | 20 | warn |
| `src/maintainability_audit/_prompt_sections.py` | `prompt_focus_sections` | 454 | 60 | 13 | 3 | warn |
| `tests/test_language_coverage.py` | `test_every_parsed_language_can_reach_a_complexity_analyzer` | 218 | 58 | 13 | 3 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 13 | 10 | warn |
| `src/maintainability_audit/_metric_adapters.py` | `expand_files` | 46 | 47 | 13 | 6 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `tests/test_authorship_gates.py` | `_step_scripts` | 41 | 43 | 13 | 23 | warn |
| `src/maintainability_audit/_discovery.py` | `discover` | 466 | 42 | 13 | 12 | warn |
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
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 12 | 8 | warn |
| `tests/test_platform_claim.py` | `test_the_macos_runner_actually_runs_the_suite` | 174 | 61 | 12 | 8 | warn |
| `src/maintainability_audit/_masking.py` | `_mask_code` | 68 | 47 | 12 | 20 | warn |
| `src/maintainability_audit/_ranges_js.py` | `js_declaration_ranges` | 202 | 38 | 12 | 24 | warn |
| `src/maintainability_audit/_test_execution.py` | `run_test_suite` | 152 | 80 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 225 | 66 | 11 | 6 | warn |
| `src/maintainability_audit/cli.py` | `main` | 447 | 64 | 11 | 12 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 300 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_masking.py` | `_blank_fstring_literals` | 353 | 44 | 11 | 18 | warn |
| `src/maintainability_audit/_ranges_fortran.py` | `_fortran_end` | 163 | 38 | 11 | 16 | warn |
| `tests/test_network_disclosure.py` | `test_no_module_imports_an_http_client` | 69 | 24 | 11 | 16 | warn |
| `src/maintainability_audit/_analysis.py` | `_attempt` | 398 | 80 | 10 | 12 | warn |
| `tests/test_verified_grade.py` | `test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor` | 271 | 80 | 10 | 0 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 437 | 77 | 10 | 13 | warn |
| `tests/test_written_record.py` | `test_no_document_says_a_register_entry_is_open_that_the_register_closed` | 343 | 45 | 10 | 16 | warn |
| `tests/test_anticipated_refusals.py` | `_named_exceptions` | 95 | 26 | 10 | 16 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 461 | 80 | 9 | 3 | warn |
| `src/maintainability_audit/_prompt_sections.py` | `prompt_pressure_section` | 359 | 66 | 9 | 5 | warn |
| `src/maintainability_audit/_ranges_shell.py` | `_mask_code` | 84 | 25 | 9 | 16 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 82 | 16 | 9 | 17 | warn |
| `src/maintainability_audit/_mcp_audit.py` | `audit_repository` | 181 | 73 | 8 | 9 | warn |
| `tests/test_release_plan.py` | `test_the_release_plan_table_is_measured_not_remembered` | 27 | 68 | 8 | 2 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/config.py` | 101 | 1192 | 73 | 2 | 7373 |
| `src/maintainability_audit/cli.py` | 40 | 2856 | 88 | 2 | 3520 |
| `src/maintainability_audit/_mcp_audit.py` | 28 | 1094 | 56 | 2 | 1568 |
| `src/maintainability_audit/_work_order.py` | 12 | 1142 | 102 | 1 | 1224 |
| `src/maintainability_audit/metrics.py` | 14 | 1261 | 79 | 2 | 1106 |
| `src/maintainability_audit/_mcp_setup.py` | 18 | 1032 | 61 | 2 | 1098 |
| `src/maintainability_audit/_html_view.py` | 16 | 869 | 68 | 1 | 1088 |
| `src/maintainability_audit/report.py` | 33 | 964 | 31 | 2 | 1023 |
| `tests/test_architecture.py` | 35 | 736 | 28 | 2 | 980 |
| `src/maintainability_audit/renderers.py` | 33 | 1339 | 27 | 2 | 891 |
| `src/maintainability_audit/mcp_server.py` | 33 | 2117 | 26 | 2 | 858 |
| `src/maintainability_audit/_masking.py` | 7 | 490 | 120 | 2 | 840 |
| `src/maintainability_audit/declarations.py` | 18 | 569 | 43 | 2 | 774 |
| `src/maintainability_audit/scoring.py` | 18 | 1199 | 43 | 2 | 774 |
| `tools/prove_falsifiers.py` | 11 | 758 | 66 | 1 | 726 |
| `src/maintainability_audit/_prompt_sections.py` | 9 | 762 | 80 | 1 | 720 |
| `src/maintainability_audit/_scan_view.py` | 11 | 771 | 63 | 1 | 693 |
| `src/maintainability_audit/_discovery.py` | 8 | 815 | 85 | 1 | 680 |
| `tests/test_first_run_elicitation.py` | 10 | 816 | 65 | 1 | 650 |
| `src/maintainability_audit/_scan_history.py` | 12 | 768 | 54 | 2 | 648 |
| `src/maintainability_audit/_analysis.py` | 14 | 857 | 39 | 2 | 546 |
| `src/maintainability_audit/_ranges_core.py` | 7 | 334 | 75 | 1 | 525 |
| `tests/test_written_record.py` | 14 | 830 | 36 | 2 | 504 |
| `src/maintainability_audit/_evidence_view.py` | 11 | 458 | 44 | 1 | 484 |
| `src/maintainability_audit/_cognitive.py` | 9 | 390 | 53 | 2 | 477 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `README.md` | `src/maintainability_audit/__init__.py` | 70 | 90% |
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 69 | 88% |
| `README.md` | `docs/release-plan.md` | 68 | 74% |
| `README.md` | `src/maintainability_audit/config.py` | 67 | 73% |
| `docs/release-plan.md` | `src/maintainability_audit/__init__.py` | 62 | 80% |
| `docs/release-plan.md` | `src/maintainability_audit/config.py` | 55 | 60% |
| `docs/architecture.md` | `tests/test_architecture.py` | 29 | 97% |
| `SECURITY.md` | `src/maintainability_audit/config.py` | 29 | 91% |
| `SECURITY.md` | `src/maintainability_audit/__init__.py` | 28 | 88% |
| `README.md` | `SECURITY.md` | 26 | 81% |
| `SECURITY.md` | `docs/release-plan.md` | 26 | 81% |
| `docs/architecture.md` | `docs/decisions.md` | 25 | 81% |
| `docs/architecture.md` | `src/maintainability_audit/cli.py` | 24 | 69% |
| `README.md` | `docs/roadmap.md` | 22 | 60% |
| `docs/cli.md` | `src/maintainability_audit/cli.py` | 19 | 83% |
| `docs/architecture.md` | `docs/cli.md` | 18 | 78% |
| `docs/architecture.md` | `src/maintainability_audit/mcp_server.py` | 18 | 60% |
| `README.md` | `src/maintainability_audit/renderers.py` | 17 | 59% |
| `docs/architecture.md` | `tests/_architecture_layers.py` | 16 | 100% |
| `docs/decisions.md` | `docs/release-plan.md` | 16 | 52% |
| `SECURITY.md` | `docs/architecture.md` | 16 | 50% |
| `README.md` | `tests/_architecture_layers.py` | 15 | 94% |
| `docs/architecture.md` | `src/maintainability_audit/report.py` | 15 | 52% |
| `src/maintainability_audit/config.py` | `tests/_architecture_layers.py` | 14 | 88% |
| `README.md` | `docs/cli.md` | 14 | 61% |


<!--
Generated from the tree at commit af96de137282e74256073f33b25c3a2f772f6a20. This is a **provenance record, not a promise of currency**: it
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

- Generated: 2026-09-06T18:51:33+00:00
- Commit: `af96de137282e74256073f33b25c3a2f772f6a20` · Branch: `feat/go-language`
- Root: `.`
- Standard: ISO/IEC 25010 maintainability-inspired 0-5 scale, rate-based

## Summary

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.2 / 5 |
| Estimate source | Built-in detectors (fallback tier) |
| Range (unmeasured evidence priced 0..5) | 4.1 – 4.3 |
| Evidence | Evidence complete under profile `default-v1`. |
| Verified grade | B |
| Files scanned | 476 |
| File warnings | 149 |
| File failures | 0 |
| Function warnings | 83 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

*Swift and COBOL and Go and Rust and PHP and Ruby are parsed but are not in the reference corpus, so a grade or multiple reported for code in them is provisional: the findings are as good as the parser, the rate they are compared against was measured on other languages.*


## Trend

38 separate series. Scans either side of a break were produced by different instruments and cannot be compared, so they are reported apart rather than joined into one line.

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

**Break before this series:** rubric_version, calibration, analyzers, scope changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 7** — 4 scans, 2026-09-01T22:50:04Z to 2026-09-01T23:57:58Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 3 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 8** — 3 scans, 2026-09-02T00:13:53Z to 2026-09-02T02:55:46Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 9** — 2 scans, 2026-09-02T02:37:15Z to 2026-09-02T03:10:30Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 10** — 5 scans, 2026-09-02T04:13:12Z to 2026-09-02T04:32:59Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 11** — 2 scans, 2026-09-02T05:07:33Z to 2026-09-02T05:21:56Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 12** — 4 scans, 2026-09-02T15:53:44Z to 2026-09-02T16:09:57Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 13** — 5 scans, 2026-09-02T16:49:38Z to 2026-09-02T18:17:31Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 2 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 14** — 1 scans, 2026-09-02T19:09:34Z to 2026-09-02T19:09:34Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 15** — 4 scans, 2026-09-02T19:48:51Z to 2026-09-02T20:10:01Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 16** — 1 scans, 2026-09-02T20:57:23Z to 2026-09-02T20:57:23Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 17** — 1 scans, 2026-09-02T21:22:31Z to 2026-09-02T21:22:31Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 18** — 1 scans, 2026-09-03T01:50:55Z to 2026-09-03T01:50:55Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 19** — 3 scans, 2026-09-03T03:14:36Z to 2026-09-03T03:26:28Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 20** — 10 scans, 2026-09-03T04:32:13Z to 2026-09-03T14:04:41Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 21** — 5 scans, 2026-09-03T14:19:51Z to 2026-09-03T15:38:52Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 1 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 22** — 15 scans, 2026-09-03T16:43:03Z to 2026-09-03T19:57:41Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 4 introduced, 5 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, calibration changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 23** — 11 scans, 2026-09-03T22:26:06Z to 2026-09-04T04:12:38Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 2 introduced, 3 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 24** — 6 scans, 2026-09-04T04:25:28Z to 2026-09-04T05:44:00Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 1 introduced, 1 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 25** — 4 scans, 2026-09-04T05:56:43Z to 2026-09-04T06:58:47Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 26** — 2 scans, 2026-09-04T07:11:36Z to 2026-09-04T07:40:48Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 27** — 1 scans, 2026-09-04T07:53:46Z to 2026-09-04T07:53:46Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 28** — 2 scans, 2026-09-04T16:40:06Z to 2026-09-04T17:56:04Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 29** — 1 scans, 2026-09-04T19:08:33Z to 2026-09-04T19:08:33Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 30** — 16 scans, 2026-09-04T19:52:42Z to 2026-09-04T22:33:54Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 2 introduced, 5 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 31** — 6 scans, 2026-09-04T22:42:23Z to 2026-09-05T00:47:24Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 3 introduced, 3 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 32** — 23 scans, 2026-09-05T00:59:02Z to 2026-09-05T18:15:54Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 2 introduced, 2 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 33** — 1 scans, 2026-09-05T19:52:45Z to 2026-09-05T19:52:45Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** scope changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 34** — 1 scans, 2026-09-05T20:44:46Z to 2026-09-05T20:44:46Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

**Break before this series:** analyzers, scored_languages changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 35** — 2 scans, 2026-09-05T20:49:08Z to 2026-09-05T20:53:53Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version, analyzers, scored_languages, scope changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 36** — 6 scans, 2026-09-05T21:35:57Z to 2026-09-06T04:02:48Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 4 introduced, 2 cleared (adding faster than clearing).
- **Growth:** got worse without growing.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 37** — 9 scans, 2026-09-06T14:42:34Z to 2026-09-06T18:28:54Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 6 introduced, 7 cleared (clearing faster than adding).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

**Break before this series:** rubric_version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Series 38** — 2 scans, 2026-09-06T18:48:06Z to 2026-09-06T18:55:57Z.

- **Direction:** indistinguishable — moved, but by less than the evidence can resolve. Change +0.00.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** neither grew nor got worse.
- **Never cleared in this window:** 0 findings.

Every figure above describes scans that happened. This tool does not forecast, and no number here should be read as one.

## Work Order

Ordered by what it costs to leave against what it costs to fix (see the standard). `Worth` is what clearing the whole class moves the score, recomputed through the rubric rather than estimated.

| # | Band | Item | Worth | Target |
|---:|---|---|---:|---|
| 1 | quick-win | unpaired file in src/maintainability_audit/_metric_adapters.py (`src/maintainability_audit/_metric_adapters.py`) | — | add a paired test for `_metric_adapters.py` |
| 2 | quick-win | unpaired file in src/maintainability_audit/evidence.py (`src/maintainability_audit/evidence.py`) | — | add a paired test for `evidence.py` |
| 3 | quick-win | unpaired file in src/maintainability_audit/prompts.py (`src/maintainability_audit/prompts.py`) | — | add a paired test for `prompts.py` |
| 4 | quick-win | unpaired file in src/maintainability_audit/report.py (`src/maintainability_audit/report.py`) | — | add a paired test for `report.py` |
| 5 | quick-win | unpaired file in src/maintainability_audit/scoring.py (`src/maintainability_audit/scoring.py`) | — | add a paired test for `scoring.py` |
| 6 | quick-win | unpaired file in src/maintainability_audit/_work_order.py (`src/maintainability_audit/_work_order.py`) | — | add a paired test for `_work_order.py` |
| 7 | quick-win | unpaired file in src/maintainability_audit/_adapters.py (`src/maintainability_audit/_adapters.py`) | — | add a paired test for `_adapters.py` |
| 8 | quick-win | unpaired file in src/maintainability_audit/_analysis.py (`src/maintainability_audit/_analysis.py`) | — | add a paired test for `_analysis.py` |
| 9 | quick-win | unpaired file in src/maintainability_audit/_scan_history.py (`src/maintainability_audit/_scan_history.py`) | — | add a paired test for `_scan_history.py` |
| 10 | quick-win | unpaired file in src/maintainability_audit/_metrics_types.py (`src/maintainability_audit/_metrics_types.py`) | — | add a paired test for `_metrics_types.py` |
| 11 | quick-win | unpaired file in src/maintainability_audit/_mcp_audit.py (`src/maintainability_audit/_mcp_audit.py`) | — | add a paired test for `_mcp_audit.py` |
| 12 | quick-win | unpaired file in src/maintainability_audit/_discovery.py (`src/maintainability_audit/_discovery.py`) | — | add a paired test for `_discovery.py` |
| 13 | quick-win | unpaired file in tools/calibration/measure.py (`tools/calibration/measure.py`) | — | add a paired test for `measure.py` |
| 14 | quick-win | unpaired file in src/maintainability_audit/_masking.py (`src/maintainability_audit/_masking.py`) | — | add a paired test for `_masking.py` |
| 15 | quick-win | unpaired file in src/maintainability_audit/config.py (`src/maintainability_audit/config.py`) | — | add a paired test for `config.py` |
| 16 | quick-win | unpaired file in tools/build_catalog.py (`tools/build_catalog.py`) | — | add a paired test for `build_catalog.py` |
| 17 | quick-win | unpaired file in src/maintainability_audit/_runner.py (`src/maintainability_audit/_runner.py`) | — | add a paired test for `_runner.py` |
| 18 | quick-win | unpaired file in src/maintainability_audit/_scan_view.py (`src/maintainability_audit/_scan_view.py`) | — | add a paired test for `_scan_view.py` |
| 19 | quick-win | unpaired file in src/maintainability_audit/_formula.py (`src/maintainability_audit/_formula.py`) | — | add a paired test for `_formula.py` |
| 20 | quick-win | unpaired file in src/maintainability_audit/_pressures.py (`src/maintainability_audit/_pressures.py`) | — | add a paired test for `_pressures.py` |
| 21 | quick-win | unpaired file in src/maintainability_audit/_jvm_adapters.py (`src/maintainability_audit/_jvm_adapters.py`) | — | add a paired test for `_jvm_adapters.py` |
| 22 | quick-win | unpaired file in src/maintainability_audit/_verdict_adapters.py (`src/maintainability_audit/_verdict_adapters.py`) | — | add a paired test for `_verdict_adapters.py` |
| 23 | quick-win | unpaired file in src/maintainability_audit/declarations.py (`src/maintainability_audit/declarations.py`) | — | add a paired test for `declarations.py` |
| 24 | quick-win | unpaired file in src/maintainability_audit/_mcp_setup.py (`src/maintainability_audit/_mcp_setup.py`) | — | add a paired test for `_mcp_setup.py` |
| 25 | quick-win | unpaired file in src/maintainability_audit/_html_view.py (`src/maintainability_audit/_html_view.py`) | — | add a paired test for `_html_view.py` |
| 26 | quick-win | unpaired file in src/maintainability_audit/_evidence_view.py (`src/maintainability_audit/_evidence_view.py`) | — | add a paired test for `_evidence_view.py` |
| 27 | quick-win | unpaired file in src/maintainability_audit/git_tools.py (`src/maintainability_audit/git_tools.py`) | — | add a paired test for `git_tools.py` |
| 28 | quick-win | unpaired file in src/maintainability_audit/_verification.py (`src/maintainability_audit/_verification.py`) | — | add a paired test for `_verification.py` |
| 29 | quick-win | unpaired file in src/maintainability_audit/_practice.py (`src/maintainability_audit/_practice.py`) | — | add a paired test for `_practice.py` |
| 30 | quick-win | unpaired file in tools/calibration/select_authored.py (`tools/calibration/select_authored.py`) | — | add a paired test for `select_authored.py` |
| 31 | quick-win | unpaired file in src/maintainability_audit/_html_report_sections.py (`src/maintainability_audit/_html_report_sections.py`) | — | add a paired test for `_html_report_sections.py` |
| 32 | quick-win | unpaired file in src/maintainability_audit/_finding_match.py (`src/maintainability_audit/_finding_match.py`) | — | add a paired test for `_finding_match.py` |
| 33 | quick-win | unpaired file in src/maintainability_audit/_skill_install.py (`src/maintainability_audit/_skill_install.py`) | — | add a paired test for `_skill_install.py` |
| 34 | quick-win | unpaired file in src/maintainability_audit/renderers.py (`src/maintainability_audit/renderers.py`) | — | add a paired test for `renderers.py` |
| 35 | quick-win | unpaired file in tools/calibration/measure_cohorts.py (`tools/calibration/measure_cohorts.py`) | — | add a paired test for `measure_cohorts.py` |
| 36 | quick-win | unpaired file in src/maintainability_audit/_aspects.py (`src/maintainability_audit/_aspects.py`) | — | add a paired test for `_aspects.py` |
| 37 | quick-win | unpaired file in src/maintainability_audit/_charts.py (`src/maintainability_audit/_charts.py`) | — | add a paired test for `_charts.py` |
| 38 | quick-win | unpaired file in src/maintainability_audit/_precommit.py (`src/maintainability_audit/_precommit.py`) | — | add a paired test for `_precommit.py` |
| 39 | quick-win | unpaired file in src/maintainability_audit/_documents.py (`src/maintainability_audit/_documents.py`) | — | add a paired test for `_documents.py` |
| 40 | quick-win | unpaired file in src/maintainability_audit/_generic.py (`src/maintainability_audit/_generic.py`) | — | add a paired test for `_generic.py` |
| 41 | quick-win | unpaired file in tools/calibration/measure_fix_breadth.py (`tools/calibration/measure_fix_breadth.py`) | — | add a paired test for `measure_fix_breadth.py` |
| 42 | quick-win | unpaired file in src/maintainability_audit/_cognitive.py (`src/maintainability_audit/_cognitive.py`) | — | add a paired test for `_cognitive.py` |
| 43 | quick-win | unpaired file in src/maintainability_audit/_derive.py (`src/maintainability_audit/_derive.py`) | — | add a paired test for `_derive.py` |
| 44 | quick-win | unpaired file in src/maintainability_audit/_first_run.py (`src/maintainability_audit/_first_run.py`) | — | add a paired test for `_first_run.py` |
| 45 | quick-win | unpaired file in src/maintainability_audit/_ranges_cobol.py (`src/maintainability_audit/_ranges_cobol.py`) | — | add a paired test for `_ranges_cobol.py` |
| 46 | quick-win | unpaired file in src/maintainability_audit/_ranges_core.py (`src/maintainability_audit/_ranges_core.py`) | — | add a paired test for `_ranges_core.py` |
| 47 | quick-win | unpaired file in src/maintainability_audit/_in_loop.py (`src/maintainability_audit/_in_loop.py`) | — | add a paired test for `_in_loop.py` |
| 48 | quick-win | unpaired file in src/maintainability_audit/_safe_write.py (`src/maintainability_audit/_safe_write.py`) | — | add a paired test for `_safe_write.py` |
| 49 | quick-win | unpaired file in src/maintainability_audit/_hostile_prompt.py (`src/maintainability_audit/_hostile_prompt.py`) | — | add a paired test for `_hostile_prompt.py` |
| 50 | quick-win | unpaired file in src/maintainability_audit/metrics.py (`src/maintainability_audit/metrics.py`) | — | add a paired test for `metrics.py` |
| 51 | quick-win | unpaired file in src/maintainability_audit/_trends.py (`src/maintainability_audit/_trends.py`) | — | add a paired test for `_trends.py` |
| 52 | quick-win | unpaired file in src/maintainability_audit/_catalog.py (`src/maintainability_audit/_catalog.py`) | — | add a paired test for `_catalog.py` |
| 53 | quick-win | unpaired file in src/maintainability_audit/_recurrence.py (`src/maintainability_audit/_recurrence.py`) | — | add a paired test for `_recurrence.py` |
| 54 | quick-win | unpaired file in src/maintainability_audit/_test_commands.py (`src/maintainability_audit/_test_commands.py`) | — | add a paired test for `_test_commands.py` |
| 55 | major-project | near-duplicate declaration in src/maintainability_audit/_pressures.py (`src/maintainability_audit/_pressures.py`:97) | — | remove the near-duplicate declaration |
| 56 | major-project | near-duplicate declaration in src/maintainability_audit/_ranges_php.py (`src/maintainability_audit/_ranges_php.py`:81) | — | remove the near-duplicate declaration |
| 57 | major-project | near-duplicate declaration in src/maintainability_audit/_verdict_adapters.py (`src/maintainability_audit/_verdict_adapters.py`:79) | — | remove the near-duplicate declaration |
| 58 | major-project | near-duplicate declaration in src/maintainability_audit/_semantic_policy.py (`src/maintainability_audit/_semantic_policy.py`:30) | — | remove the near-duplicate declaration |
| 59 | fill-in | unreferenced declaration in src/maintainability_audit/_pressures.py (`src/maintainability_audit/_pressures.py`:263) | — | remove the unreferenced declaration |
| 60 | fill-in | unreferenced declaration in src/maintainability_audit/_grant_ledger.py (`src/maintainability_audit/_grant_ledger.py`:44) | — | remove the unreferenced declaration |

Verify with: `python -m maintainability_audit --root . --format json`

### Copy-paste prompts

One self-contained prompt per item — paste any block whole into a coding agent.

#### unpaired file in src/maintainability_audit/_metric_adapters.py
`src/maintainability_audit/_metric_adapters.py` · quick-win

```text
Repository: .
Task: add a paired test for `_metric_adapters.py`.
Location: src/maintainability_audit/_metric_adapters.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/evidence.py
`src/maintainability_audit/evidence.py` · quick-win

```text
Repository: .
Task: add a paired test for `evidence.py`.
Location: src/maintainability_audit/evidence.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/prompts.py
`src/maintainability_audit/prompts.py` · quick-win

```text
Repository: .
Task: add a paired test for `prompts.py`.
Location: src/maintainability_audit/prompts.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/report.py
`src/maintainability_audit/report.py` · quick-win

```text
Repository: .
Task: add a paired test for `report.py`.
Location: src/maintainability_audit/report.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/scoring.py
`src/maintainability_audit/scoring.py` · quick-win

```text
Repository: .
Task: add a paired test for `scoring.py`.
Location: src/maintainability_audit/scoring.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_work_order.py
`src/maintainability_audit/_work_order.py` · quick-win

```text
Repository: .
Task: add a paired test for `_work_order.py`.
Location: src/maintainability_audit/_work_order.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_adapters.py
`src/maintainability_audit/_adapters.py` · quick-win

```text
Repository: .
Task: add a paired test for `_adapters.py`.
Location: src/maintainability_audit/_adapters.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_analysis.py
`src/maintainability_audit/_analysis.py` · quick-win

```text
Repository: .
Task: add a paired test for `_analysis.py`.
Location: src/maintainability_audit/_analysis.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_scan_history.py
`src/maintainability_audit/_scan_history.py` · quick-win

```text
Repository: .
Task: add a paired test for `_scan_history.py`.
Location: src/maintainability_audit/_scan_history.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_metrics_types.py
`src/maintainability_audit/_metrics_types.py` · quick-win

```text
Repository: .
Task: add a paired test for `_metrics_types.py`.
Location: src/maintainability_audit/_metrics_types.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_mcp_audit.py
`src/maintainability_audit/_mcp_audit.py` · quick-win

```text
Repository: .
Task: add a paired test for `_mcp_audit.py`.
Location: src/maintainability_audit/_mcp_audit.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_discovery.py
`src/maintainability_audit/_discovery.py` · quick-win

```text
Repository: .
Task: add a paired test for `_discovery.py`.
Location: src/maintainability_audit/_discovery.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in tools/calibration/measure.py
`tools/calibration/measure.py` · quick-win

```text
Repository: .
Task: add a paired test for `measure.py`.
Location: tools/calibration/measure.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_masking.py
`src/maintainability_audit/_masking.py` · quick-win

```text
Repository: .
Task: add a paired test for `_masking.py`.
Location: src/maintainability_audit/_masking.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/config.py
`src/maintainability_audit/config.py` · quick-win

```text
Repository: .
Task: add a paired test for `config.py`.
Location: src/maintainability_audit/config.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in tools/build_catalog.py
`tools/build_catalog.py` · quick-win

```text
Repository: .
Task: add a paired test for `build_catalog.py`.
Location: tools/build_catalog.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_runner.py
`src/maintainability_audit/_runner.py` · quick-win

```text
Repository: .
Task: add a paired test for `_runner.py`.
Location: src/maintainability_audit/_runner.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_scan_view.py
`src/maintainability_audit/_scan_view.py` · quick-win

```text
Repository: .
Task: add a paired test for `_scan_view.py`.
Location: src/maintainability_audit/_scan_view.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_formula.py
`src/maintainability_audit/_formula.py` · quick-win

```text
Repository: .
Task: add a paired test for `_formula.py`.
Location: src/maintainability_audit/_formula.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_pressures.py
`src/maintainability_audit/_pressures.py` · quick-win

```text
Repository: .
Task: add a paired test for `_pressures.py`.
Location: src/maintainability_audit/_pressures.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_jvm_adapters.py
`src/maintainability_audit/_jvm_adapters.py` · quick-win

```text
Repository: .
Task: add a paired test for `_jvm_adapters.py`.
Location: src/maintainability_audit/_jvm_adapters.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_verdict_adapters.py
`src/maintainability_audit/_verdict_adapters.py` · quick-win

```text
Repository: .
Task: add a paired test for `_verdict_adapters.py`.
Location: src/maintainability_audit/_verdict_adapters.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/declarations.py
`src/maintainability_audit/declarations.py` · quick-win

```text
Repository: .
Task: add a paired test for `declarations.py`.
Location: src/maintainability_audit/declarations.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_mcp_setup.py
`src/maintainability_audit/_mcp_setup.py` · quick-win

```text
Repository: .
Task: add a paired test for `_mcp_setup.py`.
Location: src/maintainability_audit/_mcp_setup.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_html_view.py
`src/maintainability_audit/_html_view.py` · quick-win

```text
Repository: .
Task: add a paired test for `_html_view.py`.
Location: src/maintainability_audit/_html_view.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_evidence_view.py
`src/maintainability_audit/_evidence_view.py` · quick-win

```text
Repository: .
Task: add a paired test for `_evidence_view.py`.
Location: src/maintainability_audit/_evidence_view.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/git_tools.py
`src/maintainability_audit/git_tools.py` · quick-win

```text
Repository: .
Task: add a paired test for `git_tools.py`.
Location: src/maintainability_audit/git_tools.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_verification.py
`src/maintainability_audit/_verification.py` · quick-win

```text
Repository: .
Task: add a paired test for `_verification.py`.
Location: src/maintainability_audit/_verification.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_practice.py
`src/maintainability_audit/_practice.py` · quick-win

```text
Repository: .
Task: add a paired test for `_practice.py`.
Location: src/maintainability_audit/_practice.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in tools/calibration/select_authored.py
`tools/calibration/select_authored.py` · quick-win

```text
Repository: .
Task: add a paired test for `select_authored.py`.
Location: tools/calibration/select_authored.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_html_report_sections.py
`src/maintainability_audit/_html_report_sections.py` · quick-win

```text
Repository: .
Task: add a paired test for `_html_report_sections.py`.
Location: src/maintainability_audit/_html_report_sections.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_finding_match.py
`src/maintainability_audit/_finding_match.py` · quick-win

```text
Repository: .
Task: add a paired test for `_finding_match.py`.
Location: src/maintainability_audit/_finding_match.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_skill_install.py
`src/maintainability_audit/_skill_install.py` · quick-win

```text
Repository: .
Task: add a paired test for `_skill_install.py`.
Location: src/maintainability_audit/_skill_install.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/renderers.py
`src/maintainability_audit/renderers.py` · quick-win

```text
Repository: .
Task: add a paired test for `renderers.py`.
Location: src/maintainability_audit/renderers.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in tools/calibration/measure_cohorts.py
`tools/calibration/measure_cohorts.py` · quick-win

```text
Repository: .
Task: add a paired test for `measure_cohorts.py`.
Location: tools/calibration/measure_cohorts.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_aspects.py
`src/maintainability_audit/_aspects.py` · quick-win

```text
Repository: .
Task: add a paired test for `_aspects.py`.
Location: src/maintainability_audit/_aspects.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_charts.py
`src/maintainability_audit/_charts.py` · quick-win

```text
Repository: .
Task: add a paired test for `_charts.py`.
Location: src/maintainability_audit/_charts.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_precommit.py
`src/maintainability_audit/_precommit.py` · quick-win

```text
Repository: .
Task: add a paired test for `_precommit.py`.
Location: src/maintainability_audit/_precommit.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_documents.py
`src/maintainability_audit/_documents.py` · quick-win

```text
Repository: .
Task: add a paired test for `_documents.py`.
Location: src/maintainability_audit/_documents.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_generic.py
`src/maintainability_audit/_generic.py` · quick-win

```text
Repository: .
Task: add a paired test for `_generic.py`.
Location: src/maintainability_audit/_generic.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in tools/calibration/measure_fix_breadth.py
`tools/calibration/measure_fix_breadth.py` · quick-win

```text
Repository: .
Task: add a paired test for `measure_fix_breadth.py`.
Location: tools/calibration/measure_fix_breadth.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_cognitive.py
`src/maintainability_audit/_cognitive.py` · quick-win

```text
Repository: .
Task: add a paired test for `_cognitive.py`.
Location: src/maintainability_audit/_cognitive.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_derive.py
`src/maintainability_audit/_derive.py` · quick-win

```text
Repository: .
Task: add a paired test for `_derive.py`.
Location: src/maintainability_audit/_derive.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_first_run.py
`src/maintainability_audit/_first_run.py` · quick-win

```text
Repository: .
Task: add a paired test for `_first_run.py`.
Location: src/maintainability_audit/_first_run.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_ranges_cobol.py
`src/maintainability_audit/_ranges_cobol.py` · quick-win

```text
Repository: .
Task: add a paired test for `_ranges_cobol.py`.
Location: src/maintainability_audit/_ranges_cobol.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_ranges_core.py
`src/maintainability_audit/_ranges_core.py` · quick-win

```text
Repository: .
Task: add a paired test for `_ranges_core.py`.
Location: src/maintainability_audit/_ranges_core.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_in_loop.py
`src/maintainability_audit/_in_loop.py` · quick-win

```text
Repository: .
Task: add a paired test for `_in_loop.py`.
Location: src/maintainability_audit/_in_loop.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_safe_write.py
`src/maintainability_audit/_safe_write.py` · quick-win

```text
Repository: .
Task: add a paired test for `_safe_write.py`.
Location: src/maintainability_audit/_safe_write.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_hostile_prompt.py
`src/maintainability_audit/_hostile_prompt.py` · quick-win

```text
Repository: .
Task: add a paired test for `_hostile_prompt.py`.
Location: src/maintainability_audit/_hostile_prompt.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/metrics.py
`src/maintainability_audit/metrics.py` · quick-win

```text
Repository: .
Task: add a paired test for `metrics.py`.
Location: src/maintainability_audit/metrics.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_trends.py
`src/maintainability_audit/_trends.py` · quick-win

```text
Repository: .
Task: add a paired test for `_trends.py`.
Location: src/maintainability_audit/_trends.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_catalog.py
`src/maintainability_audit/_catalog.py` · quick-win

```text
Repository: .
Task: add a paired test for `_catalog.py`.
Location: src/maintainability_audit/_catalog.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_recurrence.py
`src/maintainability_audit/_recurrence.py` · quick-win

```text
Repository: .
Task: add a paired test for `_recurrence.py`.
Location: src/maintainability_audit/_recurrence.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired file in src/maintainability_audit/_test_commands.py
`src/maintainability_audit/_test_commands.py` · quick-win

```text
Repository: .
Task: add a paired test for `_test_commands.py`.
Location: src/maintainability_audit/_test_commands.py
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### near-duplicate declaration in src/maintainability_audit/_pressures.py
`src/maintainability_audit/_pressures.py:97` · major-project

```text
Repository: .
Task: remove the near-duplicate declaration.
Location: src/maintainability_audit/_pressures.py:97
Why: near-copies drift apart silently, which is worse than exact duplication; reconciling them requires deciding which behaviour was intended

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### near-duplicate declaration in src/maintainability_audit/_ranges_php.py
`src/maintainability_audit/_ranges_php.py:81` · major-project

```text
Repository: .
Task: remove the near-duplicate declaration.
Location: src/maintainability_audit/_ranges_php.py:81
Why: near-copies drift apart silently, which is worse than exact duplication; reconciling them requires deciding which behaviour was intended

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### near-duplicate declaration in src/maintainability_audit/_verdict_adapters.py
`src/maintainability_audit/_verdict_adapters.py:79` · major-project

```text
Repository: .
Task: remove the near-duplicate declaration.
Location: src/maintainability_audit/_verdict_adapters.py:79
Why: near-copies drift apart silently, which is worse than exact duplication; reconciling them requires deciding which behaviour was intended

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### near-duplicate declaration in src/maintainability_audit/_semantic_policy.py
`src/maintainability_audit/_semantic_policy.py:30` · major-project

```text
Repository: .
Task: remove the near-duplicate declaration.
Location: src/maintainability_audit/_semantic_policy.py:30
Why: near-copies drift apart silently, which is worse than exact duplication; reconciling them requires deciding which behaviour was intended

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unreferenced declaration in src/maintainability_audit/_pressures.py
`src/maintainability_audit/_pressures.py:263` · fill-in

```text
Repository: .
Task: remove the unreferenced declaration.
Location: src/maintainability_audit/_pressures.py:263
Why: unreachable code costs reading time and misleads a search, but deleting it is the cheapest change there is

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unreferenced declaration in src/maintainability_audit/_grant_ledger.py
`src/maintainability_audit/_grant_ledger.py:44` · fill-in

```text
Repository: .
Task: remove the unreferenced declaration.
Location: src/maintainability_audit/_grant_ledger.py:44
Why: unreachable code costs reading time and misleads a search, but deleting it is the cheapest change there is

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

## TDD-shaped tests

TDD-shaped tests: detected beside 6 of 142 production source files (path pairing). Constructs: pytest in 207 file(s), unittest in 1 file(s), describe_it in 14 file(s), parametrize in 72 file(s), given_when_then in 1 file(s).
Chronology is not measured. Effectiveness is unscored unless the operator opted into suite execution.

## Test Suite

- The operator opted in to running the repository's test command; it passed.
- Command: PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92
- Coverage: 95.4% line coverage

## Semantic Findings (ADR 003)

TypeScript semantic coverage: **unknown** — no recorded type analysis and no local type checker: semantic coverage for TypeScript is unknown. Absence of analysis is not absence of findings.

- **Design-review candidate**: `tests/fixtures/semantic_ts/src/operations.ts` — one operation-name set recurs across dispatch, capability and description roles. That is an observed symptom; the intended abstraction is not proven by this evidence. Review whether these operations should carry their own behavior and result types, and preserve operation-specific input and result types in any redesign.

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

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `types-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

11 of 366 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.c` | C | 1 |
| `.cpp` | C++ | 1 |
| `.cs` | C# | 1 |
| `.f90` | Fortran | 1 |
| `.go` | Go | 1 |
| `.js` | JavaScript | 1 |
| `.php` | PHP | 1 |
| `.rb` | Ruby | 1 |
| `.rs` | Rust | 1 |
| `.sh` | Shell | 1 |
| `.swift` | Swift | 1 |

Add these to `paths.include_extensions` and re-run to audit them.

## Analyzer Coverage

2 of 13 tools contributed — concerns `all`, depth `moderate`, license policy `permissive`.

Plus 8 built-in detectors, which always run and whose measurements are single-source.

| Source | Tier | Outcome | Version | Measurements | Findings | Note |
|---|---|---|---|---|---|---|
| `eslint` | analyzer | not-applicable | — | — | — | reads javascript, jsx, typescript; this tree is Python, Shell, so it had nothing |
| `fortitude` | analyzer | not-applicable | — | — | — | reads fortran; this tree is Python, Shell, so it had nothing to examine |
| `complexipy` | analyzer | not-installed | — | — | — | complexipy is not installed or not on PATH |
| `interrogate` | analyzer | not-installed | — | — | — | interrogate is not installed or not on PATH |
| `lizard` | analyzer | not-installed | — | — | — | lizard is not installed or not on PATH |
| `multimetric` | analyzer | not-installed | — | — | — | multimetric is not installed or not on PATH |
| `mypy` | analyzer | not-installed | — | — | — | mypy is not installed or not on PATH |
| `pydocstyle` | analyzer | not-installed | — | — | — | pydocstyle is not installed or not on PATH |
| `radon` | analyzer | not-installed | — | — | — | radon is not installed or not on PATH |
| `ruff` | analyzer | not-installed | — | — | — | ruff is not installed or not on PATH |
| `vulture` | analyzer | not-installed | — | — | — | vulture is not installed or not on PATH |
| `jscpd` | analyzer | ran | cpd 5.1.1 | 1 | 135 |  |
| `pmd` | analyzer | ran | PMD 7.26.0 (8fd38edf285a33e1164f66205ebe243441db9557, 2026-06-29T08:22:36Z) | 0 | 0 |  |
| `competing-libraries` | built-in | ran | — | 476 | 0 | two libraries doing one job; no adapter emits idioms |
| `dead-code` | built-in | ran | — | 3614 | 2 | vulture, ruff and eslint cover this |
| `declaration-size` | built-in | ran | — | 3614 | 83 | lizard and complexipy cover these; the only source when neither runs |
| `duplicate-blocks` | built-in | ran | — | 476 | 0 | jscpd covers this; the only source when Node is unavailable |
| `file-size` | built-in | ran | — | 476 | 149 | per-file line counts; no adapter emits file_lines |
| `history` | built-in | ran | — | 473 | 54 | git history; no adapter emits churn, coupling or ownership |
| `near-duplicates` | built-in | ran | — | 3614 | 4 | token-shingle near-matches, which jscpd's exact-block scan misses |
| `risk-patterns` | built-in | ran | — | 476 | 0 | regex policy from this repository's own config; nothing external can hold a proj |

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
| duplication | 1 | jscpd | single source | 1.26 | 1.26 | 1.26 | 1.26 |

*The analyzers ran but measured none of the dimensions the rubric scores, so the estimate comes from the built-in detectors. Treat an analyzer finding as evidence about the code, never as a change to the score.*

## Analyzer Findings

135 findings from external analyzers — 135 duplication.

| File | Line | Concern | Tool | Rule | Finding |
|---|---|---|---|---|---|
| `.github/workflows/quality-gates.yml` | 52 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 208 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 312 | duplication | `jscpd` | — | 9 duplicated lines |
| `README.md` | 143 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 143 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 143 | duplication | `jscpd` | — | 7 duplicated lines |
| `docs/cli.md` | 76 | duplication | `jscpd` | — | 11 duplicated lines |
| `docs/pr-and-baseline-workflows.md` | 38 | duplication | `jscpd` | — | 9 duplicated lines |
| `docs/standard.md` | 227 | duplication | `jscpd` | — | 7 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 127 | duplication | `jscpd` | — | 44 duplicated lines |
| `skills/maintainability-agent/SKILL.md` | 174 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_adapters.py` | 302 | duplication | `jscpd` | — | 7 duplicated lines |
| `src/maintainability_audit/_generic.py` | 146 | duplication | `jscpd` | — | 9 duplicated lines |
| `src/maintainability_audit/_html_report_sections.py` | 183 | duplication | `jscpd` | — | 8 duplicated lines |
| `src/maintainability_audit/_jvm_adapters.py` | 79 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_mcp_audit.py` | 157 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_ranges_php.py` | 87 | duplication | `jscpd` | — | 8 duplicated lines |
| `src/maintainability_audit/_ranges_php.py` | 94 | duplication | `jscpd` | — | 14 duplicated lines |
| `src/maintainability_audit/_recurrence.py` | 3 | duplication | `jscpd` | — | 9 duplicated lines |
| `src/maintainability_audit/_verdict_adapters.py` | 76 | duplication | `jscpd` | — | 10 duplicated lines |
| `src/maintainability_audit/_work_order.py` | 72 | duplication | `jscpd` | — | 8 duplicated lines |
| `tests/_analyzer_fixtures.py` | 29 | duplication | `jscpd` | — | 7 duplicated lines |
| `tests/_mcp_fixtures.py` | 35 | duplication | `jscpd` | — | 18 duplicated lines |
| `tests/_mcp_fixtures.py` | 41 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/_mcp_fixtures.py` | 70 | duplication | `jscpd` | — | 10 duplicated lines |
| `tests/_scoring_fixtures.py` | 113 | duplication | `jscpd` | — | 8 duplicated lines |
| `tests/test_added_lines.py` | 33 | duplication | `jscpd` | — | 6 duplicated lines |
| `tests/test_analyzer_config_isolation.py` | 258 | duplication | `jscpd` | — | 10 duplicated lines |
| `tests/test_analyzer_estimate_claims.py` | 207 | duplication | `jscpd` | — | 14 duplicated lines |
| `tests/test_analyzer_estimate_claims.py` | 213 | duplication | `jscpd` | — | 10 duplicated lines |
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

Showing 40 of 135. The complete list is in the JSON report under `analyzer_findings`.

## Why the verified grade is not higher

- graded on the evidence floor 4.1 (point estimate 4.2, ceiling 4.3): unmeasured aspects price at 0 for the grade
- unpaired fail-band production unit: testability capped at 4.0

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 4.0 |
| reusability | 4.7 |
| analyzability | 4.3 |
| modifiability | 4.0 |
| testability | 4.0 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 4.0 |
| declaration size | 4.6 |
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
| test effectiveness | 4.8 |

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
| `src/maintainability_audit/_metric_adapters.py` | 500 | warn |
| `src/maintainability_audit/evidence.py` | 500 | warn |
| `src/maintainability_audit/prompts.py` | 500 | warn |
| `src/maintainability_audit/report.py` | 500 | warn |
| `tests/test_calibration_corpus.py` | 499 | warn |
| `src/maintainability_audit/scoring.py` | 497 | warn |
| `src/maintainability_audit/_work_order.py` | 496 | warn |
| `tests/test_evidence_properties.py` | 496 | warn |
| `tests/test_docs_links.py` | 494 | warn |
| `src/maintainability_audit/_adapters.py` | 492 | warn |
| `tests/test_written_record.py` | 492 | warn |
| `tests/test_adapters.py` | 491 | warn |
| `.github/workflows/quality-gates.yml` | 488 | warn |
| `tests/test_mcp_server.py` | 487 | warn |
| `src/maintainability_audit/_analysis.py` | 485 | warn |
| `tests/test_mcp_history.py` | 482 | warn |
| `src/maintainability_audit/_scan_history.py` | 480 | warn |
| `src/maintainability_audit/cli.py` | 480 | warn |
| `tests/test_grant_only_user_tier.py` | 475 | warn |
| `tools/prove_falsifiers.py` | 472 | warn |
| `tests/test_consumer_migration.py` | 470 | warn |
| `tests/test_analyzer_provenance_exclusions.py` | 464 | warn |
| `tests/test_first_run_elicitation.py` | 462 | warn |
| `src/maintainability_audit/_metrics_types.py` | 461 | warn |
| `tests/test_git_argv.py` | 461 | warn |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `src/maintainability_audit/_selection.py` | `select_runnable` | 58 | 79 | 15 | 20 | warn |
| `src/maintainability_audit/idioms.py` | `divergent_idioms` | 152 | 51 | 15 | 15 | warn |
| `tools/build_catalog.py` | `build` | 327 | 36 | 15 | 0 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 168 | 35 | 15 | 20 | warn |
| `src/maintainability_audit/_discovery.py` | `_asset_evidence` | 296 | 16 | 15 | 4 | warn |
| `src/maintainability_audit/_first_run.py` | `maybe_prompt_test_command` | 231 | 57 | 14 | 17 | warn |
| `src/maintainability_audit/_catalog.py` | `decide` | 183 | 52 | 14 | 13 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 288 | 51 | 14 | 3 | warn |
| `src/maintainability_audit/_html_report_sections.py` | `_pillars_section` | 173 | 49 | 14 | 12 | warn |
| `src/maintainability_audit/_scan_view.py` | `pillars_markdown` | 328 | 49 | 14 | 12 | warn |
| `src/maintainability_audit/_practice.py` | `practice_level` | 299 | 48 | 14 | 16 | warn |
| `tools/build_catalog.py` | `_entry` | 257 | 46 | 14 | 15 | warn |
| `src/maintainability_audit/_ranges_fortran.py` | `_fortran_end` | 138 | 45 | 14 | 23 | warn |
| `tests/_ast_reading.py` | `reachable_names` | 203 | 44 | 14 | 17 | warn |
| `src/maintainability_audit/metrics.py` | `hard_gate_failures` | 225 | 41 | 14 | 14 | warn |
| `src/maintainability_audit/_html_view.py` | `_chart_sections` | 191 | 39 | 14 | 4 | warn |
| `tests/test_identity_resolution.py` | `test_fail_on_new_uses_structured_matching_not_a_label_set_difference` | 278 | 33 | 14 | 13 | warn |
| `src/maintainability_audit/_in_loop_view.py` | `render_check` | 31 | 30 | 14 | 9 | warn |
| `src/maintainability_audit/_ranges_core.py` | `scan_bounded` | 207 | 78 | 13 | 19 | warn |
| `src/maintainability_audit/_skill_install.py` | `install_skill` | 48 | 67 | 13 | 13 | warn |
| `tests/test_git_argv.py` | `test_every_git_command_disables_gits_own_housekeeping` | 396 | 66 | 13 | 20 | warn |
| `tests/test_language_coverage.py` | `test_every_parsed_language_can_reach_a_complexity_analyzer` | 212 | 58 | 13 | 3 | warn |
| `tools/calibration/sampling_error.py` | `main` | 88 | 54 | 13 | 10 | warn |
| `src/maintainability_audit/prompts.py` | `prompt_work_order` | 177 | 53 | 13 | 11 | warn |
| `src/maintainability_audit/_metric_adapters.py` | `expand_files` | 46 | 47 | 13 | 6 | warn |
| `src/maintainability_audit/history.py` | `change_coupling` | 341 | 47 | 13 | 15 | warn |
| `tools/resolve_pool.py` | `main` | 65 | 46 | 13 | 12 | warn |
| `tests/test_authorship_gates.py` | `_step_scripts` | 41 | 42 | 13 | 23 | warn |
| `src/maintainability_audit/evidence.py` | `_check_relations` | 297 | 39 | 13 | 10 | warn |
| `tests/test_analysis_coverage.py` | `test_no_built_in_claims_to_be_unique_when_an_adapter_exists` | 302 | 36 | 13 | 2 | warn |
| `src/maintainability_audit/duplication.py` | `duplicate_blocks` | 50 | 35 | 13 | 10 | warn |
| `tests/test_ci_installs_the_analyzer_pool.py` | `_pip_installed_by_ci` | 73 | 35 | 13 | 15 | warn |
| `src/maintainability_audit/_documents.py` | `coverage_document` | 262 | 34 | 13 | 4 | warn |
| `src/maintainability_audit/_semantic_view.py` | `semantic_markdown` | 36 | 33 | 13 | 12 | warn |
| `src/maintainability_audit/_jvm_adapters.py` | `_finding_of` | 367 | 27 | 13 | 12 | warn |
| `tests/test_promises.py` | `_paths_the_audit_produced` | 129 | 25 | 13 | 20 | warn |
| `tests/test_first_run_elicitation.py` | `_preferred_for` | 255 | 18 | 13 | 14 | warn |
| `src/maintainability_audit/_analysis.py` | `analyze` | 274 | 79 | 12 | 5 | warn |
| `src/maintainability_audit/_runner.py` | `run` | 329 | 79 | 12 | 12 | warn |
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 12 | 8 | warn |
| `src/maintainability_audit/_masking.py` | `_mask_code` | 68 | 47 | 12 | 20 | warn |
| `src/maintainability_audit/_masking.py` | `mask_python_lines` | 399 | 46 | 12 | 22 | warn |
| `src/maintainability_audit/_ranges_js.py` | `js_declaration_ranges` | 202 | 38 | 12 | 24 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 225 | 66 | 11 | 6 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_masking.py` | `_blank_fstring_literals` | 353 | 44 | 11 | 18 | warn |
| `src/maintainability_audit/_work_order.py` | `_items_from_semantic` | 308 | 43 | 11 | 19 | warn |
| `tests/test_network_disclosure.py` | `test_no_module_imports_an_http_client` | 69 | 24 | 11 | 16 | warn |
| `src/maintainability_audit/_analysis.py` | `_attempt` | 398 | 80 | 10 | 12 | warn |
| `tests/test_verified_grade.py` | `test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor` | 254 | 80 | 10 | 0 | warn |

## Near-Duplicate Declarations

| Location | Declaration | Duplicates | Named | Similarity | Scope |
|---|---|---|---|---|---|
| `src/maintainability_audit/_verdict_adapters.py:79` | `_read` | `src/maintainability_audit/_verdict_adapters.py:144` | `_read` | 100% | same file |
| `src/maintainability_audit/_ranges_php.py:81` | `_qualify_methods` | `src/maintainability_audit/_ranges_rust.py:130` | `_qualify_impl_members` | 95% | cross-file |
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
| `src/maintainability_audit/config.py` | 66 | 960 | 74 | 2 | 4884 |
| `src/maintainability_audit/cli.py` | 33 | 2730 | 84 | 2 | 2772 |
| `tests/test_architecture.py` | 35 | 736 | 28 | 2 | 980 |
| `src/maintainability_audit/_masking.py` | 8 | 458 | 122 | 2 | 976 |
| `src/maintainability_audit/_mcp_audit.py` | 18 | 988 | 48 | 2 | 864 |
| `src/maintainability_audit/declarations.py` | 20 | 543 | 43 | 2 | 860 |
| `src/maintainability_audit/prompts.py` | 16 | 548 | 48 | 2 | 768 |
| `src/maintainability_audit/renderers.py` | 26 | 1222 | 26 | 2 | 676 |
| `src/maintainability_audit/_html_view.py` | 10 | 838 | 67 | 1 | 670 |
| `src/maintainability_audit/metrics.py` | 10 | 1119 | 67 | 2 | 670 |
| `tools/prove_falsifiers.py` | 9 | 724 | 65 | 1 | 585 |
| `src/maintainability_audit/scoring.py` | 13 | 1153 | 43 | 2 | 559 |
| `src/maintainability_audit/_mcp_setup.py` | 12 | 874 | 46 | 2 | 552 |
| `src/maintainability_audit/mcp_server.py` | 25 | 1809 | 21 | 2 | 525 |
| `src/maintainability_audit/_work_order.py` | 5 | 600 | 104 | 1 | 520 |
| `tests/test_first_run_elicitation.py` | 8 | 810 | 65 | 1 | 520 |
| `src/maintainability_audit/_analysis.py` | 13 | 855 | 39 | 2 | 507 |
| `tests/test_written_record.py` | 12 | 590 | 42 | 2 | 504 |
| `src/maintainability_audit/_verdict_adapters.py` | 11 | 847 | 41 | 1 | 451 |
| `src/maintainability_audit/_discovery.py` | 6 | 654 | 74 | 1 | 444 |
| `tests/test_git_argv.py` | 9 | 683 | 48 | 1 | 432 |
| `tests/_ast_reading.py` | 6 | 368 | 63 | 1 | 378 |
| `src/maintainability_audit/report.py` | 24 | 718 | 15 | 2 | 360 |
| `src/maintainability_audit/_metric_adapters.py` | 6 | 544 | 59 | 2 | 354 |
| `src/maintainability_audit/_skill_install.py` | 6 | 543 | 58 | 1 | 348 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 40 | 98% |
| `README.md` | `src/maintainability_audit/config.py` | 36 | 59% |
| `README.md` | `src/maintainability_audit/__init__.py` | 32 | 78% |
| `README.md` | `docs/release-plan.md` | 30 | 60% |
| `docs/architecture.md` | `tests/test_architecture.py` | 29 | 97% |
| `docs/release-plan.md` | `src/maintainability_audit/config.py` | 27 | 54% |
| `docs/release-plan.md` | `src/maintainability_audit/__init__.py` | 26 | 63% |
| `docs/architecture.md` | `docs/release-plan.md` | 26 | 52% |
| `SECURITY.md` | `src/maintainability_audit/config.py` | 23 | 88% |
| `SECURITY.md` | `src/maintainability_audit/__init__.py` | 22 | 85% |
| `docs/architecture.md` | `docs/decisions.md` | 21 | 78% |
| `docs/architecture.md` | `src/maintainability_audit/cli.py` | 21 | 68% |
| `SECURITY.md` | `docs/release-plan.md` | 20 | 77% |
| `README.md` | `SECURITY.md` | 19 | 73% |
| `docs/cli.md` | `src/maintainability_audit/cli.py` | 16 | 84% |
| `docs/architecture.md` | `tests/_architecture_layers.py` | 15 | 100% |
| `docs/architecture.md` | `docs/cli.md` | 15 | 79% |
| `SECURITY.md` | `docs/architecture.md` | 15 | 58% |
| `README.md` | `tests/_architecture_layers.py` | 14 | 93% |
| `docs/architecture.md` | `src/maintainability_audit/mcp_server.py` | 14 | 64% |
| `docs/language-support.md` | `src/maintainability_audit/declarations.py` | 13 | 76% |
| `README.md` | `src/maintainability_audit/declarations.py` | 13 | 72% |
| `README.md` | `docs/roadmap.md` | 13 | 65% |
| `README.md` | `docs/language-support.md` | 12 | 71% |
| `docs/architecture.md` | `src/maintainability_audit/report.py` | 12 | 57% |


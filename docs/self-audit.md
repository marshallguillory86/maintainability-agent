<!--
Generated from the tree at commit 513978ebac2ba762c22ef0338b8d07d19155fec6. This is a **provenance record, not a promise of currency**: it
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

- Generated: 2026-09-17T05:30:08+00:00
- Commit: `513978ebac2ba762c22ef0338b8d07d19155fec6` · Branch: `docs/sync-with-the-build`
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
| Files scanned | 498 |
| File warnings | 3 |
| File failures | 0 |
| Function warnings | 77 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

## Trend

57 separate series. Scans either side of a break were produced by different instruments and cannot be compared, so they are reported apart rather than joined into one line. The current series is given in full; the earlier ones are summarized, because a reader deciding what to do today is acting on the instrument in use today.

**This series begins at a break:** the tool version changed, so scans before this point were produced by a different instrument and cannot be joined to those after it.

**Current series** — 1 scan, 2026-09-17T05:30:41Z to 2026-09-17T05:30:41Z.

- **Direction:** unknown — not computable from these scans.
- **Debt velocity:** 0 introduced, 0 cleared (unchanged).
- **Growth:** unknown.
- **Never cleared in this window:** 0 findings.

### Earlier series (56 series)

| Window | Scans | Direction | Change | Began at a break in |
|---|---|---|---|---|
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

Written by secure-code-agent 0.12.4 and reproduced as it wrote it. It is that tool's work order, not this one's: its findings are not re-ranked or merged into the maintainability work order above.

### Security work order

**69 to fix · 4 to review · 5098 suppression candidates.**

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

#### §FIX — patch these

##### 1. `B314` — Using xml.etree.ElementTree.fromstring to parse untrusted XML data is known to be vulnerab

`src/maintainability_audit/_xml.py:70`

```
69             )
70     return ElementTree.fromstring(payload)  # noqa: S314 - declarations refused above
```

Using xml.etree.ElementTree.fromstring to parse untrusted XML data is known to be vulnerable to XML attacks. Replace xml.etree.ElementTree.fromstring with its defusedxml equivalent function or make sure defusedxml.defuse_stdlib() is called
[CWE-20](https://cwe.mitre.org/data/definitions/20.html) (Top 25) · medium/high via `bandit`

##### 2. `B310` — Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often un

`tools/sonar_resolve.py:56`

```
55     request.add_header("Authorization", f"Basic {basic}")
56     with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
57         body = response.read().decode()
```

Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected.
[CWE-22](https://cwe.mitre.org/data/definitions/22.html) (Top 25) · A01:2021-Broken Access Control · medium/high via `bandit`

##### 3. `B310` — Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often un

`tools/sonar_resolve.py:109`

```
108     request.add_header("Authorization", f"Basic {basic}")
109     with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310 - fixed host
110         found = json.loads(response.read().decode()).get("issues") or []
```

Audit url open for permitted schemes. Allowing use of file:/ or custom schemes is often unexpected.
[CWE-22](https://cwe.mitre.org/data/definitions/22.html) (Top 25) · A01:2021-Broken Access Control · medium/high via `bandit`

##### 4. `B108` — Probable insecure usage of temp file/directory.

`tools/validation/run_sample.py:124`

```
123     parser = argparse.ArgumentParser()
124     parser.add_argument("--cache", default="/tmp/validation-cache")
125     parser.add_argument("--only", help="Run a single repository by name.")
```

Probable insecure usage of temp file/directory.
[CWE-377](https://cwe.mitre.org/data/definitions/377.html) · medium/medium via `bandit`

##### 5. `B404` — Consider possible security implications associated with the subprocess module.

`src/maintainability_audit/_backfill.py:29`

```
28 
29 import subprocess
30 from pathlib import Path
```

Consider possible security implications associated with the subprocess module.
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 6. `B607` — Starting a process with a partial executable path

`src/maintainability_audit/_backfill.py:51-69`

```
50     try:
51         result = subprocess.run(  # noqa: S603 - argv list, never a shell
52             # D71: this spawn is not `run_git`, and the sweep that was
… 18 more line(s) — open the file
```

Starting a process with a partial executable path
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 7. `B603` — subprocess call - check for execution of untrusted input.

`src/maintainability_audit/_backfill.py:51-69`

```
50     try:
51         result = subprocess.run(  # noqa: S603 - argv list, never a shell
52             # D71: this spawn is not `run_git`, and the sweep that was
… 18 more line(s) — open the file
```

subprocess call - check for execution of untrusted input.
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 8. `B405` — Using ElementTree to parse untrusted XML data is known to be vulnerable to XML attacks. Re

`src/maintainability_audit/_jvm_adapters.py:21`

```
20 from typing import Any
21 from xml.etree import ElementTree
22
```

Using ElementTree to parse untrusted XML data is known to be vulnerable to XML attacks. Replace ElementTree with the equivalent defusedxml package, or make sure defusedxml.defuse_stdlib() is called.
[CWE-20](https://cwe.mitre.org/data/definitions/20.html) (Top 25) · low/high via `bandit`

##### 9. `B404` — Consider possible security implications associated with the subprocess module.

`src/maintainability_audit/_runner.py:33`

```
32 import shutil
33 import subprocess
34 import sys
```

Consider possible security implications associated with the subprocess module.
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 10. `B603` — subprocess call - check for execution of untrusted input.

`src/maintainability_audit/_runner.py:243-248`

```
242     try:
243         completed = subprocess.run(  # noqa: S603 - argv list, never a shell
244             [npm, "config", "get", "registry"],
… 5 more line(s) — open the file
```

subprocess call - check for execution of untrusted input.
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 11. `B603` — subprocess call - check for execution of untrusted input.

`src/maintainability_audit/_runner.py:370-378`

```
369     try:
370         completed = subprocess.run(  # noqa: S603 - argv is built by adapters, never a shell string
371             argv,
… 8 more line(s) — open the file
```

subprocess call - check for execution of untrusted input.
[CWE-78](https://cwe.mitre.org/data/definitions/78.html) (Top 25) · A03:2021-Injection · low/high via `bandit`

##### 12. `B405` — Using ElementTree to parse untrusted XML data is known to be vulnerable to XML attacks. Re

`src/maintainability_audit/_xml.py:30`

```
29 from typing import Any
30 from xml.etree import ElementTree
31
```

Using ElementTree to parse untrusted XML data is known to be vulnerable to XML attacks. Replace ElementTree with the equivalent defusedxml package, or make sure defusedxml.defuse_stdlib() is called.
[CWE-20](https://cwe.mitre.org/data/definitions/20.html) (Top 25) · low/high via `bandit`

> **57 more in §FIX.** Fix this batch, re-run, and the next order carries the rest. All of them are in the JSON report.

#### §REVIEW — confirm before changing

Low-precision rules or low scanner confidence. **Check each is real before patching it.** If it is, fix it under the §FIX constraints. If it is not, emit a suppression candidate with the justification — that is a successful outcome for this tier.

1. `src/maintainability_audit/_masking.py:20` · `B105`  — Name heuristic, not a value check: it fires when an identifier looks credential-ish. Across the calibration corpus all 22 scored hits were non-credentials — `EMAIL_HOST_PASSWORD = ""` and `SECRET_KEY = ""` (empty defaults), `PASSWORD_FIELD = "password"` and `reset_url_token = "set-password"` (field names). The same rule does catch a real hardcoded credential, so it is demoted, not dropped.
2. `src/maintainability_audit/_masking.py:33` · `B105`  — Name heuristic, not a value check: it fires when an identifier looks credential-ish. Across the calibration corpus all 22 scored hits were non-credentials — `EMAIL_HOST_PASSWORD = ""` and `SECRET_KEY = ""` (empty defaults), `PASSWORD_FIELD = "password"` and `reset_url_token = "set-password"` (field names). The same rule does catch a real hardcoded credential, so it is demoted, not dropped.
3. `src/maintainability_audit/_masking.py:103` · `B105`  — Name heuristic, not a value check: it fires when an identifier looks credential-ish. Across the calibration corpus all 22 scored hits were non-credentials — `EMAIL_HOST_PASSWORD = ""` and `SECRET_KEY = ""` (empty defaults), `PASSWORD_FIELD = "password"` and `reset_url_token = "set-password"` (field names). The same rule does catch a real hardcoded credential, so it is demoted, not dropped.
4. `src/maintainability_audit/_masking.py:105` · `B105`  — Name heuristic, not a value check: it fires when an identifier looks credential-ish. Across the calibration corpus all 22 scored hits were non-credentials — `EMAIL_HOST_PASSWORD = ""` and `SECRET_KEY = ""` (empty defaults), `PASSWORD_FIELD = "password"` and `reset_url_token = "set-password"` (field names). The same rule does catch a real hardcoded credential, so it is demoted, not dropped.

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
| `B101` | 4595 | low | `tests/_ast_reading.py:94` |
| `B603` | 213 | low | `tests/_analyzer_fixtures.py:30` |
| `B607` | 183 | low | `tests/_analyzer_fixtures.py:30` |
| `B404` | 96 | low | `tests/_analyzer_fixtures.py:27` |
| `B405` | 1 | low | `tests/test_analyzer_xml_bounds.py:112` |
| `B105` | 1 | low | `tests/test_root_grants.py:263` |

A suppression covering one of these groups looks like:

```yaml
- rule_id: B108
  paths: ["*/tests/*"]
  reason: "state why this is deliberate, and what you checked"
  expires: "YYYY-MM-DD"
```

---

End of findings. Apply the patch protocol above per finding. Report each one in the summary block format.

## TDD-shaped tests

TDD-shaped tests: detected beside 126 of 153 production source files (path pairing). Constructs: pytest in 243 file(s), unittest in 1 file(s), describe_it in 16 file(s), parametrize in 85 file(s), given_when_then in 2 file(s).
Chronology is not measured. Effectiveness is unscored unless the operator opted into suite execution.

## Test Suite

- The operator opted in to running the repository's test command; it did not run (exit None).
- Command: PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-report=term-missing --cov-report=xml:coverage.xml --cov-fail-under=92
- Coverage: no coverage reported by the run
- Detail: opted in, but no test command is recorded in the user tier; the repository's documented command is not run on its own say-so

## Semantic Findings (ADR 003)

TypeScript semantic coverage: **unknown** — no recorded type analysis and no local type checker: semantic coverage for TypeScript is unknown. Absence of analysis is not absence of findings.

## Pillars

**Practice level 4 of 5** — CI holds a numeric quality gate.

| Pillar | Scope | Practice | Condition | Reading |
|---|---|---:|---:|---|
| readability | partial | 4 | 4.8 | healthy: enforced, and the code reflects it |
| maintainability | owned | 4 | 3.9 | healthy: enforced, and the code reflects it |
| efficiency | out-of-scope | 4 | — | not measured — see below |
| security | delegated | 5 | — | unverified: not graded — no gates.require_scanners is declared, so no scanner set was asserted to have run; findings: 4 medium, 69 low, 4 informational |
| testability | partial | 4 | 5.0 | healthy: enforced, and the code reflects it |

**Not measured here, and why:**

- **efficiency** — requires profiling, load testing and runtime telemetry, none of which a static pass produces; permanently out of scope rather than temporarily unmeasured
- **security** — secure-code-agent owns the security pillar: it runs the scanner floor, reports coverage as a separate axis, and withholds a grade when the evidence cannot support one

Enforcement found: `linter-config`, `recorded-decisions`, `lint-in-ci`, `types-in-ci`, `duplication-in-ci`, `coverage-gate`.

## Source Not Read

20 of 422 source files were not opened by this scan. Their extensions are absent from `paths.include_extensions`, so nothing below describes them.

| Extension | Language | Files |
|---|---|---|
| `.ts` | TypeScript | 9 |
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

11 of 13 tools contributed — concerns `all`, depth `moderate`, license policy `permissive`.

Plus 8 built-in detectors, which always run and whose measurements are single-source.

| Source | Tier | Outcome | Version | Measurements | Findings | Note |
|---|---|---|---|---|---|---|
| `eslint` | analyzer | not-applicable | — | — | — | reads javascript, jsx, typescript; this tree is Python, Shell, so it had nothing |
| `fortitude` | analyzer | not-applicable | — | — | — | reads fortran; this tree is Python, Shell, so it had nothing to examine |
| `complexipy` | analyzer | ran | 7.0.1 | 3850 | 0 |  |
| `interrogate` | analyzer | ran | interrogate, version 1.7.0 | 1 | 0 |  |
| `jscpd` | analyzer | ran | cpd 5.1.1 | 1 | 138 |  |
| `lizard` | analyzer | ran | 1.24.0 | 12351 | 0 |  |
| `multimetric` | analyzer | ran | multimetric 2.4.4 | 1700 | 0 |  |
| `mypy` | analyzer | ran | mypy 2.3.1 (compiled: yes) | 0 | 0 |  |
| `pmd` | analyzer | ran | PMD 7.26.0 (8fd38edf285a33e1164f66205ebe243441db9557, 2026-06-29T08:22:36Z) | 0 | 0 |  |
| `pydocstyle` | analyzer | ran | 6.3.0 | 0 | 561 |  |
| `radon` | analyzer | ran | 6.0.1 | 404 | 0 |  |
| `ruff` | analyzer | ran | ruff 0.16.5 | 0 | 1 |  |
| `vulture` | analyzer | ran | vulture 2.16 | 0 | 3 |  |
| `competing-libraries` | built-in | ran | — | 498 | 0 | two libraries doing one job; no adapter emits idioms |
| `dead-code` | built-in | ran | — | 4082 | 0 | vulture, ruff and eslint cover this |
| `declaration-size` | built-in | ran | — | 4082 | 77 | lizard and complexipy cover these; the only source when neither runs |
| `duplicate-blocks` | built-in | ran | — | 498 | 0 | jscpd covers this; the only source when Node is unavailable |
| `file-size` | built-in | ran | — | 498 | 3 | per-file line counts; no adapter emits file_lines |
| `history` | built-in | ran | — | 497 | 70 | git history; no adapter emits churn, coupling or ownership |
| `near-duplicates` | built-in | ran | — | 4082 | 0 | token-shingle near-matches, which jscpd's exact-block scan misses |
| `risk-patterns` | built-in | ran | — | 498 | 0 | regex policy from this repository's own config; nothing external can hold a proj |

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
| cognitive_complexity | 3850 | complexipy | single source | 0.0 | 1.0 | 6.0 | 34.0 |
| cyclomatic_complexity | 4117 | lizard | single source | 1.0 | 2.0 | 6.0 | 27.0 |
| declaration_lines | 4117 | lizard | single source | 1.0 | 13.0 | 33.0 | 80.0 |
| documentation | 426 | interrogate, multimetric | no shared units | 0.0 | 37.3 | 57.34 | 92.26 |
| duplication | 1 | jscpd | single source | 1.16 | 1.16 | 1.16 | 1.16 |
| file_cyclomatic_complexity | 425 | multimetric | single source | 0.0 | 2.0 | 27.0 | 77.0 |
| halstead_difficulty | 425 | multimetric | single source | 0.67 | 52.06 | 98.5 | 164.54 |
| maintainability_index | 425 | multimetric, radon | 38% | 19.23 | 55.07 | 73.52 | 135.29 |
| parameters | 4117 | lizard | single source | 0.0 | 1.0 | 2.0 | 18.0 |

Where two tools measured the same thing, their disagreement is shown rather than averaged away — it is the uncertainty a single-tool number hides.

*The maintainability estimate uses the analyzer readings for declarations (completed by built-in detectors) — external tools are the primary evidence there. Dimensions no analyzer measured kept the fallback tier. Where the two sources disagree the range widens to contain both; they are never averaged.*

## Analyzer Findings

703 findings from external analyzers — 3 dead-code, 561 documentation, 138 duplication, 1 style.

| File | Line | Concern | Tool | Rule | Finding |
|---|---|---|---|---|---|
| `.github/workflows/quality-gates.yml` | 75 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 138 | duplication | `jscpd` | — | 9 duplicated lines |
| `.github/workflows/quality-gates.yml` | 250 | duplication | `jscpd` | — | 9 duplicated lines |
| `README.md` | 193 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 193 | duplication | `jscpd` | — | 6 duplicated lines |
| `README.md` | 193 | duplication | `jscpd` | — | 7 duplicated lines |
| `docs/cli.md` | 77 | duplication | `jscpd` | — | 11 duplicated lines |
| `docs/pr-and-baseline-workflows.md` | 38 | duplication | `jscpd` | — | 9 duplicated lines |
| `docs/standard.md` | 248 | duplication | `jscpd` | — | 7 duplicated lines |
| `examples/demo/billing.py` | 89 | documentation | `pydocstyle` | D401 | First line should be in imperative mood; try rephrasing (found 'The') |
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

Showing 40 of 703. The complete list is in the JSON report under `analyzer_findings`.

## Why the verified grade is not higher

- graded on the evidence floor 4.1 (point estimate 4.4, ceiling 4.7): unmeasured aspects price at 0 for the grade

## ISO/IEC 25010 Maintainability Score

| Category | Score |
|---|---|
| modularity | 3.9 |
| reusability | 4.9 |
| analyzability | 4.4 |
| modifiability | 3.8 |
| testability | 4.8 |

## Aspect Scores

| Aspect | Score |
|---|---|
| file size | 4.5 |
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
| change coupling | 2.0 |
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
| `src/maintainability_audit/_work_order.py` | 666 | warn |
| `src/maintainability_audit/_scan_history.py` | 624 | warn |
| `tests/test_operator_named_reads.py` | 613 | warn |
| `.github/workflows/quality-gates.yml` | 590 | ok |
| `src/maintainability_audit/_prompt_sections.py` | 569 | ok |
| `src/maintainability_audit/_discovery.py` | 553 | ok |
| `src/maintainability_audit/cli.py` | 549 | ok |
| `src/maintainability_audit/report.py` | 538 | ok |
| `tests/test_docs_links.py` | 524 | ok |
| `tests/test_mcp_server.py` | 520 | ok |
| `README.md` | 506 | ok |
| `tools/prove_falsifiers.py` | 500 | ok |
| `src/maintainability_audit/scoring.py` | 499 | ok |
| `tests/test_calibration_corpus.py` | 499 | ok |
| `src/maintainability_audit/_mcp_audit.py` | 497 | ok |
| `src/maintainability_audit/mcp_server.py` | 497 | ok |
| `tests/test_evidence_properties.py` | 496 | ok |
| `src/maintainability_audit/_adapters.py` | 492 | ok |
| `tests/test_adapters.py` | 491 | ok |
| `tests/test_mcp_history.py` | 486 | ok |
| `src/maintainability_audit/_analysis.py` | 485 | ok |
| `src/maintainability_audit/_masking.py` | 476 | ok |
| `tests/test_grant_only_user_tier.py` | 475 | ok |
| `src/maintainability_audit/_metrics_types.py` | 472 | ok |
| `tests/test_consumer_migration.py` | 471 | ok |

## Function Hotspots

| File | Declaration | Line | Lines | Complexity | Cognitive | Status |
|---|---|---|---|---|---|---|
| `tools/build_catalog.py` | `build` | 327 | 36 | 15 | 0 | warn |
| `tests/test_docs_links.py` | `test_no_markdown_table_is_split_by_prose` | 198 | 35 | 15 | 20 | warn |
| `src/maintainability_audit/history.py` | `history_section` | 298 | 51 | 14 | 3 | warn |
| `tools/build_catalog.py` | `_entry` | 257 | 46 | 14 | 15 | warn |
| `tests/_ast_reading.py` | `reachable_names` | 203 | 44 | 14 | 17 | warn |
| `src/maintainability_audit/_html_view.py` | `_chart_sections` | 196 | 39 | 14 | 4 | warn |
| `tests/test_identity_resolution.py` | `test_fail_on_new_uses_structured_matching_not_a_label_set_difference` | 278 | 33 | 14 | 13 | warn |
| `src/maintainability_audit/_ranges_core.py` | `scan_bounded` | 207 | 78 | 13 | 19 | warn |
| `src/maintainability_audit/_skill_install.py` | `install_skill` | 48 | 67 | 13 | 13 | warn |
| `tests/test_git_argv.py` | `test_every_git_command_disables_gits_own_housekeeping` | 396 | 66 | 13 | 20 | warn |
| `tests/test_language_coverage.py` | `test_every_parsed_language_can_reach_a_complexity_analyzer` | 212 | 58 | 13 | 3 | warn |
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
| `src/maintainability_audit/_runner.py` | `run` | 356 | 79 | 12 | 12 | warn |
| `tools/calibration/measure_cohorts.py` | `main` | 251 | 67 | 12 | 8 | warn |
| `tests/test_platform_claim.py` | `test_the_macos_runner_actually_runs_the_suite` | 174 | 61 | 12 | 8 | warn |
| `src/maintainability_audit/_masking.py` | `_mask_code` | 68 | 47 | 12 | 20 | warn |
| `src/maintainability_audit/_ranges_js.py` | `js_declaration_ranges` | 202 | 38 | 12 | 24 | warn |
| `src/maintainability_audit/_test_execution.py` | `run_test_suite` | 133 | 66 | 11 | 11 | warn |
| `tools/calibration/measure_fix_breadth.py` | `main` | 225 | 66 | 11 | 6 | warn |
| `src/maintainability_audit/_prompt_sections.py` | `prompt_work_order` | 237 | 55 | 11 | 20 | warn |
| `tests/test_finding_identity.py` | `test_no_module_hardcodes_an_ordinal` | 301 | 47 | 11 | 19 | warn |
| `src/maintainability_audit/_masking.py` | `_blank_fstring_literals` | 353 | 44 | 11 | 18 | warn |
| `src/maintainability_audit/_ranges_fortran.py` | `_fortran_end` | 163 | 38 | 11 | 16 | warn |
| `tests/test_network_disclosure.py` | `test_no_module_imports_an_http_client` | 69 | 24 | 11 | 16 | warn |
| `src/maintainability_audit/_analysis.py` | `_attempt` | 398 | 80 | 10 | 12 | warn |
| `tests/test_verified_grade.py` | `test_not_applicable_rollup_is_the_only_change_to_the_pre_stage_five_anchor` | 255 | 80 | 10 | 0 | warn |
| `src/maintainability_audit/_mcp_audit.py` | `audit_repository` | 179 | 74 | 10 | 11 | warn |
| `src/maintainability_audit/scoring.py` | `_score_document` | 433 | 67 | 10 | 13 | warn |
| `tests/test_written_record.py` | `test_no_document_says_a_register_entry_is_open_that_the_register_closed` | 343 | 45 | 10 | 16 | warn |
| `tests/test_anticipated_refusals.py` | `_named_exceptions` | 95 | 26 | 10 | 16 | warn |
| `src/maintainability_audit/report.py` | `build_report` | 459 | 80 | 9 | 3 | warn |
| `src/maintainability_audit/_prompt_sections.py` | `prompt_pressure_section` | 318 | 66 | 9 | 5 | warn |
| `tests/test_docs_links.py` | `test_every_internal_link_resolves_to_a_file_and_an_anchor` | 82 | 16 | 9 | 17 | warn |
| `tests/test_release_plan.py` | `test_the_release_plan_table_is_measured_not_remembered` | 27 | 68 | 8 | 2 | warn |
| `tools/calibration/verify_corpus.py` | `main` | 100 | 74 | 7 | 7 | warn |
| `tests/test_determinism.py` | `test_the_history_window_is_disclosed_as_clock_relative` | 230 | 71 | 7 | 4 | warn |

## Hotspots — churn x cognitive complexity (12 months ago)

| File | Commits | Lines +/- | Cognitive | Authors | Score |
|---|---|---|---|---|---|
| `src/maintainability_audit/config.py` | 89 | 1137 | 78 | 2 | 6942 |
| `src/maintainability_audit/cli.py` | 37 | 2839 | 86 | 2 | 3182 |
| `src/maintainability_audit/_work_order.py` | 11 | 874 | 120 | 1 | 1320 |
| `src/maintainability_audit/_mcp_audit.py` | 23 | 1041 | 51 | 2 | 1173 |
| `src/maintainability_audit/metrics.py` | 14 | 1261 | 79 | 2 | 1106 |
| `src/maintainability_audit/report.py` | 32 | 960 | 31 | 2 | 992 |
| `tests/test_architecture.py` | 35 | 736 | 28 | 2 | 980 |
| `src/maintainability_audit/_html_view.py` | 14 | 863 | 68 | 1 | 952 |
| `src/maintainability_audit/_masking.py` | 7 | 490 | 120 | 2 | 840 |
| `src/maintainability_audit/renderers.py` | 31 | 1327 | 27 | 2 | 837 |
| `src/maintainability_audit/mcp_server.py` | 29 | 1894 | 28 | 2 | 812 |
| `tools/prove_falsifiers.py` | 11 | 758 | 66 | 1 | 726 |
| `src/maintainability_audit/declarations.py` | 16 | 539 | 43 | 2 | 688 |
| `src/maintainability_audit/scoring.py` | 16 | 1179 | 43 | 2 | 688 |
| `src/maintainability_audit/_discovery.py` | 8 | 815 | 85 | 1 | 680 |
| `tests/test_first_run_elicitation.py` | 10 | 816 | 65 | 1 | 650 |
| `src/maintainability_audit/_scan_history.py` | 12 | 768 | 54 | 2 | 648 |
| `src/maintainability_audit/_prompt_sections.py` | 8 | 625 | 78 | 1 | 624 |
| `src/maintainability_audit/_mcp_setup.py` | 13 | 879 | 46 | 2 | 598 |
| `src/maintainability_audit/_analysis.py` | 14 | 857 | 39 | 2 | 546 |
| `src/maintainability_audit/_ranges_core.py` | 7 | 334 | 75 | 1 | 525 |
| `src/maintainability_audit/_scan_view.py` | 9 | 715 | 56 | 1 | 504 |
| `tests/test_written_record.py` | 14 | 830 | 36 | 2 | 504 |
| `src/maintainability_audit/_verdict_adapters.py` | 12 | 933 | 37 | 1 | 444 |
| `tools/calibration/measure.py` | 7 | 534 | 63 | 2 | 441 |

## Change Coupling — files that keep changing together

| File | Changes with | Co-changes | Confidence |
|---|---|---|---|
| `src/maintainability_audit/__init__.py` | `src/maintainability_audit/config.py` | 58 | 98% |
| `README.md` | `src/maintainability_audit/config.py` | 56 | 69% |
| `README.md` | `src/maintainability_audit/__init__.py` | 51 | 86% |
| `README.md` | `docs/release-plan.md` | 50 | 69% |
| `docs/release-plan.md` | `src/maintainability_audit/config.py` | 45 | 62% |
| `docs/release-plan.md` | `src/maintainability_audit/__init__.py` | 44 | 75% |
| `docs/architecture.md` | `tests/test_architecture.py` | 29 | 97% |
| `SECURITY.md` | `src/maintainability_audit/config.py` | 29 | 91% |
| `SECURITY.md` | `src/maintainability_audit/__init__.py` | 28 | 88% |
| `README.md` | `SECURITY.md` | 26 | 81% |
| `SECURITY.md` | `docs/release-plan.md` | 26 | 81% |
| `docs/architecture.md` | `docs/decisions.md` | 24 | 80% |
| `docs/architecture.md` | `src/maintainability_audit/cli.py` | 22 | 67% |
| `README.md` | `docs/roadmap.md` | 22 | 65% |
| `docs/cli.md` | `src/maintainability_audit/cli.py` | 18 | 82% |
| `docs/architecture.md` | `docs/cli.md` | 17 | 77% |
| `docs/architecture.md` | `src/maintainability_audit/mcp_server.py` | 16 | 62% |
| `README.md` | `src/maintainability_audit/renderers.py` | 16 | 57% |
| `SECURITY.md` | `docs/architecture.md` | 16 | 50% |
| `docs/architecture.md` | `tests/_architecture_layers.py` | 15 | 100% |
| `docs/architecture.md` | `src/maintainability_audit/report.py` | 15 | 54% |
| `docs/decisions.md` | `docs/release-plan.md` | 15 | 50% |
| `README.md` | `tests/_architecture_layers.py` | 14 | 93% |
| `src/maintainability_audit/config.py` | `tests/_architecture_layers.py` | 13 | 87% |
| `README.md` | `docs/cli.md` | 13 | 59% |


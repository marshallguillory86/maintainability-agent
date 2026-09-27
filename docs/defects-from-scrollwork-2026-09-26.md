# Defects found auditing Scrollwork, 2026-09-26

Version 1.1.0 · 2026-09-27 · Filed by Claude, for Marshall, from a real audit
of `scrollworkapp` (maintainability-agent 3.9.0, secure-code-agent 0.12.9).
Both are triaged and closed: **D214** and **D215** in
`defect-register-chat-surface.md`, each with a failing test written first.

---

## 1. The consented test command is one per person, so it runs in every repository

**Seen.** Scrollwork's audit ran `pytest -n auto --cov=maintainability_audit
--cov-report=xml:coverage.xml -q` -- this repository's own suite -- against a
JavaScript and Python tree it has nothing to do with. pytest exited 5 (no tests
collected), coverage said "no data was collected", and `test_effectiveness`
went unscored. The report said so in one line under *Test Suite*; nothing
flagged the command as belonging to another repository.

**Why.** D147/D152 moved the choice of program to the person's tier, correctly:
the tree may say how it is tested, only the person chooses what this host runs.
But `~/.config/maintainability-agent/config.json` holds a single
`expected_commands.test`. Consent given while setting up one repository is
therefore consent for every repository the person later audits, and it runs a
program chosen for somewhere else.

**Population.** Every person who opts into suite execution and audits more than
one repository. The second repository onward runs the first one's command.

**Expected.** The consented command is keyed by repository (root path or
remote), so a repository with no consent of its own asks, rather than
inheriting. Or, at the least, the run reports that the command it executed was
consented for a different repository and scores nothing from it.

**Also.** Coverage is read only from `coverage.xml`. Scrollwork measures with
V8 (`node scripts/coverage.mjs`) and has no Cobertura output, so even a correct
command would leave `test_effectiveness` unscored. Worth deciding whether lcov
or V8 JSON is read too, or saying in the report that the format was the reason.

**Closing test (suggested).** Two repositories, consent given in the first; an
audit of the second must not spawn the first's command.

---

## 2. `acceptance/` is not recognised as a test directory

**Seen.** Scrollwork's behaviour tests live in `acceptance/<suite>/run.mjs`,
more than sixty suites that import and drive the production handlers. The audit
treats every one of them as production code:

- 18 of 25 duplicate blocks, all 25 near-duplicates, and most of the oversized
  files and declarations it reported are in `acceptance/`;
- 106 `unpaired-hotspot` findings, and `test_presence` at 2.5, although
  `functions/` is covered at 98% by those same suites.

So the audit both over-reports production debt and under-reports testing, from
one misclassification.

**Why.** `_discovery._is_test` accepts `is_test_path` plus a directory segment in
`TEST_DIRECTORY_NAMES = {"testing", "tests", "test", "__tests__", "spec",
"specs"}`. `acceptance` is not there, and a file named `run.mjs` does not look
like a test either, so import-based pairing never sees these as tests.

**Population.** Any repository whose behaviour tests use a conventional name
outside that set: `acceptance/`, `e2e/`, `integration/`, `features/`
(Cucumber), `cypress/`, `playwright/`. Probably common.

**Expected.** Either widen the set to the common names, or let the repository
declare its test roots in `maintainability-agent.json` (`paths.test_roots`),
and report which roots were used. Declaring is the more honest of the two: a
name list will always miss someone's convention, and it fails in the
flattering-to-no-one direction here (worse debt, worse testing).

**Closing test (suggested).** A fixture tree with `acceptance/x/run.mjs`
importing `src/handler.js`: the handler is paired, and the suite's size and
duplication are not graded as production code.

---

## Resolution

**1 → D214.** Consent is keyed by repository (resolved root path). The coverage-format
question under *Also* is not decided: only `coverage.xml` is read, and whether lcov or V8
JSON is read too is open.

**2 → D215.** Decided 2026-09-27: widen the name list with the unambiguous names —
`acceptance`, `e2e`, `cypress`, `playwright` — rather than add `paths.test_roots`.
`integration` and `features` stay out, as ordinary production names.

## Changelog

1.1.0 Resolved as D214 and D215; the test-roots decision recorded.

1.0.0 Filed: the per-person test command, and `acceptance/` as tests.

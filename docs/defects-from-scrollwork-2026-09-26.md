# Defects found auditing Scrollwork, 2026-09-26

Version 1.4.0 · 2026-09-27 · Filed from a real audit
of `scrollworkapp` (maintainability-agent 3.9.0, secure-code-agent 0.12.9).
1 and 2 are closed as **D214** and **D215** in `defect-register-chat-surface.md`,
each with a failing test written first. 3 and 4 are decided, below, and not yet built.

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

---

## 3. The report could not be delivered on the chat door

**Seen.** First run, `audit_repository {action: "run", format: "html"}`,
2026-09-27 00:03Z. Claude Code refused the result: *"result (308,957
characters) exceeds maximum allowed tokens"*. The payload carried
`report_html` inline (257,306 characters) beside `report_markdown`, the
security work order and the remediation prompt, and no path. MA writes no
report file, by design, so nothing was delivered: Claude extracted the HTML
from the host's overflow file with `jq` and wrote it by hand.

**Why.** An inline report is bounded by the host's result limit, and an HTML
report of a real repository is far past it. Asking for `html` does not drop
the other skins, so the payload is larger than the one report asked for.

**Population.** Every chat-door user who chooses `html` on a repository of
any size; very likely `markdown` on large ones.

**Expected.** Not decided. Writing a file is outside the six local artifacts
the MCP server may write, so either that list gains an operator-chosen report
path, or the payload carries only the chosen skin, bounded, with the full
report behind a resource. A product decision before a fix.

---

## 4. The chat door and the terminal decide "first run" differently

**Seen, from the code (no terminal transcript of the Scrollwork run exists).**
The chat door asked no setup question on Scrollwork, which had no
`maintainability-agent.json`: `_mcp_setup.setup_pending` counts a repository
as configured when the person's tier exists, which the help page documents.
The terminal asks whenever the repository file is absent
(`_first_run.maybe_prompt_first_run`), whatever the person's tier holds.

The terminal also asks a subset. Six questions, not seven: the presentation
is asked on every run and never recorded. The staged follow-ups — the three
labor rates and the test command — read the merged configuration, so a person
whose tier already holds them is never asked them for a new repository, even
after answering *include* or *yes*.

**Why it matters.** `docs/help/first-run.md`: *"Chat, MCP, and an interactive
CLI TTY are one setup: the same questions … A surface that asks a subset is a
bug."* Two doors, two answers to "has this repository been set up".

**Expected.** Not decided: which rule is the product's — the person's answers
carry to every new repository (the chat door today), or a new repository is
asked (the terminal today). Either way one rule, both doors, and the
questions that are repository-specific — the test command, which D214 made
per repository — asked for every new one.

---

## 5. Smaller, from the same run

- The markdown report is titled "Maintainability CI Report" on the chat door.
- Running another repository's test command left an untracked `.coverage` in
  Scrollwork's tree, outside the six declared artifacts (a consequence of
  D214, now closed; inferred rather than proven to be the source).

## Resolution

**1 → D214.** Consent is keyed by repository (resolved root path). The coverage-format
question under *Also* is not decided: only `coverage.xml` is read, and whether lcov or V8
JSON is read too is open.

**2 → D215.** Decided 2026-09-27: widen the name list rather than add
`paths.test_roots`, with `acceptance` and `e2e` only. `cypress` and `playwright`
were proposed on the claim that they are unambiguous, and withdrawn when an
audit showed they are production code in their own projects and that
microsoft/playwright is in the calibration corpus. `testing` stays a
discovery-only name until the next recalibration, for the same reason (lapack).
`integration` and `features` stay out, as ordinary production names.

**3. Decided 2026-09-27: MA writes the report to the path the person chose.**
`audit_repository` takes an output path the person named — the skill already
asks where to save — writes the chosen format there, and returns a short
summary and the path rather than the report inline. A seventh local artifact,
written only to a path the operator named.

**4. Decided 2026-09-27: carry the person's answers, ask what is the
repository's own.** On both doors, the person's answers — pool, depth,
license, rates, presentation, history — carry to a new repository. A new
repository is still asked what belongs to it: whether to run its test suite,
and its test command. It is told which carried answers apply, and that
reconfigure changes them.

## Changelog

1.4.0 D215 narrowed to `acceptance` and `e2e`.

1.3.0 Decisions recorded for 3 and 4.

1.2.0 Filed 3–5 from auditing MA's first run on Scrollwork.

1.1.0 Resolved as D214 and D215; the test-roots decision recorded.

1.0.0 Filed: the per-person test command, and `acceptance/` as tests.

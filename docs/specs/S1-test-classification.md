# S1 — Which files are tests

Version 0.1.0 · 2026-11-25 · Owner: Marshall Guillory · Status: **Draft** (written from the code, the closing tests and D238; not yet approved)

Changelog: 0.1.0 first draft. It states the rule `is_test_path` applies today, including the two Swift conventions added by D238, so that the rule is written down and not only in the code.

## 1. Purpose

A file is either test code or production code, and almost every score reads that split: test presence, testability, the pairing of tests to code, and the exclusion of test code from the declaration-size and duplication readings. A file read as the wrong kind makes a tested repository look untested (D238) or an untested one look tested. This specification is the one place the rule is stated.

## 2. Traces to

Product intent: [product-intent.md](../product-intent.md), the independent check that must not flatter the code it grades.
Decisions and defects: D238 (Swift tests read as production), the 2026-09-27 decision that a name which is also an ordinary production name stays out of the list, and D137 (a change that moves corpus readings rides a recalibration).
Code: `is_test_path` in `src/maintainability_audit/_metrics_types.py`; `_is_test` in `_discovery.py`, which reads it first.

## 3. Interface

`is_test_path(rel) -> bool` takes a path relative to the audited root and returns whether the file is test code. It reads the path only: no file is opened.

## 4. The rule

A path is a test when any of these holds.

1. **A test directory.** Any directory segment, compared lower-cased and whole, is one of `tests`, `test`, `__tests__`, `spec`, `specs`, `acceptance`, `e2e`.
2. **A test file name.** The lower-cased name starts with `test_` or `test.`, ends in `.pf`, or its stem ends in `_test`, `.test`, `.spec` or `_spec`.
3. **A Swift test file.** The file ends in `.swift` and its stem, in its original case, ends in `Tests` or `Test` with at least one character before it (`OrderTests.swift`, `OrderTest.swift`).
4. **An Xcode test target.** The file ends in `.swift` and a directory segment, in its original case, ends in `Tests` with at least one character before it (`MaccyTests/`, `Bible ReaderTests/`, `FooUITests/`).

Rules 3 and 4 are case-sensitive and `.swift`-only on purpose, so that `Contest.swift`, `Latest.swift`, a bare `Tests.swift`, a lower-case `attests/` folder, and a folder of Python files called `ApiTests/` stay production.

## 5. Acceptance criteria

1. WHEN a path matches rule 1, 2, 3 or 4, `is_test_path` SHALL return true.
2. WHEN a name merely resembles a test name (`integration`, `features`, `playwright`, `cypress`, `acceptance_rules.py`, `Contest.swift`), `is_test_path` SHALL return false.
3. WHEN `_discovery._is_test` and `is_test_path` are asked about the same path, they SHALL agree, except for the one declared discovery-only directory, `testing`.
4. WHEN a repository has an Xcode test target, the report's test file count SHALL count its `.swift` files, and test presence SHALL be read from them.

## 6. Invariants

- Adding a name to a list that is also an ordinary production name flatters the grade, which this project refuses; such a name is not added.
- A change to this rule moves the readings of every repository it newly classifies, including calibration-corpus repositories, so it ships with a recalibration and is not a patch.

## 7. Out of scope

Pairing a Swift test to the production file it covers. `.swift` is deliberately not in `PAIRABLE`: claiming a language there without teaching `subject_stem` its naming would report every Swift production file as untested. That is a separate decision.

## 8. Tests

`tests/test_swift_test_conventions.py` (criteria 1, 2 and 4), `tests/test_behaviour_suites_are_tests.py` (criteria 1 to 3 for `acceptance` and `e2e`).

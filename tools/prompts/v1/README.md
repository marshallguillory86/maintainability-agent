# 1.0 close — prompt pack

Not an audit. The 1.0 hostile pass already failed. These prompts *build*
the remaining product work. Verification is: the tests named in each
prompt pass, and the class lints they add stay green. Do not start a
new research audit until this pack is implemented.

Prompt index only. Scope lives in `docs/release-plan.md` and
`docs/product-intent.md`. Do not invent either here.

## Order — one class at a time

| # | Pair | Who | Exit |
|---|---|---|---|
| 01–02 | MCP (already landed) | Claude implemented | shipped |
| 03 | Close-out docs | Codex (doc editor) | shipped |
| 04 | 6.1 first-run TTY prompt | Claude implements against `tests/test_first_run_prompt.py` | those three tests green |

Do **02** only after **01** is on a branch and its tests pass. Do **03**
only after **02** is merged. Grok (or a human) checks the named tests
against the prompt. That *is* 7.5 for this class. It is not a new
inventory of the whole repo.

## House rules (every prompt)

- TDD. Tests that would fail on today's tree first.
- Close the class: a structural lint so the old "two tools only / no
  resources" contract cannot come back.
- File budget 500 lines, CCN 15, no drive-by parsers, no new language
  rangers, no installing tools, no `_bands` import.
- Java ranger stays. ADR 006 stays analyzer-primary.
- Grok audits. Claude implements. Codex writes tests or edits docs.
- Claude wrap-up: files / tests / still open.
- The line “Claude writes tests, Codex implements” was an invented split. It is revoked.
- Do not regenerate `docs/self-audit.md` except in **03**.

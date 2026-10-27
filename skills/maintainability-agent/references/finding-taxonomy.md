# Finding Taxonomy

Use this reference when deciding how to respond to maintainability-agent findings.

## Long Files

First decide whether the file is large because it owns a coherent module or because unrelated concerns accumulated there. Extract only when there is a natural boundary such as parsing, rendering, configuration loading, or report generation.

Do not split files just to reduce line count if the result hides related logic across weak helper modules.

## Long Functions

Prefer a small extraction when a block has a name a maintainer would recognize. Good extraction candidates include validation, normalization, rendering, filtering, and conversion steps.

Avoid helper functions named after mechanics such as `process_items_part_two`. If no clear name exists, simplify local branching before extracting.

## Complexity

Reduce complexity with guard clauses, table-driven decisions, or narrowly named helpers. Keep policy decisions visible near their inputs.

Do not replace straightforward conditionals with clever dispatch maps unless the repo already uses that pattern or the branch table is genuinely data-like.

## Duplication

Consolidate duplicated business rules, thresholds, parsing logic, and report formatting that must evolve together.

Leave superficial duplication alone when two call sites have different business meanings or are likely to diverge.

## Risk Patterns

Treat risk-pattern matches as review triggers. Confirm whether the match is executable code, documentation, fixture text, or an intentional warning.

Fix real risks directly. For false positives, explain why the match is safe and prefer configuration refinement over code contortions.

## Test Honesty

Reported only; these move no score and are not work by themselves. After Ken Pugh's AlignThree Spectables (https://alignthree.com).

A skipped, pending or expected-failure test never counts as passing. Run it, remove it, or record why it is skipped; never delete one only to clear the list.

A test that computes its own expected value (`assert add(a, b) == a + b`) passes whatever the code does. Replace the arithmetic with the stated value it should produce. If the comparison is a real relation between two results, say so rather than rewriting it.

A Spectables finding (`column-count`, `duplicate-scenario`, `undefined-reference`) is an authoring mistake in a `.spectable` file. Fix the specification, not the generated tests.

## Missing Expected Files Or Commands

Add missing docs or command declarations only when the repo actually owns those workflows. Do not invent fake tests, placeholder docs, or misleading commands to satisfy the gate.

## Baselines

Use baselines to adopt the gate incrementally. Do not baseline new findings introduced by the current patch unless the user explicitly accepts that debt.

## Closeout

A good closeout distinguishes:

- fixed findings
- unchanged justified findings
- commands that passed
- commands that could not run and why
- follow-ups intentionally kept out of scope

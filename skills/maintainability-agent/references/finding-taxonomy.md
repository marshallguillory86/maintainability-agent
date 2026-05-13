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

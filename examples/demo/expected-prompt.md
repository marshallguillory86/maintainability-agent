## Work Order

Ordered by what it costs to leave against what it costs to fix (see the standard). `Worth` is what clearing the whole class moves the score, recomputed through the rubric rather than estimated.

| # | Band | Item | Worth | Target |
|---:|---|---|---:|---|
| 1 | quick-win | apply_pricing in billing.py (`billing.py`:14) | — | reduce below the configured limits (currently 72 lines, complexity 27) |
| 2 | quick-win | unpaired declaration in billing.py (`billing.py`:14) | — | add a paired test for `apply_pricing` |
| 3 | major-project | duplicated block in billing.py (`billing.py`:16) | — | remove the duplicated block |
| 4 | major-project | duplicated block in billing.py (`billing.py`:55) | — | remove the duplicated block |

Verify with: `python -m maintainability_audit --root . --format json`

### Copy-paste prompts

One self-contained prompt per item — paste any block whole into a coding agent.

#### apply_pricing in billing.py
`billing.py:14` · quick-win

```text
Repository: .
Task: reduce below the configured limits (currently 72 lines, complexity 27).
Location: billing.py:14
Why: a long, branching function is where defects concentrate and where every future change has to be understood first; extracting one is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### unpaired declaration in billing.py
`billing.py:14` · quick-win

```text
Repository: .
Task: add a paired test for `apply_pricing`.
Location: billing.py:14
Why: an oversized production unit with no paired test is where changes land unguarded; adding a characterization test is bounded, local work

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### duplicated block in billing.py
`billing.py:16` · major-project

```text
Repository: .
Task: remove the duplicated block.
Location: billing.py:16
Why: duplicated logic means a fix applied in one place and missed in the others; deduplicating across a codebase is a design change, not a tidy-up

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```

#### duplicated block in billing.py
`billing.py:55` · major-project

```text
Repository: .
Task: remove the duplicated block.
Location: billing.py:55
Why: duplicated logic means a fix applied in one place and missed in the others; deduplicating across a codebase is a design change, not a tidy-up

Make one small, reviewable change. Do not alter public behavior or refactor unrelated code. If this is a false positive, say so and leave it unchanged; add or update a test when behavior changes.
Verify when done: python -m maintainability_audit --root . --format json
```


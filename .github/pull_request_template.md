## What this changes

<!-- The behaviour that moves, stated first, then why. Link the issue it closes: "Closes #123". -->

## How it is tested

<!-- The test that fails without this change and passes with it. A change with no behaviour to test says so and why. -->

## Checklist

- [ ] A failing test was written first and now passes; the full suite passes (`python3 -m pytest -n auto -q`).
- [ ] `python3 -m ruff check src tests tools` is clean.
- [ ] The self-audit passes: `python3 -m maintainability_audit --root . --config maintainability-agent.json --fail-on-gate`.
- [ ] `CHANGELOG.md` has an entry under **Unreleased** for anything a user would notice.
- [ ] Documentation that describes the changed behaviour is updated, and `docs/html/` is re-rendered with `tools/render_docs.py`.
- [ ] No published number (score, grade, calibration constant) moves, or the PR says which one and why.

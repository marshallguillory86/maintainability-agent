# Contributing

Thanks for helping improve Maintainability Agent.

## Project Rules

- No cloud service requirement.
- No automatic LLM calls by default.
- No vendor lock-in.
- Deterministic analysis comes first.
- AI prompts are generated artifacts for human-reviewed workflows.
- Tests are required for CLI behavior changes.
- Keep changes small and reviewable.

## Local Verification

```bash
python3 -m py_compile src/maintainability_audit/*.py
PYTHONPATH=src python3 -m pytest
PYTHONPATH=src python3 -m maintainability_audit --config maintainability-audit.example.json --fail-on-gate
```

## Pull Requests

Include:

- what changed
- why it belongs here
- commands run
- any follow-up work

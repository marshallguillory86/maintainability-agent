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
# Install dev extras (ruff + pip-audit + jsonschema + pytest-cov).
python3 -m pip install -e ".[dev]"

# Lint, deps scan, tests with coverage gate, self-audit.
ruff check src tests
pip-audit
PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-fail-under=92
PYTHONPATH=src python3 -m maintainability_audit \
  --config maintainability-agent.json --fail-on-gate
```

Sandbox-friendly invocation (for AI agents that disable plugin autoload)
drops coverage and works fine:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
  PYTHONPATH=src python3 -m pytest -p no:cacheprovider
```

Single-test fast-iteration (no coverage gate):

```bash
PYTHONPATH=src python3 -m pytest tests/test_cli.py::test_version_flag
```

## Pull Requests

Include:

- what changed
- why it belongs here
- commands run
- any follow-up work

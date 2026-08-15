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
# Install dev extras (ruff + pip-audit + jsonschema + pytest-cov + PyYAML
# for tools/build_catalog.py). The shipped package does not depend on PyYAML.
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

## Releasing

Publishing to PyPI is automated. Pushing a version tag builds, verifies and
publishes; there are no credentials to manage because authentication uses
PyPI Trusted Publishing (OIDC), which mints a short-lived token scoped to
`release.yml` in this repository.

```bash
# 1. bump the version in all three places
#      pyproject.toml            version = "X.Y.Z"
#      src/maintainability_audit/__init__.py   __version__
#      src/maintainability_audit/config.py     VERSION
# 2. add the CHANGELOG entry, open a PR, merge it
# 3. tag the merged commit and push
git checkout main && git pull
git tag -a vX.Y.Z -m "vX.Y.Z — one-line summary"
git push origin vX.Y.Z
```

The workflow refuses to publish if the tag disagrees with the packaged
version. It also installs the built wheel and runs both the test suite and
the tool's own `--fail-on-gate` audit against that artifact, so what ships
is what was verified.

Then cut the GitHub Release from the CHANGELOG section:

```bash
gh release create vX.Y.Z --title "vX.Y.Z — summary" --notes-file <(...)
```

If the default thresholds changed in the release, recalibrate first —
the constants are the anchor for every score the tool emits:

```bash
python3 tools/calibration/measure.py --check
```

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
# secure-code-agent, which every audit runs (D177), is installed alongside,
# not as a dependency: python3 -m pip install 'secure-code-agent>=0.12.2'.
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
# 1. bump the version in ONE place
#      src/maintainability_audit/__init__.py   __version__
#    `pyproject.toml` derives it and `config.py` re-exports it (D198);
#    writing it into either again fails the suite.
python3 tools/stamp_version.py   # 2. writes the four documents that state it
# 3. add the CHANGELOG entry (## X.Y.Z), open a PR, merge it
# 4. tag the merged commit and push
git checkout main && git pull
git tag -a vX.Y.Z -m "vX.Y.Z — one-line summary"
git push origin vX.Y.Z
```

Step 2 is not optional and is not a formatting chore. The README's version
line, the README's GitHub Action pin, the `docs/release-plan.md` row and the
SECURITY.md support table each have to state the number, each went stale once,
and each is now written from the single literal rather than typed. The tool
exits non-zero if any of them stopped matching, so a document that drifts out
of its reach fails rather than being silently skipped. v3.7.9 was tagged and
lost its release because one of those four was missed by hand.

Step 3 is likewise enforced: the GitHub Release job reads its notes from the
CHANGELOG section for that version, and the suite fails if the shipping version
has no section — otherwise the job publishes a release whose entire notes are
the sentence `Release X.Y.Z.` (D204).

The workflow refuses to publish if the tag disagrees with the version in the
source, and again if the **built wheel** disagrees with the tag (D205). It
installs that wheel and runs both the test suite and the tool's own
`--fail-on-gate` audit against it, so what ships is what was verified.

Cutting the GitHub Release is automatic — the tag triggers a job that creates
it, or refreshes its notes on a re-run. There is nothing to do by hand.

If the default thresholds changed in the release, recalibrate first —
the constants are the anchor for every score the tool emits:

```bash
python3 tools/calibration/measure.py --check
```

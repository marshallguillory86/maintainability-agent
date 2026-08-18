# Codex — ruff I001 on the ADR 009 contract

You are Codex. Tests only. No src/. No docs.

Repo: maintainability-agent. Owner marshallguillory86.

    git fetch origin
    git switch test/adr-009-close
    cd /tmp/ma-test-adr-009-close || git worktree add /tmp/ma-test-adr-009-close test/adr-009-close

Fix only tests/test_identity_resolution.py. ruff I001: unsorted imports.
Do not change test bodies.

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    ruff check --fix tests/test_identity_resolution.py
    ruff check tests/test_identity_resolution.py
    PYTHONPATH=src python -m pytest tests/test_identity_resolution.py tests/test_migration_1_0.py -q

One commit. Push origin test/adr-009-close. No PR. Never push main.

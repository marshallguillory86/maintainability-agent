# 19 Claude — ADR 009 close: make Codex tests pass

You are Claude. Implementor. Do not rewrite Codex’s files.

Repo: maintainability-agent. Owner marshallguillory86.
Your earlier commit is origin/feat/adr-009-identity. Continue from it.

    git fetch origin
    git switch feat/adr-009-identity
    git worktree add /tmp/ma-feat-adr-009-close feat/adr-009-identity
    cd /tmp/ma-feat-adr-009-close

STOP if origin/test/adr-009-close does not contain
tests/test_identity_resolution.py. Do not invent a suite.

    git checkout origin/test/adr-009-close -- \
      tests/test_identity_resolution.py \
      tests/test_identity_docs.py \
      tests/test_doc_claims.py \
      tests/test_history_schema2.py \
      tests/test_architecture.py \
      docs/adr-009-scan-history.md \
      docs/decisions.md \
      docs/architecture.md \
      docs/migration-1.0.md \
      docs/report-contract.md

Do not edit those after checkout.

Fix src so the contract passes. Likely gap: _recurrence.outcomes still
treats a git mv as CLEARED because it looks up the old label in the new
fingerprint set. After a rename the finding is NEVER_CLEARED. Use the
matcher / walk, not string membership of the old label.

Do not change fingerprint label format. Do not touch _formula,
_calibration, _bands, _economics, or any _semantic* file.

Paths you may edit: src/maintainability_audit/_finding_match.py,
_identity.py, baseline.py, git_tools.py, declarations.py,
_metrics_types.py, _recurrence.py, _scan_history.py, cli.py.

Verify:

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-feat-adr-009-close
    PYTHONPATH=src python -m pytest tests/test_identity_resolution.py tests/test_identity_docs.py tests/test_finding_identity.py tests/test_doc_claims.py tests/test_architecture.py tests/test_history_schema2.py tests/test_recurrence.py tests/test_scan_history.py -q

Then the full suite. ruff is .venv/bin/ruff. Do not install tools.

Wrap-up: files / tests / still open. One commit. Push
feat/adr-009-identity. No PR unless Marshall says so. Never push main.

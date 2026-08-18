# 17 Claude — ADR 003 option C: implement until Codex tests pass

You are Claude. Implementor. Do not rewrite Codex’s files.

Repo: maintainability-agent. Owner marshallguillory86.
Option C. No string-flagging hack. No LLM. No score or gate from
candidates. TypeScript only. Other languages: unknown semantic
coverage, not zero violations.

    git fetch origin
    git switch -c feat/adr-003-semantic origin/main
    git worktree add /tmp/ma-feat-adr-003-semantic feat/adr-003-semantic
    cd /tmp/ma-feat-adr-003-semantic

STOP if origin/test/adr-003-semantic does not contain
tests/test_semantic_policy.py. Do not invent a suite.

    git checkout origin/test/adr-003-semantic -- \
      tests/test_semantic_policy.py \
      tests/fixtures/semantic_ts \
      docs/adr-003-deterministic-semantic-policy.md \
      docs/semantic-prototype.md \
      docs/config-schema.md \
      docs/product-intent.md \
      docs/decisions.md \
      docs/architecture.md

Do not edit those after checkout. If architecture.md was not in the
Codex commit, skip that path.

New modules:

src/maintainability_audit/_semantic.py
- CLASS_UNIVERSAL, CLASS_POLICY, CLASS_CANDIDATE
- finding: class, rule_id, rule_version, path, locations/symbols,
  type_facts, policy_id (empty unless policy), review_boundary
  (candidates), message
- semantic_findings(root, config, *, history=None, type_analysis=...)
  deterministic, sorted

src/maintainability_audit/_semantic_policy.py
- load semantic_policy from the config dict
- exact paths + required_type / operation contract
- missing policy → no class-policy findings

src/maintainability_audit/_semantic_ts.py
- type facts from Codex’s pinned recordings, or local tsc if present
- never install, never npx --yes, never network
- universal only when a declared type is used as string at a typed
  boundary
- repeated literals / lockstep history without a declared type →
  candidate; message says the abstraction is not proven
- unavailable analysis → unknown coverage, empty universal/policy

Wiring only, after the score or proven not to move it:

- config.py — optional semantic_policy, default absent
- report.py — report["semantic_findings"] and coverage; do not pass
  semantic data into score_report
- prompts.py — list by class; candidates labeled; no prescribed enum
- _work_order.py — universal and policy are work items; candidates go
  to design-review, not hard_gate_failures
- _analysis.py — only if you need a coverage row
- tests/test_architecture.py — add the three modules to the right
  layers (not scoring)

If you invoke tsc, it goes through _runner.

Do not touch: _identity.py, _finding_match.py, baseline.py, git_tools.py,
declarations.py, _metrics_types.py, _recurrence.py, _scan_history.py,
cli.py, _formula.py, _calibration.py, _bands.py, scoring.py,
tests/test_identity_*.py, docs/adr-009-scan-history.md,
docs/migration-1.0.md, docs/report-contract.md.

Verify:

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-feat-adr-003-semantic
    PYTHONPATH=src python -m pytest tests/test_semantic_policy.py tests/test_promises.py -q
    .venv/bin/ruff check src/maintainability_audit/_semantic.py src/maintainability_audit/_semantic_ts.py src/maintainability_audit/_semantic_policy.py

Then a broader suite. Do not install tools.

Wrap-up: files / tests / still open. One commit. Push
feat/adr-003-semantic. No PR unless Marshall says so. Never push main.

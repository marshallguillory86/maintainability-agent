# 16 Codex — ADR 003 option C: tests and docs

You are Codex. Tests and docs only. No src/.

Repo: maintainability-agent. Owner marshallguillory86.
Marshall accepted option C. Do it correctly. No string-flagging hack.
No LLM. No score change.

Read: docs/product-intent.md, docs/adr-003-deterministic-semantic-policy.md,
docs/architecture.md.

    git fetch origin
    git switch -c test/adr-003-semantic origin/main
    git worktree add /tmp/ma-test-adr-003-semantic test/adr-003-semantic
    cd /tmp/ma-test-adr-003-semantic

If that branch exists on the remote, stop. Write nothing under src/.
Claude implements on feat/adr-003-semantic.

Three classes only:

1. Universal — a type checker proves a string where a declared
   OrderStatus (or equivalent) is required. No repo-specific meaning.
2. Policy — checked-in semantic_policy names the concept; typed analysis
   proves the breach. The finding names the policy entry.
3. Candidate — repeated operation-name set or lockstep history. Prompt
   only. Never a gate. Never a score input.

TypeScript only. High precision, accept low recall. No _formula weight.

Signals (do not invent a fourth): domain type used as string at a typed
boundary; same primitive re-validated at a public boundary; operation
names repeated across dispatch/capability/description — candidate only.
No “every *_id must be a value object.”

Create docs/semantic-prototype.md before results exist: TypeScript only;
named signals; corpus path tests/fixtures/semantic_ts/; precision and
recall separate; freeze a precision bar now; scoring forbidden; a
candidate must not fail --fail-on-gate.

Create that fixture tree: labeled true positives and benign lookalikes.
Prefer recorded typechecker output under
tests/fixtures/semantic_ts/recordings/. No npm install. No network.
Missing compiler is Unknown coverage, not a skip that greens vapor.

Write tests/test_semantic_policy.py only (new). Claude implements:

    from maintainability_audit._semantic import (
        CLASS_UNIVERSAL, CLASS_POLICY, CLASS_CANDIDATE, semantic_findings,
    )
    from maintainability_audit._semantic_policy import load_semantic_policy

Properties:

1. Same source, history, analyzer versions, policy → byte-identical findings.
2. Policy violation names the policy entry and source evidence.
3. Removing semantic_policy cannot create a policy violation.
4. A candidate is not in hard_gate_failures and does not change
   maintainability_estimate, maintainability_range, verified_grade, or
   evidence_status.
5. Missing type analysis is unknown coverage, never zero violations.
6. render_ai_prompt labels candidates as candidates. Must not say
   “replace with an enum” as proven.
7. Bare strings with no declared domain type → candidates or nothing,
   never universal.
8. Fixture policy uses exact paths + required_type.
9. No semantic weight in _formula.CATEGORY_ASPECTS. No repo-specific
   branch in _calibration.py.

Docs: adr-003 status Accepted, option C, progress in the ADR.
docs/config-schema.md — optional semantic_policy (version, domain_types,
operations), default absent.
docs/product-intent.md — only the ADR 003 paragraph: accepted,
TypeScript-only this increment, no score.
docs/decisions.md — 003 row only: Accepted, this increment TS-only.
docs/architecture.md — name the new modules in Known direction / mermaid
if you add them to a layer list. Do not rewrite identity or 009 text.

Do not touch: _identity.py, _finding_match.py, baseline.py, git_tools.py,
declarations.py, _metrics_types.py, _recurrence.py, _scan_history.py,
cli.py, tests/test_identity_*.py, tests/test_architecture.py (Claude
adds modules there), docs/adr-009-scan-history.md, docs/migration-1.0.md,
docs/report-contract.md.

Verify (fails until Claude implements):

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-test-adr-003-semantic
    PYTHONPATH=src python -m pytest tests/test_semantic_policy.py -q

One commit. Push origin test/adr-003-semantic. No PR. Never push main.
If you do not push, Claude will stop.

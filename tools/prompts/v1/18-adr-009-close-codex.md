# 18 Codex — ADR 009 close: land the contract

You are Codex. Tests and docs only. No src/.

Repo: maintainability-agent. Owner marshallguillory86.
Read docs/product-intent.md and docs/adr-009-scan-history.md.

Claude already implemented on origin/feat/adr-009-identity (e215627).
You write the contract that implementation must pass. Do not reimplement.

    git fetch origin
    git switch -c test/adr-009-close origin/main
    git worktree add /tmp/ma-test-adr-009-close test/adr-009-close
    cd /tmp/ma-test-adr-009-close

If that branch exists on the remote, stop.

Write tests/test_identity_resolution.py. Import these names and no others
for matching:

    Identity, identities_from_report, rename_map, same_finding, unmatched
    from maintainability_audit._finding_match
    BASELINE_VERSION, StaleBaseline, load_baseline, load_baseline_identities,
    write_baseline, findings_not_in_baseline from maintainability_audit.baseline

Kinds are declaration, file, risk, duplicate. unmatched and
findings_not_in_baseline return a frozenset. Compare with not unmatched(...)
or len(...), never == [].
same_finding(current, known, renames) — current is the later scan.

Cases (real build_report + git in tmp_path):

1. git mv a failing function: findings_not_in_baseline empty; recurrence
   empty; outcomes(..., root=root) is NEVER_CLEARED for the old targeted
   label. A rename is not a clear.
2. git mv an oversized file: file finding not new.
3. Swap two same-named failing huges with different bodies: both match.
4. Insert a third same-named sibling: only the new one is unmatched.
5. Edit the body, still failing: still matches (ordinal rule).
6. Reindent only: digest unchanged, still matches.
7. def huge -> def enormous: not a match, even if digest matches.
8. Copy the file, no git mv: copy is new; rename_map empty.
9. load_baseline rejects version 2; write_baseline is version 3 with
   commit plus identities records (kind, path, name, ordinal, body_digest,
   fingerprint); round-trip matches the same tree.
10. New history lines are schema 3 and store identities; schema 2 lines
    still load; recurrence between two schema-2 records is string equality.
11. No src/ compare is finding_fingerprints(...) - a set. cli.audit_exit_code
    must call findings_not_in_baseline. Do not flag comments.
12. Every fail/warn function_hotspot has body_digest. _identity.py does
    not open or read_text the audited tree.

Rewrite tests/test_identity_docs.py and
test_adr_009_states_the_shipped_ordinal_identity in tests/test_doc_claims.py
so they require the matcher + digest + rename follow, and fail if docs
still say the body hash did not ship. Label format stays
function:{path}:{name}#{ordinal}. Do not skip.

Fix tests/test_history_schema2.py: new writes are schema 3 and still
store categories, aspects, pillars, practice_level, evidence_status.
Schema 1 still loads. Rename the “schema two” assertions; do not delete
the chart fields.

Add _finding_match to FOUNDATIONS in tests/test_architecture.py.

Docs only: docs/adr-009-scan-history.md, docs/decisions.md (009 row),
docs/architecture.md (Known debt + Layers mermaid must name
_finding_match), docs/migration-1.0.md (baseline v3, regenerate),
docs/report-contract.md (structured identities).

Do not edit src/. Do not edit tests/test_finding_identity.py.

Verify (must fail on origin/main, pass docs/honesty after your doc edits):

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    cd /tmp/ma-test-adr-009-close
    PYTHONPATH=src python -m pytest tests/test_identity_resolution.py tests/test_identity_docs.py tests/test_doc_claims.py tests/test_history_schema2.py tests/test_architecture.py -q

One commit. Push origin test/adr-009-close. No PR. Never push main.
If you do not push, Claude will stop. That is the handoff.

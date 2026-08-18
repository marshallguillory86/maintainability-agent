# Codex — ADR 009 identity resolution (tests + docs)

You are Codex. Test writer / tester, or doc editor. **Do not implement product code.**

Repo: `maintainability-agent` (GitHub owner `marshallguillory86`).
This is a parked defect on an **Accepted** decision. `--fail-on-new` and recurrence still lie after `git mv` and after same-name reorder. Close it. Do not invent product intent. Governing docs: `docs/product-intent.md`, `docs/adr-009-scan-history.md`, `docs/architecture.md`.

## Branch and tree (mandatory)

```bash
git fetch origin
git switch -c test/adr-009-identity origin/main
# Isolated worktree. Do not work in a dirty main checkout.
git worktree add /tmp/ma-test-adr-009-identity test/adr-009-identity
cd /tmp/ma-test-adr-009-identity
```

If `test/adr-009-identity` already exists on the remote, stop and tell Marshall.

**You do not write anything under `src/`.** Claude implements on `feat/adr-009-identity`. Different branch. Non-overlapping paths.

## What is true today

Shipped declaration identity is the *label* `function:{path}:{name}#{ordinal}` in `src/maintainability_audit/_identity.py`. Line insertion is fixed. These still break the accepted contract:

1. `git mv` a file → path changes → `--fail-on-new` and recurrence treat an untouched function as new.
2. Insert or reorder a same-named declaration → ordinal changes → same lie.

`tests/test_identity_docs.py` currently **locks the hole in**: it requires docs to say the body hash did not ship, and skips if `_identity.py` grows a hash. That honesty was correct for the partial ship. It is now the test that must change, because the hole is the work.

Architecture: `_identity` is presentation and **must not read source**. Body digest is computed at scan time and stored on the report. Matching for `--fail-on-new` and recurrence cannot live only in presentation: `_recurrence` is scoring and may not import presentation. Put the matcher in **foundations**.

Presentation still emits the human label `function:{path}:{name}#{ordinal}`. Do **not** make body-hash the only fingerprint string. Body edits of a still-failing function must remain the same finding (`--fail-on-new` must not fire). Existing tests in `tests/test_finding_identity.py` that pin `#0` / `#1` labels must keep passing.

## The contract you write

Create **`tests/test_identity_resolution.py`**. Property tests over real `build_report` + git repos in `tmp_path`, not hand-built fingerprint strings alone.

### Required cases

1. **`git mv` does not mint a new declaration.** Write a failing `huge` function, commit, write baseline, `git mv` the file, commit. `--fail-on-new` / `findings_not_in_baseline` (name the public function Claude must provide) reports **empty**. Recurrence across two history records that straddle the rename reports the **same** finding, not cleared+new.

2. **`git mv` does not mint a new file-lines finding.** Same shape for an oversized file (`file-lines:{path}`).

3. **Same-name reorder does not mint a new declaration.** Two failing `huge` methods with **different** bodies in one file. Write baseline. Swap their order. Both still match. Identities follow the bodies, not the ordinals.

4. **Insert a third same-named sibling above the pair.** The original two still match the baseline. The new sibling is new.

5. **Body edit of a still-failing function is not new.** Add statements inside `huge` so it is still over budget. Path, name, ordinal unchanged. Must still match (ordinal / path rule). Must **not** require the body digest to stay equal.

6. **Reindent only is not new.** Dedent/indent the body. Must still match.

7. **Rename the unit is new.** `def huge` → `def enormous` must **not** match (already pinned in `test_finding_identity.py`; keep a resolution-level assertion so the matcher cannot “helpfully” glue them via digest alone).

8. **Copy is not a rename.** Duplicate the file to a new path without `git mv`. The copy is new. The original still matches. Do not treat an identical body in a second path as the same finding unless git recorded a rename **or** the (path, name, digest) rule is applied only after a rename map exists for that path.

9. **v2 baseline is rejected.** `load_baseline` on a version-2 file raises the existing stale type (or a sibling) and names `--write-baseline`. Version 3 is written. A v3 file stores enough to match: at least `version`, `root`, `commit`, and structured identity records (`kind`, `path`, `name`, `ordinal`, `body_digest`, `fingerprint` label). Round-trip: write, load, match the same tree.

10. **History schema 3 stores identity records.** New JSONL lines carry structured identities (and still carry the label strings so charts do not break). Schema-2 lines still load. Recurrence between two schema-2 lines stays string equality (document that). Recurrence between two schema-3 lines uses the matcher + `git diff --find-renames` between the two stored commits.

11. **No set-difference escape.** Grep `src/` for `finding_fingerprints(...) - ` and for fail-on-new comparing two `set`s of strings without the matcher. If Claude leaves a compare path that is raw string difference, this test fails. Lint the class.

12. **Digest is on the hotspot, not computed in presentation from source.** After `build_report`, every fail/warn `function_hotspots` item has a non-empty `body_digest`. `_identity.py` must not open the audited tree.

### Honesty tests you must rewrite

Edit **`tests/test_identity_docs.py`** so it no longer requires “body hash did not ship” and no longer skips when a digest exists.

Rewrite **`test_adr_009_states_the_shipped_ordinal_identity`** in `tests/test_doc_claims.py`: the ADR must still name the label format `function:{path}:{name}#{ordinal}`, and must **not** say the body hash / rename follow “did not ship.” It must state that matching uses rename-adjusted (path, name, ordinal), then (path, name, body_digest), and that git rename follow is shipped.

## Docs you edit (only these)

- `docs/adr-009-scan-history.md` — Decision 1: label stays ordinal; matching + stored digest + git rename follow **ship**. Update invariant 2 so `--fail-on-new` is about matched identity, not raw string absence of `function:{path}:{name}#{ordinal}`.
- `docs/decisions.md` — 009 row: identity matching shipped; baseline v3; history schema 3 identities.
- `docs/architecture.md` — Known debt: remove “body hash did not ship.” Layers: new foundations matcher module (Claude will name it `_finding_match` unless you specify otherwise in a test import — **import `maintainability_audit._finding_match`** from the new tests). Identity row in the table: label is ordinal; comparison is the matcher.
- `docs/migration-1.0.md` — Baseline becomes **version 3**. Regenerating is required. Say so.
- `docs/report-contract.md` — Baseline findings are structured records, not only strings. `function_hotspots` carry `body_digest`.

Do **not** edit `src/`. Do **not** edit `tests/test_finding_identity.py` (those labels stay). Do **not** edit `tests/test_architecture.py` (Claude adds the new module to FOUNDATIONS).

## Public names the tests should import

These are the names Claude must make exist. Use them so the implementor is not guessing:

```python
from maintainability_audit._finding_match import (
    Identity,
    identities_from_report,
    rename_map,
    same_finding,
    unmatched,
)
from maintainability_audit.baseline import (
    BASELINE_VERSION,  # == 3
    load_baseline_identities,
    write_baseline,
    findings_not_in_baseline,
)
```

`findings_not_in_baseline(report, baseline_path, root)` is what `cli.audit_exit_code` must use.

If a name is slightly wrong in the tree when you start, still write the tests against **these** names. Claude implements these names.

## How to run

```bash
source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
cd /tmp/ma-test-adr-009-identity
PYTHONPATH=src python -m pytest tests/test_identity_resolution.py tests/test_identity_docs.py tests/test_doc_claims.py -q
```

New resolution tests should **fail** on current `origin/main` (no matcher, v2 baseline). Honesty/doc tests you rewrote will fail until you update the docs in this same branch. Do not implement src to make them pass.

## Commit

One commit. Tests + docs only. Push the branch. Do not open a PR unless Marshall says so. Never push `main`.

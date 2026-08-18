# Claude — ADR 009 identity resolution (implementation)

You are Claude. Coder / implementor. **Not tests-only.** You do not rewrite Codex’s test or doc files. You take them with `git checkout` and make them pass.

Repo: `maintainability-agent` (GitHub owner `marshallguillory86`).
Do not invent product intent. Governing docs: `docs/product-intent.md`, `docs/adr-009-scan-history.md`, `docs/architecture.md`.
Child sandbox is refused. Do not touch analyzers, scoring weights, or ADR 003 files.

This defect has been documented and re-listed across audits. Close it. No “did not ship” left in the implementation.

## Branch and tree (mandatory)

```bash
git fetch origin
git switch -c feat/adr-009-identity origin/main
git worktree add /tmp/ma-feat-adr-009-identity feat/adr-009-identity
cd /tmp/ma-feat-adr-009-identity
```

If `feat/adr-009-identity` already exists, stop.

Codex is on **`test/adr-009-identity`**. When that branch is on the remote (or you are given the path), take **only** the contract files:

```bash
git fetch origin
git checkout origin/test/adr-009-identity -- \
  tests/test_identity_resolution.py \
  tests/test_identity_docs.py \
  tests/test_doc_claims.py \
  docs/adr-009-scan-history.md \
  docs/decisions.md \
  docs/architecture.md \
  docs/migration-1.0.md \
  docs/report-contract.md
```

Do **not** edit those files after checkout. If a test is wrong, stop and say so. Do not “fix” the contract.

## What to implement

### 1. Scan-time body digest (parsing / metrics)

`FunctionMetric` (`_metrics_types.py`) gains `body_digest: str = ""`.

In `declarations.py`, where `block = code[decl.start - 1 : decl.end]` already exists, set `body_digest` to a 12-char sha256 hex of a **normalized** body:

- `textwrap.dedent`
- strip trailing whitespace per line
- join with `\n`
- do **not** strip comments
- do **not** rename identifiers

`report._function_hotspots` already `asdict`s the metric. Do not add a parallel field in `report.py` unless a test forces it.

Presentation (`_identity.py`) **must not open the audited tree**. It reads `body_digest` off the hotspot dict.

### 2. Foundations matcher (new module)

Create `src/maintainability_audit/_finding_match.py`. This is **foundations**. Scoring may import it. Presentation may import it. It imports `git_tools` only.

```python
@dataclass(frozen=True)
class Identity:
    kind: str          # "declaration" | "file" | "risk" | "duplicate"
    path: str
    name: str
    ordinal: int
    body_digest: str
    fingerprint: str   # existing human label
```

Required functions (Codex imports these names):

- `identities_from_report(report) -> frozenset[Identity]`
- `rename_map(root, old_commit, new_commit) -> dict[str, str]`  
  `git diff --name-status --find-renames <old> <new>` via existing `run_git`. Parse `R*` lines (`R100\told\tnew`). Empty commits → empty map. No network.
- `same_finding(current, known, renames) -> bool`
- `unmatched(current, known, renames) -> frozenset[Identity]`

**Match order** (all after applying `renames` to `known.path`):

1. Exact `fingerprint` string.
2. Same `(path, name, ordinal)` and same `kind`. Survives body edits and line inserts.
3. Same `(path, name, body_digest)` and same `kind`, digest non-empty. Survives same-name reorder.
4. File kind: rename-mapped path only (`file-lines`).
5. Duplicate: existing sample digest; apply rename map to each path, then sort.

A **copy** (identical body, new path, no git rename) is **not** a match. Do not use digest-only matching across paths.

`def huge` → `def enormous` must not match (name changed). Do not glue via digest alone.

### 3. git_tools

Add a thin helper if it keeps `_finding_match` free of extra process rules. Only `_runner`, `git_tools`, and `_backfill` may spawn. `rename_map` must go through `run_git`.

### 4. Labels stay ordinal

`declaration_fingerprint` / `risk_fingerprint` / `file_fingerprint` / `duplicate_fingerprint` keep today’s string shapes. `tests/test_finding_identity.py` must stay green without edits.

`declaration_identities` still numbers by `(path, name)` ordered by start line. The digest is extra data on the Identity, not a replacement label.

### 5. Baseline v3

`baseline.py`:

- `BASELINE_VERSION = 3`
- `write_baseline` stores `version`, `root`, `commit` (`report["git_commit"]`), and structured records (kind, path, name, ordinal, body_digest, fingerprint).
- `load_baseline` on version ≠ 3 raises `StaleBaseline` and names `--write-baseline` (same fail-closed as v1).
- `load_baseline_identities(path) -> frozenset[Identity]`
- `findings_not_in_baseline(report, baseline_path, root)` uses `unmatched` + `rename_map(root, baseline_commit, report["git_commit"])`.

Keep `load_baseline` returning something honest for any leftover string consumer, or stop using the string set for the gate. The gate must not be `finding_fingerprints(report) - set_of_strings`.

### 6. CLI

`cli.audit_exit_code`: `--fail-on-new` uses `findings_not_in_baseline`. Pass `root` from the report.

### 7. Recurrence and history

`_recurrence.py` must not compare raw fingerprint string sets when **both** records carry structured identities. Use `same_finding` + `rename_map` between the two records’ commits.

`_scan_history.py`: new lines are schema 3 and store identity records (in addition to the existing fingerprint label tuple, so charts still have strings). Schema 1/2 lines still load. Recurrence between two schema-2 records stays string equality.

### 8. Architecture test

Edit **only** `tests/test_architecture.py`: add `_finding_match` to `FOUNDATIONS`. Do not edit Codex’s other tests.

## Paths you may write

```
src/maintainability_audit/_finding_match.py
src/maintainability_audit/_identity.py
src/maintainability_audit/baseline.py
src/maintainability_audit/git_tools.py
src/maintainability_audit/declarations.py
src/maintainability_audit/_metrics_types.py
src/maintainability_audit/_recurrence.py
src/maintainability_audit/_scan_history.py
src/maintainability_audit/cli.py
tests/test_architecture.py
```

Do **not** write `tests/test_identity_resolution.py`, `tests/test_identity_docs.py`, `tests/test_doc_claims.py`, or the ADR/docs Codex owns. Do **not** touch `report.py` unless a failing test proves `asdict` is insufficient. Do **not** touch scoring weights, `_formula`, `_bands`, `_economics`, or anything under a semantic/ADR 003 name.

## How to run

```bash
source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
cd /tmp/ma-feat-adr-009-identity
PYTHONPATH=src python -m pytest \
  tests/test_identity_resolution.py \
  tests/test_identity_docs.py \
  tests/test_finding_identity.py \
  tests/test_doc_claims.py \
  tests/test_architecture.py \
  tests/test_recurrence.py \
  tests/test_scan_history.py \
  -q
```

Then the full suite. `ruff` is `.venv/bin/ruff`. Do not install tools.

## Wrap-up

Files you wrote / tests that pass / still open. Do not claim the hole is closed if `git mv` or same-name reorder still changes unmatched findings.

One commit on `feat/adr-009-identity`. Push the branch. Do not open a PR unless Marshall says so. Never push `main`.

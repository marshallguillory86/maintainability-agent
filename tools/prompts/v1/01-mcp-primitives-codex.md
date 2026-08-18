# 01 Codex — MCP primitives: implement until Claude's tests pass

You implement ADR 008's missing MCP primitives. Claude's tests from
`tools/prompts/v1/01-mcp-primitives-claude.md` are the spec. If those
tests are not on the branch yet, **stop** and say so. Do not invent a
parallel suite.

## Why

1.0 includes the local MCP add-on. Tools already run the audit. Resources
must expose rubric, catalog, and the Markdown report. Prompts is the
slash command. The report resource must be byte-identical to
`render_markdown(build_report(...))`.

## Do

1. Register resources on the existing `MCPServer` in
   `src/maintainability_audit/mcp_server.py` (split a module if the
   file would cross 500 lines — entry stays `mcp_server`).
   Suggested URIs (change only if tests demand it):
   - `maintainability://standard` — text of the applied rubric
     (`docs/standard.md` is acceptable if tests allow; or the printed
     rubric from `_formula` / `standard.md` scoring section)
   - `maintainability://catalog` — analyzer catalog facts the pool
     already ships (`data/analyzer-catalog.json` summary or the
     document `docs/analyzer-pool.md` — pick one and stick to it)
   - report: a **template** resource whose parameter is the repository
     root (SDK: URI with `{root}`), `mime_type="text/markdown"`.
     Handler: `authorize_repository` then `load_config` /
     `discovered_config` then `build_report` then `render_markdown`.
     Same defaults as the CLI (no analyzers unless a test says so).
2. Register one `@server.prompt` named to match Claude's test
   (`maintainability-agent` or `audit`). Body: call `audit_repository`,
   obey the returned remediation prompt, do not widen.
3. Keep `audit_repository` / `get_agent_info` and their path rules.
   Keep the server read-only: no writes, no shell, no installs.
4. Do **not** add the CLI subcommand here (that's 02). Do **not**
   flip `tests/test_phase6_claims.py`. Do **not** regenerate the
   self-audit.

## Constraints

- `pip install "maintainability-agent[mcp]"` is the extra; do not
  add other deps.
- Agent never installs tools into the audited repo.
- No Go/C rangers, no `_bands` import, no calibration edits.
- CCN ≤ 15, file ≤ 500. Fence public helpers.

## Done when

- Claude's new tests pass.
- Existing MCP tests that are still valid still pass
  (`PathNotAllowed`, revspec, no-write, stdio `get_agent_info`).
- `ruff check` on touched files is clean.
- Wrap-up: files, tests run, no leftover "only two tools" assertion.

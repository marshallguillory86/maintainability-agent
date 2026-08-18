# 01 Claude — MCP primitives: tests only

You are on `main` of `maintainability-agent` (Marshall Guillory, public
career-showcase repo). **Tests and open files only.** Do not implement
the server. Do not edit docs except a test docstring. Do not install
packages. Do not touch `_bands`, Java ranges, calibration, or analyzers.

## Why

ADR 008: MCP has three primitives. Shipped today: two tools
(`audit_repository`, `get_agent_info`) on `maintainability-agent-mcp`.
Markdown is a field on the tool result. No resources. No prompts
primitive. 1.0 now includes the local MCP add-on. This pair builds it.

Read first:

- `docs/adr-008-translation-and-decision.md` § Two entry points, Markdown delivery
- `src/maintainability_audit/mcp_server.py`
- `tests/test_mcp_server.py`
- `src/maintainability_audit/renderers.py` (`render_markdown`)
- `src/maintainability_audit/report.py` (`build_report`)
- `.venv/.../mcp/server/mcpserver/server.py` — `@server.resource`, `@server.prompt`

## What to write

Add tests (prefer extending `tests/test_mcp_server.py`; split the file
if it would cross 500 lines). Today's tree must **fail** them.

### Resources

1. `list_resources` includes at least:
   - a **rubric/standard** resource (the applied standard, not a blog post)
   - a **catalog** resource (the analyzer catalog / pool)
   - a **report** resource whose contents are Markdown (`text/markdown`)
2. Reading the report resource for an authorized repo produces **exactly**
   `render_markdown(build_report(...))` on the same root, same config,
   same `run_analyzers` default (false). Byte-identical. One rendering.
   If they disagree, the CLI file is right and the resource is the bug.
3. Reading a report resource for a path outside allowed roots raises
   `PathNotAllowed` (same class the tools already use). No scan of
   unauthorized trees.
4. Rubric and catalog resources do not require a prior `audit_repository`
   call and do not write files.

### Prompts primitive

5. `list_prompts` includes one slash-command prompt (name
   `maintainability-agent` or `audit`).
6. Getting that prompt returns instructions that:
   - tell the model to call `audit_repository`
   - treat `remediation_prompt` / the work order as the bound
   - forbid widening past listed findings
   - do not invent findings

### Tools stay

7. `audit_repository` and `get_agent_info` still exist, still
   read-only annotated, still do not write the tree.
8. **Replace** `test_sdk_exposes_only_the_two_read_only_tools`.
   "Only two tools" is the old contract. Tools remain those two;
   resources and prompts are additional primitives, not extra tools.

### Class lint

9. A test that fails if `create_server` registers no resources or no
   prompts (look at the live SDK server, not a comment). This is the
   lint that replaces `test_mcp_server_has_no_resources` later — for
   this pair, leave `tests/test_phase6_claims.py` **alone**. 02 flips it.

## Constraints

- Use the installed `mcp` SDK (`MCPServer.resource`, `.prompt`). Do not
  invent a second protocol.
- Do not require network. Tests construct a tiny git repo like the
  existing fixture.
- `from mcp import Client` already fails in some local envs; if you
  need the in-process client, skip only when the import fails, and
  still test the registration/read functions **without** the client
  so CI (`mcp` in `[dev]`) is the source of truth.
- File ≤ 500 lines, CCN ≤ 15 on anything you add.

## Done when

`pytest tests/test_mcp_server.py` (and any new `test_mcp_*.py`) **fails**
on current `main` with assertion messages that name the missing
primitive. Open a PR or leave the test file on a branch
`test/mcp-primitives`. Wrap-up lists: files opened, tests added, what
fails. No implementation.

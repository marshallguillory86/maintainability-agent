# Codex — align the docs with D32, D33, D34

You are Codex. **Docs only.** No `src/`. No `tests/`. Do not touch
`docs/defect-register-chat-surface.md` or `CHANGELOG.md` — both are
already written and are the source you are aligning *to*.

Repo: maintainability-agent. Owner marshallguillory86.

    git fetch origin
    git switch -c docs/d32-d34-alignment origin/main

Three defects closed on 2026-08-24 in PRs #95 (D32), #96 (D33), #97
(D34). Read those three register entries first; they are the
specification. If a branch has not merged yet:

    git show origin/fix/d33-declared-refusals:docs/defect-register-chat-surface.md

## What is actually missing

The contracts themselves are documented. What is undocumented is **how
one of them survives the transport** — so a reader adding a new refusal
path today has nothing telling them they must declare it.

### 1. `docs/architecture.md` — record the transport refusal boundary

The entry layer (line ~138) lists every module at the boundary and calls
it "the one layer where the tool may ask a question". It does not say
which exceptions may *cross* it.

Add the rule, either in that layer's description or as a numbered
invariant beside the existing ones:

- A failure this seam makes on purpose — the allowed-roots boundary
  (D10/D20), the setup precondition (D26/D30), argument validation —
  crosses as the SDK's declared form: `ToolError` from the audit tool,
  `ResourceError` from the report resource and its security validator.
  Its message reaches the caller.
- Anything else is a crash: the caller gets `Error executing tool
  <name>` or a bare resource URI, and the traceback stays server-side.
  That is correct and must stay that way — nothing internal leaks.
- The plain functions in `_mcp_audit` keep raising the domain types
  (`PathNotAllowed`, `SetupRequired`, `ValueError`). **Only the
  transport translates**, because the CLI and every library caller
  depend on the domain types. `ANTICIPATED_REFUSALS` in `mcp_server.py`
  is the list.

One line on why it matters: before this was declared, `mcp` 2.1.0
classified every boundary refusal as a crash and withheld its text, so
the refusal went on refusing but stopped teaching its remedy.

### 2. `docs/decisions.md` Decision 5, and `docs/help/first-run.md`

Both promise that a declined or unelicitable grant "returns the static
`--allow-root` and environment-variable remedies" / "returns the
boundary error with the `--allow-root` and
`MAINTAINABILITY_MCP_ALLOWED_ROOTS` remedies".

That promise is now kept by a *mechanism*, and neither file says so. Add
one sentence to each pointing at the rule from item 1. Do not restate
the contract; link it.

The variable is `MAINTAINABILITY_MCP_ALLOWED_ROOTS`. Both files already
have it right. **Do not "fix" them.**

### 3. `docs/cli.md` — the `--install-skill` / `--force-skill` rows

D34 made the built distribution's skill payload an asserted artifact:
staged, byte-identical to `skills/maintainability-agent/SKILL.md`, and
carrying D21's call-first rule. Add one sentence so a reader knows the
copy `--install-skill` writes out is checked against the reviewed one,
not merely declared in `package-data`.

## What NOT to do

- Do not add a "closed does not mean released" note anywhere. It is
  true, and how to record it is the operator's call, not this slice's.
- Do not restructure `architecture.md`. One rule, in the existing shape.
- Do not touch the mermaid graph.
- Do not document `ANTICIPATED_REFUSALS` as public API. It is a
  module-level detail, named here only so the rule has an address.

## Verify

    source /Users/marshallguillory/repos/maintainability-agent/.venv/bin/activate
    PYTHONPATH=src python -m pytest tests/test_chat_primary_docs.py tests/test_written_record.py tests/test_architecture.py -q
    ruff check src tests
    PYTHONPATH=src python -m maintainability_audit --config maintainability-agent.json --changed-only main...HEAD --fail-on-gate

`test_architecture.py` reads `docs/architecture.md` and will tell you if
the layer description stops matching the module list. Do not satisfy it
by deleting a claim.

**Known environment traps on this machine** (a MacBook Pro that has not
been used for a release; these are not defects, do not chase them):

- ~292 tests fail locally with `git init` exit 1 — Command Line Tools
  are an empty husk and the fixtures pin `PATH=/usr/bin:/bin`.
- The analyzer pool is almost entirely absent, so local audits measure
  the built-in fallback, not the product.
- The `maintainability-agent` on `PATH` is a released 0.9.1, not this
  checkout. Use the `.venv`, which is editable onto the tree.

One commit. Push `origin docs/d32-d34-alignment`. Open a PR. Never push
`main`.

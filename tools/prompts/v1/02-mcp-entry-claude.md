# 02 Claude — MCP entry + honesty: tests only

**Depends on 01.** If resources/prompts are not implemented on the
branch you start from, stop.

Tests and open files only. No implementation. No self-audit regen.

## Why

ADR 008: the server is a **subcommand of this package**. Shipped today:
separate console script `maintainability-agent-mcp` only. IDEs already
point at that script — keep it. 1.0 also needs `maintainability-agent mcp`.

`tests/test_phase6_claims.py` currently **asserts absence** of resources
and of a subcommand. After 01, `test_mcp_server_has_no_resources` will
be wrong. This pair flips the honesty lint from "must not claim they
ship" to "must not claim they don't, and the entry point exists."

## What to write

1. **Subcommand.** A test that `maintainability_audit.cli.main(["mcp",
   "--help"])` (or equivalent argv) exits 0 and describes the MCP
   server / `--allow-root`. Must not break `maintainability-agent --root
   . --help`. `tests/test_cli.py` already drives `main([...])`.
2. **Alias survives.** `maintainability-agent-mcp` entry point in
   `pyproject.toml` still points at `mcp_server:main`.
3. **Flip `tests/test_phase6_claims.py`:**
   - Delete or invert `test_mcp_server_has_no_resources` so it now
     requires resources **and** a subcommand (detect
     `add_parser("mcp")` **or** an explicit `argv[0] == "mcp"`
     dispatch — don't force argparse subparsers if a first-arg
     handoff is cleaner).
   - Remove MCP phrases from `_MCP_CLAIMS` *or* invert them: live
     docs may now say resources exist; they must not still say
     "not shipped (6.3)" / "only two tools" as current fact.
   - Keep the **6.1** half (`prompt_when_interactive` unread). 6.1
     is still cut.
   - `test_the_register_names_the_mcp_gap_on_adr_008` must flip:
     once resources ship, the register row may not still list
     "MCP resources/prompts (6.3)" as the remaining gap.

4. **cli.md** will be updated in Codex; add a test in
   `test_docs_links.py` / `test_cli.py` if a documented `mcp`
   subcommand must appear next to flags (the existing "every flag
   is documented" test is `--` flags only — add a sibling for the
   `mcp` subcommand if you need it to fail today).

Today's tree (even after 01) should fail the subcommand test and
still fail the inverted phase-6 MCP assertions until Codex edits
docs + CLI.

## Done when

New/inverted tests fail with messages that name "no mcp subcommand"
or "register still lists 6.3 as open". Wrap-up: files, tests, failures.
No implementation.

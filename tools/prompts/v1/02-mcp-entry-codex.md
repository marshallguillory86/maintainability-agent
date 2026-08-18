# 02 Codex — MCP subcommand + honesty flip

Claude's tests from `tools/prompts/v1/02-mcp-entry-claude.md` are the
spec. 01 must already be on this branch.

## Do

1. **`maintainability-agent mcp`**
   - First-arg dispatch is fine and avoids breaking the existing
     flat flag parser:
     `if argv and argv[0] == "mcp": return mcp_server.main(argv[1:])`
   - Same `--allow-root` as today's `mcp_server._parser`.
   - Missing extra still raises the existing install hint
     (`pip install "maintainability-agent[mcp]"`).
   - Keep `[project.scripts] maintainability-agent-mcp`.
2. **Docs (current fact, not target-architecture):**
   - `docs/adr-008-translation-and-decision.md` — resources and
     prompts **ship**; drop "Not shipped (6.3)" / "Only the tool
     primitive shipped."
   - `docs/decisions.md` ADR 008 row — remaining gap is the band
     matrix, **not** MCP resources.
   - `docs/architecture.md` as-is MCP paragraph — three primitives
     on this server; subcommand exists; console script remains.
   - `docs/cli.md` — document the `mcp` subcommand.
   - `docs/ide-agent-integration.md` — still document
     `maintainability-agent-mcp` (IDEs); mention
     `maintainability-agent mcp` as the package subcommand.
   - `docs/release-plan.md` 6.2 and 6.3 — mark done with the
     actual exit (byte-identical resource; three primitives).
   - `docs/migration-1.0.md` — remove "MCP resources … not shipped"
     from "what you can ignore"; add a short "MCP now has
     resources/prompts" note. Not a new break.
   - 6.1 stays open. Do not implement `prompt_when_interactive`.
3. Satisfy Claude's inverted `test_phase6_claims` MCP half.
4. Do **not** regenerate `docs/self-audit.md` (03).
5. Do not implement `_bands`, 2.5c, 2.7, or 6.1.

## Done when

- `pytest tests/test_mcp_server.py tests/test_phase6_claims.py tests/test_cli.py tests/test_docs_links.py` pass.
- `ruff check` on touched files is clean.
- `maintainability-agent mcp --help` and `maintainability-agent-mcp --help` both work.

# 03 Codex — 1.0 MCP close-out (no audit)

**Depends on 01 and 02 merged.** Docs and stamp only, plus any test
that already exists and is red because the stamp drifted. Do not
start a hostile audit. Do not reopen 6.1 / bands / 2.7 / 2.5c.

## Do

1. Regenerate the self-audit the way CI does (no `--analyzers`):

   ```bash
   python3 -m maintainability_audit --config maintainability-agent.json \
     --output /tmp/self-audit.md
   ```

   Stamp the **parent** commit (the honesty/MCP tree), sanitize
   `$(pwd)` → `.`, write `docs/self-audit.md`. Update the README
   self-audit table to match. See the existing preamble.

2. `docs/release-plan.md` standing table: 6.2 and 6.3 are no longer
   open. 6.1 and 6.4 cache and Phase 7.3/7.5 remain honest.

3. CHANGELOG Unreleased: MCP resources, prompts primitive, and
   `maintainability-agent mcp`.

4. Run `pytest tests/test_docs_links.py tests/test_phase6_claims.py tests/test_migration_1_0.py`.

## Do not

- Re-derive calibration.
- Run a 40-repo corpus.
- Write a new "hostile audit" document.
- Claim 1.0 is tagged. Last tag stays 0.7.0 until a human tags it.

## Done when

README table == stamped self-audit. Release plan does not list 6.2/6.3
as open. Tests above pass.

After this lands, Grok verifies **against 01–03 prompts and their
tests**, not against a new inventory. That is the only 7.5 for MCP.

# 13 Claude — P1 class lint + no silent npx fetch

Repo: maintainability-agent. Branch from current **main** (do not sit
on the uncommitted Phase 8 HTML work unless it is already merged).
This prompt says implement. You are the coder. One prompt.

Read: `docs/product-intent.md` P1 and “What it must never claim”,
`src/maintainability_audit/_adapters.py` `_npx`,
`tests/test_promises.py` P1 enforcement,
`tests/test_network_disclosure.py` if present.

## What this is

The small close: **this agent** must not grow an HTTP client and must
not fetch a Node tool unless the user opted into acquisition. It does
**not** sandbox child processes (item 2 / 3 — out of scope).

Today `_npx` returns `("npx", "--yes", tool, …)` when the binary is
missing. That is a silent network fetch during analysis.

## Do (TDD first)

1. **AST lint on `src/`:** no import of `urllib`, `urllib.request`,
   `requests`, `httpx`, `aiohttp`. No `socket.create_connection` /
   `urlopen` used to talk to the internet. Fail the class, not one
   file. Add the test names to `ENFORCEMENT["P1"]` in
   `tests/test_promises.py`.

2. **`_npx` default:** if the binary is not on `PATH`, do **not**
   emit `npx --yes`. The runner must treat that as `not-installed`
   (coverage + environment work order). A test: missing `eslint` /
   `jscpd` on PATH with acquisition off → argv never contains
   `--yes`, outcome is not a silent fetch.

3. **Opt-in acquisition only.** An explicit flag or config key
   (name it in cli.md / config-schema) must be set before `_npx`
   may use `--yes`. Default off. Document that this is acquisition,
   not analysis.

4. **Honesty.** Buyer docs already disclose no-transmit + unpoliced
   children. Do not claim children are air-gapped. Update the
   analyzer-pool `npx` paragraph so it matches the new default
   (fetch is opt-in, not automatic).

## Do not

- Wrap subprocesses in `unshare` / `sandbox-exec` (that is item 2).
- Touch Phase 8 HTML / schema 2 / format ask unless already on the
  branch you were given.
- Import `_bands`. Re-derive `CALIBRATION_C`. Install tools.
- Start 7.5.

## Verify

```
PYTHONPATH=src python3 -m pytest tests/test_promises.py tests/test_network_disclosure.py tests/test_analysis_execution.py -q
```

plus the new P1 tests.

Wrap-up: files, tests, still open.

# 04 Claude — implement 6.1 (first-run TTY prompt)

Repo: maintainability-agent. Current main. This prompt says implement.

You are the coder / implementor. Codex (or the existing test file) wrote
the contract. `tests/test_first_run_prompt.py` exists and must fail on
today's tree because nothing reads `analyzers.prompt_when_interactive`.
Write the product code that makes those three tests pass. Do not replace
the tests with a different contract. Do not stop at tests.

## Exit (release-plan 6.1)

*"Prompts only on a TTY with no config; never in CI; the answer persists."*

The tests already encode that:

1. TTY + no `maintainability-agent.json` → ask depth and license policy
   (catalog vocabulary: `DEPTH_ORDER` and `LICENSE_POLICIES`). Persist
   answers to repo-root `maintainability-agent.json`. Second run on a
   TTY asks nothing.
2. Non-TTY → never call `input`, never write a config.
3. Existing config on a TTY → never call `input`, file stays
   byte-identical.

Answers in the test (`heavy` / `copyleft-weak`) differ from defaults on
purpose. A file that just dumps defaults is not persistence.

## Do

- Read `prompt_when_interactive` and actually prompt when it is true,
  stdin is a TTY, and no config exists.
- Use the same config file `discovered_config` already reads. No second
  persistence mechanism.
- Wire it from the CLI so `main(["--root", ...])` hits it. A helper
  nobody calls is not 6.1.
- Close the class: a lint or test so a stub key that nothing reads
  cannot come back as “shipped.”
- File budget 500 lines, CCN 15.

## Do not

- Prompt in CI / non-TTY.
- Rewrite an existing config.
- Install tools. Touch `_bands`. Add a language ranger. Change scoring.
- Start 2.5c in this prompt.
- Invent flags. `--depth` / `--license-policy` live on
  `tools/resolve_pool.py`; the audit CLI’s non-interactive path is the
  config file.

## Verify

```
PYTHONPATH=src python3 -m pytest tests/test_first_run_prompt.py -q
```

Wrap-up: files changed, tests run, what is still open. No essay.

# CLI Reference

## Audit

```bash
maintainability-agent --config maintainability-agent.json
```

Aliases:

- `maintainability-agent`
- `maintainability-audit`

## MCP server

Install the optional extra, then start the same local MCP server through the package CLI (it writes only the five disclosed config/state artifacts — never source, never a report). The MCP `audit_repository` tool does not audit until configuration is answered and `action` is `run`; see [first run and questions](help/first-run.md):

```bash
python3 -m pip install "maintainability-agent[mcp]"
maintainability-agent mcp --allow-root /absolute/path/to/repository
```

Repeat `--allow-root` to authorize unrelated repository directories. With no explicit root, the server permits only its launch directory. The standalone `maintainability-agent-mcp` console script remains available for existing IDE configurations.

## Options

| Option | Purpose |
|---|---|
| `--root` | Repository root to scan. Defaults to current directory. |
| `--version` | Print the CLI version and exit. |
| `--config` | JSON config path. Optional `economic_context` (ADR 004 v1) is described in [config schema](config-schema.md#economic-context). |
| `--format` | `markdown`, `json` or `html`. Omitted at a terminal, the CLI asks which presentation you want (Enter = chat); in CI it defaults to `markdown` and never asks (ADR 011). |
| `--output` | Report output path. |
| `--html-output` | Write the single-file HTML report (inlined CSS, deterministic SVG charts from the recorded history; opens offline). |
| `--prompt-output` | AI remediation prompt output path. |
| `--comment-output` | PR comment body output path. |
| `--agent-instructions-output` | Audit-specific agent instructions output path. |
| `--sarif-input` | External SARIF file to summarize in the report. Repeatable. |
| `--changed-only` | Git revspec for changed-file-only mode, e.g. `main...HEAD`. |
| `--baseline` | Existing baseline JSON file. |
| `--write-baseline` | Write current findings as a baseline JSON file. |
| `--fail-on-new` | Exit nonzero only for findings not in baseline. |
| `--fail-on-gate` | Exit nonzero when hard gates fail. |
| `--analyzers` | Force the external analyzer pool on, overriding `analyzers.run`. A configured repository runs its pool by default. A complete concept set moves the point estimate; otherwise the built-in fallback stands and the range widens. Missing-tool acquisition is separately controlled by `analyzers.acquire_tools` and defaults off. See [the analyzer pool](analyzer-pool.md). |
| `--no-analyzers` | Force the external analyzer pool off for this invocation, overriding `analyzers.run`. |
| `--work AXIS=VALUE` | Narrow the work order. Repeatable; every criterion must match. Axes: `band`, `finding_class`, `path`, `verification`. Narrowing changes what is shown and never what anything scored. |
| `--record-history` | Create or append this scan to `.maintainability/history.jsonl`. Once the file exists, every later successful scan appends to it and reads the resulting history without another flag. |
| `--backfill REVSPEC` | Scan each commit in a range into the history and exit, e.g. `HEAD~50..HEAD`. Each commit is checked out in a temporary worktree; the working tree is never touched. Expensive, so it never runs as part of a normal scan. |
| `--backfill-interval N` | With `--backfill`, scan every Nth commit instead of all of them. |
| `--sarif-output` | Write SARIF report for GitHub code scanning. |
| `--init-agent-standards` | Generate model/tool-specific instruction files and exit without running an audit. |
| `--install-skill` | Copy the packaged agent skill into the skills directory and exit. Re-run after every upgrade: an installed skill that drifts from the shipped one teaches agents a dead workflow. What it writes is the `_skill_data` payload inside the distribution; the command reads that payload and compares it against what is already installed, and it does not consult the repository. That the payload matches the reviewed `skills/maintainability-agent/SKILL.md` is held by the suite — `tests/test_wheel_contents.py` asserts it byte-for-byte against a staged build — not by a check at run time. |
| `--skills-dir` | Where `--install-skill` writes (default `~/.claude/skills`). |
| `--force-skill` | With `--install-skill`: overwrite a differing installed copy and remove files the package no longer ships. Without it, a differing copy is refused with the list of differences against the packaged payload. |
| `--target` | Instruction target. Repeatable. |
| `--instructions-output-dir` | Output directory for generated instruction files. |

## Examples

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --changed-only main...HEAD \
  --fail-on-gate
```

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --init-agent-standards \
  --target codex \
  --target claude-code \
  --target cursor
```

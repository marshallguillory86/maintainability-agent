# CLI Reference

## Audit

```bash
maintainability-agent --config maintainability-agent.json
```

Aliases:

- `maintainability-agent`
- `maintainability-audit`

## MCP server

Install the optional extra, then start the same read-only MCP server through the package CLI:

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
| `--config` | JSON config path. |
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
| `--analyzers` | Run the external analyzer pool and report its coverage. A complete concept set moves the point estimate; otherwise the built-in fallback stands and the range widens. See [the analyzer pool](analyzer-pool.md). |
| `--work AXIS=VALUE` | Narrow the work order. Repeatable; every criterion must match. Axes: `band`, `finding_class`, `path`, `verification`. Narrowing changes what is shown and never what anything scored. |
| `--record-history` | Append this scan to `.maintainability/history.jsonl`. Opt-in, like every other write. Once the file exists, later runs read it without being asked. |
| `--backfill REVSPEC` | Scan each commit in a range into the history and exit, e.g. `HEAD~50..HEAD`. Each commit is checked out in a temporary worktree; the working tree is never touched. Expensive, so it never runs as part of a normal scan. |
| `--backfill-interval N` | With `--backfill`, scan every Nth commit instead of all of them. |
| `--sarif-output` | Write SARIF report for GitHub code scanning. |
| `--init-agent-standards` | Generate model/tool-specific instruction files and exit without running an audit. |
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

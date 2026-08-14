# CLI Reference

## Audit

```bash
maintainability-agent --config maintainability-agent.json
```

Aliases:

- `maintainability-agent`
- `maintainability-audit`

## Options

| Option | Purpose |
|---|---|
| `--root` | Repository root to scan. Defaults to current directory. |
| `--version` | Print the CLI version and exit. |
| `--config` | JSON config path. |
| `--format` | `markdown` or `json`. |
| `--output` | Report output path. |
| `--prompt-output` | AI remediation prompt output path. |
| `--comment-output` | PR comment body output path. |
| `--agent-instructions-output` | Audit-specific agent instructions output path. |
| `--sarif-input` | External SARIF file to summarize in the report. Repeatable. |
| `--changed-only` | Git revspec for changed-file-only mode, e.g. `main...HEAD`. |
| `--baseline` | Existing baseline JSON file. |
| `--write-baseline` | Write current findings as a baseline JSON file. |
| `--fail-on-new` | Exit nonzero only for findings not in baseline. |
| `--fail-on-gate` | Exit nonzero when hard gates fail. |
| `--analyzers` | Run the external analyzer pool and report its coverage. See [the analyzer pool](analyzer-pool.md). |
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

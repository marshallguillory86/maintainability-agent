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

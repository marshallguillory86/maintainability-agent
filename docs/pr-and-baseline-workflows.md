# PR and Baseline Workflows

Audit only the PR diff:

```bash
maintainability-agent \
  --changed-only main...HEAD \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

Create a baseline for existing debt:

```bash
maintainability-agent \
  --write-baseline maintainability-baseline.json
```

Fail only on findings not present in the baseline:

```bash
maintainability-agent \
  --baseline maintainability-baseline.json \
  --fail-on-new
```

Generate reusable AI coding-agent instructions:

```bash
maintainability-agent \
  --agent-instructions-output AGENTS-maintainability.md
```

Generate persistent agent standards before code is written:

```bash
maintainability-audit \
  --config maintainability-agent.json \
  --init-agent-standards \
  --target codex \
  --target claude-code \
  --target cursor \
  --target copilot \
  --target windsurf \
  --instructions-output-dir .
```

This writes tool-native instruction files such as `AGENTS.md`,
`CLAUDE.md`, `.cursor/rules/maintainability.mdc`,
`.github/copilot-instructions.md`, and
`.windsurf/rules/maintainability.md`.

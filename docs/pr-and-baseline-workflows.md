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

Check a remediating diff against the work order that produced it:

```bash
maintainability-agent \
  --conformance main...HEAD \
  --fail-on-out-of-scope \
  --fail-on-regression \
  --attestation-output maintainability-attestation.md
```

`clean` fails on a suppression directive the diff *added* to a file the work order named, and — since 3.11.0 — on any test file in the diff made unable to fail: a skip or suppression, an assertion that cannot fail, the assertion API replaced, a failing assertion swallowed, or assertions deleted with nothing in their place (`_oracle`, reported as `oracle_weakened`). Held to a precision bar frozen before the detector was written. For work this tool did not order, pass the task's ask with `--ask FILE`.

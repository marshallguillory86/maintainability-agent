# IDE and Agent Integration

This guide shows how to use Maintainability Audit CI with editors and AI coding agents.

The core loop is:

```text
1. Generate standards for the agent before code is written.
2. Let the human/agent make a small patch.
3. Run the audit locally or in CI.
4. Use the generated remediation prompt if the patch drifts.
```

## First-Class Commands

### Run Audit

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --output maintainability-report.md
```

### Generate AI Remediation Prompt

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md
```

### Generate PR Comment Body

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --output maintainability-report.md \
  --comment-output maintainability-pr-comment.md
```

### Audit Only Changed Files

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --changed-only main...HEAD \
  --output maintainability-report.md
```

### Create Baseline

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --write-baseline maintainability-baseline.json
```

### Fail Only on New Findings

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --baseline maintainability-baseline.json \
  --fail-on-new
```

### Generate Agent Standards

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target generic \
  --target codex \
  --target claude-code \
  --target cursor \
  --target copilot \
  --target windsurf \
  --instructions-output-dir .
```

Generated files:

| Target | File |
|---|---|
| generic | `AI-MAINTAINABILITY.md` |
| codex | `AGENTS.md` |
| claude-code | `CLAUDE.md` |
| cursor | `.cursor/rules/maintainability.mdc` |
| copilot | `.github/copilot-instructions.md` |
| windsurf | `.windsurf/rules/maintainability.md` |

## VS Code

VS Code itself does not enforce agent behavior, but it can run the audit as a task and expose the generated prompt/report to Copilot Chat, Codex, Claude Code, or any terminal-based agent.

Add `.vscode/tasks.json` to the target repo:

```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Maintainability: Audit",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-audit.json --output maintainability-report.md --prompt-output maintainability-remediation-prompt.md --comment-output maintainability-pr-comment.md",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Maintainability: Changed Only",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-audit.json --changed-only main...HEAD --output maintainability-report.md --prompt-output maintainability-remediation-prompt.md",
      "group": "test",
      "problemMatcher": []
    },
    {
      "label": "Maintainability: Init Agent Standards",
      "type": "shell",
      "command": "maintainability-audit --config maintainability-audit.json --init-agent-standards --target generic --target codex --target claude-code --target cursor --target copilot --target windsurf --instructions-output-dir .",
      "group": "build",
      "problemMatcher": []
    }
  ]
}
```

Suggested VS Code workflow:

1. Run `Maintainability: Init Agent Standards`.
2. Ask the agent to follow the generated repo instruction file.
3. Make changes.
4. Run `Maintainability: Changed Only`.
5. If it fails, give the agent `maintainability-remediation-prompt.md`.

## GitHub Copilot

GitHub Copilot can use repository custom instructions from:

```text
.github/copilot-instructions.md
```

Generate it:

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target copilot \
  --instructions-output-dir .
```

Recommended prompt to Copilot Chat:

```text
Follow .github/copilot-instructions.md. Fix only the findings in maintainability-remediation-prompt.md. Keep the patch small and preserve current behavior unless the report says behavior is wrong.
```

## Cursor

Cursor rules can live under:

```text
.cursor/rules/maintainability.mdc
```

Generate it:

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target cursor \
  --instructions-output-dir .
```

Recommended Cursor workflow:

1. Generate Cursor rules.
2. Run the audit.
3. Open `maintainability-remediation-prompt.md`.
4. Ask Cursor to apply only that prompt.

## Codex

Codex-style repo instructions can use:

```text
AGENTS.md
```

Generate it:

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target codex \
  --instructions-output-dir .
```

Recommended Codex prompt:

```text
Follow AGENTS.md. Use maintainability-report.md and maintainability-remediation-prompt.md as the source of truth. Fix the highest-severity maintainability findings only, with tests where behavior changes.
```

## Claude Code

Claude Code-style repo instructions can use:

```text
CLAUDE.md
```

Generate it:

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target claude-code \
  --instructions-output-dir .
```

Recommended Claude prompt:

```text
Read CLAUDE.md, maintainability-report.md, and maintainability-remediation-prompt.md. Make a small patch that resolves the hard gates. Do not refactor outside the reported scope.
```

## Windsurf

Windsurf rules can be stored at:

```text
.windsurf/rules/maintainability.md
```

Generate it:

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target windsurf \
  --instructions-output-dir .
```

## Generic Agents

For any other agent, generate:

```text
AI-MAINTAINABILITY.md
```

```bash
maintainability-agent \
  --config maintainability-audit.json \
  --init-agent-standards \
  --target generic \
  --instructions-output-dir .
```

Then prompt:

```text
Follow AI-MAINTAINABILITY.md. Use maintainability-remediation-prompt.md as the bounded task. Keep the patch small, testable, and aligned with existing architecture.
```

## Local CI

For repos that do not use GitHub Actions:

```bash
examples/local-ci.sh
```

Or copy the command:

```bash
maintainability-audit \
  --config maintainability-audit.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

## GitHub Actions

Use `.github/workflows/maintainability.yml` from this repo as a starting point.

Artifacts:

- `maintainability-report.md`
- `maintainability-remediation-prompt.md`
- `maintainability-pr-comment.md`

## Recommended Human Workflow

Do not let an AI agent blindly auto-fix everything.

Use this sequence:

1. Review `maintainability-report.md`.
2. Decide which hard gates or high-value findings matter.
3. Give the agent `maintainability-remediation-prompt.md`.
4. Review the patch.
5. Run native tests/lints.
6. Run the audit again.
7. Commit only bounded, explainable changes.

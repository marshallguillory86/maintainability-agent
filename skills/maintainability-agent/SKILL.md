---
name: maintainability-agent
description: Use when the agent needs to run or respond to maintainability-agent audits, generate bounded remediation prompts, initialize AI coding-agent standards, interpret maintainability reports, or make small maintainability fixes without broad rewrites.
---

# Maintainability Agent

## Purpose

Use the `maintainability-agent` CLI as the source of truth for deterministic maintainability gates and bounded AI remediation prompts. Treat the tool as a guardrail for small, reviewable engineering changes, not as permission to refactor unrelated code.

## Core Workflow

1. Inspect the repo's existing instructions and config before running anything:
   - `AGENTS.md`, `CLAUDE.md`, or other local agent instruction files.
   - `maintainability-agent.json` when present.
   - The repo's native CI/test commands.
2. Prefer the repo's configured command when it exists. Otherwise use:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

3. For branch or PR work, use a changed-file audit when the base branch is known:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --changed-only main...HEAD \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md
```

4. If the audit emits `maintainability-remediation-prompt.md`, read it before editing and treat it as the bounded task.
5. Fix only the reported hard gates or highest-value findings. Keep unrelated cleanup as follow-up notes.
6. Re-run the audit and any native tests/lints required by the repo.
7. Report the commands run, whether the maintainability gate passed, and any remaining false positives or follow-ups.

## Installing Or Running

If `maintainability-agent` is missing from `PATH`, do not assume the repo is unwired. Check project docs first. Common options are:

```bash
python3 -m pip install maintainability-agent
python3 -m pip install -e .
python3 -m maintainability_audit --config maintainability-agent.json
```

Use the local repo or virtualenv command preferred by the project. If install or execution needs network or elevated permissions, ask for approval through the normal tool flow.

## Generating Agent Standards

When asked to add maintainability standards for AI coding tools, use the CLI rather than hand-writing each target file:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --init-agent-standards \
  --target codex \
  --target claude-code \
  --target cursor \
  --target copilot \
  --target windsurf \
  --instructions-output-dir .
```

Generated standards are additive to repository-specific rules. When they conflict, the repo-specific rules win.

## Remediation Rules

- Preserve existing architecture, naming, module boundaries, and behavior unless the finding directly concerns them.
- Prefer boring, obvious code over clever abstractions.
- Add tests for meaningful behavior changes; avoid tests that only lock implementation details.
- Consolidate duplication only when the duplicated logic has the same business meaning.
- Explain false positives or justified complexity instead of contorting clear code to satisfy a metric.
- Do not bundle "while here" refactors into a maintainability patch.

For interpretation guidance, read `references/finding-taxonomy.md` only when the audit report needs judgment.

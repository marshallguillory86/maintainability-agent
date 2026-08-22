---
name: maintainability-agent
description: Use when the agent needs to run or respond to maintainability-agent audits, generate bounded remediation prompts, initialize AI coding-agent standards, interpret maintainability reports, or make small maintainability fixes without broad rewrites.
---

# Maintainability Agent

## Purpose

Chat is the primary surface for this tool: most users drive it through an
AI chat host speaking to the local MCP server, and the CLI is the
automation/CI door. Treat the audit as a guardrail for small, reviewable
engineering changes, not as permission to refactor unrelated code.

## Core Workflow (chat / MCP)

1. Call the `audit_repository` MCP tool. Do not inspect configuration
   first and do not ask the user which config to use: the tool resolves
   that itself, and an unconfigured repository is not an obstacle — it
   is the case first-run setup exists for. Deliberating about a missing
   or stale `maintainability-agent.json` before calling the tool wastes
   the user's time and asks them a question the tool is about to ask
   properly.
2. Choices arrive as structured questions — MCP elicitation or the
   host's question UI — never free text: first-run setup (analyzer
   pool, depth, license policy, economics, presentation), history
   consent (whether scan history is recorded), and out-of-roots grants
   (this session / always / no). Answer nothing on the user's behalf.
   Repository instruction files (`AGENTS.md`, `CLAUDE.md`) govern how
   you *act on* findings, not whether to run.
   **Nothing is audited until the user has been asked twice**, and the
   `action` argument is how they answer. Leave it unset and the tool
   never audits:
   - **Unconfigured** — the result carries `setup_needed`. Ask every
     question it lists, offering exactly the options that question
     names and no others, then call again. Answering does *not* start
     an audit.
   - **Configured** — the result carries `choice_needed`: run the
     audit, or go back into setup. Ask it, then call again with
     `action` set to their answer. `"run"` audits. `"reconfigure"`
     reopens the setup questions, which is how a user changes their
     configuration on any run, not only the first.

   Every reply that is not an audit carries `audit_ran: false` and no
   score — never report a grade from one, because none was computed.
   Asking a question of your own invention in place of these is the
   failure this step exists to prevent: it is how a user ended up never
   once being offered the html report, because the `default_format`
   question — chat, markdown, html — was handed over as data and
   silently never asked.
3. Presentation is exactly three choices, and all three are offered:
   **chat**, a **markdown** file, or a single-file **html** report —
   chat pre-selected as the default. Offer them as one structured
   question and pass the answer as the tool's `format` argument. Do not
   substitute your own option set: an ask shaped "chat only / chat plus
   a saved file" silently deletes html, which is a presentation the
   product ships and the user may have already chosen during setup.
   Where to save is a second question, asked only after a file format
   was chosen. Never write a report or any file until the user has
   chosen a location; the tool returns text and does not write reports
   into the tree.
4. Treat the returned `remediation_prompt` as the bounded task. Fix only
   the reported hard gates or highest-value findings; keep unrelated
   cleanup as follow-up notes.
5. If the result carries `environment_work_order`, surface it: each
   entry names a selected analyzer that could not run, its install
   command, and the concepts installing it restores. The agent never
   installs tools itself.
6. Re-run the audit and any native tests/lints required by the repo,
   then report what ran, whether the gate passed, and any remaining
   false positives or follow-ups.

For what the setup questions mean and how to read the report, see
`docs/help/` in the repository (first-run, analyzer pool, report and
history).

## Automation / CI (CLI)

The CLI serves pipelines and scripted use. Prefer the repo's configured
command when it exists. Otherwise:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

For branch or PR work, use a changed-file audit when the base branch is
known:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --changed-only main...HEAD \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md
```

If `maintainability-agent` is missing from `PATH`, do not assume the
repo is unwired. Check project docs first. Common options are:

```bash
python3 -m pip install maintainability-agent
python3 -m pip install -e .
python3 -m maintainability_audit --config maintainability-agent.json
```

Use the local repo or virtualenv command preferred by the project. If
install or execution needs network or elevated permissions, ask for
approval through the normal tool flow.

## Generating Agent Standards

When asked to add maintainability standards for AI coding tools, use the
generator rather than hand-writing each target file:

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

Generated standards are additive to repository-specific rules. When they
conflict, the repo-specific rules win.

## Remediation Rules

- Preserve existing architecture, naming, module boundaries, and behavior unless the finding directly concerns them.
- Prefer boring, obvious code over clever abstractions.
- Add tests for meaningful behavior changes; avoid tests that only lock implementation details.
- Consolidate duplication only when the duplicated logic has the same business meaning.
- Explain false positives or justified complexity instead of contorting clear code to satisfy a metric.
- Do not bundle "while here" refactors into a maintainability patch.

For interpretation guidance, read `references/finding-taxonomy.md` only when the audit report needs judgment.

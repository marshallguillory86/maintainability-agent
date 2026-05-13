# Changelog

All notable changes to Maintainability Agent will be documented here.

## 0.2.0 - 2026-05-12

- Adds a portable invokable skill under `skills/maintainability-agent/` that drops into Codex, Claude Code, and GitHub Copilot Chat so `/maintainability-agent` is one keystroke away in any of them.
- Adds per-host adapters: `agents/openai.yaml` (Codex, already present), `agents/anthropic.yaml` (Claude Code install paths), `agents/copilot.yaml` (Copilot prompt-file source/destination).
- Adds `copilot/maintainability-agent.prompt.md` — VS Code Copilot Chat prompt file shaped for Copilot's prompt-file frontmatter; reuses the SKILL.md body verbatim.
- Documents the new install paths in README ("Invokable Skill / Slash Command" section + 5th bullet in the feature list).
- Updates SKILL.md description so Claude's relevance ranker fires correctly while staying valid for Codex.

## 0.1.0 - 2026-05-11

- Initial local implementation of deterministic maintainability auditing.
- Adds Markdown, JSON, SARIF, PR comment, baseline, and AI remediation prompt outputs.
- Adds model/tool-specific instruction generation for Claude Code, Codex, Cursor, Copilot, Windsurf, and generic agents.
- Adds 92% coverage gating, `coverage.xml` output, SonarQube Cloud starter config, and external quality-tool readiness docs.
- Self-audit on this codebase: **5.0 / 5 (A+)**, zero warnings across every category. Checked in at [docs/self-audit.md](docs/self-audit.md).

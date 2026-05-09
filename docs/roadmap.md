# Roadmap

This project should stay a thin orchestration and prompt layer, not a replacement for mature analyzers.

## Current Scope

- Dependency-light native scanner.
- Markdown and JSON reports.
- AI remediation prompt generation.
- PR comment body generation.
- Changed-only audit mode.
- Baseline/new-finding gating.
- AI agent instruction output.
- Tool-specific maintainability instruction pack generation.
- SARIF ingest and emit with rule metadata.
- ISO/IEC 25010-inspired scoring.

## Near-Term

1. **Analyzer adapters**
   - Semgrep JSON/SARIF.
   - ESLint JSON.
   - Ruff JSON.
   - Radon JSON.
   - Pytest/coverage summaries.
   - SonarQube API export where configured.

2. **Prompt packs**
   - richer `claude-code-prompt.md`
   - richer `codex-prompt.md`
   - richer `cursor-prompt.md`
   - richer `github-copilot-prompt.md`
   - `human-reviewer-summary.md`

3. **Policy-as-code**
   - New code thresholds.
   - Changed-file-only thresholds.
   - Required tests for changed service/API files.
   - Forbidden mass-rewrite patterns.
   - Architecture boundary rules by path.

4. **AI-written-code risk labels**
   - speculation
   - over-abstraction
   - duplicated helper
   - untested behavior
   - architecture drift
   - security footgun
   - stale generated comments
   - unsupported public claim

## Later

- GitHub app or action wrapper that posts/updates PR comments.
- GitLab/Azure DevOps comment adapters.
- Historical trend report.
- HTML dashboard.
- Config generator for existing repos.
- Maintainer-approved autofix patch bundles, still human-reviewed.

## Non-Goals

- Replace SonarQube, Semgrep, Qlty, Code Climate, ESLint, Ruff, Radon, or language-native tooling.
- Automatically rewrite repos.
- Send code to an LLM by default.
- Treat maintainability as purely numeric.

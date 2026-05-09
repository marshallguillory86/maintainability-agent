# Maintainability Agent

A dependency-light maintainability audit tool for Git repositories.

This project turns maintainability review into a repeatable CI check without pretending that a single metric can judge a codebase. It combines:

- ISO/IEC 25010 maintainability categories
- objective code signals such as size, complexity, duplication, and risk patterns
- configurable hard gates for CI
- coverage gating at a configurable project threshold
- Markdown and JSON reports
- a generated AI remediation prompt for human-reviewed AI coding sessions
- PR comment, agent-instruction, and baseline/new-debt outputs
- model/tool-specific maintainability instruction packs

It is intended for public GitHub repos, private repos, and local CI runners.

## Why

Maintainability is the cost and confidence level of making future changes.

This tool answers:

> Can a competent developer make a normal change quickly, confidently, and with tests that catch likely mistakes?

## Install

Run directly from source:

```bash
python3 -m maintainability_audit \
  --root . \
  --config maintainability-agent.json \
  --output maintainability-report.md
```

Or install editable during development:

```bash
python3 -m pip install -e .
maintainability-audit --root . --config maintainability-agent.json
maintainability-agent --root . --config maintainability-agent.json
```

## Quick Start

Copy the example config to your repo root as `maintainability-agent.json`:

```bash
cp maintainability-audit.example.json maintainability-agent.json
```

Run:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --format markdown \
  --output maintainability-report.md
```

Fail CI on hard gates:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md
```

## What It Checks

- largest files
- approximate function/class size
- approximate cyclomatic complexity
- duplicate blocks
- ISO/IEC 25010-inspired 0-5 score and letter grade
- expected files
- expected test/lint commands
- dirty worktree gate, if enabled
- configurable risk patterns
- AI remediation prompt generation
- changed-only PR audits
- baseline/new-finding gates
- PR comment generation
- AI agent instruction generation
- agent standards initialization for Claude Code, Codex, Cursor, Copilot, Windsurf, and generic tools

The built-in analyzer is intentionally conservative and dependency-free. Mature repos should pair it with native tools such as ESLint, Ruff, Radon, Semgrep, SonarQube, or Qlty/Code Climate.

## AI Remediation Prompt

The runner can generate a bounded prompt for a human developer to give to Claude, Codex, or another coding assistant:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md
```

The prompt is designed for AI-written or AI-assisted code reviews. It tells the assistant to:

- fix only the highest-value maintainability issues
- keep the patch small and reviewable
- preserve existing architecture and behavior
- add tests where behavior changes
- report false positives instead of rewriting blindly

This makes the CI artifact actionable without letting the audit turn into an unbounded refactor request.

## PR and Baseline Workflows

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

This writes tool-native instruction files such as `AGENTS.md`, `CLAUDE.md`, `.cursor/rules/maintainability.mdc`, `.github/copilot-instructions.md`, and `.windsurf/rules/maintainability.md`.

## Running Tests

```bash
# Sandbox-friendly invocation (works with PYTEST_DISABLE_PLUGIN_AUTOLOAD=1):
PYTHONPATH=src python3 -m pytest

# With coverage gate (matches CI):
PYTHONPATH=src python3 -m pytest \
  --cov=maintainability_audit --cov-fail-under=92

# With ruff lint + pip-audit (matches CI):
python3 -m pip install -e ".[dev]"
ruff check src tests
pip-audit
PYTHONPATH=src python3 -m pytest --cov=maintainability_audit --cov-fail-under=92
```

Coverage is intentionally NOT in `[tool.pytest.ini_options].addopts` so the
sandbox-friendly invocation (`PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`) doesn't choke
on `--cov` flags it can't load. Pass coverage flags explicitly when you want
the gate.

## Scoring Standard

The audit model is based on ISO/IEC 25010 maintainability:

- modularity
- reusability
- analyzability
- modifiability
- testability

See [docs/standard.md](docs/standard.md).

## Project Docs

- [CLI reference](docs/cli.md)
- [Config schema](docs/config-schema.md)
- [Philosophy](docs/philosophy.md)
- [Analyzer adapters](docs/adapters.md)
- [External quality tools](docs/external-quality-tools.md)
- [IDE and agent integration](docs/ide-agent-integration.md)
- [Roadmap](docs/roadmap.md)

## GitHub Action

This repo includes `action.yml`, so it can be used as a composite action after publishing:

```yaml
- uses: marshallguillory86/maintainability-agent@v0.1.0
  with:
    config: maintainability-agent.json
    changed-only: main...HEAD
```

## GitHub Actions

After publishing, copy `.github/workflows/maintainability.yml` into the target repo or adapt it for your local CI.

## IDE and Agent Integration

See [docs/ide-agent-integration.md](docs/ide-agent-integration.md) for VS Code tasks and integration notes for Copilot, Cursor, Codex, Claude Code, Windsurf, generic agents, local CI, and GitHub Actions.

## Local CI

For repos that do not use GitHub Actions, use:

```bash
examples/local-ci.sh
```

The local CI script enforces test coverage at `>=92%` and writes `coverage.xml` for SonarQube Cloud, Qlty, Codacy, or any other tool that can ingest Python coverage.

## License

MIT

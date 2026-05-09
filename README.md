# Maintainability Agent

A deterministic CI gate + bounded remediation prompt generator for repos that use AI coding agents (Claude, Codex, Cursor, Copilot, Windsurf, …).

## Why this exists

AI-written code fails in recognizable ways: speculative refactors, duplicated helpers, broad rewrites for narrow bugs, stale comments that sound confident, tests that assert implementation details instead of behavior, architecture drift across modules. SonarQube / CodeClimate / Qlty / ESLint / Ruff / Radon all catch some of this. None of them ship a **bounded prompt back to the agent** that says *"fix only these specific findings, do not refactor outside this scope."*

That's the point of this tool:

1. Run a deterministic local audit — file size, function size, approximate cyclomatic complexity, duplication, configurable risk patterns, ISO/IEC 25010-inspired 0–5 score.
2. Emit Markdown, JSON, SARIF, a PR comment, and a baseline for incremental adoption.
3. Generate an **AI remediation prompt scoped to the actual findings** — bounded, with explicit "don't rewrite the codebase" rules.
4. Hand that prompt to your agent. Get a small, reviewable fix instead of a 600-line speculative cleanup PR.

The remediation prompt is the differentiator. Every other tool in this space stops at "here's a list of findings."

## Who it's for

- Teams running AI agents in the dev loop who are tired of unbounded agent rewrites and want a CI gate that actively constrains follow-up scope.
- Repos that want a maintainability gate without paying for SonarQube / CodeClimate / Qlty or sending code to a third party.
- Solo devs who want a single-binary deterministic audit they can pin in a Makefile, a pre-commit, or a local CI script.

## Design principles

- **Deterministic first, AI optional.** The audit never calls an LLM by default. The remediation prompt is a generated artifact that you choose to hand to an agent.
- **Bounded scope.** The remediation prompt explicitly tells the agent to fix the listed findings only — not to embark on architecture cleanup.
- **No vendor lock-in.** All outputs (Markdown, JSON, SARIF, PR comment) are plain files. Pair this tool with mature analyzers (ESLint, Ruff, Radon, Semgrep, SonarQube, Qlty/Code Climate) — don't replace them.
- **Pass-the-cost-of-disclosure.** A finding that's "just a warning" never blocks CI alone. Hard gates are configurable + opt-in.

See [docs/philosophy.md](docs/philosophy.md) for the longer version.

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

## What It Analyzes

The deterministic scanner reads code from your repo (no LLM calls) and produces signals on:

- largest files (warn / fail thresholds configurable per-repo)
- approximate function/class size
- approximate cyclomatic complexity
- duplicate blocks (≥ N consecutive non-trivial lines, configurable)
- configurable risk patterns (regex matchers — TODO/FIXME, `eval(`, `exec(`, custom)
- expected files present (README, LICENSE, etc. — opt-in hard gate)
- expected test/lint commands declared in the config (opt-in hard gate)
- worktree-clean state at audit time (opt-in hard gate)
- ISO/IEC 25010-inspired 0–5 score per category + overall letter grade

The analyzer is intentionally conservative and dependency-free. Mature repos should **pair** this with native tools (ESLint, Ruff, Radon, Semgrep, SonarQube, Qlty / Code Climate) — not replace them. SARIF input from those tools can be folded into this tool's report via `--sarif-input`.

## What It Produces

Each run can emit any combination of:

- `maintainability-report.md` — the full Markdown report with summary, score, hotspots, duplicates, risk findings, external (SARIF) findings.
- `maintainability-remediation-prompt.md` — bounded AI prompt scoped to the run's findings.
- `maintainability-pr-comment.md` — short body suitable for a `gh pr comment` post.
- `maintainability.sarif` — SARIF 2.1.0 output for GitHub Code Scanning ingestion.
- `maintainability-baseline.json` — fingerprints of current findings, for `--fail-on-new` incremental adoption.
- Per-tool agent instruction files (`AGENTS.md`, `CLAUDE.md`, `.cursor/rules/maintainability.mdc`, `.github/copilot-instructions.md`, `.windsurf/rules/maintainability.md`, `AI-MAINTAINABILITY.md`) via `--init-agent-standards`.

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

## Documentation

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

## Get in Touch

- **Bug reports / feature requests / general questions** — open a [GitHub Issue](https://github.com/marshallguillory86/maintainability-agent/issues/new).
- **Discussion / ideas** — use the [Discussions tab](https://github.com/marshallguillory86/maintainability-agent/discussions) (enable in repo settings if not visible yet).
- **Security vulnerabilities** — see [`SECURITY.md`](SECURITY.md) and use the [private security advisory flow](https://github.com/marshallguillory86/maintainability-agent/security/advisories/new). Do **not** post vulnerabilities in public issues.

## License

MIT

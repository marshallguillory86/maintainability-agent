# Maintainability Agent

A deterministic CI gate + bounded remediation prompt generator for repos that use AI coding agents (Claude, Codex, Cursor, Copilot, Windsurf, …) — **ships an invokable skill for Codex, Claude Code, and GitHub Copilot Chat** so `/maintainability-agent` is one keystroke away in any of them.

```bash
pip install maintainability-agent          # CLI + library
cp -r skills/maintainability-agent ~/.claude/skills/                                  # Claude Code skill
cp skills/maintainability-agent/copilot/maintainability-agent.prompt.md .github/prompts/  # Copilot Chat (VS Code)
# Codex picks up skills/maintainability-agent/ via its own convention.
```

Jump to [Invokable Skill / Slash Command](#invokable-skill--slash-command) for the full install table.

> **v0.4.0** rewrote TypeScript/JavaScript declaration detection — ranges are bounded by their own braces instead of by the next regex match, which had been reporting a 4-line function as 262 lines and grading clean files an F. Details in the [changelog](CHANGELOG.md) and [docs/language-support.md](docs/language-support.md).

## Why this exists

AI-written code fails in recognizable ways: speculative refactors, duplicated helpers, broad rewrites for narrow bugs, stale comments that sound confident, tests that assert implementation details instead of behavior, architecture drift across modules. SonarQube / CodeClimate / Qlty / ESLint / Ruff / Radon all catch some of this. None of them ship a **bounded prompt back to the agent** that says *"fix only these specific findings, do not refactor outside this scope."*

That's the point of this tool:

1. Run a deterministic local audit — file size, function size, approximate cyclomatic complexity, duplication, configurable risk patterns, ISO/IEC 25010-inspired 0–5 score.
2. Emit Markdown, JSON, SARIF, a PR comment, and a baseline for incremental adoption.
3. Generate an **AI remediation prompt scoped to the actual findings** — bounded, with explicit "don't rewrite the codebase" rules.
4. Hand that prompt to your agent. Get a small, reviewable fix instead of a 600-line speculative cleanup PR.
5. Drop the shipped **portable invokable skill** into Codex, Claude Code, or GitHub Copilot Chat so `/maintainability-agent` is one keystroke away in any of them. See [Invokable Skill](#invokable-skill--slash-command) below.

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

## Self-Audit

This repo eats its own dogfood — the tool is run against this codebase as part of CI, and the latest report is checked in at [docs/self-audit.md](docs/self-audit.md):

| Metric | Value |
|---|---:|
| Overall score | **5.0 / 5 (A+)** |
| Files scanned | 54 |
| File warnings | 0 |
| File failures | 0 |
| Function warnings | 0 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

All five ISO/IEC 25010 categories (modularity, reusability, analyzability, modifiability, testability) score 5.0, against thresholds this repo deliberately sets stricter than the shipped defaults — a 250-line file warning versus the default 400.

That grade is maintained, not assumed. The v0.4.0 work initially pushed this repo to 4.4 / 5 (B): four files had grown past the warn threshold. Rather than publish a fix while advertising a stale A+, `metrics.py` was split along its actual responsibilities (`declarations`, `duplication`, `report`), the two oversized test files were split to match, and this README's duplicated content moved into the docs it duplicated. The score is the output of that work, not a claim that preceded it.

Regenerate with `maintainability-agent --config maintainability-agent.json --output docs/self-audit.md` (see the file's preamble for the path-sanitization step).

## Install

```bash
python3 -m pip install maintainability-agent
maintainability-agent --root . --config maintainability-agent.json
```

Or run from a source checkout without installing:

```bash
python3 -m maintainability_audit --root . --config maintainability-agent.json
```

For an editable dev install, see [CONTRIBUTING.md](CONTRIBUTING.md#local-verification).

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
- function size and complexity — exact ranges for Python via `ast`, brace-bounded for JS/TS/JSX/TSX/HTML
- class size, against its own separate budget (`max_class_lines`), on length alone
- approximate cyclomatic complexity
- duplicate blocks (≥ N consecutive non-trivial lines, configurable)
- configurable risk patterns (regex matchers — TODO/FIXME, `eval(`, `exec(`, custom)
- expected files present (README, LICENSE, etc. — opt-in hard gate)
- expected test/lint commands declared in the config (opt-in hard gate)
- worktree-clean state at audit time (opt-in hard gate)
- ISO/IEC 25010-inspired 0–5 score per category + overall letter grade

The analyzer is intentionally conservative and dependency-free. It is built to **under-report rather than over-report**: a declaration it can't recognize costs one missed finding, never a cascade of false ones. Per-language accuracy, the known limitations, and why classes are graded separately are documented in [docs/language-support.md](docs/language-support.md).

Mature repos should **pair** this with native tools (ESLint, Ruff, Radon, Semgrep, SonarQube, Qlty / Code Climate) — not replace them. SARIF input from those tools can be folded into this tool's report via `--sarif-input`.

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

PR-only audits, baseline grandfathering, AI-agent instruction
generation, and reusable agent-standard file generation are covered
in [PR and Baseline Workflows](docs/pr-and-baseline-workflows.md).

## Running Tests

```bash
PYTHONPATH=src python3 -m pytest
```

The full local verification sequence that matches CI — ruff, pip-audit, the 92% coverage gate, and the self-audit — is in [CONTRIBUTING.md](CONTRIBUTING.md#local-verification), along with the sandbox-friendly invocation for agents that disable plugin autoload.

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
- [Language support and detection accuracy](docs/language-support.md)
- [Philosophy](docs/philosophy.md)
- [Changelog](CHANGELOG.md)
- [Analyzer adapters](docs/adapters.md)
- [External quality tools](docs/external-quality-tools.md)
- [IDE and agent integration](docs/ide-agent-integration.md)
- [PR and baseline workflows](docs/pr-and-baseline-workflows.md)
- [Roadmap](docs/roadmap.md)

## GitHub Action

This repo includes `action.yml`, so it can be used as a composite action:

```yaml
- uses: marshallguillory86/maintainability-agent@v0.4.0
  with:
    config: maintainability-agent.json
    changed-only: main...HEAD
```

Or copy `.github/workflows/maintainability.yml` into the target repo and adapt it.

## IDE and Agent Integration

See [docs/ide-agent-integration.md](docs/ide-agent-integration.md) for VS Code tasks and integration notes for Copilot, Cursor, Codex, Claude Code, Windsurf, generic agents, local CI, and GitHub Actions.

## Invokable Skill / Slash Command

For agents that support invokable skills, this repo ships a portable skill under [`skills/maintainability-agent/`](skills/maintainability-agent/). The `SKILL.md` body is the source of truth; per-host adapters live under `agents/` and `copilot/`.

| Host | Install destination | Invocation |
|---|---|---|
| Codex / OpenAI | wired via `skills/maintainability-agent/agents/openai.yaml` | per Codex's skills convention |
| Claude Code | copy `skills/maintainability-agent/` → `~/.claude/skills/maintainability-agent/` (user-scope) or `<repo>/.claude/skills/maintainability-agent/` (project-scope) | `/maintainability-agent` (or surfaced automatically when description matches) |
| GitHub Copilot (VS Code) | copy `skills/maintainability-agent/copilot/maintainability-agent.prompt.md` → `<repo>/.github/prompts/maintainability-agent.prompt.md` | `/maintainability-agent` in Copilot Chat |

The copy commands are in the [intro block](#maintainability-agent) at the top of this file. For non-invokable, always-on guidance, use `--init-agent-standards` (see [docs/ide-agent-integration.md](docs/ide-agent-integration.md)).

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

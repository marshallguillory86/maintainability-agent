# Maintainability Agent

A deterministic CI gate + bounded remediation prompt generator for repos that use AI coding agents (Claude, Codex, Cursor, Copilot, Windsurf, …) — **ships an invokable skill for Codex, Claude Code, and GitHub Copilot Chat** so `/maintainability-agent` is one keystroke away in any of them.

```bash
pip install maintainability-agent          # CLI + library
pip install "maintainability-agent[mcp]"   # optional local MCP server for Codex / VS Code
cp -r skills/maintainability-agent ~/.claude/skills/                                  # Claude Code skill
cp skills/maintainability-agent/copilot/maintainability-agent.prompt.md .github/prompts/  # Copilot Chat (VS Code)
# Codex picks up skills/maintainability-agent/ via its own convention.
```

Jump to [Invokable Skill / Slash Command](#invokable-skill--slash-command) for the full install table.

**0.7.0** withholds a score when the evidence cannot support one — a `--changed-only` diff is not a repository grade, and a tree smaller than the calibration population is not a 5.0. External analyzers (`--analyzers`) are the primary evidence where they measured a full concept set; the built-in detectors remain the fallback, and disagreement widens the range rather than being averaged. Two incompatibilities from 0.6: report schema version 3 (nullable estimate) and baseline format version 2. See [docs/migration-0.7.md](docs/migration-0.7.md). After 0.7.0 the scale moved and `--analyzers` moves the point estimate; see [docs/migration-1.0.md](docs/migration-1.0.md).

> **Retracted: the claim that near-duplication distinguishes AI-written code.** It was called "the first signal that separates AI-written applications from mature human-written OSS". 0.6.0 reported near-duplication at 1.49% for AI-written applications against 0.20% for human-written OSS, comparing six young applications against twelve decade-old libraries. Authorship, age, domain and size all differed at once. Re-run against a control matched on age, popularity and language, the near-duplication gap is not significant (p = 0.546), and no other metric earns the claim either. The AI figure barely moved (1.49% to 1.73%); the control moved, from 0.20% to 0.83%, because it stopped being decade-old libraries. The replacement study has its own stated limits (small n, size handled post-hoc, and a control that cannot be verified as human), so the honest summary is "this design could not measure a difference", not "there is no difference". See [docs/studies.md](docs/studies.md#does-this-detect-ai-written-code).
>
> **v0.6.0 detects a helper written twice under two names** — clone-instead-of-reuse, the most-cited complaint about AI-written code. Renamed copies defeat text matching, so bodies are compared structurally with identifiers anonymized. Each finding names the declaration to reuse, so the prompt says *`toAtomicAmount` at `TradeTicket.tsx:862` already does this* rather than "there is duplication". It is a useful finding on its own terms; it is not evidence about who wrote the code.
>
> **v0.5.0 rebuilt the scoring engine.** The old model counted findings absolutely, so it scored repo *size* rather than maintainability: it graded **Django, pytest, black, tornado, click, httpx, attrs, lodash, svelte, axios and fastapi all at 0.0 / F** while a 53-file toy repo scored 4.6 / A. Scores are now rates, normalized per dimension against what real code carries, and calibrated so the corpus median earns a B. See [docs/standard.md](docs/standard.md#how-the-scale-was-calibrated-050).

## Why this exists

Agents produce code faster than humans can review it. Not measurably *worse* code — this project tested its own claim that AI code fails in recognizably different ways, and retracted it — just **more** code, arriving faster than trust can accumulate: duplicated helpers, oversized files, speculative abstractions, the same slop hand-written codebases have always accumulated, now at machine speed. SonarQube / CodeClimate / Qlty / ESLint / Ruff / Radon all catch some of this. None of them ship a **bounded prompt back to the agent** that says *"fix only these specific findings, do not refactor outside this scope."*

That's the point of this tool:

1. Run a deterministic local audit — file size, function size, approximate cyclomatic complexity, duplication, configurable risk patterns, and an ISO/IEC 25010-inspired 0–5 estimate that is withheld when the evidence cannot support one.
2. Emit Markdown, JSON, SARIF, a PR comment, and a baseline for incremental adoption.
3. Generate an **AI remediation prompt scoped to the actual findings** — bounded, with explicit "don't rewrite the codebase" rules.
4. Hand that prompt to your agent. One pre-registered experiment has tested this: Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count. The registered hypothesis was *narrower* diffs and it did not hold, so the registered verdict stands at **INCONCLUSIVE**. Method, limits and raw data: [docs/studies.md](docs/studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered).
5. Drop the shipped **portable invokable skill** into Codex, Claude Code, or GitHub Copilot Chat so `/maintainability-agent` is one keystroke away in any of them. See [Invokable Skill](#invokable-skill--slash-command) below.

The remediation prompt is the differentiator. Every other tool in this space stops at "here's a list of findings."

## Who it's for

- Teams running AI agents in the dev loop who are tired of unbounded agent rewrites and want a CI gate that actively constrains follow-up scope.
- Repos that want a maintainability gate without paying for SonarQube / CodeClimate / Qlty or sending code to a third party.
- Solo devs who want a single-binary deterministic audit they can pin in a Makefile, a pre-commit, or a local CI script.

## Design principles

- **Deterministic first, AI optional.** The audit never calls an LLM by default. The remediation prompt is a generated artifact that you choose to hand to an agent.
- **This agent does not transmit your tree.** Analysis is local: no upload of the audited source, no LLM in the scanner. **Third-party tools it may spawn (eslint, jscpd, lizard, …) are not network-sandboxed** — this process does not police whether *they* phone home. Acquisition (`npx --yes` when `analyzers.acquire_tools` is set and a Node tool is missing) is a documented, opt-in network action. Install those tools yourself for an air-gapped run. An IDE chat session that pastes the report to a model is your channel, not this binary.
- **Bounded scope.** The remediation prompt explicitly tells the agent to fix the listed findings only — not to embark on architecture cleanup.
- **No vendor lock-in.** All outputs (Markdown, JSON, SARIF, PR comment) are plain files. Pair this tool with mature analyzers (ESLint, Ruff, Radon, Semgrep, SonarQube, Qlty/Code Climate) — don't replace them.
- **Pass-the-cost-of-disclosure.** A finding that's "just a warning" never blocks CI alone. Hard gates are configurable + opt-in.

See [docs/philosophy.md](docs/philosophy.md) for the longer version, and [docs/product-intent.md](docs/product-intent.md) for what this product promises and what it must never claim — that document is authoritative, and this README defers to it wherever the two differ.

## Self-Audit

This repo eats its own dogfood — the tool runs against this codebase in CI, and a report is checked in at [docs/self-audit.md](docs/self-audit.md). The checked-in copy is **stamped with the exact source commit it was generated against** — a provenance record, not a promise that it reflects the current HEAD. It deliberately makes no claim about distance: a self-report cannot contain its own commit, and no merge strategy preserves a fixed gap. Check the stamp against the commit you care about:

| Metric | Value |
|---|---:|
| Maintainability estimate | **4.6 / 5** |
| Verified grade | **B** |
| Files scanned | 235 |
| File warnings | 65 |
| File failures | 0 |
| Function warnings | 28 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Yes, a **B** — demoted from the A band because warning rates exceed the A-grade ceilings, against thresholds this repo deliberately sets stricter than the shipped defaults (a 250-line file warning versus the default 400). An earlier revision of this table advertised 5.0/A+ after the codebase had drifted to a B; a hostile audit caught the stale claim, which is precisely the failure mode this tool exists to catch. The table matches the stamped report, and every threshold gate — file, function, duplication — is opted **on** for this repo's own CI, so drifting below the bar fails the build instead of the README.

The grade is **gated, not averaged**: A+ requires every dimension clean, and since the rubric rework a repository with production code and zero test files cannot receive an A-grade at all. It is also **banded from the evidence floor, not the score** — the grade reads `overall_range[0]`, with every unmeasured aspect priced at 0, so withholding evidence can never buy a better letter. This repository's required evidence is complete under the default profile, so its floor and its score are the same number; a shallow clone's would not be, and the report says so in a blocker. (Practical note for CI: `actions/checkout` defaults to `fetch-depth: 1`, which hides history and costs roughly a grade. Use `fetch-depth: 0`.)

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
- approximate cyclomatic complexity, plus **cognitive complexity** — nesting-weighted reading cost, so five guard clauses no longer score the same as five levels of nesting
- duplicate blocks (≥ N consecutive non-trivial lines, configurable)
- near-duplicate declarations — the same helper written twice under different names, compared structurally so renaming can't hide it, each paired with the original to reuse
- unreferenced private declarations — debris nothing in the repo can reach, scoped to internal names so a library's public surface is never flagged
- competing libraries for one concern — two HTTP clients or two schema validators mean two mental models; curated list, extensible via `idiom_groups`
- configurable risk patterns (regex matchers — TODO/FIXME, `eval(`, `exec(`, custom)
- expected files present (README, LICENSE, etc. — opt-in hard gate)
- expected test/lint commands declared in the config (opt-in hard gate)
- worktree-clean state at audit time (opt-in hard gate)
- ISO/IEC 25010-inspired 0–5 estimate per category, and a verified grade only when the required evidence is complete. Otherwise the estimate and grade are withheld, not invented.

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

The audit model is based on ISO/IEC 25010 maintainability — modularity, reusability, analyzability, modifiability, testability.

Scores are **rates calibrated against real code**, not counts. Every pressure is normalized against the median that a pinned 40-repo corpus of mature open-source projects (django, angular, transformers, webpack, vite, playwright, …) actually exhibits, so `2.5x` means "two and a half times what well-maintained real code carries." The corpus median earns a **B**; **A+ is gated**, requiring every dimension clean rather than a good average.

The corpus is **selected by query, not by taste** — `stars:>3000 created:<2021-01-01 pushed:>2026-01-01` across Python, TypeScript and JavaScript, then filtered to repositories that actually contain code. An earlier version was fourteen repositories chosen by hand, which is selection bias sitting underneath a scale used to grade everyone else.

The calibration is reproducible rather than asserted: `python3 tools/calibration/measure.py --check` re-measures the corpus and fails if the shipped constants have drifted, and `tests/test_calibration_corpus.py` re-derives them offline from checked-in measurements — no network, no trust required.

See [docs/standard.md](docs/standard.md).

## Documentation

Start with [the documentation index](docs/README.md), which states each document's genre and what it is allowed to assert.

**Governing**

- [Product intent](docs/product-intent.md) — what this is for, what it promises, what it must never claim, and the evidence bar for each kind of claim
- [Architecture](docs/architecture.md) — layers, dependency rules, enforced invariants, known debt
- [Philosophy](docs/philosophy.md) — why AI-specific: volume, not pathology
- [Decision register](docs/decisions.md) — every architectural decision and its current status, including [ADR 001](docs/adr-001-evidence-and-verification.md) (evidence states and verification) and the open questions

**Reference and operations**

- [Maintainability standard](docs/standard.md) — the rubric and thresholds
- [Studies and measured results](docs/studies.md) — what has been tested, and what it does not license
- [Report contract](docs/report-contract.md)
- [CLI reference](docs/cli.md)
- [Config schema](docs/config-schema.md)
- [Language support and detection accuracy](docs/language-support.md)
- [Analyzer adapters](docs/adapters.md)
- [External quality tools](docs/external-quality-tools.md)
- [IDE and agent integration](docs/ide-agent-integration.md)
- [PR and baseline workflows](docs/pr-and-baseline-workflows.md)
- [Roadmap](docs/roadmap.md)
- [Changelog](CHANGELOG.md)

## GitHub Action

This repo includes `action.yml`, so it can be used as a composite action:

```yaml
- uses: marshallguillory86/maintainability-agent@v0.7.0
  with:
    config: maintainability-agent.json
    changed-only: main...HEAD
```

Or copy `.github/workflows/maintainability.yml` into the target repo and adapt it.

## IDE and Agent Integration

See [docs/ide-agent-integration.md](docs/ide-agent-integration.md) for VS Code tasks and integration notes for Copilot, Cursor, Codex, Claude Code, Windsurf, generic agents, local CI, and GitHub Actions.

The optional local MCP server exposes the same deterministic audit and bounded
remediation prompt directly to Visual Studio, VS Code and Codex. It is a local
stdio process, not a hosted service. It may write exactly five local artifacts:
the repository config, XDG user config, XDG user state and repository scan
history at `.maintainability/history.jsonl`, plus the repository baseline at
`.maintainability/baseline.json`. It never writes source or a report, and it
rejects repository or config paths outside its explicit allow-list. See
[Local MCP server](docs/ide-agent-integration.md#local-mcp-server-visual-studio-vs-code-and-codex).

`record_history=None` follows the persisted first-run history consent and
always appends an existing history, while explicit `true` or `false` wins. An
out-of-roots tool call can use the host's structured question UI for a
session-only or user-tier grant; the report resource never asks or persists a
grant. Missing selected analyzers are returned in the top-level
`environment_work_order` for the host to surface.

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

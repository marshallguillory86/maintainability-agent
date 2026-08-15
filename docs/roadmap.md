# Roadmap

Governed by [product intent](product-intent.md). Anything here that would require a claim the intent forbids is not on this list, however interesting.

This project should stay a thin orchestration and prompt layer, not a replacement for mature analyzers.

## Shipped

Dependency-light native scanner; Markdown, JSON, SARIF and PR-comment output; bounded AI remediation prompt; changed-only mode; baseline gating; agent instruction packs; ISO/IEC 25010-inspired rubric calibrated against a query-selected 40-repo corpus; git-history aspects (churn, hotspots, coupling, ownership); 92% coverage gate; portable invokable skill for Claude Code, Codex and Copilot Chat; optional read-only local MCP server for Codex and its VS Code extension.

## Next: finish ADR 001

The architecture migration outranks new features. Six audit rounds were spent on one bug class that the typed evidence boundary is meant to end; leaving it half-migrated is how the seventh round happens. The open stages and their current status are in the [decision register](decisions.md); the immediate work is:

1. Separate history-window materialization from fix-breadth measurement, with checked-in manifests: pinned head, selection rule, selected commit ids, required parent objects and tool version, so analysis reads only the manifest and touches no network.

The evidence model, its property tests, consumer migration and the version-2 contract are done; [ADR 002](adr-002-null-verified-grade-in-ci.md) stays rejected because it assumed `--fail-on-gate` consumes a grade when it only checks hard findings.

## A known shape problem: this tool is end-of-loop heavy

Worth stating plainly because it aims several roadmap items. Addy Osmani frames agent constraints as **back-pressure that should exist throughout the loop, not as a single review at the very end** ([Agentic Code Quality](https://addyo.substack.com/p/agentic-code-quality)). Measured against that, this tool is strong where it is cheapest to be strong — a CI gate after the work is done — and thin during the loop, where a constraint is worth far more because it prevents rather than rejects. The shipped IDE and agent skills are a partial answer; a pre-commit path and in-loop signal are not built.

He also names the trade-off available once generation outruns verification: scale verification, slow generation, lower standards, or **relax constraints in low-risk areas while tightening them elsewhere**. Only the last is a real engineering answer, and it is what the policy-as-code item below is for. This is a borrowed frame, not evidence — it tells us where to look, not what is true.

## Then

**Additional analyzer adapters** — Semgrep, pytest/coverage, and SonarQube export. Ingest output, preserve provenance, and do not pretend every analyzer has the same semantics. The fourteen shipped adapters — twelve native plus the declared pylint and mypy integrations — are listed in [analyzer pool](analyzer-pool.md#adapter-status-stated-plainly).

**Deterministic semantic policy** — prototype [ADR 003](adr-003-deterministic-semantic-policy.md) in TypeScript first: compiler-backed facts, explicit repository policies, and non-gating design-review candidates. Measure precision before adding any hard gate, and do not add a score weight during discovery.

**Economic context and impact scenarios** — prototype [ADR 004](adr-004-economic-context.md) as an optional, separately labeled prioritization layer. Prefer repository-derived exposure data, ask only for business context the repository cannot contain, and keep all scenarios out of the standard grade.

**Additional detectors.** Worth building because the cost they name is real, and — per [philosophy](philosophy.md) — worth detecting *regardless of who wrote the code*: docstring and signature drift, tests asserting private names, single-use abstractions, speculative generality, stale generated comments. Each becomes scored only by being given weight in the rubric.

**Policy-as-code** — new-code thresholds, changed-file thresholds, required tests for changed API files, architecture boundary rules by path.

**Per-repository rubric overrides.** Currently refused: the rubric is a standard, and a standard everyone edits stops being one. Any override mechanism must label its output a **house variant** so it cannot be compared to a standard score.

**Delivery** — a GitHub Action wrapper that posts and updates PR comments; GitLab and Azure DevOps adapters; historical trend reporting.

## Studies that would earn a claim

Listed with the bar each must clear, because the project has retracted one empirical claim already:

- **Outcome tuning.** Score a repository at a past commit, measure the following year's fix churn on held-out repositories. This is the only study that could license "the score predicts anything", and until it runs, the rubric is a standard and not a predictor.
- **Economic-impact validation.** Pre-register a model, estimate maintenance effort from information available before the work, and compare it with held-out task effort or cost. Organization-specific calibration comes before any cross-organization claim; configured assumptions alone license only scenario language.
- **Fix breadth, done properly.** A diff-content fix detector, a registered primary outcome, and commit-level authorship. The current result is a consistent direction across three specifications that straddle p = 0.05 and fails Holm correction — exploratory, and labeled so.
- **Bounded-prompt effectiveness.** The pre-registered experiment returned INCONCLUSIVE: far more findings closed, no measurable narrowing. A better-powered design with more subjects would settle it.

## Non-goals

Replace SonarQube, Semgrep, Qlty, Code Climate, ESLint, Ruff, Radon or language-native tooling. Automatically rewrite repositories. Send code to an LLM by default. Treat maintainability as purely numeric. Claim to detect AI authorship — [tested, retracted](studies.md#does-this-detect-ai-written-code), and not revivable without a pre-registered design.

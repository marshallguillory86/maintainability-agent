# Roadmap

Governed by [product intent](product-intent.md). Anything here that would require a claim the intent forbids is not on this list, however interesting.

This project should stay a thin orchestration and prompt layer, not a replacement for mature analyzers.

## Shipped

Dependency-light native scanner; Markdown, JSON, SARIF and PR-comment output; bounded AI remediation prompt; changed-only mode; baseline gating; agent instruction packs; ISO/IEC 25010-inspired rubric calibrated against a query-selected 40-repo corpus; git-history aspects (churn, hotspots, coupling, ownership); 92% coverage gate; portable invokable skill for Claude Code, Codex and Copilot Chat.

## Next: finish ADR 001

The architecture migration outranks new features. Six audit rounds were spent on one bug class that the typed evidence boundary is meant to end; leaving it half-migrated is how the seventh round happens. Stages 4–9 in [ADR 001](adr-001-evidence-and-verification.md), the immediate ones being:

1. Move aspect scoring behind the typed boundary and delete the raw-dictionary fallbacks.
2. Introduce `evidence_status` and `verified_grade` alongside the compatibility fields.
3. **Open decision, blocking stage 5:** what a CI gate does when `verified_grade` is null. Failing open would let a repository turn the gate green by withholding evidence, which is worse than today's floor grade.
4. Separate history-window materialization from fix-breadth measurement, with checked-in manifests.

## Then

**Analyzer adapters** — Semgrep, ESLint, Ruff, Radon, pytest/coverage, SonarQube export. Ingest output, preserve provenance, do not pretend every analyzer has the same semantics.

**Additional detectors.** Worth building because the cost they name is real, and — per [philosophy](philosophy.md) — worth detecting *regardless of who wrote the code*: docstring and signature drift, tests asserting private names, single-use abstractions, speculative generality, stale generated comments. Each becomes scored only by being given weight in the rubric.

**Policy-as-code** — new-code thresholds, changed-file thresholds, required tests for changed API files, architecture boundary rules by path.

**Per-repository rubric overrides.** Currently refused: the rubric is a standard, and a standard everyone edits stops being one. Any override mechanism must label its output a **house variant** so it cannot be compared to a standard score.

**Delivery** — a GitHub Action wrapper that posts and updates PR comments; GitLab and Azure DevOps adapters; historical trend reporting.

## Studies that would earn a claim

Listed with the bar each must clear, because the project has retracted one empirical claim already:

- **Outcome tuning.** Score a repository at a past commit, measure the following year's fix churn on held-out repositories. This is the only study that could license "the score predicts anything", and until it runs, the rubric is a standard and not a predictor.
- **Fix breadth, done properly.** A diff-content fix detector, a registered primary outcome, and commit-level authorship. The current result is a consistent direction across three specifications that straddle p = 0.05 and fails Holm correction — exploratory, and labeled so.
- **Bounded-prompt effectiveness.** The pre-registered experiment returned INCONCLUSIVE: far more findings closed, no measurable narrowing. A better-powered design with more subjects would settle it.

## Non-goals

Replace SonarQube, Semgrep, Qlty, Code Climate, ESLint, Ruff, Radon or language-native tooling. Automatically rewrite repositories. Send code to an LLM by default. Treat maintainability as purely numeric. Claim to detect AI authorship — [tested, retracted](standard.md#does-this-detect-ai-written-code), and not revivable without a pre-registered design.

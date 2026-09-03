# Roadmap

Governed by [product intent](product-intent.md). Anything here that would require a claim the intent forbids is not on this list, however interesting.

This project should stay a thin orchestration and prompt layer, not a replacement for mature analyzers.

## Shipped

Dependency-light native scanner; Markdown, JSON, SARIF and PR-comment output; bounded AI remediation prompt; changed-only mode; baseline gating; agent instruction packs; ISO/IEC 25010-inspired rubric calibrated against a query-selected 40-repo corpus; git-history aspects (churn, hotspots, coupling, ownership); 92% coverage gate; portable invokable skill for Claude Code, Codex and Copilot Chat; optional local MCP server (writes only its five disclosed config/state artifacts, never source or reports) for Codex and its VS Code extension.

**Nine declaration languages**, each shipped as its own minor release: Python and Java, JS/TS/JSX and HTML, then C (1.1.0), C++ (1.2.0), C# (1.3.0), free-form Fortran (1.4.0) and fixed-form Fortran (1.6.0), over one shared walk in `_ranges_core` where a language is a module and a row. Fortran is the first with no braces, so the walk takes its bounding rule as an argument. Fortran also gained an analyzer adapter (fortitude, 1.5.0), its own complexity and cognitive readings rather than the C-family default (1.6.0), and toolchain practice detection (1.7.0). Per-language scope and misses are in [language support](language-support.md).

## Next: finish ADR 001

The architecture migration outranks new features. Six audit rounds were spent on one bug class that the typed evidence boundary is meant to end; leaving it half-migrated is how the seventh round happens. The open stages and their current status are in the [decision register](decisions.md); the immediate work is:

1. Separate history-window materialization from fix-breadth measurement, with checked-in manifests: pinned head, selection rule, selected commit ids, required parent objects and tool version, so analysis reads only the manifest and touches no network.

The evidence model, its property tests, consumer migration and the version-2 contract are done; [ADR 002](adr-002-null-verified-grade-in-ci.md) stays rejected because it assumed `--fail-on-gate` consumes a grade when it only checks hard findings.

## Language adapters

The cadence is **one language per minor release, never a batch** — five were written that way between 1.1.0 and 1.6.0, and the reason is that each one has to earn its claim separately.

**The price of admission, unchanged since [ADR 006](decisions.md):** a language is claimed only when it has a scanner of its own, a documented list of what it misses, and tests that pin them. The register's original wording said no further range detectors would be written; five were, and the rule that wording protected is what survived. A language does not get onto the table below by having its extension added to a config.

**Next:**

| Target | Language | What it costs |
|---|---|---|
| 1.9.0 | **Swift** | Braced, so it reuses the `_ranges_core` walk. Four things make it not-quite-C-family: an `extension` adds methods to a type declared elsewhere, so a name has to stay findable (`extension Widget { func draw() }` reports `Widget.draw`, the way C++ keeps `geo::Widget::draw`); a `protocol` declares bodiless requirements, which mint nothing, as in every other language here; **computed properties** (`var area: Double { w * h }`) have braces and would bound cleanly, and are the C# properties problem again — counting them would dilute the population every rate divides by; and string interpolation (`"\(a + b)"`) puts braces inside literals, so masking has to run before depth counting or a range ends early. |

Go and Rust remain named in [ADR 006](decisions.md) as unwritten on exactly these terms. They are not refused and not scheduled.

**What an unwritten language already gets today.** Swift, Go and Rust are all classified by discovery, and all have practice signals wired (`.swiftlint.yml`, `.golangci.yml`, `rustfmt.toml`, `clippy.toml`, and the `swiftlint` / `golangci-lint` / `clippy` command patterns). What none of them gets is a declaration population: rates are **withheld** with the missing parser named, rather than approximated. That is the P7 boundary and it is the reason a language is a release rather than a config entry.

**Two gaps that widen with every language added**, and should be closed alongside rather than after:

- **Test-command detection stops at Python.** `_test_execution` knows `pytest -q`; `swift test`, `xcodebuild test`, `fpm test`, `ctest`, `go test` and `cargo test` are unrecognised, so `expected_commands.test` stays hand-configured on every non-Python tree. Swift lands in 1.9.0 with that gap unless it is closed alongside. Fortran's practice detection (1.7.0) reads `fpm.toml` but nothing runs from it.
- **The calibration corpus is 40 JS/TS/Python repositories.** Every language above is scored against references derived from code unlike it — measured, not hypothetical: LAPACK read 7.18x the declaration median. [The audit](audit-v091-v170.md#f1--the-calibration-corpus-contains-none-of-four-claimed-languages-high) records this as a disclosure gap, and each new language inherits it. Extending the corpus moves `CALIBRATION_C` and re-grades every repository, so it is a deliberate release of its own, not a patch bundled with a scanner.

**Not scheduled, and the distinction matters.** Go, Rust, Kotlin, Scala, Ruby, PHP and the rest are classified by discovery and may be measured by adapters, but no scanner is scheduled for any of them. They are not refused — they are unwritten, on the terms above. A language moves onto this list when it is decided here, not by being named in an older register entry.

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

**Hostile-audit prompt** — [ADR 013](adr-013-hostile-audit-prompt.md), a third emitter on the prompt seam that seeds an adversarial audit from the report so the loop that builds this tool becomes repeatable. Near-term and low-risk: deterministic input, the LLM reasons outside, no gate, no score.

## Distant future

**Deterministic adversarial-properties detection.** The second play behind [ADR 013](adr-013-hostile-audit-prompt.md): a detection dimension that audits a *target* repository for the hardening classes this agent enforces on itself — a write that follows a symlinked route, an empty tool run read as clean, a caller argument reaching a filesystem or shell sink unvalidated, absence read as a pass. Deterministic and AST/pattern-derivable, so it fits the suite rather than the prompt seam; distinct from [ADR 013](adr-013-hostile-audit-prompt.md)'s emitter, and it brushes the `secure-code-agent` boundary, so it needs an explicit scope decision and its own ADR before any build. A future release, not a next step.

## Studies that would earn a claim

Listed with the bar each must clear, because the project has retracted one empirical claim already:

- **Outcome tuning.** Score a repository at a past commit, measure the following year's fix churn on held-out repositories. This is the only study that could license "the score predicts anything", and until it runs, the rubric is a standard and not a predictor.
- **Economic-impact validation.** Pre-register a model, estimate maintenance effort from information available before the work, and compare it with held-out task effort or cost. Organization-specific calibration comes before any cross-organization claim; configured assumptions alone license only scenario language.
- **Fix breadth, done properly.** A diff-content fix detector, a registered primary outcome, and commit-level authorship. The current result is a consistent direction across three specifications that straddle p = 0.05 and fails Holm correction — exploratory, and labeled so.
- **Bounded-prompt effectiveness.** The pre-registered experiment returned INCONCLUSIVE: far more findings closed, no measurable narrowing. A better-powered design with more subjects would settle it.

## Non-goals

Replace SonarQube, Semgrep, Qlty, Code Climate, ESLint, Ruff, Radon or language-native tooling. Automatically rewrite repositories. Send code to an LLM by default. Treat maintainability as purely numeric. Claim to detect AI authorship — [tested, retracted](studies.md#does-this-detect-ai-written-code), and not revivable without a pre-registered design.

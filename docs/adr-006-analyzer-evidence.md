# ADR 006: External analyzers produce the evidence; the agent orchestrates and corroborates

- Status: Accepted. Implementation progress is tracked in the [decision register](decisions.md), which is the single place it is stated
- Date: 2026-08-12
- Scope: The whole evidence layer, the score, the report contract, installation, CI
- Supersedes the "planned adapters" position in [adapters.md](adapters.md)
- Related: [ADR 001](adr-001-evidence-and-verification.md), [ADR 007](adr-007-pillars-and-practice.md), [tool inventory](tool-inventory.md)

## Context

The README states the design principle plainly: *"Pair this tool with mature analyzers (ESLint, Ruff, Radon, Semgrep, SonarQube, Qlty/Code Climate) — don't replace them."* The roadmap lists replacing them as an explicit non-goal.

The implementation does the opposite. `src/` contains `_cognitive.py`, `duplication.py`, `similarity.py`, `deadcode.py`, `idioms.py` and `metrics.py` — six homegrown detectors that reimplement, less well, what radon, jscpd, vulture, ruff and lizard already do. External analyzers are relegated to an optional side-channel: `--sarif-input`, which the operator must run themselves and hand to the tool. **The commodity layer is bolted to the side of the thing it should sit underneath.**

The cost is not theoretical. A repository with one production function and one test scored **5.0 / A+, evidence complete, verified**. Six shallow detectors found nothing and the rubric read that as excellence. The tool reported thirteen aspects and examined enough material to support none of them.

Two further facts, established by running the tools rather than reading about them:

**One tool covers most languages.** `lizard` measures cyclomatic complexity, NLOC, parameter count and token count across C, C++, C#, Java, Fortran, Go, Rust, Kotlin, Swift, PHP, Ruby, Scala, JS/TS and more, with no per-language configuration. The same tangled function written in seven languages returned C 11, C# 11, Java 11, Go 10, Rust 10, C++ 7, Fortran 6. `jscpd` does the equivalent for duplication across ~150 formats.

**Tools that claim the same metric disagree.** On this repository's `history.py`:

| Tool | `history_section` | `change_coupling` |
|---|---|---|
| lizard | 14 | 13 |
| radon | 14 | 13 |
| mccabe | not in top 3 | 8 |

All three report "cyclomatic complexity". radon and lizard count boolean operators and comprehensions; mccabe's path graph does not. A single-tool number is therefore **a measurement of that tool's counting convention, not of the code**. Any score derived from one source inherits that convention silently and presents it as a property of the repository.

## Decision

The agent becomes an orchestrator over external analyzers. Five changes, in dependency order.

### 1. Analyzers are the primary evidence source

The pipeline's first act is to run the available FOSS quality analyzers over the target tree and collect their machine-readable output. Findings and metrics flow from those tools into the typed evidence model built by ADR 001. The rubric scores that evidence.

The built-in detectors are **demoted, not deleted**. They remain as a fallback tier for languages and environments where nothing else runs, and for the zero-install path. Every measurement they produce is tagged single-source (see §3) and carries the weaker evidence strength that implies.

Demotion means a lower tier, not a hidden one. The eight built-in sources appear in the coverage record beside the analyzers, each carrying `tier: built-in` and a note saying where it stands: which external tools cover the same concept, or that no adapter emits it at all. Four are in that second group — `file_lines`, `risk`, `idioms`, and the history concepts `churn` / `coupling` / `ownership` — so they are not merely a fallback but the only source the tool has for those. `test_no_built_in_claims_to_be_unique_when_an_adapter_exists` holds each of those notes against the adapter registry, so a claim of uniqueness fails the build on the day an adapter contradicts it.

Leaving them out of coverage was itself a reporting defect, and the same one in mirror image: a section headed "what examined this code" that omitted half of what examined it. Coverage now reports **three** states per concern rather than two — corroborated by an external tool, single-source (a built-in looked and nothing else did), and unexamined. Collapsing single-source into "covered" would let a fallback pass for independent evidence; collapsing it into "unexamined" would claim nobody looked when something did.

### 2. Availability is reported, never assumed — and proven by invocation

Presence on `PATH` is not availability. Measured: `/usr/bin/java` exists and `command -v java` succeeds, but it is the macOS stub with no JDK behind it, and PMD refused to launch through it.

Exit codes are not a sufficient signal either, in both directions: many linters exit non-zero precisely to report findings, so treating that as failure discards real evidence, while a launcher can exit zero having done nothing. Either mistake ends the same way — a tool recorded as having run, found nothing, and contributed a clean result, which is the hello-world A+ arriving through a new door.

So a tool counts as available only when invoked and its output validated against an expected shape. Version capture doubles as the probe.

Each run records which analyzers were attempted, which ran, which were unavailable and why (not installed, unsupported language, timed out, crashed). A tool that did not run is **not a clean result**. `secure-code-agent` already reports `scanners run:` and `unavailable:`; this agent adopts the same discipline.

This is the concept whose absence produced the A+. With coverage reporting, "twelve analyzers found nothing" and "one fallback detector found nothing" stop being the same output.

### 2c. Coverage gaps are reported with the remedy, and never remedied automatically

Language detection, the catalog and the availability probe compose into an answer no current tool gives: what part of this codebase was not examined, and what would it take. The gap is rarely total — multi-language tools reach nearly everything — so it is reported per language *and per concern*. Measured on a 60%-Java tree: complexity, duplication, documentation, structure and metrics covered; **dead-code, testing, style and types covered by nothing**, with 58 cataloged tools that could.

Each gap names the tools that would close it and the prerequisite runtime — a JDK for PMD and Checkstyle, Node, the Go or Rust toolchain, the .NET SDK.

**The agent never installs anything.** Installation is a network and privilege action belonging to the user. The agent emits an *environment work order* in the same shape as the code work order — what is missing, why it matters, the exact command — so a person can run it or hand it to their own AI agent. One artifact, either consumer.

### 3. Several tools measure each concept, and their readings are combined with weights

The unit of evidence stops being *a tool's output* and becomes *a measurement concept* — cyclomatic complexity, duplication ratio, dead code, docstring coverage — measured by every available tool that speaks to it. Each concept declares its contributing tools and their weights. The target is **at least four independent sources where the ecosystem supports it**. Redundancy is the point.

The combination is ordinary arithmetic, not a new discipline:

```text
concept "cyclomatic complexity" on a function
   lizard    14   weight 1.0
   radon     14   weight 1.0
   mccabe     8   weight 1.0
   ->  value  = weighted mean = 12.0
       spread = 8 .. 14
       sources = 3
```

That is the whole mechanism. Tools disagree because their counting rules differ — radon and lizard count boolean operators and comprehensions, mccabe's path graph does not — and a weighted mean over three readings is a better estimate of the underlying property than any one of them. The spread is kept because it is real information, not because disagreement needs adjudication.

Weights are rubric data and live beside the aspect weights in the concept registry, visible and arguable. A tool known to be stricter or looser on a concept can be down-weighted with a stated reason; the default is equal weight, because that is the least arguable starting point.

Two things are recorded with every value: **how many tools produced it**, and **their spread**. A measurement from four agreeing tools and a measurement from one tool are both usable; they are not equally well supported, and the report says which is which.

Where **no** tool measured a concept, it is `Unknown` under ADR 001, with the attempted-tool list as the reason. That is the only case that produces no number.

### 4. Spread becomes the reported interval

`maintainability_range` already exists but is currently decorative — a fixed band around the estimate. It becomes the propagation of the measured spread from step 3: concepts where the tools agree narrow it, concepts where they disagree widen it, single-source concepts widen it further because one reading has no spread to trust.

This gives the interval an empirical meaning it has never had, using machinery already in the contract.

### 5. Installation is layered and explicit

Analyzers span ecosystems and cannot all be a hard dependency. Three tiers:

- **Core** — installed with the package, always present: `lizard` (multi-language metrics), `jscpd` where Node exists, `radon`, `ruff`.
- **Detected** — used when already on `PATH`: `eslint`, `pylint`, `vulture`, `complexipy`, `interrogate`, `golangci-lint`, `detekt`, `PMD`, `clippy`, `cppcheck`, `rubocop`, `phpstan`, `swiftlint`.
- **Declared** — named in configuration by the operator, for site-specific analyzers.

Missing tools degrade evidence strength and are reported. They never fail the run, and they never silently become a clean result.

## Options considered

**A. Keep the built-ins as primary, add adapters later.** Rejected — this is the status quo, it contradicts the stated principle, and it produced the A+.

**B. Delete the built-ins entirely, require external tools.** Rejected. It breaks the zero-install path and abandons languages the ecosystem covers poorly. Demotion preserves the capability while ending the pretence that it is sufficient.

**C. Single best tool per concept.** Rejected, and this is the option the mccabe/radon evidence kills. Choosing radon over mccabe is choosing a counting convention, and the choice would be invisible in the output. Combining readings makes the spread visible instead of hiding it behind a preference.

**D. Run everything available, combine the readings with weights.** Accepted.

## Consequences

- The agent gains a process-execution layer it does not currently have: subprocess invocation, timeouts, output parsing, failure isolation. Determinism (promise **P1**) now depends on pinned analyzer versions, which must be recorded in the report.
- Runtime rises from milliseconds to seconds or minutes. The `--changed-only` path becomes load-bearing rather than a convenience.
- Report schema gains an analyzer-coverage section and per-measurement provenance listing contributing tools. Another contract version.
- `docs/adapters.md` "planned adapters" is superseded by this record.
- The six built-in detector modules become a fallback tier and must be labelled as such in code and docs, so nobody mistakes them for the primary path again.
- Scoring must handle contested measurements, which is new behavior in `_formula.py` and the interval logic.

## Invariants

1. Every report names every analyzer attempted, with an outcome for each: ran, unavailable, failed.
1b. Availability is established by invoking the tool and validating its output shape, never by `PATH` presence or exit code alone.
2. No measurement is reported without the list of tools that produced it and their count.
3. A concept measured by zero tools is `Unknown` with the attempted-tool list as its reason — never a default, never a zero, never a 5.0.
4. Where two or more tools measure one concept, the report carries the combined value, the spread and the tool attribution. No tool is silently dropped.
5. Combination weights are declared as data in the concept registry, never embedded in code paths.
6. Analyzer versions are recorded in the report, and identical versions over an identical tree produce identical output.
7. An unavailable analyzer never fails the run and never improves a score.
8. Built-in fallback detectors are always tagged single-source.
9. The built-in language set does not grow. Python and JS/TS/HTML keep
   their shipped range detectors as the zero-install fallback. Java, Go,
   C, C++, C# and Rust wait on analyzer measurements plus recalibration,
   not on a new `_ranges` function per language.

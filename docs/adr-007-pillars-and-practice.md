# ADR 007: Adopt the five-pillar framework, and separate practice maturity from code condition

- Status: Accepted
- Date: 2026-08-12
- Scope: Reporting taxonomy, the score's meaning, remediation prioritisation, scope boundaries
- Source: *Code Quality Framework — Readability · Maintainability · Efficiency & Scalability · Security · Testability*, July 2026
- Related: [ADR 006](adr-006-analyzer-evidence.md), [ADR 005](adr-005-insufficient-population.md), [product intent](product-intent.md)

## Context

An internal framework document defines code quality across five pillars, gives each a 1–5 maturity rubric, a cost/risk table and a standards checklist, and adds a Risk × Effort prioritisation matrix and a per-stack tooling template.

Two things make it worth adopting rather than noting.

**It has a concept this tool lacks, and that concept is exactly the one whose absence caused this week's central bug.** Its 1–5 scale measures *process maturity*, not code properties:

| Level | Meaning |
|---|---|
| 1 Initial | Ad hoc; problems found reactively, often in production |
| 2 Managed | Practices exist but are inconsistently applied or enforced |
| 3 Defined | Standards documented and **enforced automatically in CI** |
| 4 Quantitatively Managed | Metrics tracked over time and used to guide decisions |
| 5 Optimizing | Continuous data-driven improvement; near best-practice outcomes |

Score the hello-world repository against that rubric and it lands at **Level 1**: no enforced linter, no CI gate, no tracked metrics, no coverage threshold. It cannot reach Level 3 no matter how few findings it has, because Level 3 asks whether a standard is *enforced*, not whether a scan came back empty.

This tool gave the same repository 5.0 / A+. The framework's rubric would have caught what four days of internal audits did not, because it measures a different thing.

**It also names the audience problem this tool has never solved.** The cost/risk tables translate technical neglect into velocity loss, incident cost and rework cost; the Risk × Effort matrix sequences remediation into Quick Wins, Major Projects, Fill-Ins and Reconsider. That matrix is a direct answer to the failure mode this project keeps hitting — remediation prompts that generate endless low-value nits because nothing ranks findings by consequence against effort.

### Where the two models already agree

The tool's five scoring categories are the ISO/IEC 25010 sub-characteristics of maintainability: modularity, reusability, analyzability, modifiability, testability. The framework's **Maintainability** pillar is defined in the same terms — modularity, low coupling, low duplication, clear architecture.

So the tool is a deep decomposition of one pillar, with partial reach into two others. That is a clean relationship, not a conflict, and stating it prevents the two 1–5 scales from being mistaken for each other.

### Where they conflict

- **Same numerals, different meaning.** The framework's 1–5 is CMMI-style process maturity. This tool's 1–5 is a code-property scale calibrated so the mature-OSS median lands at 4.0. A "3" means unrelated things in each. Left unreconciled, someone will average them.
- **Aggregation differs.** The framework averages five pillars equally. The tool takes a weighted mean of categories, weighted again over aspects.
- **Scope differs.** Security is a framework pillar and is out of scope here by design. Efficiency & Scalability is not statically measurable at all.

## Decision

### 1. The five pillars become the top-level reporting taxonomy, with declared scope

| Pillar | This agent's position |
|---|---|
| **Readability** | **Partial.** Linter conformance, docstring coverage, declaration size, naming conventions where analyzers report them. Reported, with gaps named. |
| **Maintainability** | **Owned.** The existing ISO 25010 decomposition is the detail view of this pillar. |
| **Efficiency & Scalability** | **Out of scope, permanently.** Requires profiling, load testing and runtime telemetry. Reported as `NotApplicable` with that reason — an explicit statement, not a silent omission. |
| **Security** | **Delegated** to `secure-code-agent`. Reported as `NotApplicable` naming the other tool, so a reader never mistakes silence for safety. |
| **Testability** | **Partial.** Test presence, declaration size and policy gates today; coverage and mutation results when the operator supplies them. |

Declaring scope per pillar is itself a fix. Today the tool is silent about efficiency and security, and silence reads as "fine".

### 2. Every pillar reports two independent values that are never averaged together

**Practice level (1–5)** — the framework's maturity rubric, scored from detectable evidence of enforcement: does a linter config exist, is it wired into CI, is there a coverage gate, are complexity thresholds configured, are ADRs maintained, is there a duplication check. This is measured by looking at the repository's configuration and CI, not its source.

**Code condition** — what the analyzers found, normalised over population, as the tool scores today.

The two are orthogonal and both are needed:

| | Poor condition | Good condition |
|---|---|---|
| **High practice** | Known debt, managed — invest in remediation | Healthy |
| **Low practice** | Unmanaged debt — highest risk | **Unverified.** Clean scan, no enforcement, nothing preventing regression tomorrow |

The hello-world sits in the bottom-right cell. Today the tool calls that A+. Under this decision it reads *"practice level 1, condition unmeasured"*, which is the truth.

Combining them into one number is forbidden. They answer different questions and the framework's own document keeps them apart.

### 3. Findings are prioritised by Risk × Effort, and the prompt leads with Quick Wins

Every finding class carries a risk weighting (its cost driver, from the framework's cost/risk tables) and an effort estimate. The remediation prompt orders by that matrix rather than by count or severity alone:

- **Quick Wins** (high risk, low effort) — lead with these
- **Major Projects** (high risk, high effort) — name them, do not inline them into a prompt
- **Fill-Ins** (low risk, low effort) — offer opportunistically, never as the headline
- **Reconsider** (low risk, high effort) — suppress unless explicitly requested

This is the structural answer to nit-loops: a prompt that opens with eighty line-length violations is generating Fill-Ins as if they were Quick Wins.

### 4. Shared vocabulary is adopted verbatim

The framework's glossary — cyclomatic complexity, duplication %, code churn, bus factor, coverage % — becomes the tool's published vocabulary. The tool already measures churn and a bus-factor proxy under the name `knowledge_concentration`; that aspect is renamed or aliased to the shared term so a report and the framework can be read side by side.

The framework's action thresholds (below 2.5 urgent, 2.5–3.5 targeted, above 3.5 maintain) apply to **practice level**, where they were designed to apply. They are not applied to the condition scale, whose bands are separately calibrated.

## Options considered

**A. Ignore the framework; keep ISO 25010 only.** Rejected. It forfeits the practice-maturity concept, which demonstrably catches a bug the current model cannot see, and leaves the tool speaking a vocabulary no stakeholder uses.

**B. Replace ISO 25010 with the five pillars.** Rejected. Two pillars are unmeasurable or delegated, and the ISO decomposition is the tool's calibrated, tested detail. Replacement would discard working machinery for a taxonomy that does not decompose far enough to score.

**C. Adopt the pillars as the outer taxonomy, keep ISO 25010 as the Maintainability detail, and add practice level as a second axis.** Accepted. Nothing calibrated is discarded, the tool gains the missing concept, and the two 1–5 scales stay explicitly separate.

**D. Merge practice and condition into one composite score.** Rejected. It is the mistake that makes both meaningless, and it would reintroduce exactly the confusion this record exists to prevent.

## Consequences

- A new detection layer is required for practice level: reading CI configuration, linter configuration, coverage thresholds and hook definitions. It examines repository configuration, not source, which is a genuinely new capability.
- The report gains a pillar-level view above the existing categories. The category detail is retained unchanged beneath Maintainability.
- Two pillars will always report `NotApplicable`. That is the intended output and must survive review as a feature, not get "fixed" later.
- Findings need risk and effort metadata, which is new per-finding-class data and a judgment call to be stated in `standard.md`, not hidden in code.
- The framework's per-stack tooling template maps onto [tool inventory](tool-inventory.md) — the same artefact, one for humans and one for the runner.

## Invariants

1. Every pillar appears in every report, with an explicit scope status: owned, partial, delegated or out of scope.
2. Practice level and code condition are separate fields and are never averaged into a single number.
3. A repository with no enforcement evidence cannot report a practice level above 2, regardless of findings.
4. Delegated and out-of-scope pillars carry a reason naming what would be required, so silence is never read as a pass.
5. Remediation output is ordered by the Risk × Effort matrix, and Fill-Ins never appear above Quick Wins.
6. The framework's action thresholds are applied only to practice level, never to the condition scale.

# Documentation

Every document here has a **genre**, and the genre determines what it may assert. This is not filing tidiness: mixing genres is how a claim in this repository once reached the README as settled fact and had to be retracted. See [the evidence standard](product-intent.md#the-evidence-standard).

| Genre | May assert | Changes when |
|---|---|---|
| **Governing** | What the product is for and what it may never claim | The product's purpose changes |
| **Normative** | The standard applied to every repository — weights, bands, thresholds | A judgment is deliberately revised |
| **Decision** | One architectural choice, its context, its consequences | Superseded by a later decision |
| **Empirical** | What was measured, with pinned inputs and stated limits | New evidence is derived |
| **Operational** | How to run, configure, and integrate the tool | Behavior changes |
| **Generated** | Output of a command; never hand-edited | Regenerated |

**Where empirical numbers may appear.** `studies.md` is the **source of record**: every result lives there in full, with its method, controls and limits. Other documents **may quote an approved summary sentence verbatim** — a governing document that cannot state what the product may claim is not governing anything — and may not restate a result's interpretation in their own words. The approved sentences are listed under [Approved summaries](studies.md#approved-summaries) and `test_docs_links.py` compares quotations character for character. It detects sentences carrying an "N of M", a p-value or a "median of N"; it does **not** detect percentage-only claims, because this repository also writes "92% coverage gate" and "25% of modularity" and no pattern separates those from a study figure. The recognized statistical forms are checked automatically; **discovering a new or paraphrased percentage claim is a review responsibility**. The canonical wording for the percentage claims that exist is in the approved list so there is something to review against, not because the build enforces it.

Verbatim, not "contains the same numbers": an earlier guard checked whether each figure appeared *somewhere* in `studies.md`, which cannot detect a swapped attribution or a different sentence assembled from the same digits. It also only examined blockquotes, so a restatement written as ordinary prose passed unread.

## Start here

| Document | Genre | What it settles |
|---|---|---|
| [Product intent](product-intent.md) | Governing | What this is, what it promises, what it must never claim, and the bar each kind of claim must clear. **When another document disagrees with this one, this one is right.** |
| [Architecture](architecture.md) | Governing | Layers, dependency rules, invariants and where each is enforced, and the known debt — **as the code is today** |
| [Target architecture](target-architecture.md) | Decision | Where the design is going: analyzer pipeline, pillars, band matrix, work order. Nothing here ships |
| [Philosophy](philosophy.md) | Governing | Why the tool is AI-specific — volume, not pathology |

## Decisions

**[The decision register](decisions.md)** lists every architectural decision and its status, including the ones not yet made. It also holds the ADR template and the rule for when to write one.

| Document | Status |
|---|---|
| [ADR 001 — Evidence and verification](adr-001-evidence-and-verification.md) | Accepted — status in the [register](decisions.md) |
| [ADR 002 — Null verified grade in CI](adr-002-null-verified-grade-in-ci.md) | **Rejected** — assumed a CI grade gate that does not exist |
| [ADR 003 — Deterministic semantic policy](adr-003-deterministic-semantic-policy.md) | **Proposed** — repository semantics without rubric drift |
| [ADR 004 — Economic context](adr-004-economic-context.md) | **Proposed** — impact scenarios separate from score and grade |
| [ADR 005 — Insufficient population](adr-005-insufficient-population.md) | Accepted — status in the [register](decisions.md). No rate without a denominator that supports one |
| [ADR 006 — Analyzer evidence](adr-006-analyzer-evidence.md) | Accepted — status and remaining gaps in the [register](decisions.md). Optional analyzers report measurements, findings, provenance, and coverage; their measurements do not yet drive the point estimate |
| [ADR 007 — Pillars and practice](adr-007-pillars-and-practice.md) | Accepted — status in the [register](decisions.md). Five-pillar taxonomy; practice maturity separate from code condition. The §4 rename was refused, not deferred |
| [ADR 008 — Translation and decision](adr-008-translation-and-decision.md) | Accepted — status in the [register](decisions.md). Tool output to scoring input, the LLM boundary, CLI and MCP |
| [ADR 009 — Scan history](adr-009-scan-history.md) | Accepted — status in the [register](decisions.md). Maintainability is a trend; comparability is checked before any of it is computed |
| [ADR 010 — Repository discovery](adr-010-repository-discovery.md) | Accepted — status in the [register](decisions.md). What is in this tree and whose code it is, from evidence the repository provides |
| [Report contract](report-contract.md) | Current — the report's producers, consumers, and schema-version policy |

New ADRs are `adr-NNN-short-title.md`, numbered in order, added to the register, and never edited after acceptance except to record implementation progress or mark them superseded.

## The standard, and what has been measured

| Document | Genre | Note |
|---|---|---|
| [Maintainability standard](standard.md) | Normative | The rubric, its weights and bands, the calibration method, and the reference corpus. Judgments applied uniformly to every repository; requires no study to be legitimate |
| [Studies and measured results](studies.md) | Empirical | Every claim about the world, with pinned inputs, controls and stated limits — the bounded-prompt experiment, the retracted AI-authorship claim, and fix breadth. Licenses nothing beyond the sentence stated with each result |
| [Self-audit](self-audit.md) | Generated | This tool run against this repository, stamped with the source commit that produced it; provenance is the stamp, not a fixed distance from current HEAD |
| [FOSS tool inventory](tool-inventory.md) | Empirical | Every free quality analyzer this agent could run, which were installed and executed here, and what each one found. Separates proven from listed |
| [The analyzer pool](analyzer-pool.md) | Reference | The 760-tool catalog, its license classification, and the depth and license-policy selectors that narrow it at run time |

## Operating the tool

| Document | Covers |
|---|---|
| [CLI](cli.md) | Commands and flags |
| [Config schema](config-schema.md) | Configuration file |
| [Language support](language-support.md) | What is parsed, and how well |
| [PR and baseline workflows](pr-and-baseline-workflows.md) | Incremental adoption |
| [Adapters](adapters.md) | Ingesting other analyzers |
| [External quality tools](external-quality-tools.md) | Sitting alongside SonarQube and friends |
| [IDE and agent integration](ide-agent-integration.md) | Claude Code, Codex, Copilot Chat, Cursor |
| [Roadmap](roadmap.md) | What is planned, and what is deliberately refused |
| [Release plan](release-plan.md) | The ordered work from here to 1.0, with an exit condition per task |
| [Migrating to 0.7](migration-0.7.md) | Reference | What breaks — baselines and the nullable estimate — what is new and optional, and what you can ignore |
| [Report validation](../tools/validation/results.md) | Fourteen real repositories against a frame written before selection: what the output actually looked like, and the defect it exposed |

## Adding a claim to any of these

1. Decide its tier — deterministic property, standard, or empirical ([definitions](product-intent.md#the-evidence-standard)).
2. Meet that tier's bar. A property needs a test over the real input space; a standard needs to be explicit and uniform; an empirical claim needs pinned inputs and a control.
3. Put it in a document of the matching genre.
4. If it is empirical and later changes, correct it **everywhere it is quoted**, naming the correction rather than rewriting silently.

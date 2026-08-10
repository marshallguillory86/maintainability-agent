# Documentation

Every document here has a **genre**, and the genre determines what it may assert. This is not filing tidiness: mixing genres is how a claim in this repository once reached the README as settled fact and had to be retracted. See [the evidence standard](product-intent.md#the-evidence-standard).

| Genre | May assert | Changes when |
|---|---|---|
| **Governing** | What the product is for and what it may never claim | The product's purpose changes |
| **Normative** | The standard applied to every repository — weights, bands, thresholds | A judgment is deliberately revised |
| **Decision** | One architectural choice, its context, its consequences | Superseded by a later decision |
| **Empirical** | What was measured, with pinned inputs and stated limits | New evidence is derived |

**Where empirical numbers may appear.** `studies.md` is the **source of record**: every result lives there in full, with its method, controls and limits. Other documents **may quote an approved one-sentence summary** — a governing document that cannot state what the product may claim is not governing anything — but may not restate a result's interpretation, and every figure they quote must also appear in `studies.md`. `test_docs_links.py` fails the build otherwise. The earlier rule said empirical claims belong *only* in `studies.md`, which the governing document then immediately violated; this states the rule that was actually being followed.
| **Operational** | How to run, configure, and integrate the tool | Behavior changes |
| **Generated** | Output of a command; never hand-edited | Regenerated |

## Start here

| Document | Genre | What it settles |
|---|---|---|
| [Product intent](product-intent.md) | Governing | What this is, what it promises, what it must never claim, and the bar each kind of claim must clear. **When another document disagrees with this one, this one is right.** |
| [Architecture](architecture.md) | Governing | Layers, dependency rules, invariants and where each is enforced, and the known debt |
| [Philosophy](philosophy.md) | Governing | Why the tool is AI-specific — volume, not pathology |

## Decisions

**[The decision register](decisions.md)** lists every architectural decision and its status, including the ones not yet made. It also holds the ADR template and the rule for when to write one.

| Document | Status |
|---|---|
| [ADR 001 — Evidence and verification](adr-001-evidence-and-verification.md) | Accepted — status in the [register](decisions.md) |
| [ADR 002 — Null verified grade in CI](adr-002-null-verified-grade-in-ci.md) | **Proposed** — open question, blocks ADR 001 stage 5 |
| [Report contract](report-contract.md) | Current — the report's producers, consumers, and schema-version policy |

New ADRs are `adr-NNN-short-title.md`, numbered in order, added to the register, and never edited after acceptance except to record implementation progress or mark them superseded.

## The standard, and what has been measured

| Document | Genre | Note |
|---|---|---|
| [Maintainability standard](standard.md) | Normative | The rubric, its weights and bands, the calibration method, and the reference corpus. Judgments applied uniformly to every repository; requires no study to be legitimate |
| [Studies and measured results](studies.md) | Empirical | Every claim about the world, with pinned inputs, controls and stated limits — the bounded-prompt experiment, the retracted AI-authorship claim, and fix breadth. Licenses nothing beyond the sentence stated with each result |
| [Self-audit](self-audit.md) | Generated | This tool run against this repository. Always one commit behind the HEAD it ships with |

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

## Adding a claim to any of these

1. Decide its tier — deterministic property, standard, or empirical ([definitions](product-intent.md#the-evidence-standard)).
2. Meet that tier's bar. A property needs a test over the real input space; a standard needs to be explicit and uniform; an empirical claim needs pinned inputs and a control.
3. Put it in a document of the matching genre.
4. If it is empirical and later changes, correct it **everywhere it is quoted**, naming the correction rather than rewriting silently.

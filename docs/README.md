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

## Start here

| Document | Genre | What it settles |
|---|---|---|
| [Product intent](product-intent.md) | Governing | What this is, what it promises, what it must never claim, and the bar each kind of claim must clear. **When another document disagrees with this one, this one is right.** |
| [Architecture](architecture.md) | Governing | Layers, dependency rules, invariants and where each is enforced, and the known debt |
| [Philosophy](philosophy.md) | Governing | Why the tool is AI-specific — volume, not pathology |

## Decisions

| Document | Status |
|---|---|
| [ADR 001 — Evidence and verification](adr-001-evidence-and-verification.md) | Accepted; stages 1–3 implemented, 4–9 pending |
| [Report contract](report-contract.md) | Current — the report's producers, consumers, and schema-version policy |

New ADRs are `adr-NNN-short-title.md`, numbered in order, and never edited after acceptance except to mark them superseded.

## The standard, and what has been measured

| Document | Genre | Note |
|---|---|---|
| [Maintainability standard](standard.md) | Normative **and** Empirical | The rubric, the calibration, and the studies. **Known debt:** this file mixes two genres and should be split — the rubric is a judgment applied uniformly and needs no study; the studies are claims about the world and carry pinned inputs, controls, and stated fragility. Read the study sections as exploratory unless they say otherwise. |
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

# ADR 011: Three report presentations from one report

- Status: Accepted. Implementation progress is tracked in the [decision register](decisions.md), which is the single place it is stated
- Date: 2026-08-14
- Scope: How a finished report is shown — chat, Markdown file, HTML file — and how the user chooses
- Related: [ADR 008](adr-008-translation-and-decision.md), [ADR 009](adr-009-scan-history.md), [product intent](product-intent.md)

## Context

The product already has one report dictionary and several writers: Markdown (`--output`), a PR comment, a remediation prompt, SARIF. Chat (MCP / IDE agent) returns that Markdown. There is no HTML. Choosing a format is a flag, not a question.

1.0 needs three **user-facing** skins of the **same** data: what the human sees in IDE chat, a Markdown file, and a single packaged HTML file that an executive will actually open. The bounded work order remains the product ([product intent](product-intent.md)); these are presentations of it, not a dashboard product.

MCP is a local stdio process and does not run `input()`. It may write exactly five local artifacts: the repository config, user config, user state, repository scan history at `.maintainability/history.jsonl` and repository baseline at `.maintainability/baseline.json`; it never writes source or a report. First-run setup writes the first three, the audit's history rule may append the fourth, and an explicit baseline write controls the fifth. The host agent (Grok, Claude, …) is what can ask the user where to save returned report text.

## Options

**A. Three independent report builders.** Each walk of the tree produces its own numbers. Rejected: two scores is the class of bug this repo already paid for (P4).

**B. One report dict, three renderers; flags only.** Smallest change. Rejected: the user wants the agent to **ask** on invoke, default chat if they hit enter.

**C. One report dict, three renderers; ask on every interactive invoke; flags win; CI never asks.** Chosen.

**D. MCP server writes `.html` / `.md` into the repo.** Rejected: the MCP write boundary permits setup configuration and state, never reports. Chat shows text. Files are written by the CLI or saved by the host after it asks the user for a location.

## Decision

1. **One view model, three renderers.** Chat/CLI text, Markdown file, and one self-contained HTML file all read the report dictionary (and the scan-history records). None compute a score. Architecture rule 3 and the existing extension point stand.

2. **Default is chat/CLI text** — the Markdown the host already prints in an IDE conversation. Enter / go with no choice selects this.

3. **TTY:** ask every interactive invoke which of the three to produce. Do not persist the choice. `--format` / `--output` / `--html-output` skip the question and win. Non-TTY and CI never call `input()` (same class as 6.1).

4. **MCP:** first-run setup uses structured elicitation. The `maintainability-agent` prompt still tells the host in prose to ask, then call `audit_repository` with a format argument; that free-text ask remains open under D3. Chat returns Markdown. HTML and Markdown **files** are written by the CLI or saved by the host after a location ask, never by the MCP process.

> **Amended 2026-08-22 (D3 closed).** The free-text ask closed under D3.
> Presentation now arrives through the `format` argument;
> `action`/`choice_needed` separately governs whether an audit runs at all.

**Chat-path amendment (2026-08-16).** First-run setup persists a default presentation for later chat calls. An explicit per-call format and the host's own presentation ask always win over that stored default. The TTY rule is unchanged: it asks on every interactive invocation unless an explicit format or output option already decides.

5. **HTML** is one file: inlined CSS, charts as deterministic SVG generated from stored fields (no CDN, no fetch at view time — P1). It leads with an **executive summary** (estimate, grade, range, series direction or “no history yet”). Required charts, from schema-2 records only:
   - estimate + range over recorded scans
   - **five pillars over time** (condition)
   - **practice / maturity level over time** (separate series — never averaged with condition, [ADR 007](adr-007-pillars-and-practice.md))
   - current-run category bars
   Schema-1 scans appear on the rollup series and are gaps on pillar/practice charts. Empty history is an empty state, not a fabricated sparkline.
   Same remaining sections as Markdown: coverage, trend text, economic
   context, pillars (with practice caps), ISO categories, aspect scores
   including the unscored list, environment work order, largest files,
   function hotspots, work order / prompt, findings. A heading Markdown
   prints because the report dict has the data cannot be HTML-only-absent;
   `tests/test_html_section_parity_class.py` holds the catalog, not two
   leftover headings.
   Finding rows carry a presentation severity derived from the published class risk in the [standard](standard.md) and `CLASS_RISK_EFFORT`: risk 5 is **Severe**, 4 is **High**, 3 is **Medium**, and 1–2 is **Low**. Hard-gate failures display as **Severe**. These labels organize the existing findings; they do not change the estimate, range, or verified grade.

6. **SARIF and the PR comment stay.** They are CI artifacts, not this trio.

7. **History for charts** is [ADR 009](adr-009-scan-history.md) schema 2. No second store. Empty history is an empty state, not a fabricated series. Trends describe past scans; nothing forecasts.

## Consequences

Presentation grows an HTML renderer and a TTY format question. MCP grows a format parameter and a prompt line. The CLI writes `--output` and `--html-output`. Consumers who only ever use `--output` keep today’s Markdown path.

A pretty HTML page that invents a second score, or that cannot be reproduced from tree + config + history, is a defect.

## Invariants

1. Two renderers of the same report dict never disagree on estimate, range, grade, or finding identity.
2. HTML contains no `http://` or `https://` resource load (no CDN, no live chart library).
3. Non-TTY runs never call `input()` for format.
4. A set `--format` / output path suppresses the TTY question.
5. MCP never writes source or report files. Its write boundary is exactly repository configuration, user configuration, user state, repository scan history at `.maintainability/history.jsonl` and repository baseline at `.maintainability/baseline.json`.
6. Charts and trend sentences are computed only from fields present on stored `ScanRecord`s (schema 2). A missing series is omitted or named empty, never interpolated.

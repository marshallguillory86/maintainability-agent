# Roadmap

Governed by [product intent](product-intent.md). Anything here that would require a claim the intent forbids is not on this list, however interesting.

This project should stay a thin orchestration and prompt layer, not a replacement for mature analyzers.

## Shipped

Dependency-light native scanner; Markdown, JSON, SARIF and PR-comment output; bounded AI remediation prompt; changed-only mode; baseline gating; agent instruction packs; ISO/IEC 25010-inspired rubric calibrated against a query-selected corpus (40 repositories of Python/TypeScript/JavaScript through 1.10.x; 112 across all eight parsed languages from 2.0.0); git-history aspects (churn, hotspots, coupling, ownership); 92% coverage gate; portable invokable skill for Claude Code, Codex and Copilot Chat; optional local MCP server (writes only its five disclosed config/state artifacts, never source or reports) for Codex and its VS Code extension.

**Nine declaration languages**, each shipped as its own minor release: Python and Java, JS/TS/JSX and HTML, then C (1.1.0), C++ (1.2.0), C# (1.3.0), free-form Fortran (1.4.0) and fixed-form Fortran (1.6.0), over one shared walk in `_ranges_core` where a language is a module and a row. Fortran is the first with no braces, so the walk takes its bounding rule as an argument. Fortran also gained an analyzer adapter (fortitude, 1.5.0), its own complexity and cognitive readings rather than the C-family default (1.6.0), and toolchain practice detection (1.7.0). Per-language scope and misses are in [language support](language-support.md).

## ADR 001 is finished

**Stage 9 shipped in 1.9.0, and the migration is complete.** History materialization is separated from measurement: `tools/calibration/history_manifest.py` fetches and writes down what it fetched — pinned head, selection rule, selected commit ids, required parent objects and tool version — and `measure_fix_breadth` reads that manifest and never touches the network. A cache that has drifted from the pin is refused with the difference named, rather than measured as if it were pinned.

The checked-in `history_manifest.json` pins 33 subjects, 6,120 commit ids and 293 required parent objects. It also records something the study could not previously see: **five of the original 38 subjects no longer exist** — deleted or made private since selection — which is an argument for pinning rather than against it.

That closes the stage this project spent six audit rounds circling. The measurement that produced a false result did so because the oldest commit in a shallow clone has no parent, so git diffs it against the empty tree; each audit repaired the symptom it found because there was nothing to check a cache *against*. Now there is.

The evidence model, its property tests, consumer migration and the version-2 contract were already done; [ADR 002](adr-002-null-verified-grade-in-ci.md) stays rejected because it assumed `--fail-on-gate` consumes a grade when it only checks hard findings.

## The hostile audit has an artifact

**[ADR 013](adr-013-hostile-audit-prompt.md) shipped in 1.10.0.** The adversarial loop is the highest-leverage quality process here and was the only one with no artifact: it depended on a person hand-writing a fresh prompt into a fresh session, re-deriving context the report already held, so runs were neither seeded nor comparable.

`render_hostile_audit_prompt` is now the third emitter on the prompt seam beside `render_ai_prompt` and `render_agent_instructions` — CLI `--hostile-prompt-output`, MCP prompt `maintainability-hostile-audit`. It seeds the adversary from one run: the commit under audit, the evidence already computed (what ran, what did not, which concepts nothing measured), P1–P8 with the shape of evidence that falsifies each, and the audit contract this project already holds itself to. The boundary is ADR 008's: **the deterministic core seeds the hostile audit; it never performs it.** No gate, no score, nothing written or sent.

## Next

**Swift** — see [language adapters](#language-adapters). The remediation-integrity checks below are the other near-term block.

## Language adapters

The cadence is **one language per minor release, never a batch** — five were written that way between 1.1.0 and 1.6.0, and the reason is that each one has to earn its claim separately.

**The price of admission, unchanged since [ADR 006](decisions.md):** a language is claimed only when it has a scanner of its own, a documented list of what it misses, and tests that pin them. The register's original wording said no further range detectors would be written; five were, and the rule that wording protected is what survived. A language does not get onto the table below by having its extension added to a config.

**Swift shipped in 2.4.0.** Braced, so it reuses the `_ranges_core` walk; what needed its own answer was narrower than this section predicted, and one of the four predictions was wrong.

Right: an `extension` adds methods to a type declared elsewhere, so a member is reported as `Widget.draw` rather than a bare `draw`; a `protocol` declares bodiless requirements that mint nothing; **computed properties** are the C# properties problem again and are not declarations.

**Wrong: "string interpolation puts braces inside literals".** Swift interpolates with `\(expr)` — parentheses, not braces — and string contents are masked before any counting regardless. The real hazards were different and neither was predicted here: Swift has **no statement terminator**, so the shared bare-signature rule could not see where a protocol requirement ended and reported it as two lines of body; and **`class` is both a keyword and a modifier** (`class Widget` versus `class func make()`), so stripping it with the other modifiers cost every `final class Store` its type. Both are pinned by tests.

Swift also needed its own reading of a branch: `guard` is the language's primary early exit and is absent from the C-family pattern, so a guard-heavy function would have read as branchless — the defect Fortran shipped with.

Go and Rust remain named in [ADR 006](decisions.md) as unwritten on exactly these terms. They are not refused and not scheduled.

**What an unwritten language already gets today.** Swift, Go and Rust are all classified by discovery, and all have practice signals wired (`.swiftlint.yml`, `.golangci.yml`, `rustfmt.toml`, `clippy.toml`, and the `swiftlint` / `golangci-lint` / `clippy` command patterns). What none of them gets is a declaration population: rates are **withheld** with the missing parser named, rather than approximated. That is the P7 boundary and it is the reason a language is a release rather than a config entry.

**Two gaps that widen with every language added**, and should be closed alongside rather than after:

- ~~**Test-command detection stops at Python.**~~ **Closed in 2.5.0.** `_test_commands` reads the tree's build manifests and offers the command as the setup question's default, on every surface: `swift test`, `fpm test`, `cargo test`, `go test ./...`, `ctest`, `mvn test`, `gradle test` (the wrapper when one is checked in), `dotnet test`, `npm test` and `pytest`. Two properties are the whole design. It **suggests, never decides** — the `require_test_command` hard gate asks whether a *human documented* a command, and a value the tool wrote unasked would satisfy that gate on evidence it invented. And `xcodebuild test`, named in the original entry, is **deliberately not shipped**: bare `xcodebuild test` needs `-scheme` and usually `-destination`, so every suggestion it could make is a command that fails, and a suggestion that always fails teaches the operator to ignore suggestions.
- **A new language inherits whatever the corpus does not hold.** This was the sharper of the two gaps until 2.0.0: the corpus was 40 JS/TS/Python repositories and LAPACK read 7.18x the declaration median against an anchor containing no Fortran. It is now 112 repositories across all eight parsed languages, so the gap closes for what ships today — and reopens for every language added after, since a scanner without corpus members is scored against code unlike it again. Extending the corpus moves `CALIBRATION_C` and re-grades every repository, so it stays a release of its own rather than a patch bundled with a scanner.

### Corpus policy: recalibrate once, after the remaining scanners land

**Decided 2026-09-04.** A language ships parsed and **unanchored**: its scanner lands, and the reference corpus is *not* extended to hold it in the same release. The corpus is re-measured and `CALIBRATION_C` re-derived **once**, after the remaining planned scanners are written — not once per language.

Swift (2.4.0) is the first language to ship under this policy and is unanchored today. It is measured by a parser and scored against a 112-repository anchor containing no Swift. COBOL (2.7.0) and then Go, Rust, PHP and Ruby (2.11.0) shipped the same way, so six languages now await the one recalibration rather than each paying for its own.

The reason is cost, and it is worth stating exactly rather than as "it's slow". Reuse (`--reuse`) makes a *corpus* change cheap: adding one repository re-measures one and reuses 111. It does nothing for a *language* change, because adding a scanner changes the measurement code, which moves `scanner_fingerprint`, which invalidates every stored row. So every new language costs a full re-measure of the whole corpus — and each one also re-grades every repository this tool has ever scored, since `CALIBRATION_C` moves. Paying that per language means paying it in full, repeatedly, for an anchor that is obsolete again at the next scanner.

**What this policy costs, stated so nobody has to discover it:** an unanchored language is scored against code unlike it, and its grades are therefore less trustworthy than an anchored language's. That is the same defect as LAPACK's 7.18x reading, accepted deliberately and for a bounded time rather than encountered by surprise. The honest framing is that Swift's *findings* are as good as its parser, and Swift's *grade* is provisional until the recalibration.

**What must happen at that recalibration**, so it is a checklist and not a memory: re-measure the full corpus with the then-current scanners, re-derive `CALIBRATION_C` by bisection, re-run the calibration corpus tests, publish the study, and ship it as a **major** release — it re-grades every repository, which is a breaking change to every published number.

**Not scheduled, and the distinction matters.** Kotlin, Scala, Elixir, Zig and the rest are classified by discovery and may be measured by adapters, but no scanner is scheduled for any of them. They are not refused — they are unwritten, on the terms above. A language moves onto this list when it is decided here, not by being named in an older register entry.

Go, Rust, PHP and Ruby sat on that list until 2.11.0, when scanners were written for all four. The sentence above went on naming them for the length of that release, which is why a test now holds this paragraph against the languages the scanner actually reads.

## A known shape problem: this tool is end-of-loop heavy

Worth stating plainly because it aims several roadmap items. Addy Osmani frames agent constraints as **back-pressure that should exist throughout the loop, not as a single review at the very end** ([Agentic Code Quality](https://addyo.substack.com/p/agentic-code-quality)). Measured against that, this tool is strong where it is cheapest to be strong — a CI gate after the work is done — and thin during the loop, where a constraint is worth far more because it prevents rather than rejects. The shipped IDE and agent skills are a partial answer.

**The pre-commit half closed in 2.9.0.** `--staged` scans what the git index will commit — the index, not the working tree, so a half-staged file is measured as it will land — against the same thresholds the gate uses, and `--install-precommit-hook` writes the hook. It is deliberately not a small audit: it produces **no score**, because a diff has no population to draw a rate from, and it applies no repository gates, writes nothing and runs no tests. On this repository it costs 0.17 seconds against the full audit's 266, and that ratio is the feature — a hook slower than the author's patience is a hook they uninstall, at which point it constrains nothing.

**The in-loop half closed in 2.10.0.** `--check PATH` answers what a budget allows for content that has not been written yet: no repository, no git, no scan, and the path names the content rather than being opened. It reports breaches and, while there is room, how much is left — which is the part a gate cannot give, because a gate only speaks once it is already too late to be cheap. That is what "prevents rather than rejects" meant.

**What this section no longer claims.** Both moments the work stops are now covered, and so is the moment it does not. The shape problem as Addy Osmani framed it is closed; what is left is not another door but evidence that these are used — the headroom figure in particular is justified by argument and not yet by anybody's behaviour. A field check on 2.10.0 found the figure only changes an author's decision once it is already near the line, which is worth knowing before any more is built on it.

One door is still missing and it is not a shape problem: `--check` is CLI-only, while [product intent](product-intent.md) names chat/MCP the primary surface. A feature built for agents that an agent cannot call over MCP is a gap in delivery, not in design.

He also names the trade-off available once generation outruns verification: scale verification, slow generation, lower standards, or **relax constraints in low-risk areas while tightening them elsewhere**. Only the last is a real engineering answer, and it is what the policy-as-code item below is for. This is a borrowed frame, not evidence — it tells us where to look, not what is true.

## The remediation hole: closed in 2.1.0 through 2.3.0

The second known shape problem, and for most of this project's life the more serious one, because it sat under the product's central claim. The bounded work order *told* an agent to fix exactly these findings and refactor nothing else, and nothing checked that it did. It is now checked.

Prompted by [What is agentic testing?](https://theaiengineer.substack.com/p/what-is-agentic-testing-fa2), whose argument for where the model should stop — agent at authoring, model out of CI, frozen oracle in the gate — is the architecture this tool already has. The score is a rate computed by code, not a model's opinion, so the "right by construction becomes right most of the time" failure it warns about does not apply here. Its failure modes for the *repair* step did.

Three checks closed it, and they shipped in the order they were worth building — the first two in 2.1.0, the third in 2.2.0:

**1. Scope conformance, verified against the work order** — `--conformance <revspec>`, `--fail-on-out-of-scope`. The work order names its findings and their paths, so comparing a diff against them is mechanical. A remediation diff that touches files the work order never named is reported as out of scope. One rule is not mechanical and is worth knowing: a test added for a fix stays in scope even though the work order never named the test file, because demanding otherwise would make the check punish the behaviour the product asks for. `_conformance.py`.

**2. A suppression is a finding, not a fix** — the same check's second, separate verdict. A finding could be made to disappear by deleting the code, adding `# noqa`, `# type: ignore`, `eslint-disable` or `pragma: no cover`, or skipping the test; the gate went green and nothing noticed. Encoded now: a suppression added on a path the work order named is reported whether or not the diff stayed in scope. `conformant` and `clean` are two answers, never merged into one, because a change can obey the work order and still silence a finding inside it.

**3. Per-dimension score regression fails the run** (2.2.0) — `--fail-on-regression`. `--fail-on-new` plus a version-3 baseline and `_finding_match` already recognised a finding that cleared and returned. The ratchet on the *dimensions* is what was missing: a change that improved one dimension while quietly regressing another passed. It has three outcomes rather than two — held, regressed, and **not comparable** — because two scans taken under different calibration cannot be differenced, and reporting that as "held" would be the overclaim the check exists to prevent. `_ratchet.py`.

### The umbrella: an attestation artifact — shipped in 2.3.0

The three checks are mechanisms. What they add up to is one thing worth naming: **a per-change record that an independent process can produce and a generator cannot produce about itself.** `--attestation-output`, `_attestation.py`.

Reproducible and derived from one run: what was measured, what the agent was *told* to change, whether it stayed inside the work order, whether it silenced anything, and what moved on each dimension. A code-generating agent has an audit trail of its own actions; that is a self-report. This is the second opinion, and it is the shape a regulated reviewer asks for — the question there is never "is the tool good", it is "who checked the vendor's output, and can they re-derive the check months later".

Two words it refuses. It is **not signed** — nothing here holds a key, and "signed" is exactly the word a reader reaches for with an attestation, so the document says the opposite in its own text. And a question nobody ran renders as *not asked*, never as passed; an incomparable ratchet renders as *not established*. The artifact's whole value is in what it declines to claim.

This is the one place where determinism stops being an engineering preference and becomes the product. A tool that routes across models cannot re-derive last quarter's verdict; this one can, byte for byte, which is why the attestation can be evidence rather than a log line.

**What is still open here:** the checks read the diff's *shape* — which paths it touched, what it silenced, which dimensions moved. Nothing reads whether the change was correct, and nothing will; that is a claim this tool does not make and the attestation says so in its own text.

### Two features that only a deterministic, unmetered checker can offer

**Run-over-run comparison of generated output** — **shipped in 2.6.0**, `--transformation NAME`. Where an agent performs the same class of work repeatedly — a migration, a framework upgrade, a codemod applied repeatedly in one repository — nobody measures whether run seven produced better code than run six. The generator cannot answer it: its output is not reproducible and it has no memory across runs. This tool already had pinned references, structured finding identity and scan history, so the comparison was a join rather than new machinery. The value is highest exactly where volume is highest and review capacity is lowest.

What it reports is each labelled run's **movement in estimate since the previous recorded scan**, and how the newest run's movement compares with the one before it. Three things it deliberately does not do. It never says one run was **"better"** — two runs of one codemod land on different code, so a larger movement can come from the tree as easily as from the run, and "moved further" is what the numbers support. It attributes nothing to the transformation: the label is the operator's claim about what happened in an interval, and everything else that happened in that interval is inside the number. And it **refuses across an instrument change**, naming how many runs it refused rather than dropping them silently — a reader who cannot see a refusal concludes there was no history.

**The work not sent** — **decided against as a feature (2026-09-04); it is one sentence in the README instead.** The idea: every finding this tool produces without a model call, and every diff its bounded work order keeps from becoming an open-ended rewrite, is work that never reaches a metered agent. Under per-action pricing that is a number with a currency attached, and the tool that produces it is the one with no incentive to inflate it.

It was dropped on inspection, and the reason is worth keeping. Every quantity it would report — files examined, declarations examined, findings produced, bounded work-item count — **is already in every report**. The feature added no measurement; it added a label. And the label is where it goes wrong: "work not sent" is heard as "money saved", and converting it to money needs a price per token, an assumption about what an agent would have done unprompted, and an assumption about how many turns it would have taken. All three are counterfactual and none is in the repository. Anything stronger would be the economic-ladder claim [ADR 004](adr-004-economic-context.md) has not earned — and ADR 004, which ships, prices *human* labour against recurrence and churn, which is a different question from agent metering.

What survives is the true part, stated where a reader meets it: the report says what it examined and produced, and all of it is computed with no model call.

### What this tool does not compete on

Named because the failure mode for a one-maintainer project is competing everywhere and winning nowhere. **Code generation. Security scanning and compliance profiles. Comprehension of languages it does not parse. IDE experience. Model routing.** Tools that do those things are the customer for what this produces, not the competition — and the better a generator gets, the more an independent check on its output is worth.

**Related, and named separately because it is a detector rather than a gate:** *tests that assert implementation details instead of behaviour* is listed under Additional detectors below. It is the direct answer to the review problem the same article raises — generated tests that look like yours and slide through review — and it is aspirational today.

## Then

**Additional analyzer adapters** — Semgrep, pytest/coverage, and SonarQube export. Ingest output, preserve provenance, and do not pretend every analyzer has the same semantics. The fourteen shipped adapters — twelve native plus the declared pylint and mypy integrations — are listed in [analyzer pool](analyzer-pool.md#adapter-status-stated-plainly).

**Deterministic semantic policy** — prototype [ADR 003](adr-003-deterministic-semantic-policy.md) in TypeScript first: compiler-backed facts, explicit repository policies, and non-gating design-review candidates. Measure precision before adding any hard gate, and do not add a score weight during discovery.

**Economic context and impact scenarios** — prototype [ADR 004](adr-004-economic-context.md) as an optional, separately labeled prioritization layer. Prefer repository-derived exposure data, ask only for business context the repository cannot contain, and keep all scenarios out of the standard grade.

**Additional detectors.** Worth building because the cost they name is real, and — per [philosophy](philosophy.md) — worth detecting *regardless of who wrote the code*: docstring and signature drift, tests asserting private names, single-use abstractions, speculative generality, stale generated comments. Each becomes scored only by being given weight in the rubric.

**Policy-as-code** — new-code thresholds, changed-file thresholds, required tests for changed API files, architecture boundary rules by path.

**Per-repository rubric overrides.** Currently refused: the rubric is a standard, and a standard everyone edits stops being one. Any override mechanism must label its output a **house variant** so it cannot be compared to a standard score.

**Delivery** — GitLab and Azure DevOps adapters. The GitHub Action (`action.yml`), the PR-comment body (`--comment-output`) and historical trend reporting all **ship**; this line listed them as future work long after they landed, and an external evaluation of the tool got the CI story right by reading the README *despite* this roadmap. A document that under-claims is the same defect as one that over-claims — it just fails in the direction that costs adoption instead of credibility.

## Distant future

**Cross-repository transformation comparison — not built, low priority.** `--transformation` (2.6.0) compares runs **within one repository**. The fleet version — many repositories' histories joined on one label, to report how a single codemod fared across an org's services — is wanted eventually and is not scheduled.

The reason it is low priority is not appetite, it is that the hard part is not the join. `COMPARABILITY_FIELDS` names what makes two scans differenceable: `rubric_version`, `calibration`, `thresholds_digest`, `analyzers`, `scored_languages`, `scope`. Two scans differing on any of them came from different instruments, and a trend across them measures the instrument rather than the code. **Across repositories every one of those differs by default** — each repository has its own thresholds file, its own installed analyzer set, its own language mix. So the feature is not "join the histories"; it is *prove a fleet shares one instrument and refuse the members that do not*, reusing `segments`. A version that skipped that proof would report an org's variation in **configuration** as variation in its **code**, confidently.

The honest first step is smaller than the feature and worth building alone: **export a history**, then compare exported histories that declare the same instrument. Nothing collects them today — a history lives at `.maintainability/history.jsonl` inside each repository, and this is a local stdio process with no fleet surface.

Two clarifications, because this item has been misread twice. The corpus is a **calibration instrument, not a usage pattern**: the repositories in it exist to fit the scale, and their number says nothing about how many a user points this at. And the resolved debt entry *"nothing compares two runs of the same transformation"* closed a single-repository gap — it is not the first half of a larger cross-repository item.

**Deterministic adversarial-properties detection.** The second play behind [ADR 013](adr-013-hostile-audit-prompt.md): a detection dimension that audits a *target* repository for the hardening classes this agent enforces on itself — a write that follows a symlinked route, an empty tool run read as clean, a caller argument reaching a filesystem or shell sink unvalidated, absence read as a pass. Deterministic and AST/pattern-derivable, so it fits the suite rather than the prompt seam; distinct from [ADR 013](adr-013-hostile-audit-prompt.md)'s emitter, and it brushes the `secure-code-agent` boundary, so it needs an explicit scope decision and its own ADR before any build. A future release, not a next step.

## Studies that would earn a claim

Listed with the bar each must clear, because the project has retracted one empirical claim already:

- **Outcome tuning.** Score a repository at a past commit, measure the following year's fix churn on held-out repositories. This is the only study that could license "the score predicts anything", and until it runs, the rubric is a standard and not a predictor.
- **Economic-impact validation.** Pre-register a model, estimate maintenance effort from information available before the work, and compare it with held-out task effort or cost. Organization-specific calibration comes before any cross-organization claim; configured assumptions alone license only scenario language.
- **Fix breadth, done properly.** A diff-content fix detector, a registered primary outcome, and commit-level authorship. The current result is a consistent direction across three specifications that straddle p = 0.05 and fails Holm correction — exploratory, and labeled so.
- **Bounded-prompt effectiveness.** The pre-registered experiment returned INCONCLUSIVE: far more findings closed, no measurable narrowing. A better-powered design with more subjects would settle it.

## Non-goals

Replace SonarQube, Semgrep, Qlty, Code Climate, ESLint, Ruff, Radon or language-native tooling. Automatically rewrite repositories. Send code to an LLM by default. Treat maintainability as purely numeric. Claim to detect AI authorship — [tested, retracted](studies.md#does-this-detect-ai-written-code), and not revivable without a pre-registered design.

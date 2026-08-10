# Product intent

The governing document. When another document, a code comment, or a release note disagrees with this one, this one is right and the other is a bug.

## What this is

A deterministic maintainability audit that produces a **bounded work order** for an AI coding agent.

Not a linter (those exist and are better at it), not an AI reviewer, not a quality dashboard. The scanner and the score exist to aim the remediation prompt. If the prompt were removed, the rest would be a worse version of tools that already ship.

## The job it does

Agents write code faster than humans can read it. The ratio of code-written to code-reviewed has collapsed, and unmaintainable code that used to accumulate over years can now accumulate in an afternoon. The same speed is the way out: an agent pointed at specific, deterministic findings can fix them at the same rate they appear.

The loop this product closes:

1. Measure pressure points deterministically, with no LLM involved.
2. Apply one uniform standard, so "better" and "worse" are not an argument.
3. Emit a prompt scoped to *those findings only*, with explicit instructions not to refactor beyond them.
4. Hand it to the agent. Review a scoped diff instead of a speculative rewrite.

Step 3 is the product. Steps 1 and 2 are in service of it.

## Who it is for

- Teams running agents in the dev loop who are tired of unbounded cleanup PRs.
- Repos that want a maintainability gate without a SaaS analyzer or shipping code to a third party.
- Solo developers who want one deterministic audit pinnable in a Makefile or CI script.

## What it promises

Each promise is falsifiable, and named so a failure can be reported against it.

| # | Promise | Falsified by |
|---|---|---|
| P1 | The audit is deterministic: same tree and config in, same findings out, no network, no LLM | Two runs disagreeing on identical input |
| P2 | The score applies the same rubric to every repository, and the rubric is readable in source | A repo-specific code path changing a weight or band |
| P3 | Withholding evidence cannot improve the reported grade | Any input whose removal raises the graded field |
| P4 | The overall equals the weighted mean of the categories printed beside it | A report where the arithmetic does not check |
| P5 | The remediation prompt names only findings the audit actually produced | A prompt instruction with no corresponding finding |
| P6 | Every empirical claim in this repo is reproducible from checked-in pinned inputs | A quoted number that cannot be re-derived offline |

## What it must never claim

This list exists because the project has already broken it once and retracted. Adding a claim in these shapes requires deleting it from this list first, with the evidence that earns it.

- **That it detects AI-written code**, or that any metric distinguishes AI authorship. Tested with a matched control and retracted (p = 0.546). Any revival needs a pre-registered design with commit-level authorship.
- **That the score predicts business outcomes** — defect rates, delivery speed, cost. No outcome study has been run. The rubric is a standard, not a model of the future.
- **That a passing grade means the code is maintainable.** It means nothing this tool measures is out of band.
- **That the architecture, or any ADR, is "fully implemented"** while its consumers and invariants have not migrated.
- **That a bug class is closed** because the reported instance stopped reproducing. See the closure rules below.

## The evidence standard

Six audit rounds went in circles for one reason: claims of different kinds were held to the same loose bar. A judgment was defended as if it needed a study, and a study was asserted as if it were a judgment. Every claim in this repository is exactly one of these, and its type determines what it needs.

### Tier 1 — Deterministic property

*"The overall is the mean of the printed categories."* A statement about what the code does.

**Requires:** a test that fails if it stops being true. Not an example — a property over the real field set or input space. No study, no debate.

### Tier 2 — Standard (judgment)

*"Duplication is 25% of modularity."* *"A file over 400 lines warns."*

**Requires:** that it be explicit, deterministic, uniform across repositories, and readable in source. **It requires no validation study, and no apology.** Every standard — ISO 25010, a building code, a style guide — is judgment made explicit and applied uniformly. Anyone may disagree with a weight; they can read it and argue. Legitimacy comes from being stated and applied evenly, not from being proven optimal.

Calibration against the reference corpus is what keeps these judgments *anchored* to real code. It does not convert them into Tier 3 facts.

### Tier 3 — Empirical claim

*"AI-assisted fixes touch more files."* A statement about the world.

**Requires:** pinned inputs checked in, a matched control, a pre-registered primary outcome, correction for multiple comparisons, and re-derivation offline. Absent any of those, it is reported as an **exploratory direction** and never as a finding. A result that crosses significance depending on a specification choice is *fragile by demonstration* and must be labeled so.

**The failure mode this prevents:** stating a Tier 3 claim in a document whose genre implies Tier 1 or 2. That is precisely how the retracted claim reached the README headline.

## When a finding is closed

Adapted from [ADR 001](adr-001-evidence-and-verification.md), which earned these the hard way. All conditions, not a majority:

1. The original reproduction no longer fails.
2. The governing invariant is stated **independently of that reproduction**.
3. Tests exercise the production model, not a hand-built fixture that happens to carry the right keys.
4. The equivalent missing, invalid, zero, and not-applicable states are all covered.
5. Public claims do not exceed what the invariant and tests establish.
6. Any changed empirical result is re-derived from pinned inputs and corrected **everywhere it is quoted**.

Passing the test suite and the self-audit is necessary and is not sufficient. Two consecutive audit rounds were rejected for fixing the demonstrated instance and leaving structurally identical paths untouched.

## What success looks like

- An agent handed the bounded work order acts on the standard instead of wandering.
- A maintainer can explain any grade by pointing at a named measurement.
- A hostile audit finds nothing that a stated invariant did not already cover.

### What the evidence currently supports

**[studies.md](studies.md) owns the numbers.** This section deliberately holds none, because the previous revision duplicated the experiment's table and interpretation here and the two copies promptly disagreed — which is the failure the [genre split](README.md) exists to prevent, committed in the governing document itself.

One pre-registered experiment has been run: [does the bounded prompt work?](studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered). Its registered verdict is **INCONCLUSIVE** and stays recorded that way; the registered hypothesis was that bounded prompts produce narrower diffs, and they did not.

**The defensible public sentence**, and the only one:

> Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count.

An earlier revision of this line read "bounded ones did not" — which concealed the bounded arm's own failure and was flagged as a misleading public claim. Two limits travel with that sentence wherever it goes: the bounded arm is told which findings to close and then scored on closing them, and "improved" means "closed the findings this tool names", which no outcome study has yet connected to real maintenance cost.

## What failure looks like

- The score becomes something to game rather than something to act on.
- The tool grows into a worse SonarQube.
- A claim outruns its evidence tier — the single failure this project has actually committed.

## Non-goals

Replacing mature analyzers; rewriting repositories automatically; sending code to an LLM by default; treating maintainability as purely numeric; preserving undocumented behavior for hypothetical consumers.

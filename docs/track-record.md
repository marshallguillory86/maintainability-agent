# Track record

Every claim this project made, tested, and kept or withdrew — kept as its own
document because it is the argument for trusting the numbers, and that argument
is made by what was *removed*, not by what was added.

Moved out of the README in 2.0.0. It had grown to 52 lines of a 500-line budget
on the page a first-time reader scans, and a reader deciding whether to run the
tool needs the promises and the limits before they need the history. The history
still matters — it is why the promises are believable — so it gets a page rather
than a trim.

## The road to 1.0

1.0 is not a rewrite. It is the line drawn under a long arc of **subtraction** —
what remained after every claim the project could not stand behind was removed.
The arc is the credibility:

> **0.5.0 — the scoring engine was rebuilt.** The old model counted findings
> absolutely, so it graded repo *size*, not maintainability: it scored
> **Django, pytest, black, tornado, httpx, lodash, svelte, fastapi all at
> 0.0 / F** while a 53-file toy repo scored 4.6 / A. Scores became **rates**,
> normalized per dimension against what real code carries and calibrated so
> the corpus median earns a B. See
> [standard.md](standard.md#how-the-scale-was-calibrated-050).

> **0.6.0 — a near-duplication finding that pairs the copies**, naming the
> declaration to reuse (*`toAtomicAmount` at `TradeTicket.tsx:862` already does
> this*), so renaming can't hide clone-instead-of-reuse. Useful on its own
> terms — and explicitly **not** evidence about who wrote the code.

> **Retracted: that near-duplication distinguishes AI-written code.** 0.6.0 had
> called it "the first signal that separates AI-written applications from mature
> human-written OSS."
> Re-run against a control matched on age, popularity and language, the near-duplication gap is not significant (p = 0.546), and no other metric earns the claim either.
> The honest summary is *this design could not measure a difference*, not *there
> is no difference*. See [studies.md](studies.md#does-this-detect-ai-written-code).

> **0.7.0 — the evidence model.** The score is **withheld** when the evidence
> cannot support one; a diff is not a repository grade. External analyzers
> became the **primary** evidence where they measured a full concept set, with
> the built-in detectors as the fallback and disagreement **widening the range**
> rather than being averaged. The grade is *gated* and *banded from the evidence
> floor*, so withholding evidence can never buy a better letter.

> **0.8–0.9 — one setup, chat-first.** Chat / MCP became the primary surface,
> the CLI the automation door, and the three transports converged on a single
> question set. A run of chat-surface wiring defects — and their closing tests —
> is recorded in
> [defect-register-chat-surface.md](defect-register-chat-surface.md).

> **1.0.0 — acceptance and the complete work order.** A real-repo acceptance
> round on a mixed Python/TypeScript codebase hardened the last edges: the
> report now carries the entire backlog with a per-item copy-paste prompt,
> charts were rebuilt for legibility, reconfigure stopped destroying hand-tuned
> config, and TypeScript semantic coverage learned to find workspace projects
> and a locally-installed compiler. See the [changelog](../CHANGELOG.md#100---2026-09-01).

The through-line: this repository runs the tool against **itself** in CI and
checks the report in ([docs/self-audit.md](self-audit.md)). An earlier
revision of the self-audit table advertised 5.0/A+ after the codebase had
drifted to a B; a hostile audit caught the stale claim — precisely the failure
mode this tool exists to catch.

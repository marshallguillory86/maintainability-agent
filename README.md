# Maintainability Agent

![maintainability-agent — a deterministic audit whose output is a bounded work order for your AI coding agent: fix exactly these findings, refactor nothing else](docs/cover.png)

**A deterministic, offline maintainability audit whose output is a _bounded
work order_ for an AI coding agent** — a copy-paste prompt, per finding, that
says *fix exactly these and refactor nothing else*. Chat-primary; CLI for CI.
Version **2.8.1**.

**Languages parsed:** Python, Java, C, C++, C#, Swift, Fortran (free-form
*and* fixed-form), and the JS/TS family — each by a scanner written for it, and
measured with that language's own reading of what a branch is.
[What that means per language](#language-support).

```bash
pip install maintainability-agent          # CLI + library
pip install "maintainability-agent[mcp]"   # optional local MCP server for chat / IDE hosts
cp -r skills/maintainability-agent ~/.claude/skills/   # Claude Code slash command
```

---

## Executive summary

Agents write code faster than anyone can review it. Not measurably *worse*
code — this project tested that claim about itself and retracted it — just
**more**, arriving faster than trust can accumulate. Linters and quality
dashboards catch some of the resulting slop. None of them ship the one thing
that actually closes the loop: **a bounded prompt back to the agent, scoped to
the findings, that forbids unbounded rewrites.**

That prompt is the product. Everything else — the scanner, the ISO/IEC
25010-inspired 0–5 score, the analyzer pool, the semantic and economic
signals — exists to aim it. Remove the prompt and what's left is a worse
version of tools that already ship.

What 1.0 guarantees:

- **Deterministic and local.** Same tree, config, pinned analyzer versions and
  history in → same evidence, findings and score out. The analysis performs no
  network access and invokes no LLM, and **this agent does not transmit your
  source.** Every report states what it examined and produced — files,
  declarations, findings, bounded work items — **all computed with no model
  call**: work a metered agent never has to do. Third-party analyzers it may
  spawn (eslint, jscpd, lizard) are **not network-sandboxed** — this process does
  not police whether *they* phone home; install them for an air-gapped run.
- **One uniform rubric**, readable in source, applied to every repository —
  so "better" and "worse" are not an argument. Calibrated against a
  query-selected corpus of mature open-source projects; the corpus median
  earns a **B**, and A+ is *gated*, not averaged.
- **Honest about evidence.** A score is withheld when too little was examined
  to support one — a `--changed-only` diff is not a repository grade, and a
  shallow clone is not an A. Every reported value names what measured it.
- **The complete work order is the report; chat/CLI is a bounded UI.** The
  HTML/Markdown report carries the entire backlog with a deterministic
  copy-paste prompt for each item. The chat surface stays a tight summary so a
  host's payload cap can never truncate the prompt.
- **One setup, three transports.** Chat, MCP, and an interactive CLI TTY ask
  the *same* first-run questions. A surface that asks a subset is a bug.

Governing intent lives in [docs/product-intent.md](docs/product-intent.md) —
that document is authoritative, and this README defers to it wherever the two
differ.

## Why this exists

The ratio of code-written to code-reviewed has collapsed. Unmaintainable code
that used to accumulate over years can now accumulate in an afternoon:
duplicated helpers, oversized files, speculative abstractions — the same slop
hand-written codebases always accrued, now at machine speed.

The same speed is the way out. An agent pointed at specific, deterministic
findings can fix them at the rate they appear. The loop this tool closes:

1. **Measure** pressure points deterministically, with no LLM involved.
2. **Score** with one uniform standard, so the verdict is not a debate.
3. **Emit** a prompt scoped to *those findings only*, with explicit
   instructions not to refactor beyond them.
4. **Hand it to the agent.** Review a scoped diff instead of a speculative
   rewrite.

Step 3 is the product; steps 1 and 2 are in service of it. Every other tool in
this space stops at "here's a list of findings."

**Who does the checking matters as much as what it checks.** An author is never
the independent check on their own work, so a platform that generates code and
grades it is producing a self-assessment — a property of the arrangement, not a
criticism of any one of them. This writes nothing and runs no model, which is
what lets its verdict be evidence ([the principle](docs/philosophy.md#principles)).
Since 2.1.0 the work order is also **checked**: `--conformance` compares the
returned diff against the paths the report named, `--fail-on-regression`
ratchets the dimension scores, and `--attestation-output` composes them into one
record ([how that hole was closed](docs/roadmap.md#the-remediation-hole-closed-in-210-through-230)).
The limit, stated in the same breath: those checks read the diff's **shape**,
never its correctness — whether the change works is not a claim this tool makes.

One pre-registered experiment has tested the bounded prompt.
Generic prompting made 2 of 6 repositories worse; bounded prompting made 1 of 6 worse and improved 5 of 6, under this tool's own finding count.
The *registered* hypothesis was narrower diffs, which did not hold, so the
registered verdict stands at **INCONCLUSIVE**. Method, limits and raw data:
[docs/studies.md](docs/studies.md#does-the-bounded-prompt-work-controlled-experiment-pre-registered).

### Who it's for

- Teams running AI agents in the dev loop, tired of unbounded cleanup PRs, who
  want a CI gate that actively constrains follow-up scope.
- Repos that want a maintainability gate without a SaaS analyzer or shipping
  code to a third party.
- Solo devs who want a single deterministic audit to pin in a Makefile,
  pre-commit, or local CI script.

## The road to 1.0

1.0 was the line drawn under a long arc of **subtraction** — what remained after
every claim the project could not stand behind was removed. A scoring engine
rebuilt after it was found to grade repo *size*; a headline claim about AI
authorship retracted against a matched control; a score that is withheld rather
than guessed. That arc is the credibility, and it is recorded in full, with the
figures quoted from their approved summaries, in [the track record](docs/track-record.md).

## Install

```bash
python3 -m pip install maintainability-agent
maintainability-agent --root . --config maintainability-agent.json
```

Or run from a source checkout without installing:

```bash
python3 -m maintainability_audit --root . --config maintainability-agent.json
```

For an editable dev install and the full local-verification sequence, see
[CONTRIBUTING.md](CONTRIBUTING.md#local-verification). Upgrading from 0.x? The
scale and the evidence model changed on the way to 1.0 — see
[docs/migration-1.0.md](docs/migration-1.0.md).

## Primary Surface: Chat / MCP

Drive the local MCP process from an IDE assistant or chat host. Call
`audit_repository`; **unset `action` never audits.** An unconfigured repository
(no repository `maintainability-agent.json` and no user config) returns
`setup_needed` and `audit_ran: false` — structured setup choices for analyzer
policy, history consent, economics, test-suite execution, and presentation, and
no report. A configured repository returns `choice_needed` (`run` or
`reconfigure`), also without a report. Answering setup does not start an audit.
`action="run"` returns the report and its bounded remediation prompt to the
conversation. `record_history=None` follows the persisted first-run consent and
always appends to an existing history; an explicit `true` or `false` wins.

```bash
python3 -m pip install "maintainability-agent[mcp]"
maintainability-agent mcp --allow-root /absolute/path/to/repository
```

Presentation is exactly three choices — **chat**, a **Markdown** file, or a
single-file **HTML** report. Where to save is asked only after a file format is
chosen, and no report file is written without that choice. See
[chat workflow help](docs/help/README.md) and [IDE and agent
integration](docs/ide-agent-integration.md).

## Automation / CI: CLI

Use the CLI for scripts, repeatable automation, and CI gates. Copy the example
config to your repo root as `maintainability-agent.json`, then:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --fail-on-gate \
  --output maintainability-report.md \
  --prompt-output maintainability-remediation-prompt.md \
  --comment-output maintainability-pr-comment.md \
  --sarif-output maintainability.sarif
```

`--fail-on-gate` fails CI on hard gates only (a missing README, an undocumented
test command, a breached threshold) — never on a letter grade, and never on a
withheld estimate. For PR work, add `--changed-only main...HEAD` to audit the
diff; on a change too small to support a rate, the estimate and grade are
withheld and the scope is named as the reason.

### Checking that the agent did the work

The work order tells an agent to fix exactly these findings and refactor nothing
else. These flags check that the diff obeyed it — they read its _shape_, not its
correctness:

```bash
maintainability-agent \
  --config maintainability-agent.json \
  --conformance main...HEAD \
  --fail-on-out-of-scope \
  --fail-on-regression \
  --attestation-output maintainability-attestation.md
```

- **`--conformance <revspec>`** compares the diff against the paths the report
  named, and answers two questions separately: did it **stay in scope**, and did
  it **silence nothing**. They stay separate because a change can obey the work
  order and still add a `# noqa` to a finding inside it. A test added for a fix
  stays in scope even though the work order never named the test file.
- **`--fail-on-out-of-scope`** turns that into a CI failure.
- **`--fail-on-regression`** ratchets the _dimension_ scores against scan
  history, catching a change that improves one dimension while silently
  regressing another. It has three outcomes, not two — held, regressed, and
  **not comparable**, because two scans taken under different calibration cannot
  be differenced.
- **`--attestation-output`** writes the three into one per-change record: what
  was measured, what the agent was told to change, whether it stayed inside the
  work order, and what moved. It is reproducible and **not signed** — nothing
  here holds a key, and the document says so in its own text. A check nobody ran
  renders as _not asked_, never as passed.
- **`--transformation NAME`** names the class of work a scan followed and
  reports how this run of it compares with earlier ones. **A report, never a
  gate.** It says one run "moved further" than another, never that it was
  _better_ — two runs of one codemod land on different code — and it measures
  the interval, not the transformation.

The [roadmap](docs/roadmap.md#the-remediation-hole-closed-in-210-through-230)
has the history of why this was the hole under the product's central claim.

## What it analyzes

The deterministic scanner reads code from your repo (no LLM calls) and produces
signals on:

- largest files (configurable warn/fail thresholds)
- function size and complexity — exact ranges for Python via `ast`,
  brace-bounded for JS/TS/JSX/TSX/HTML — plus **cognitive complexity**
  (nesting-weighted reading cost)
- class size, against its own budget (`max_class_lines`)
- duplicate blocks, and **near-duplicate declarations** compared structurally so
  renaming can't hide a copy, each paired with the original to reuse
- unreferenced private declarations (debris nothing can reach)
- competing libraries for one concern (two HTTP clients, two validators)
- configurable risk patterns (`eval(`, `exec(`, TODO/FIXME, custom regex)
- expected files / commands / clean-worktree (opt-in hard gates)
- **TypeScript semantic facts** from a recorded analysis or an
  already-installed `tsc`, including workspace projects (ADR 003)
- **test effectiveness** from an opted-in suite run and parsed coverage
  (Class 5, default off — the one place the agent may execute the tree)
- an ISO/IEC 25010-inspired 0–5 estimate per category, and a verified grade —
  or a disclosed withholding when the evidence is thin.

The analyzer is intentionally conservative and under-reports rather than
over-reports: an unrecognized declaration costs one missed finding, never a
cascade of false ones. Pair it with native tools (ESLint, Ruff, Radon, Semgrep,
SonarQube, Qlty) rather than replacing them — their SARIF folds in via
`--sarif-input`. Accuracy and limits: [docs/language-support.md](docs/language-support.md).

## Language support

**Be clear-eyed: the tool does not support every language equally, and on an
unrecognized language it under-reports rather than fails.** Coverage has two layers.

Ten languages are parsed as of **2.7.0**: Python (1.0), Java (1.0), C (1.1),
C++ (1.2), C# (1.3), Fortran (free-form 1.4, fixed-form 1.6), Swift (2.4),
COBOL (2.7), the JS/TS family, and HTML. Each has a scanner written for it and a
documented list of what it misses — a language is claimed only when both exist.

**Built-in scanner (always on, no dependencies)** — reads function/class
declarations, sizes and complexity for a fixed set of languages, and **only**
these:

| Language | How it's measured | Fidelity |
|---|---|---|
| Python (`.py`) | `ast` — exact `end_lineno` | Exact |
| Java (`.java`) | dedicated brace-bounded scanner | Bounded; under-reports some constructs |
| C (`.c`, `.h`) | dedicated brace-bounded scanner — functions, `struct`/`enum`/`union` | Bounded; prototypes and macros are not declarations |
| C++ (`.cpp`, `.hpp`, `.cc`, `.cxx`, `.hh`) | dedicated brace-bounded scanner — functions, class members, namespaces, templates | Bounded; bodyless declarations are not definitions |
| C# (`.cs`) | dedicated brace-bounded scanner — methods, constructors, `class`/`interface`/`struct`/`record`/`enum` | Bounded; properties are not declarations |
| Swift (`.swift`) | dedicated brace-bounded scanner — functions, initialisers, subscripts, `class`/`struct`/`enum`/`protocol`/`actor` | Bounded; extension members carry their type, protocol requirements and computed properties are not declarations |
| COBOL (`.cbl`, `.cob`, `.cpy`, and `.CBL`/`.COB`/`.CPY`) | dedicated scanner — PROCEDURE DIVISION paragraphs, bounded by the start of whatever follows; fixed-form card columns read where the layout carries them | Bounded by the next header; level numbers and container programs/sections are not declarations |
| Fortran, free-form (`.f90`, `.f95`, `.f03`, `.f08`, `.F90`, `.F95`, `.F03`, `.F08`, `.pf`) | dedicated **keyword**-bounded scanner — modules, subroutines, functions, derived types | Bounded by `end`; measured with Fortran's own branch and nesting reading |
| Fortran, fixed-form (`.f`, `.for`, `.ftn`, `.F`, `.FOR`, `.FTN`) | the same scanner over card-column source; continuations joined, labelled `DO` loops understood | Bounded by `end` or by the loop's label |
| JS / TS / JSX / TSX (`.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`) | brace/paren depth over a masked copy | Bounded by the declaration's own braces |
| HTML (`.html`) | same brace scanner (inline `<script>`) | Bounded |
| TypeScript (semantic) | a recorded analysis or a locally-installed `tsc`, workspace projects included | Type-level facts; `unknown` when no checker is present |

Any language **not** in that table — Go, Rust, Ruby, PHP, Kotlin, and the rest —
is **not parsed for declarations by the built-in scanner.** Its files still count
toward repo size, but the built-ins produce no function-size, complexity,
duplication or dead-code findings for them, and the estimate leans on whatever
evidence *is* available (which is why the report discloses its evidence tier and
can withhold the grade).

**Which analyzer covers which language** (the opt-in pool, when installed):

| Language | Built-in scanner | External analyzer |
|---|---|---|
| Python | `ast`, exact | ruff, radon, mypy, vulture, complexipy, interrogate, pydocstyle, pylint, cohesion |
| Java | dedicated scanner | lizard, PMD, Checkstyle, SpotBugs |
| C / C++ / C# | dedicated scanners | lizard, multimetric |
| **Fortran** (free- and fixed-form) | dedicated scanner | **fortitude** — 100+ rules; **lizard** — complexity, NLOC, params |
| **COBOL** | dedicated scanner | **none** — no offline analyzer in the catalog reads it |
| JS / TS / JSX / TSX | brace scanner | ESLint, lizard, jscpd |

Fortran reached parity in 1.6.0: lizard had read it for years behind a
stale catalog row, so it came out `not-applicable` and never ran. A lint fails
the build if a parsed language has no analyzer measuring complexity — **COBOL is
the one disclosed exemption**, because the tooling that reads it is licensed and
host-resident, so its external tier is empty and the report says so.

**External analyzer adapters (opt-in pool)** — this is how coverage extends
beyond the built-in set. When you enable the analyzer pool, the tool shells out
to mature analyzers and folds their output in through per-tool
[adapters](docs/adapters.md): **lizard** (cyclomatic complexity across ~a dozen
languages), **jscpd** (cross-language duplication), **ESLint** (JS/TS),
**PMD** / **SpotBugs** (JVM), and others in the catalog. These run only when
selected *and* installed (acquisition is opt-in and off by default), and where
they measured a full concept set they become the *primary* evidence, with the
built-ins as the fallback.

So: **first-class today is Python** (and TypeScript for semantics); every other
parsed language is bounded-but-real; anything outside the table is only as
covered as the analyzer you point at it, and with none it is under-reported by
design. Per-language accuracy and limits:
[docs/language-support.md](docs/language-support.md); the adapter catalog:
[docs/adapters.md](docs/adapters.md).

## What it produces

Any combination of: `maintainability-report.md` (or a single-file HTML report),
`maintainability-remediation-prompt.md` (the bounded prompt),
`maintainability-pr-comment.md`, `maintainability.sarif` (2.1.0, for GitHub
Code Scanning), `maintainability-baseline.json` (for `--fail-on-new`
incremental adoption), and per-tool agent instruction files
(`AGENTS.md`, `CLAUDE.md`, Cursor/Copilot/Windsurf rules) via
`--init-agent-standards`.

**The report is the complete work order.** The HTML and Markdown reports carry
the whole backlog — every finding with a self-contained, deterministic
copy-paste prompt telling the agent to fix only the listed items, keep the
patch small, preserve architecture and behavior, add tests where behavior
changes, and report false positives instead of rewriting blindly. Chat and CLI
render a bounded view — a summary plus the top items and a pointer to the
report — so a payload cap can never truncate the prompt.

## Scoring standard

Based on ISO/IEC 25010 maintainability — modularity, reusability,
analyzability, modifiability, testability. Scores are **rates calibrated
against real code**, not counts: every pressure is normalized against the
median a pinned 112-repo corpus of mature projects actually carries —
eight of the ten parsed languages (django, angular, spring-framework,
ghidra, LAPACK, …); Swift and COBOL are parsed but unanchored. How that corpus was selected, what each language actually
reads, and what the numbers do *not* establish:
[the calibration study](docs/calibration-2.0-study.md), so `2.5x` means
"two and a half times what well-maintained real code shows." The corpus median
earns a **B**; **A+ is gated**, requiring every dimension clean.

The corpus is **selected by query, not taste** — `stars:>3000
created:<2021-01-01 pushed:>2026-01-01` across Python, TypeScript and
JavaScript, then filtered to repositories that contain code. The calibration is
reproducible, not asserted: `python3 tools/calibration/measure.py --check`
re-measures and fails on drift, and `tests/test_calibration_corpus.py`
re-derives the constants offline from checked-in measurements. See
[docs/standard.md](docs/standard.md).

## Self-audit

This repo eats its own dogfood — the tool runs against this codebase in CI, and
a report is checked in at [docs/self-audit.md](docs/self-audit.md), **stamped
with the exact source commit it was generated against** (a provenance record,
not a claim about HEAD). These figures mirror that stamped report row for row:

| Metric | Value |
|---|---:|
| Maintainability estimate | 4.1 / 5 |
| Verified grade | B |
| Files scanned | 391 |
| File warnings | 120 |
| File failures | 0 |
| Function warnings | 65 |
| Function failures | 0 |
| Duplicate blocks | 0 |
| Risk findings | 0 |
| Hard gate failures | 0 |

Yes, a **B** — demoted from the A band because warning rates exceed the
A-grade ceilings, against thresholds this repo sets stricter than the shipped
defaults. The grade is gated (A+ needs every dimension clean; a
repo with production code and zero test files cannot earn an A-grade) and banded
from the evidence floor, so withholding evidence never buys a better letter.
Every threshold gate — file, function, duplication — is opted **on** for this
repo's own CI, so drifting below the bar fails the build rather than the README.
(CI note: `actions/checkout` defaults to `fetch-depth: 1`, which hides history
and costs roughly a grade — use `fetch-depth: 0`.)

## Platform support

**POSIX. Windows is not claimed, for a measured reason.** A `windows-latest` probe
found most failures in two POSIX-only calls, `os.fchmod` and `os.O_DIRECTORY`. The
bounded, symlink-refusing write works through a *file descriptor*, so a validated
path cannot be swapped for a symlink before the write lands — Windows has no
equivalent and the portable rewrite is the hole. **An unsupported platform never
buys green by weakening the supported ones.**

## Invokable skill / slash command

This repo ships a portable skill under
[`skills/maintainability-agent/`](skills/maintainability-agent/) so
`/maintainability-agent` is one keystroke away. Keep the installed copy in sync
— a drifted skill teaches agents a dead workflow:

```bash
maintainability-agent --install-skill        # writes ~/.claude/skills
```

Re-run after every upgrade; a differing installed copy is refused with the
list of differences (`--force-skill` to overwrite).

| Host | Install destination | Invocation |
|---|---|---|
| Codex / OpenAI | via `skills/maintainability-agent/agents/openai.yaml` | per Codex's skills convention |
| Claude Code | `skills/maintainability-agent/` → `~/.claude/skills/maintainability-agent/` (or repo `.claude/skills/`) | `/maintainability-agent` |
| GitHub Copilot (VS Code) | `skills/maintainability-agent/copilot/maintainability-agent.prompt.md` → `<repo>/.github/prompts/` | `/maintainability-agent` in Copilot Chat |

For always-on guidance instead of an invokable skill, use
`--init-agent-standards` (see [docs/ide-agent-integration.md](docs/ide-agent-integration.md)).

## GitHub Action

This repo ships `action.yml`, usable as a composite action:

```yaml
- uses: marshallguillory86/maintainability-agent@v1.0.0
  with:
    config: maintainability-agent.json
    changed-only: main...HEAD
    fail-on-gate: "true"
```

Or copy `.github/workflows/maintainability.yml` into the target repo. For repos
not on GitHub Actions, `examples/local-ci.sh` enforces coverage and writes
`coverage.xml`.

## Documentation

Start with [the documentation index](docs/README.md), which states each
document's genre and what it is allowed to assert.

**Governing** — [Product intent](docs/product-intent.md) (authoritative:
promises, and what it must never claim) · [Architecture](docs/architecture.md)
(layers, enforced invariants, known debt) · [Philosophy](docs/philosophy.md)
(why AI-specific: volume, not pathology) · [Decision register](docs/decisions.md)
including [ADR 001](docs/adr-001-evidence-and-verification.md) (evidence and
verification).

**Reference** — [Maintainability standard](docs/standard.md) ·
[Studies and measured results](docs/studies.md) ·
[Report contract](docs/report-contract.md) · [CLI reference](docs/cli.md) ·
[Config schema](docs/config-schema.md) ·
[Language support](docs/language-support.md) ·
[Analyzer adapters](docs/adapters.md) ·
[IDE and agent integration](docs/ide-agent-integration.md) ·
[Chat workflow help](docs/help/README.md) ·
[PR and baseline workflows](docs/pr-and-baseline-workflows.md) ·
[Roadmap](docs/roadmap.md) · [Changelog](CHANGELOG.md).

## Running tests

```bash
PYTHONPATH=src python3 -m pytest
```

The full local verification that matches CI — ruff, pip-audit, the 92% coverage
gate, and the self-audit — is in
[CONTRIBUTING.md](CONTRIBUTING.md#local-verification).

## Get in touch

- **Bugs / features / questions** — open a [GitHub Issue](https://github.com/marshallguillory86/maintainability-agent/issues/new).
- **Discussion** — the [Discussions tab](https://github.com/marshallguillory86/maintainability-agent/discussions).
- **Security** — see [`SECURITY.md`](SECURITY.md) and the [private advisory flow](https://github.com/marshallguillory86/maintainability-agent/security/advisories/new). Do **not** post vulnerabilities in public issues.

## Support this work

This is a single-maintainer, MIT-licensed project — free to use, and built on a
lot of unpaid hours. If it saves you or your team time, please consider
sponsoring its continued development:

**❤️ [Sponsor on GitHub](https://github.com/sponsors/marshallguillory86)**

Sponsorship is optional and never gates a feature, a fix, or support — the whole
tool stays free and open. It just helps keep the work going.

## Acknowledgements

- **Miles Parker** — identified the friction-signal gap: that the "this keeps
  fighting me" signal a maintainer accumulates over months is exactly the
  evidence an LLM cannot hold across sessions, and that a tool positioned
  between the two should carry it. A contribution of insight rather than code,
  and it changed what this project is for.

## License

MIT

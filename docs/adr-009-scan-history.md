# ADR 009: Scan history — maintainability is a trend, not a snapshot

- Status: Accepted. Implementation progress is tracked in the [decision register](decisions.md), which is the single place it is stated
- Date: 2026-08-12
- Scope: Persistence, finding identity, the report, trend analysis, determinism
- Related: [ADR 005](adr-005-insufficient-population.md), [ADR 006](adr-006-analyzer-evidence.md), [ADR 008](adr-008-translation-and-decision.md)

## Context

Every decision recorded so far — the analyzer pool, the band matrix, the pillar view, the work order — describes **one scan**. That is a framing error, and it omits the thing practitioners actually use to judge a codebase.

Nobody forms an opinion about maintainability from a single reading. The judgment is *"this is getting worse"*, *"they keep patching around that module"*, *"complexity has been climbing since the rewrite"*. Those are statements about change over time, and they are usually better evidence than any snapshot, because a codebase at 3.8 and improving is in a completely different position from a codebase at 3.8 and sliding.

### What exists today

**Git history is analyzed, but only for the current scan.** `history.py` measures churn hotspots, change coupling, multi-commit files and single-author files over a configured window. That is history *of the code*, computed fresh each run and never retained.

**The baseline is not a history.** The original baseline held a flat list of
fingerprint strings. Baseline v3 now also stores one source commit and
structured identities, but still no timestamp series, scores, populations, or
tool coverage. It exists to suppress known findings for `--fail-on-new`, and it
is overwritten rather than appended.

So nothing anywhere records *what this repository scored last month*.

### A prerequisite defect: labels alone cannot resolve identity

The first implementation embedded the start line. The ordinal label that
replaced it — `function:{path}:{name}#{ordinal}` — fixed unrelated line shifts,
but a label alone still changes after `git mv` or after same-named declarations
are reordered. Either operation made an untouched finding look simultaneously
fixed and new.

```text
before: function:old.py:huge#0
after : function:new.py:huge#0

looks NEW to --fail-on-new: function:new.py:huge#0
looks FIXED:                function:old.py:huge#0
```

The function was not edited. One line was inserted above it.

Two consequences. `--fail-on-new` — a shipped flag — raises false failures on pre-existing findings after any refactor that shifts lines. And **recurrence tracking is impossible**: a finding that returns after remediation cannot be distinguished from a new one, which means the friction signal in [ADR 008](adr-008-translation-and-decision.md) cannot be built on this scheme.

Stable identity is therefore not a nice-to-have for this record; it is the precondition.

## Decision

### 1. Labels stay line-independent; matching becomes structural

A declaration's human label remains `function:{path}:{name}#{ordinal}`. Line
numbers stay in the report but never enter that label. The matching contract is
a structured identity record: `kind`, `path`, `name`, `ordinal`, `body_digest`,
and `fingerprint`. Declaration digests are computed during scanning from a
dedented body; `_identity` consumes the report and never reopens the audited
tree.

A later finding first matches the recorded path, name and ordinal. That keeps a
still-failing body edit attached to the finding already known. If same-named
siblings move, path + name + `body_digest` supplies the second match. The digest
is stable under indentation-only movement. It never overrides a declaration
name change.

For a path change, `_finding_match.rename_map` accepts only rename evidence from
git between the recorded and current commits. A real `git mv` follows the old
finding; a copied file does not. File, declaration, risk and duplicate findings
use this same matching relation. Fingerprint strings remain readable labels,
not the gate's comparison algorithm.

### 2. Scans are appended to a durable history

An append-only record per scan, default `.maintainability/history.jsonl`, path configurable. One line per scan, holding what a later run needs to compare honestly:

- timestamp, commit SHA, branch, and the scan **scope** (whole repository, changed-only, subset)
- the **rubric version** and the **analyzer coverage**: tools run, tools unavailable, versions, depth and license policy
- populations, counts, and band distributions — not just the rolled-up score
- aspect, category and pillar values; practice level; evidence status
- the set of stable finding fingerprints

The score alone would be useless for diagnosis. Retaining populations and band distributions is what lets a later run answer *why* something moved.

**What schema 1 actually stored** (progress in the [register](decisions.md)): timestamp, commit, branch, scope, rubric/calibration/threshold digest, contributing analyzers, estimate, range, four population counts, fingerprints, targeted findings. That is enough for rollup trajectory, velocity, growth-versus-quality, and recurrence. It is **not** enough for patterns *in the scoring* (category, aspect, pillar over time). Schema 1 is thinner than this section required.

**Schema 2** added the missing breakdown: `categories`, `aspects`, `pillars`,
`practice_level`, `evidence_status`. Those series remain separate, as ADR 007
requires.

**Schema 3** adds `identities`, the structured records used by recurrence, next
to `fingerprints`, the human labels used by charts and targeted work. Readers
still accept schema 1 and 2. Because old lines have no digest or rename inputs,
matching between two old records honestly remains string equality. No old data
is silently upgraded.

**Append policy (1.0):** if `.maintainability/history.jsonl` exists, a run appends even without `--record-history`. The first interactive run creates the file. CI already records (6.4). A forgotten flag must not drop the current scan from the series.

**Committing it is the user's choice**, and both are legitimate: checked in, history is shared and reviewable in PRs but adds churn; ignored, it is per-machine and CI needs a cache. The default is checked in, because a history only one laptop can see is a history nobody uses.

### 3. Trends are measurements of the past, never forecasts

With a history the deterministic engine can compute, as arithmetic over stored records:

- **Debt velocity** — findings introduced versus cleared per period. A repository clearing more than it adds is improving regardless of its absolute score.
- **Score trajectory** — direction and rate, with the interval, so noise is not read as movement.
- **Growth versus quality** — is the finding rate rising faster than the population? This distinguishes "getting bigger" from "getting worse", which a snapshot cannot.
- **Recurrence** — findings cleared and returned, with a count and the commits involved. This is the friction signal a language model structurally lacks.
- **Stability** — which units keep changing without their findings ever clearing.

Every one of these is a statement about scans that happened. **Extrapolating forward is a prediction and remains forbidden** under [what the product must never claim](product-intent.md#what-it-must-never-claim) until an outcome study earns it. "Complexity rose 18% over six months" is a fact; "will keep rising" is not, and the report must not blur them.

### 3b. Remediation outcomes are recorded, not just finding recurrence

Recurrence alone is a weak signal. Code churns for many reasons, so "this finding came back" says only that the file changed twice.

The tool has a stronger signal available and should use it: **it generates the remediation prompt, so it knows which findings that prompt targeted.** Recording the targeted set, then checking on the next run whether those specific findings cleared, closes a loop nothing else in the design closes — *did the advice work?*

Three outcomes, each meaning something different:

- **cleared and stayed cleared** — the advice worked; nothing more to say.
- **never cleared** — the advice was ignored, or was not actionable. Repeated across findings of one kind, it indicts the prompt rather than the developer.
- **cleared, then returned** — the strongest signal in the system. Someone was told exactly what to change, changed it, and the problem came back. That is evidence the finding is a symptom and the advice addressed the symptom, which is precisely the case that should escalate to a design-review candidate rather than being re-issued as the same nit a third time.

This is what separates the tool from a linter with a database. A linter can tell you a rule fired again. Only something that remembers what it *advised* can tell you its own advice is not working — and a model, which has no accumulated friction signal, cannot hold that across sessions no matter how much context it is given.

Requires the prompt to record its targeted finding identities alongside the scan record. Cheap once identity is stable, which it now is.

### 4. Comparability is checked, never assumed

Two scans are comparable only when the rubric version, analyzer coverage and scope match. A trend computed across a coverage change measures the tooling, not the code — precisely the error [ADR 006](adr-006-analyzer-evidence.md) exists to prevent, arriving through the time dimension.

Where records differ, the report says so and either segments the series at that boundary or withholds the trend with a reason. A silently spliced series is worse than none.

### 5. History can be backfilled

A first run need not be blind. Past commits can be scanned by materializing them in a git worktree and recording each result, producing a real series on day one. It is expensive, so it is explicit — a separate command with a commit range or sampling interval, never implicit in a normal run.

## Options considered

**A. Keep the single-scan framing; rely on git history analysis.** Rejected. Churn tells you what changed, never what it *scored*. It cannot answer whether quality improved.

**B. Extend the baseline file in place.** Rejected. The baseline is a suppression list with a defined job and a schema version, consumed by `--fail-on-new`. Overloading it would couple two lifecycles: a baseline is deliberately reset when a team accepts current debt, and resetting must not erase the history.

**C. Store only scores per scan.** Rejected as too thin. A score that moved with no populations or distributions retained cannot be diagnosed, and diagnosis is the point.

**D. Append-only scan records with line-independent finding identities.** Accepted.

## Consequences

- Determinism (**P1**) needs restating: identical tree, config *and history file* produce identical output. History is an input, and the report must name the history file and record count it used.
- New persistent state means a schema and a migration path. The history format gets its own version, independent of the report schema.
- The file grows without bound. It needs a documented compaction policy — retain full recent records, thin older ones to scores and populations — and compaction must be explicit, because silently discarding records changes computed trends.
- Baseline version 3 stores its source commit and structured identity records
  beside the labels. Version 1 and 2 baselines cannot be reconstructed from
  their strings and are rejected with an instruction to regenerate.
- CI needs the history to persist across runs — a cached path or a committed file. Without it, every CI run is the first run.
- The work order gains recurrence data, which is what turns a repeated nit into a design-review candidate.

## Invariants

1. A declaration finding's identity is unchanged by non-declaration edits above it.
2. `--fail-on-new` reports as new only findings the structured matcher cannot
   resolve against baseline version 3, including git rename evidence.
3. Every scan appends exactly one record; no run rewrites or reorders earlier records.
4. Each record states the rubric version, analyzer coverage and scope that produced it.
5. No trend is computed across records whose rubric version, coverage or scope differ; such a series is segmented or withheld with a stated reason.
6. Every trend statement describes scans that occurred. No output extrapolates beyond the last recorded scan.
7. Identical tree, config and history produce identical output, and the report names the history it consumed.
8. Compaction never occurs as a side effect of a normal scan.
9. Every remediation prompt records the finding identities it targeted, and a later run reports whether each cleared, never cleared, or cleared and returned.
10. A finding that returns after a recorded remediation attempt escalates out of the nit class; a finding that returns after unrelated churn does not.
11. A schema-3 record includes the category, aspect, pillar and practice-level
    values plus structured finding identities. Schema-1 and schema-2 records
    remain readable; missing fields stay missing. Pillar and practice series
    are never combined into one number.
12. When the history file exists, a successful scan appends exactly one new line whether or not `--record-history` was passed.

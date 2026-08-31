# Migrating from 0.7 to 1.0

**Genre: reference.** What changes the number after 0.7.0, what does not, and what you can ignore.

1.0 is not tagged yet. These breaks are already on `main` after **0.7.0**. Coming from 0.6? Do [0.7 first](migration-0.7.md). This page does not repeat that migration.

Two things change a score that 0.7 already produced. The report schema does not
break again; the finding baseline does, because rename-aware identity needs data
the old string list did not store.

The short version:

```bash
# 1. Same command. Scores can move even with no --analyzers, because the scale moved.
maintainability-agent --root . --config maintainability-agent.json

# 2. If you pass --analyzers, the point estimate now uses those readings
#    where the full concept set was measured. 0.7 only widened the range.

# 3. Do not compare a 0.7 number to a current number as if they were
#    the same measurement. The constant and the mix both changed.
```

---

## What breaks

### 1. `--analyzers` moves the point estimate

In 0.7.0, external analyzers reported coverage and findings. They widened `maintainability_range` and left the point estimate on the built-in detectors.

After 3.5, `scoring._primary_pressures` takes the analyzer reading for every dimension measured on the full concept set (cyclomatic + declaration lines + cognitive). A partial set is unmeasured, so that dimension stays on the built-in fallback. The range widens to contain both sources. They are never averaged.

The report names the mix: `score.analyzer_scored_dimensions` lists what the analyzers set. Empty means the number came from the fallback tier. The Markdown measurements section and the remediation prompt say the same thing.

A consumer that assumed `--analyzers` was display-only will now see the estimate move. That is the feature, not a regression.

JS/TS trees typically cannot compose the three-criterion set (lizard has no cognitive partner in the default pool), so they stay on the built-in fallback even with `--analyzers`. Python trees that have lizard + complexipy typically do move.

### 2. The scale moved

`CALIBRATION_C` **2.6279 → 2.2658** (2026-08-14), then **2.2658 → 5.8843** (2026-08-31). The declarations reference **0.0599 → 0.0860 → 0.1005**, and the duplication reference **3.8644 → 0.28**. The 08-14 fit followed the analyzer-primary mix after generated and vendored code left the scored population. The 08-31 re-fit followed a corpus re-measure: the stored corpus had gone stale, and plan-81dc6870 Class 4 (one clone group per clone, not one finding per overlapping window) dropped the built-in duplication reading roughly fourteenfold, so every report had been scoring duplication against a reference ~14x too high. All 40 pinned repos were re-measured `--with-analyzers`; the corpus median still rolls up to 4.0 (a well-run codebase earns a B). Old and new values are in `_calibration.py`.

A zero-install run (no `--analyzers`) still uses this constant. The same tree can score differently than it did on 0.7.0 with no other change.

### 3. Java can receive a score

0.7.0 could open `.java` for length, duplication and risk, and still measure zero declarations. A zero-install range detector now finds methods, constructors and types. A Java repository that was withheld on the population floor can now get a number. Go, Rust, C, C++, C# and Fortran still have no built-in declaration population.

---

## What does not break

| Artifact | Status |
|---|---|
| Report `schema_version` | Still **3**. The estimate and range were already nullable in 0.7. `analyzer_scored_dimensions` is an additive optional field and did not bump the version. |
| Baseline format | **Version 3.** The visible label stays `function:{path}:{name}#{ordinal}`, while each entry also stores kind, path, name, ordinal, `body_digest`, and fingerprint plus the source commit. Regenerate older baselines with `--write-baseline`; their strings cannot recover those fields. |
| `--fail-on-gate` | Still reads hard findings only. A moved estimate does not change the exit code. |
| Config file | No new required keys. `analyzers.prompt_when_interactive` controls the shipped first-run TTY prompt and remains optional. |

`normalize_report_evidence` accepts version 3 only, same as 0.7.

The optional MCP add-on now exposes tools, resources and a bounded prompt. Start
it with `maintainability-agent mcp`; the existing `maintainability-agent-mcp`
console script remains available for IDE configurations. This is additive, not
a report-schema or baseline break.

The first run asks the **same** setup questions on a CLI TTY as on
chat/MCP ([first run](help/first-run.md)) when no config exists, then
writes the answers to `maintainability-agent.json`. Non-TTY and
already-configured runs do not ask. Analyzer runs also publish an
environment work order for selected tools that were unavailable; the agent
does not install them.

---

## What you can ignore

- **Re-reading 0.6 fields.** They still mean what 0.7 said they mean.
- **Keeping a 0.7 baseline.** Baseline v3 is required for rename-aware matching.
  Regenerate it with `--write-baseline`; versions 1 and 2 fail closed with that
  instruction instead of treating every old finding as new.

---

## Coming from 0.6

[Migrating to 0.7](migration-0.7.md) is the document: regenerate the baseline, handle a nullable estimate, schema 3. Then this page.

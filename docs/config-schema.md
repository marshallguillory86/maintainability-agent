# Configuration Schema

The config file is JSON, conventionally named `maintainability-agent.json`, and currently uses `"version": 1`.

The machine-readable schema lives at:

```text
maintainability-agent.schema.json
```

## Minimal Config

```json
{
  "version": 1
}
```

## Common Fields

- `paths.include_extensions`: file extensions to scan.
- `paths.exclude_patterns`: directories or `fnmatch` glob patterns to ignore, normalized across Unix and Windows path separators. `migrations/` is excluded by default — migrations are append-only history, so a long, branchless `upgrade()` is correct code rather than a finding.
- `thresholds`: warning/failure limits for file size, function size, complexity, and duplication.
- `thresholds.max_cognitive_complexity` / `warn_cognitive_complexity` (default 25 / 15): nesting-weighted reading cost, charged per flow break *plus the depth it sits at*. Distinct from `max_complexity`, which counts branches and is blind to nesting — five guard clauses and five levels of nesting score the same under it. Fitted against 21,300 declarations in the reference corpus, where 15 sits near the 94th percentile and 25 near the 97th. Omit both keys to disable the check.
- `thresholds.max_class_lines` / `warn_class_lines`: separate budget for classes (default 300 / 200). Classes are graded on length alone: they are containers, so the per-function line budget is the wrong yardstick, and a class's measured complexity is the sum of branches already charged to its own methods.
- `idiom_groups`: concern name → list of competing package names, e.g. `{"logging": ["loguru", "structlog"]}`. Setting this **replaces** the shipped list, which covers only well-known, slow-moving alternatives (HTTP clients, date handling, client state, schema validation, ORMs, web frameworks) and is incomplete by construction.
- `hard_gates`: rules that can fail CI.
- `expected_files`: files required by the repo.
- `expected_commands`: documented native commands such as test and lint.
- `risk_patterns`: regex checks for project-specific risk language or unsafe patterns.
- `instruction_pack`: context used when generating AI agent standards.

## Analyzer policy (`analyzers`)

Controls which external analysis tools may run. Full background, including the tool inventory and what each class means, is in [the analyzer pool](analyzer-pool.md).

```json
"analyzers": {
  "depth": "moderate",
  "license_policy": "permissive",
  "prompt_when_interactive": true,
  "allow_tools": [],
  "deny_tools": [],
  "deny_license_classes": [],
  "deny_concerns": ["security"],
  "timeout_seconds": 120
}
```

- `depth`: `baseline` | `moderate` | `heavy` | `all`. Cumulative — `heavy` includes everything in `baseline` and `moderate`. Larger pools take longer and produce better-supported scores.
- `license_policy`: `permissive` | `copyleft-weak` | `copyleft-any` | `commercial-free-tier` | `unverified`. Also cumulative. Defaults to `permissive`, the setting fewest organizations have to argue about.
- `acquire_tools`: whether a missing Node tool may be fetched (`npx --yes`) during a run. **Default `false`** — acquisition is a network action, and the P1 separation of analysis from acquisition only means something when acquisition is chosen rather than defaulted. Off, a missing tool is reported `not-installed` with its install command in the environment work order.
- `prompt_when_interactive`: whether a first run at a terminal may ask for depth and license policy when no config exists (release-plan 6.1, shipped). The prompt fires only on a TTY with no discovered or `--config` file, writes the answers to `maintainability-agent.json` at the repository root, and never fires in CI — a non-TTY run neither asks nor writes. Set `false` to keep even a terminal run silent. Depth and policy otherwise come from this file, or from `--depth` / `--license-policy` on `tools/resolve_pool.py` (not the audit CLI).
- `allow_tools`: tool slugs admitted even when the policy tiers would exclude them — for a commercial analyzer you hold a license for, say.
- `deny_tools`: tool slugs never run, whatever else permits them.
- `deny_license_classes`: whole classes never run, e.g. `["strong-copyleft"]`.
- `deny_concerns`: concern tags never run. `security` is denied by default; that work belongs to `secure-code-agent` and duplicating it here would produce two tools disagreeing about the same repository.
- `timeout_seconds`: per-tool wall clock. A tool that exceeds it is recorded as unavailable-timeout, never as a clean result.

**Precedence is fixed and not configurable:** every deny wins, including over `allow_tools`. An organization's prohibition must not be overridable by a per-repository opt-in. Within what remains, `allow_tools` admits, then the depth and license tiers decide.

Slugs come from [`data/analyzer-catalog.json`](../data/analyzer-catalog.json). To see exactly what a configuration selects, and why everything else was left out:

```bash
python tools/resolve_pool.py                    # resolve the current config
python tools/resolve_pool.py --explain pylint   # why is one tool in or out?
python tools/resolve_pool.py --depth all        # what-if, without editing the file
```

A slug that is not in the catalog is a config error, not a silent no-op.

## Economic context

ADR 004 v1. Optional. The audit CLI reads these keys
(`tests/test_economic_context.py`).

Optional. Absent, the report is a normal maintainability report: no $
block, work order stays in risk×effort order. Present, it never changes
the 0–5 score or `verified_grade`.

```json
"economic_context": {
  "version": 1,
  "currency": "USD",
  "planning_horizon_months": 12,
  "loaded_engineering_cost_per_hour": { "low": 90, "base": 140, "high": 210 }
}
```

- `loaded_engineering_cost_per_hour`: **required for any $ scenario**.
  Low / base / high loaded blended rate. One number is not enough; the
  range is the honesty.
- `currency`: display label only (default `USD`). No network conversion.
- `planning_horizon_months`: default `12` when omitted.
- Optional later keys (not required for the $ block): `reliability_tier`
  (`internal` | `customer` | `regulated`), `typical_review_minutes_per_change`,
  `representative_incident_cost`.

When the labor range is missing and stdin is a TTY, a first interactive
run may ask and write this block into `maintainability-agent.json`.
Non-TTY never asks. `analyzers.prompt_when_interactive: false` suppresses
the ask. Environment overrides for one run, not persisted unless the ask
writes the file: `MAINTAINABILITY_LABOR_LOW`, `MAINTAINABILITY_LABOR_BASE`,
`MAINTAINABILITY_LABOR_HIGH`, `MAINTAINABILITY_CURRENCY`,
`MAINTAINABILITY_HORIZON_MONTHS`.

This section is the shipped v1 contract.

## Validation

Any JSON Schema validator that supports draft 2020-12 can validate the config.

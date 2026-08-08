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

## Validation

Any JSON Schema validator that supports draft 2020-12 can validate the config.

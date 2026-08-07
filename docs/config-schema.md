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
- `thresholds.max_class_lines` / `warn_class_lines`: separate budget for classes (default 300 / 200). Classes are graded on length alone: they are containers, so the per-function line budget is the wrong yardstick, and a class's measured complexity is the sum of branches already charged to its own methods.
- `hard_gates`: rules that can fail CI.
- `expected_files`: files required by the repo.
- `expected_commands`: documented native commands such as test and lint.
- `risk_patterns`: regex checks for project-specific risk language or unsafe patterns.
- `instruction_pack`: context used when generating AI agent standards.

## Validation

Any JSON Schema validator that supports draft 2020-12 can validate the config.

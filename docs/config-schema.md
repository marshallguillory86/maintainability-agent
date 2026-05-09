# Configuration Schema

The config file is JSON and currently uses `"version": 1`.

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
- `paths.exclude_patterns`: directories or glob patterns to ignore.
- `thresholds`: warning/failure limits for file size, function size, complexity, and duplication.
- `hard_gates`: rules that can fail CI.
- `expected_files`: files required by the repo.
- `expected_commands`: documented native commands such as test and lint.
- `risk_patterns`: regex checks for project-specific risk language or unsafe patterns.
- `instruction_pack`: context used when generating AI agent standards.

## Validation

Any JSON Schema validator that supports draft 2020-12 can validate the config.

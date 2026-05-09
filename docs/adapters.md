# Analyzer Adapters

Maintainability Agent should not replace mature analyzers. It should collect their output and turn it into reviewable reports and bounded AI remediation prompts.

## Supported Now

### SARIF Input

```bash
maintainability-agent \
  --sarif-input semgrep.sarif \
  --output maintainability-report.md
```

External SARIF findings appear in the Markdown report under `External Findings`.

### SARIF Output

```bash
maintainability-agent \
  --sarif-output maintainability.sarif
```

The SARIF file can be uploaded to GitHub code scanning.

## Planned Native Adapters

- Semgrep JSON
- ESLint JSON
- Ruff JSON
- Radon JSON
- pytest / coverage summaries
- SonarQube API export

The adapter rule is simple: ingest tool output, preserve provenance, and avoid pretending every analyzer has the same semantics.

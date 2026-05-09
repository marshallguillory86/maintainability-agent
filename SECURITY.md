# Security Policy

## Supported Versions

This project is currently in early development (`0.1.x`). Only the latest
release line receives security fixes.

| Version | Supported |
|---------|-----------|
| `0.1.x` | ✅ |
| < `0.1` | ❌ |

## Reporting a Vulnerability

If you find a security issue:

1. **Do not** open a public GitHub issue.
2. Use GitHub's [private security advisory flow](https://github.com/marshallguillory86/maintainability-agent/security/advisories/new):
   repo → **Security** → **Report a vulnerability**. This keeps the
   report private until coordinated disclosure.
3. Include:
   - a clear description of the issue
   - reproduction steps or a minimal proof-of-concept
   - the affected version (`maintainability-agent --version`)
   - your proposed severity (CVSS or informal)

You will receive an acknowledgement within 5 business days. If a fix is
warranted, expect a coordinated disclosure timeline of up to 90 days
depending on complexity.

## Scope

This project runs deterministic static analysis against a local git
repository and produces Markdown / JSON / SARIF artifacts. It does **not**
execute scanned code, send any code to LLMs, or transmit data over the
network unless the user explicitly opts in.

In-scope:

- arbitrary-write or arbitrary-read on the host filesystem outside the
  configured `--root`
- shell-injection in any `git` command or subprocess call
- prototype pollution / unsafe-deserialization in JSON / SARIF parsers
- denial-of-service via crafted config files or repository inputs
- secret leakage in generated reports

Out-of-scope:

- vulnerabilities in third-party analyzers whose output you ingest via
  `--sarif-input` (report those upstream)
- general code-quality findings — those belong in normal issues
- correctness bugs in the metrics themselves (file the issue or a PR)

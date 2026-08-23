# Security Policy

## Supported Versions

This project is in early development. Only the latest release line
receives security fixes.

| Version | Supported |
|---------|-----------|
| `0.9.x` | ✅ |
| < `0.9` | ❌ |

The line above is the shipped one, and keeping it that way is a
maintenance task nobody remembers. An audit found this table still
naming `0.1.x` eight release lines later, which read literally meant
the current release was unsupported by its own policy (D45).

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
repository and produces Markdown / JSON / SARIF artifacts. It does not
send any code to LLMs, and performs no network access during analysis
unless the user explicitly enables tool acquisition in their own
configuration.

**It does execute code from the repository under audit, and that is not
yet a settled design.** The agent invokes external analyzers, and
`eslint` in particular *requires* a project configuration and then runs
it; mypy and pylint can load configured plugins. Those children inherit
this host's environment. So a repository you audit can run code as you.

This sentence previously read that the agent does not execute scanned
code, which was untrue and audit-proven so (Codex, 2026-08-23). Whether
the answer is "repositories are trusted, say so plainly" or
"repositories are untrusted, so invoke analyzers with agent-owned
configuration and a scrubbed environment" is an open product decision,
tracked as D39 and D44 in the defect register with the reasoning in
`docs/security-queue.md`. Until it is made, this section describes what
the code does rather than what anyone would prefer it did.

Audit only repositories you would be willing to run a build from.

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

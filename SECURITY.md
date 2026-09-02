# Security Policy

## Supported Versions

Only the latest release line receives security fixes.

| Version | Supported |
|---------|-----------|
| `1.2.x` | ✅ |
| < `1.2` | ❌ |

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

**It does not execute code from the repository under audit, and
configuration counts as code.** An `eslint` flat config is a JavaScript
program, a `pylint` `init-hook=` runs arbitrary Python before analysis
begins, and a `mypy` `plugins =` imports a module out of the tree. So
eslint is refused by selection rather than run, pylint is invoked with
`--rcfile` and mypy with `--config-file`, both pointed at the null
device, and the analyzer child's environment has `PYTHONPATH`,
`PYTHONSTARTUP`, `NODE_PATH`, `NODE_OPTIONS` and the `LD_`/`DYLD_` pair
removed so nothing outside your own choice decides what it loads.

**The one exception is an explicit opt-in to run the tree's own test
command.** Setup asks — defaulting to **no** — whether to run the
repository's documented test command for a coverage reading, and only a
`yes` together with a recorded command lets the audit spawn it. This is
the sole path by which anything from the audited tree runs, it is off
until the operator turns it on per repository, and it executes exactly
the one command they named — not the tree's configuration, plugins, or
build. With no opt-in the guarantee above is unchanged and total
(Decision 9, amended 2026-08-31).

**This section has now been wrong in both directions, and both are
recorded rather than quietly rewritten.** It first said the agent does
not execute scanned code, which was untrue and audit-proven so (Codex,
2026-08-23). It was corrected to say the agent *does*, with the
question left open as D39 and D44. Marshall settled it on 2026-08-25 by
drawing the line at execution rather than at trusting repositories
(Decision 9), both entries closed, and this file kept describing the
defect for a further day — a promise that had become true while its
own documentation still denied it.

**What this is not.** Analyzers are ordinary local child processes and
this package does not sandbox them: it does not police what they open,
and it makes no claim that one cannot reach the network. The narrower
guarantee is the one made here — nothing from the audited tree chooses
what those children run. Child sandboxing is refused as a design
direction and the reasoning is in `docs/security-queue.md`.

Two isolation flags are structurally asserted everywhere and spawned
only where the binary exists, which `docs/analyzer-pool.md` discloses:
on a machine without pylint and mypy installed, they are documented and
asserted rather than demonstrated.

Audit only repositories you would be willing to run a build from. The
guarantee above is about this agent's own behaviour, not about the
analyzers you install to work with it.

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

# Defect register: the chat surface

**Genre: defect register.** Recorded 2026-08-16 after the first external
field test of the MCP server through an AI chat host. Every entry records
a defect against requirements that already exist — in
[ADR 006](adr-006-analyzer-evidence.md), [ADR 004](adr-004-economic-context.md),
[ADR 009](adr-009-scan-history.md), [product-intent.md](product-intent.md),
or the operator's stated requirements — none is a feature proposal. The
required behavior column cites the document that already requires it. D1
and D13 are retained as closed, tested history; the remaining entries stay
open until a test proves the required behavior.

## Context

The primary user surface is an AI chat host (an IDE assistant or chat
window driving the MCP server), not the terminal. At the field test,
nearly every capability the terminal path had — configuration, analyzer
execution, history, economics, format choice — was absent or silently
degraded on the chat path. The theme across all seventeen entries is one
defect class: **capability wired to the TTY, viewer shipped to the primary
surface.**

## Entries

### D1 — Closed: analyzer pool execution is config-driven at every seam

The FOSS analyzer pool now follows `analyzers.run` through
`build_report`, the CLI, the MCP `audit_repository` tool, and the MCP
report resource. `build_report` and the MCP tool accept a tri-state
decision: an omitted value follows the loaded configuration, while an
explicit true or false wins for that call. The CLI's `--analyzers` and
`--no-analyzers` flags likewise override configuration in either
direction. A configured repository therefore runs its pool without a
per-invocation flag; built-in detectors remain the fallback where the
pool cannot supply a complete scored dimension (ADR 006).

*Closing tests:* `test_build_report_resolves_the_pool_tristate_at_its_own_seam`,
`test_cli_runs_or_suppresses_the_pool_at_the_production_seam`,
`test_mcp_audit_runs_or_suppresses_the_pool_at_the_production_seam`, and
`test_mcp_report_resource_uses_the_repository_pool_decision` in
`tests/test_pool_runs_by_config.py`.

### D2 — No first-run setup on the chat path

An unconfigured repository audited over MCP is silently scanned with
hardcoded defaults. The first-run configuration ask exists only behind
a TTY check (`_first_run`), which is never true for an MCP server.

*Required:* on invocation, check configuration first (see D13 for the
locations). If none exists, this is a detectable first run: elicit the
setup choices — analyzer depth and license policy, pool execution,
economic context, report format, report location where a file format is
chosen — then write the answers so the questions are not repeated.

### D3 — Asks are free-text prompts, not structured choices

The format ask is a bare `input()` line on the CLI, and the MCP prompt
instructs the host in prose to "ask the user which presentation they
want." Hosts render that as a typed chat question. The stated
requirement is a multiple-choice question with **chat** pre-selected as
the default.

*Required:* every ask on the chat path is a structured multiple-choice
elicitation (MCP `elicitation/create`, falling back to instructing the
host's question UI) with the default option named. A host that supports
neither receives the documented defaults, never a hang.

### D4 — Documentation presents the CLI as the primary surface

README, product intent, and the MCP server description treat the CLI as
the product and the MCP server as a boundary added to it. The operating
reality is inverted: most users reach this tool through a chat host,
typically inside an IDE.

*Required:* the documentation states that chat is the primary surface
and the CLI is the automation/CI surface, and orders its instructions
accordingly.

### D5 — Scan history never accrues over MCP

`audit_repository` builds a report and returns it; it never appends a
scan record. Recurrence, escalation, and cleared-then-returned tracking
(ADR 009) therefore cannot exist for chat users — the durable-record
feature that distinguishes this tool from a linter is structurally
inert on the primary surface.

*Required:* a successful chat-path audit records its scan under the
same rules the CLI applies (an existing history always appends; a first
interactive run starts the series with consent).

### D6 — Targeted-advice outcomes cannot be recorded from chat

The `targeted` tuple — which findings a remediation prompt actually
asked somebody to fix — is recorded only when the CLI is invoked with
`--prompt-output`. The MCP path returns a remediation prompt on every
call and records nothing, so "told, fixed, returned" (the strongest
signal in the recurrence design) can never fire for chat users.

*Required:* handing a remediation prompt to a chat host records the
prompt's targets exactly as the CLI path does.

### D7 — No baseline workflow over MCP

There is no MCP path to write or consult a baseline, so `--fail-on-new`
adoption — the documented on-ramp for existing repositories — is
unavailable on the primary surface.

*Required:* the chat path can create and use a baseline under the same
identity rules (baseline v3, ADR 009) as the CLI.

### D8 — Every MCP call returns three copies of the findings

`audit_repository` always returns the full report JSON, the full
Markdown rendering, and the remediation prompt together, regardless of
the requested format. A chat host pays context for all three on every
call.

*Required:* the requested format governs the payload; the report is
returned once, in the presentation the caller asked for, with the
remediation prompt when requested.

### D9 — Missing-tool remedies never reach the chat user

The environment work order (install commands for analyzers that were
selected but not installed, ADR 006 §2c) populates only when the pool
runs. D1 no longer prevents that for configured repositories, but
nothing in the MCP result directs the host to surface the work order.

*Required:* when selected tools are missing, the chat user is shown the
tool names and the install commands the environment work order already
generates, and is told what coverage they restore.

### D10 — Unconfigured access control errors instead of asking

The MCP allow-list defaults to the server's launch directory. In an IDE
the server may be launched anywhere, so the first audit of a real
repository can fail with a path-authorization error the user has no way
to anticipate or grant interactively.

*Required:* an out-of-roots request explains the boundary and how to
grant the root; where elicitation is available, it offers the grant as
a structured question rather than failing with an error string.

### D11 — The economic context ask never fires in chat

The ADR 004 labor ask rides the same TTY gate as first-run setup, so
chat users never see it and the economic scenario block is silently
absent from their reports unless they hand-edit configuration.

*Required:* the economics ask is part of first-run setup on the chat
path (D2), declinable, with the same persistence rules as the TTY ask.

### D12 — The operator skill instructions are CLI-first

The installed skill for this tool instructs an agent to run the CLI and
write report files into the repository by default, contradicting the
standing rules that file outputs require an explicit save location and
that asks go through the question UI.

*Required:* the skill reflects the chat-primary flow: configuration
check, elicited choices, no file written without a chosen location.

### D13 — Closed: the XDG user configuration and state tier ships

Configuration now merges built-in defaults, the XDG user configuration,
and repository `maintainability-agent.json` in that order, so the later
repository tier wins. Any loaded configuration tier enables the D1 pool
default unless the winning tier explicitly sets `analyzers.run` false.
The XDG state file records repositories by absolute root, making first-run
detection persistent; corrupt or unreadable user files are treated as
absent rather than crashing an audit.

*Closing suite:* `tests/test_user_config_tier.py`.

### D14 — The configuration capability is not integrated with the chat UI

The configuration machinery exists — schema, depth tiers, license
policies, pool resolution, first-run asks, format ask — but every
entry point is a terminal prompt. The integration that connects this
machinery to the surface users actually occupy (elicitation / the
host's question UI) was never built, although the capability was
reported as complete.

*Required:* the asks named in D2, D3, D10 and D11 reach the chat user
through structured elicitation. This entry closes only when a test
drives the full first-run flow over the MCP boundary.

### D15 — Analyzer selection has no goal-directed composition

Selection is policy filtering (allow/deny, license, depth tier) plus
language applicability. The gap analysis that knows which concerns are
unmeasured for which languages runs only after the fact, for the
coverage report; it never drives selection, and nothing composes the
minimal tool set that covers this repository's languages for the
product's goal.

*Required:* selection consults the same language inventory and
concern→concept mapping the coverage section already uses, so a run
covers the repository's languages with the verified tools available,
and names — before or with the results — what to install to close the
remaining gaps. Deterministic; no scoring change.

### D16 — No help system exists for the intended surface

Help today is one `argparse --help` screen written for a terminal
reader. There are no help files that walk a chat-context user through
what the agent does, what it will ask, what the pool runs, or what the
report means — and the deepest capabilities (history, recurrence,
baselines, economics) are exactly the ones a first-time user cannot
discover.

*Required:* help files built out for the chat-skill-first flow, kept
beside the docs the lints already sweep, and reachable from the README
and the MCP server description. Scope is fixed in the fix-cycle prompt,
not invented here.

### D17 — The instructions doc teaches the wrong surface

[ide-agent-integration.md](ide-agent-integration.md) and the generated
agent-instruction packs (`--init-agent-standards`) instruct agents in
CLI-first terms: run the binary, write report files. They predate the
chat-primary statement and now teach integrators the inverted flow.

*Required:* the instructions doc and the generated packs are updated or
rebuilt to teach chat-first operation — configuration check, elicited
choices, no file written without a chosen location — with the CLI
documented as the automation path.

## Disposition

D1 and D13 are closed. D2–D12 and D14–D17 remain open in this
seventeen-entry register and are queued for the fix cycle beginning
2026-08-17. Entries close individually, each behind a test that would
fail if the defect returned.

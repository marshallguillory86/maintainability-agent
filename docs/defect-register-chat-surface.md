# Defect register: the chat surface

**Genre: defect register.** Recorded 2026-08-16 after the first external
field test of the MCP server through an AI chat host. Every entry records
a defect against requirements that already exist — in
[ADR 006](adr-006-analyzer-evidence.md), [ADR 004](adr-004-economic-context.md),
[ADR 009](adr-009-scan-history.md), [product-intent.md](product-intent.md),
or the operator's stated requirements — none is a feature proposal. The
required behavior column cites the document that already requires it. D1,
D2, D5–D8, D11 and D13 are retained as closed, tested history. D3 and D14
remain open with narrowed scope; the other entries stay open until a test
proves the required behavior.

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

### D2 — Closed: first-run setup ships on the chat path

An unconfigured repository audited over MCP now receives one structured
setup set covering analyzer depth and license policy, pool execution,
economic context and report format. Accepted answers are written to the
repository and user configuration tiers and apply to that same audit.
Declined or unsupported elicitation returns the same questions in
`setup_needed`; while both configuration tiers remain absent, later calls
ask again. Only written answers end setup elicitation.

Report save location is a separate host question at save time. The local
MCP process returns report text and never writes a report file; the host
asks where to save it when the user chooses a file presentation.

*Closing tests:* `test_setup_triggers_only_when_both_configuration_tiers_are_absent`,
`test_one_native_elicitation_applies_answers_to_that_same_audit`,
and `test_a_completed_mcp_audit_marks_seen_even_when_a_gate_fails` in
`tests/test_first_run_elicitation.py`; plus
`test_unanswered_setup_is_reelicited_until_answers_are_written` and
`test_repeated_declines_keep_returning_the_same_setup_needed_block` in
`tests/test_first_run_reelicitation.py`.

### D3 — Partially closed: setup is structured; the slash prompt is not

First-run chat setup now uses one structured MCP elicitation with disclosed
options and defaults, including **chat** as the presentation default. A
decline or host without elicitation support receives those same structured
questions in `setup_needed` and the audit proceeds on documented defaults.

*Remaining:* the `maintainability-agent` MCP slash prompt registered by
`mcp_server._bind_prompts` still tells the host in free text to ask which
presentation the user wants. Replacing that free-text ask is the only open
D3 scope.

*Shipped setup tests:* `test_setup_questions_are_structured_choices_with_disclosed_defaults`
and `test_declined_or_unsupported_elicitation_uses_defaults_and_returns_setup_needed`
in `tests/test_first_run_elicitation.py`.

### D4 — Documentation presents the CLI as the primary surface

README, product intent, and the MCP server description treat the CLI as
the product and the MCP server as a boundary added to it. The operating
reality is inverted: most users reach this tool through a chat host,
typically inside an IDE.

*Required:* the documentation states that chat is the primary surface
and the CLI is the automation/CI surface, and orders its instructions
accordingly.

### D5 — Closed: scan history accrues over MCP

`audit_repository` now follows the CLI's history rule through a tri-state
`record_history` decision. An existing history appends on every successful
audit; an elicitation-capable client starts a first series; a headless first
call writes nothing. Explicit true or false wins in either direction. The
returned report reads the resulting series into `scan_history` and computes
rename-aware `design_review_candidates` from its latest comparable segment.

*Closing tests:* `test_existing_history_appends_on_a_plain_mcp_call`,
`test_elicitation_capable_first_call_starts_the_mcp_history`,
`test_headless_first_call_does_not_create_mcp_history`,
`test_record_history_tristate_overrides_both_directions`,
`test_mcp_report_exposes_history_and_design_review_candidates`, and
`test_cli_and_mcp_reports_agree_over_the_same_history` in
`tests/test_mcp_history.py`.

### D6 — Closed: chat remediation targets are recorded

The MCP path returns a remediation prompt by default. Whenever that audit
writes a scan record, its `targeted` tuple stores exactly the delivered
prompt's `prompt_targets`, in the same identity space as the scan's findings;
if the caller suppresses the prompt, it stores no targets. Chat history can
therefore distinguish recurrence from the stronger "told, fixed, returned"
signal in ADR 009.

*Closing tests:* `test_mcp_history_records_the_delivered_prompt_targets`,
`test_mcp_records_only_advice_delivered_after_current_scan_escalates` and
`test_cli_records_only_advice_delivered_after_current_scan_escalates` in
`tests/test_mcp_history.py`.

### D7 — Closed: baseline adoption ships over MCP

`audit_repository` now accepts a repository-scoped baseline path and can write
the CLI's version-3 baseline format. The default standing location is
`.maintainability/baseline.json`. When that file or an explicit baseline is
present, `new_findings` carries the sorted fingerprints not matched by its
structured identities; git-attested renames do not become new findings.
`gate_passed` remains the hard-gate result and is not changed by baseline
membership.

*Closing tests:* `test_mcp_baseline_round_trip_survives_git_mv_and_names_only_new_findings`
and `test_mcp_baseline_defaults_inside_root_and_rejects_escape` in
`tests/test_mcp_baseline_payload.py`.

### D8 — Closed: requested format governs the MCP payload

Every result keeps the run metadata, while `format` selects one report
presentation: JSON returns the report dictionary; chat and Markdown return
Markdown; HTML returns HTML plus the Markdown chat fallback required by ADR
011. The bounded remediation prompt is included by default and can be omitted
with `include_prompt=false`; omitted advice is recorded as no targets. The
report resource reads stored history without appending and renders the same
document as the CLI over that series.

*Closing tests:* `test_requested_format_governs_the_mcp_payload`,
`test_suppressing_prompt_records_no_targeted_advice` and
`test_report_resource_matches_cli_over_stored_history_without_appending` in
`tests/test_mcp_baseline_payload.py`.

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

### D11 — Closed: economic context is part of chat setup

The ADR 004 labor question now rides the structured first-run chat setup.
It is declinable; accepting persists the same low/base/high
`loaded_engineering_cost_per_hour` shape to both configuration tiers, while
declining omits economic context from both.

*Closing tests:* `test_apply_answers_persists_economics_and_format_to_both_tiers`
and `test_declining_economics_omits_the_block_from_both_tiers` in
`tests/test_first_run_elicitation.py`.

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

### D14 — Open, narrowed: first-run integration ships

The chat integration is built: one native MCP elicitation applies analyzer,
depth, license, economics and presentation answers to that same audit and
persists them for later calls. This is driven end to end by
`test_one_native_elicitation_applies_answers_to_that_same_audit` in
`tests/test_first_run_elicitation.py`.

*Remaining:* D10's authorized-root grant ask and D3's free-text slash-prompt
presentation ask. D2 and D11 no longer contribute open D14 scope.

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

D1, D2, D5–D8, D11 and D13 are closed. D3 and D14 remain open with the
narrowed scope stated above. D4, D9, D10, D12 and D15–D17 remain open in this
seventeen-entry register. Entries close individually, each behind a test that
would fail if the defect returned.

# Defect register: the chat surface

**Genre: defect register.** Recorded 2026-08-16 after the first external
field test of the MCP server through an AI chat host. Every entry records
a defect against requirements that already exist — in
[ADR 006](adr-006-analyzer-evidence.md), [ADR 004](adr-004-economic-context.md),
[ADR 009](adr-009-scan-history.md), [product-intent.md](product-intent.md),
or the operator's stated requirements — none is a feature proposal. The
required behavior column cites the document that already requires it. D1–D17
are retained as closed, tested history.

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
setup set covering analyzer depth and license policy, pool execution, scan
history consent, economic context and report format. Accepted answers are
written to the repository and user configuration tiers and apply to that same audit.
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

### D3 — Closed: setup and the slash prompt use structured choices

First-run chat setup uses one structured MCP elicitation with disclosed
options and defaults, including **chat** as the presentation default. A
decline or host without elicitation support receives those same structured
questions in `setup_needed` and the audit proceeds on documented defaults.
The `maintainability-agent` slash prompt now tells the host to use its
structured elicitation or question UI for presentation, with chat
pre-selected, instead of prescribing a free-text ask.

*Closing tests:* `test_setup_questions_are_structured_choices_with_disclosed_defaults`
and `test_declined_or_unsupported_elicitation_uses_defaults_and_returns_setup_needed`
in `tests/test_first_run_elicitation.py`, plus
`test_slash_prompt_uses_structured_presentation_choice_with_chat_default` in
`tests/test_consent_and_grant.py`.

### D4 — Closed: documentation teaches the primary chat surface first

README, product intent, and the MCP server instructions now state the same
surface contract: an AI chat host driving local MCP is primary, while the CLI
is the automation and CI surface. README presents the chat workflow before CLI
usage instead of making the primary path an appendix.

*Closing test:* `test_readme_product_intent_and_mcp_description_name_the_surface_contract`
in `tests/test_chat_primary_docs.py`.

### D5 — Closed: scan history accrues over MCP

`audit_repository` follows the CLI's history rule through a tri-state
`record_history` decision. First-run setup asks whether to record scan history
and persists the yes-default answer to both configuration tiers. With the
parameter unset, that answer can start a series; an existing history remains a
standing answer and appends on every successful audit. Capability alone starts
nothing, an unconfigured headless first call writes nothing, and explicit true
or false wins in either direction. The returned report reads the resulting
series into `scan_history` and computes rename-aware
`design_review_candidates` from its latest comparable segment.

*Closing tests:* `test_existing_history_appends_on_a_plain_mcp_call`,
`test_elicitation_capability_alone_does_not_start_mcp_history`,
`test_headless_first_call_does_not_create_mcp_history`,
`test_record_history_tristate_overrides_both_directions`,
`test_mcp_report_exposes_history_and_design_review_candidates`, and
`test_cli_and_mcp_reports_agree_over_the_same_history` in
`tests/test_mcp_history.py`; consent is closed by
`test_setup_asks_for_history_consent_and_persists_it_to_both_tiers`,
`test_history_consent_drives_the_accepting_call`, and
`test_persisted_history_consent_precedes_the_standing_file_rule` in
`tests/test_consent_and_grant.py`.

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

### D9 — Closed: missing-tool remedies reach the chat user

When selected analyzers cannot run, every MCP format now carries a top-level
`environment_work_order` beside its one D8 findings body. Each item names the
tool, its install command and the concepts installation would restore, and the
server instructions tell the host to surface that order. A chat or HTML caller
does not need the JSON-only report dictionary to discover missing evidence.

*Closing tests:* `test_missing_analyzers_surface_a_top_level_environment_work_order`
in `tests/test_consent_and_grant.py` (chat), plus
`test_environment_work_order_reaches_every_format` in
`tests/test_grant_only_user_tier.py` (json, markdown, html).

### D10 — Closed: out-of-roots access has a structured grant

The MCP allow-list still defaults to the server's launch directory. When an
audit tool request falls outside it and the client can elicit, one structured
choice offers **this session** (pre-selected), **always**, or **no**. A session
grant extends only the running process. An always grant writes an
`allowed_roots` entry to the user configuration tier and is merged at server
startup; repository configuration never carries that authority. Refusal or a
client without elicitation receives `PathNotAllowed` with both `--allow-root`
and `MAINTAINABILITY_MCP_ALLOWED_ROOTS` remedies. Report resources remain
ask-free and read-only.

*Closing tests:* `test_session_root_grant_is_default_and_lives_only_for_that_server`,
`test_always_root_grant_persists_only_to_the_user_tier_and_loads_at_startup`,
`test_denied_or_unsupported_root_grant_explains_both_static_remedies`, and
`test_report_resource_never_elicits_or_persists_a_root_grant` in
`tests/test_root_grants.py`.

### D11 — Closed: economic context is part of chat setup

The ADR 004 labor question now rides the structured first-run chat setup.
It is declinable; accepting persists the same low/base/high
`loaded_engineering_cost_per_hour` shape to both configuration tiers, while
declining omits economic context from both.

*Closing tests:* `test_apply_answers_persists_economics_and_format_to_both_tiers`
and `test_declining_economics_omits_the_block_from_both_tiers` in
`tests/test_first_run_elicitation.py`.

### D12 — Closed: the operator skill teaches the chat-primary flow

The shipped skill checks configuration, uses the host's structured question UI
for elicited choices, keeps the bounded work order in chat, and writes no report
file without a chosen location. CLI commands are retained under the automation
and CI path rather than presented as the default user flow.

*Closing test:* `test_shipped_skill_teaches_chat_setup_before_cli_automation`
in `tests/test_chat_primary_docs.py`.

### D13 — Closed: the XDG user configuration and state tier ships

Configuration now merges built-in defaults, the XDG user configuration,
and repository `maintainability-agent.json` in that order, so the later
repository tier wins. Any loaded configuration tier enables the D1 pool
default unless the winning tier explicitly sets `analyzers.run` false.
The XDG state file records repositories by absolute root, making first-run
detection persistent; corrupt or unreadable user files are treated as
absent rather than crashing an audit.

*Closing suite:* `tests/test_user_config_tier.py`.

### D14 — Closed: the chat integration applies setup and root grants

The chat integration is built: one native MCP elicitation applies analyzer,
depth, license, history-consent, economics and presentation answers to that
same audit and persists them for later calls. Out-of-roots tool requests now
ride the structured grant path, and the slash prompt delegates presentation
to the host's structured question mechanism. This is driven end to end by
`test_one_native_elicitation_applies_answers_to_that_same_audit` in
`tests/test_first_run_elicitation.py`, the grant tests in
`tests/test_root_grants.py`, and the consent and slash-prompt tests in
`tests/test_consent_and_grant.py`.

### D15 — Closed: analyzer selection is goal-directed

The entry as recorded: selection was policy filtering plus language
applicability, and the gap analysis that knows which concerns are
unmeasured for which languages never drove a run. The requirement —
restored here verbatim after an audit caught the close rewriting it —
was that selection consults the same language inventory and
concern→concept mapping the coverage section uses, so a run covers
the repository's languages with the verified tools available and
names, before or with the results, what to install to close the
remaining gaps.

That requirement now holds at the production seam: language-mismatched
tools are stated inapplicable with the inventory's reason, engaged
tools follow the tree's languages, a concern-narrowed pool engages
exactly the tools that serve it, and the environment work order names
the installs — with the concepts they restore — that close the
per-language gaps the coverage section states. The composition of
source-read and artifact-read shapes (identity, path normalization,
staleness, artifact-gated applicability, `class_dirs` isolation) was
pinned in the same track.

Selection composes the runnable set in `_selection.select_runnable`
before any probe or spawn: a language-mismatched tool is never
attempted, a catalogued tool this project cannot invoke is stated as
`no-adapter` rather than counted runnable, and `coverage.selection`
carries the disjoint `runnable` and `inventory_filtered` sets.

*Closing tests:* `tests/test_d15_goal_directed.py` (the requirement as
originally written, including a minimality proof that reads the
coverage document's real `by_language` key — an earlier version read a
key that never existed and passed itself on the empty result) and
`tests/test_d15_composition.py` (the two-shape composition pins).

*Round-four verification on `5a7857c`: reopened.* A catalog tool with no
adapter is still returned as `Selected` when its catalog languages overlap the
tree, and the report consequently lists it under `coverage.selection.runnable`
with a `no-adapter` outcome even though it can neither be probed nor spawned.
The report's own description says every member of `runnable` was probed or
spawned. The minimality regression does not detect this class: it reads the
absent `coverage["languages"]` key instead of `scored_languages` /
`by_language`, then explicitly passes whenever that empty set is observed.
The queue item is to make the reported sets state their actual semantics and
replace the vacuous assertion with a production-report falsifier.

### D16 — Closed: chat workflow help is linked from both entry surfaces

The [chat workflow help](help/README.md) now explains what the agent does,
first-run setup and roots grants, history consent, analyzer-primary evidence
and built-in fallback, and how to read the report's estimate, range, grade,
history, recurrence, baselines and economic scenario. It lives beside the docs
the existing lints sweep and is reachable from README, the documentation index,
the integration guide, and the MCP server instructions.

*Closing test:* `test_chat_help_is_complete_linked_and_reachable_from_mcp` in
`tests/test_chat_primary_docs.py`.

### D17 — Closed: integration guidance and generated packs are chat-first

[ide-agent-integration.md](ide-agent-integration.md) and the generated
agent-instruction packs (`--init-agent-standards`) now teach the same sequence:
check configuration, use structured elicitation, keep the report in chat unless
the user chooses a file location, and treat the CLI as the automation and CI
door.

*Closing test:* `test_integration_guide_and_generated_packs_teach_chat_before_automation`
in `tests/test_chat_primary_docs.py`.

### D18 — Closed: skill installation is bound, atomic, and complete

`--install-skill` opens the skill root once with
`O_NOFOLLOW|O_DIRECTORY` and performs every read, write and unlink
relative to that descriptor, so swapping the pathname afterwards
cannot redirect a write. Three further holes closed after a second
audit: a failed rebind of a freshly created root used to leave
`dir_fd=None`, which resolves against the process working directory —
it is now a refusal; a leaf replaced by a HARD link was written
through, because `O_NOFOLLOW` says nothing about hard links — files
are now staged and renamed into place, so the old inode is never
modified; and `os.write` was called once, installing a truncated file
while reporting success — every byte is written or the install
refuses. Staging files are cleaned up on every failure path.

*Closing tests:* `test_the_validated_root_is_bound_by_descriptor_not_by_name`,
`test_missing_root_swap_never_falls_back_to_process_cwd`,
`test_leaf_hardlink_swap_cannot_modify_external_file` and
`test_short_write_is_completed_or_refused_without_success` in
`tests/test_skill_install.py`.

### D19 — Closed: occupancy is every entry, not every regular file

Occupancy counted regular files and symlinks, so a root holding only
an empty directory, a FIFO or a socket read as a fresh install and was
modified without consent — and a FIFO named `SKILL.md` hung the
installer forever, because reading it meant opening it. Occupancy is
now any directory entry at all, decided from `stat` metadata with
`follow_symlinks=False` so no special file is ever opened. Forced sync
removes what it understands (files, symlinks, FIFOs, sockets, empty
directories) and refuses by name anything it does not, rather than
deleting on a guess. An empty root directory is still a fresh install.

*Closing tests:* `test_a_nested_symlink_in_an_empty_root_still_needs_consent`,
`test_empty_subdirectory_counts_as_occupied`,
`test_fifo_counts_as_occupied_without_blocking`,
`test_socket_counts_as_occupied` and
`test_force_refuses_or_safely_removes_special_entries` in
`tests/test_skill_install.py`.

### D20 — Closed: a configured history path cannot escape its repository

`paths.history` is read from a file inside the repository under audit,
and every consumer built `root / configured` without validating the
result. A repository could therefore name `../outside.jsonl`, an
absolute path, or a path through a symlinked directory, and an audit
with history enabled would create and append that file outside the
authorized root — reproduced through the public MCP seam. One helper,
`config.repository_path`, now resolves and bounds every configured
repository-scoped path before any existence check, mkdir or append,
and all five construction sites across the MCP tool, the MCP report
resource and both CLI paths use it. Traversal, absolute escapes and
symlink escapes are one comparison, not three special cases, and the
refusal is the same structured `PathNotAllowed` the roots boundary
already used.

*Closing tests:* `test_mcp_history_rejects_parent_traversal_without_external_write`,
`test_mcp_history_rejects_absolute_escape_without_external_write`,
`test_mcp_history_rejects_symlink_escape_without_external_write`,
`test_a_history_path_inside_the_repository_still_records` and
`test_the_cli_door_applies_the_same_boundary` in
`tests/test_history_boundary.py`.

### D21 — Closed: the skill calls the tool instead of interrogating the repo

Found in the field on 2026-08-21. The skill's first step told the host
agent to perform a configuration check — look for
`maintainability-agent.json`, the user tier, local instruction files —
*before* calling `audit_repository`. In a repository whose config had
been deleted, that instruction produced a quarter-minute of
deliberation and then a question to the operator about which config to
use: a question the tool itself asks properly, as structured first-run
setup, the moment it is called. The agent was doing the tool's job,
worse and slower.

The first step is now the call. An unconfigured repository is not an
obstacle to reason about; it is the case first-run setup exists for.
Repository instruction files govern how findings are acted on, never
whether the audit runs.

*Closing test:* `test_the_skill_calls_the_tool_before_inspecting_configuration`
in `tests/test_chat_primary_docs.py`.

## Disposition

Every entry in this register is closed, each behind a test that would fail if
the defect returned — and the count is read from the entries themselves, never
asserted as a number that stops describing the register when it grows. D15 was
reopened twice: once when an audit found its close had rewritten the
requirement, once when the proof turned out to be vacuous. D18 and D19 were
each reopened after their first close, when audits reproduced a descriptor
race, a hard-link write-through, a short write, and three kinds of occupancy
the installer ignored. D20 was found by audit in the MCP write boundary and is
the one security defect in this register: a repository could name a history
path outside itself and be believed.

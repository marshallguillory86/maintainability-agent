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
written to the repository and user configuration tiers.
Declined or unsupported elicitation returns the same questions in
`setup_needed`; while both configuration tiers remain absent, later calls
ask again. Only written answers end setup elicitation.

> **Amended 2026-08-22 (superseded in part by D26 and D27).** This entry
> closed on answers that "apply to that same audit", and that clause is
> struck: answering setup configures the repository and returns the
> run-or-reconfigure choice, never a report. What D2 actually settled —
> that first contact asks, in structured form, and persists to both
> tiers — still holds. The closing citation below is restamped to the
> test that carries it now; the original name is kept in D27, which
> records the rename and why.

Report save location is a separate host question at save time. The local
MCP process returns report text and never writes a report file; the host
asks where to save it when the user chooses a file presentation.

*Closing tests:* `test_setup_triggers_only_when_both_configuration_tiers_are_absent`,
and `test_one_native_elicitation_configures_and_then_asks_before_auditing`
in `tests/test_first_run_elicitation.py`;
`test_a_completed_mcp_audit_marks_seen_even_when_a_gate_fails` in
`tests/test_setup_precondition.py`; plus
`test_unanswered_setup_is_reelicited_until_answers_are_written` and
`test_repeated_declines_keep_returning_the_same_setup_needed_block` in
`tests/test_first_run_reelicitation.py`.

### D3 — Closed: setup and the slash prompt use structured choices

First-run chat setup uses one structured MCP elicitation with disclosed
options and defaults, including **chat** as the presentation default. A
decline or host without elicitation support receives those same structured
questions in `setup_needed`.
The `maintainability-agent` slash prompt now tells the host to use its
structured elicitation or question UI for presentation, with chat
pre-selected, instead of prescribing a free-text ask.

> **Amended 2026-08-22 (superseded in part by D26).** This entry closed
> on "and the audit proceeds on documented defaults", which is struck:
> that audit was the defect D26 removed, and an unanswered call now
> returns the questions and nothing else. D3's actual subject — that
> the questions are structured choices with disclosed defaults, on both
> the elicited and the handed-back path — is unaffected. The second
> closing citation is restamped to the test's current name.

*Closing tests:* `test_setup_questions_are_structured_choices_with_disclosed_defaults`
in `tests/test_first_run_elicitation.py`,
`test_declined_or_unsupported_elicitation_returns_questions_not_an_audit`
in `tests/test_setup_precondition.py`, plus
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
depth, license, history-consent, economics and presentation answers and
persists them for later calls. Out-of-roots tool requests now
ride the structured grant path, and the slash prompt delegates presentation
to the host's structured question mechanism.

> **Amended 2026-08-22 (superseded in part by D27).** "to that same
> audit" is struck here for the reason given in D2: the elicitation
> configures the repository and the call returns the run-or-reconfigure
> choice. This entry also cited its falsifier in prose rather than
> under a *Closing test* marker, which is how its citation survived a
> rename unnoticed — the marker is now mandatory and machine-checked.

*Closing tests:* `test_one_native_elicitation_configures_and_then_asks_before_auditing`
in `tests/test_first_run_elicitation.py`, the grant tests in
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

### D22 — Closed: the delivery question offers every presentation the product ships

Found in the field on 2026-08-21, in the same run that produced D21.
Asked to audit a repository, the host agent offered two choices —
"chat only" or "chat plus save to a path you name" — and then asked
where to write the markdown. The HTML report was never mentioned. The
product ships three presentations (`chat`, `markdown`, `html`), the
`format` argument accepts all three, and first-run setup already asks
which one the user prefers; the operator's reaction was simply "what
happened to my HTML report option?"

Nothing in the product had lost the option. The skill's presentation
step named only chat and "a location", so the agent filled the gap with
an option set of its own invention — the D21 failure mode one layer
down: improvising a question the product already asks properly. The MCP
prompt had the correct three-way wording all along, which is why the
defect was invisible to whichever surface a reviewer happened to read.

The skill now states the three presentations, routes the answer to
`format`, names the two-option shape as the thing not to substitute,
and makes the save location a second question asked only after a file
format was chosen. Both instruction surfaces are checked together, and
against the setup vocabulary rather than a copy of it, so a fourth
presentation would have to reach the instructions to ship.

*Closing test:* `test_every_delivery_surface_offers_all_three_presentations`
in `tests/test_chat_primary_docs.py`.

### D23 — Closed: the analyzer catalog reaches an installed copy

Found in the field on 2026-08-21, in a bighound audit that reported
`analyzer catalog missing at
/Users/…/Library/Python/3.11/lib/python/data/analyzer-catalog.json`.

`CATALOG_PATH` climbed three parents from `_catalog.py` to a
repository-root `data/` directory. In a source checkout that resolves
correctly, which is why 1,383 tests and every local run agreed it
worked. From an installed wheel the identical expression points at
`<site-packages>/../data/analyzer-catalog.json` — a path that has never
existed anywhere. `docs/standard.md`, served over MCP as
`maintainability://standard`, was resolved the same way and had the
same fault.

Neither file was declared in any package, so neither was ever copied
into a distribution. Every release from 0.1.0 through 0.9.1 shipped
without them. The consequence is not cosmetic: with no catalog nothing
can be selected, so the external analyzer pool — ADR 006's primary
evidence source, and the entire JVM adapter track — was unreachable
for every pip-installed user, who silently received built-in fallback
numbers instead. The operator's field tests had been measuring the
fallback, not the product.

Both assets now live in `maintainability_audit/_assets/` and resolve
package-relative. `tools/build_catalog.py` writes there.

*Closing tests:* `test_the_built_distribution_carries_the_catalog_and_the_standard`
stages a real build and reads what came out — a green suite proved
nothing here for nine releases because nothing ever looked at an
artifact. `test_no_runtime_asset_is_read_from_outside_the_package`
refuses the path shape itself, in any runtime module, whatever it is
reaching for. Both in `tests/test_wheel_contents.py`.

### D24 — Closed: `analyzers_run` reports the outcome, not the request

Found in the same field run. With the catalog missing (D23) no
analyzer could be selected, let alone execute — and the result envelope
still carried `"analyzers_run": true`, because the key echoed the
resolved tri-state rather than what came of it. The report prose said
fallback tier; a caller trusting the machine-readable envelope got a
false green.

This is the repository's own `absence-as-zero` risk pattern one level
up: capability recorded as result. The key's own comment claimed it
existed so "a caller cannot mistake an audit that ran six built-in
detectors for one that ran ten tools" — the promise was always the
outcome reading; only the value was wrong.

`analyzers_run` is now true exactly when an analyzer contributed, read
from the coverage document. The request is preserved beside it as
`analyzers_requested`, and `environment_work_order` explains any gap
between the two.

*Closing test:* `test_a_requested_pool_that_contributes_nothing_is_not_reported_as_run`
in `tests/test_pool_runs_by_config.py`, which reproduces the cause —
an unreadable catalog with the pool explicitly requested — rather than
imitating the symptom.

### D25 — Closed: the questions handed back are questions someone is told to ask

Reported by the operator on 2026-08-21, correcting a wrong diagnosis of
D22: *"I never saw an option for HTML, ever across the prompts."* Not
in that run — in any run, for the life of the product.

D22 blamed the skill's presentation step, and fixing it was necessary
but did not touch the cause. When a host cannot be elicited, the audit
hands its entire first-run set back as `setup_needed` — including
`default_format` with chat, markdown and html — and D3 records that as
graceful degradation. But `setup_needed` was named in no instruction
surface anywhere: not the MCP server description, not the skill, not
the generated packs. Its sibling on the same degradation path,
`environment_work_order`, was explicitly instructed on both ("surface
it to the user"). One of the two keys was explained and the other was
not.

So the question that offers the three presentations was generated
correctly, returned correctly, and asked by nobody. An agent receiving
a payload it had no instruction about did what agents do with a gap: it
invented its own questions, which is what D21 and D22 each caught one
symptom of. The user's report was the only detector that ever fired,
because no test looked at the handed-back payload and no surface
mentioned the key.

Both surfaces now instruct it: ask every question, offer exactly the
options it lists and no others, then call again with the answers.

*Closing test:* `test_the_handed_back_questions_are_instructed_and_carry_every_format`
in `tests/test_chat_primary_docs.py`, which audits a genuinely
unconfigured repository through the production seam and asserts the
payload carries the presentation question with all three options, then
holds both instruction surfaces to naming the key — checked at the
seam rather than against the vocabulary, since the vocabulary was
right the whole time.

### D26 — Closed: an unconfigured repository is asked, not audited

Marshall's ruling on 2026-08-21, in response to my proposing three ways
to *disclose* a provisional grade: *"An unconfigured run is supposed to
ask the questions first."*

The behaviour I was proposing to decorate: when a host could not be
elicited, the audit ran anyway on built-in defaults and filed its
questions beside a finished report. Demonstrated on an unconfigured
scratch repository — `analyzers_requested: False`, the pool off, a
complete graded report, and the entire disclosure a single table row
reading `| Estimate source | Built-in detectors (fallback tier) |`. The
rendered report contained zero occurrences of "setup", "unconfigured",
"first run", or "not configured". Meanwhile the `run_pool` question's
own recommended answer is **yes** — so the number a first-time user saw
was computed the opposite way from the one the product recommends, and
nothing said so. bighound produced exactly that: a 3.9/C that the
operator's own agent correctly called "not the product's answer".

D25 made the questions askable. It did not stop the report being
produced before anyone asked them, which is the part that matters: a
grade nobody can act on is worse than no grade, and an agent handed a
finished report has no reason to go looking for the questions.

Setup is now a precondition. A repository with neither a repository
config nor a user tier returns `audit_ran: false`, the question set,
and a `setup_instruction` — no report, no score, nothing to mistake for
an answer.

> **Amended 2026-08-22 (extended by D27).** As shipped, this entry
> closed on "answering yields the real audit on the next call", and
> that clause is struck: it was the half of the ruling this entry got
> wrong. Answering configures the repository; the next call returns the
> run-or-reconfigure choice and the user says when to run. D26's own
> subject — that an unconfigured repository is never audited — stands
> unchanged.

Elicitation
is unaffected: a host that can be elicited is asked *before* the audit
and never reaches this path. An explicit `config_path` also passes
through, so automation is not gated on an interactive answer.

An audit twice flagged a third test cited here,
`test_the_handed_back_questions_are_instructed_and_carry_every_format`,
which proves D25's claim about instruction surfaces rather than this
entry's. Dropped rather than defended: a closing citation is the list
of tests that fail if *this* defect returns, and padding it with
adjacent ones is how a citation stops meaning anything. D31 records
that no check can catch this — deciding what a test proves is a
reviewer's job — which makes it the reviewer's job to keep the list
honest.

*Closing tests:* `test_setup_is_a_precondition_and_answering_it_yields_the_real_report`
in `tests/test_setup_precondition.py` asserts the loop whole —
questions, then the choice, then a report honouring the chosen html
presentation — because refusing to audit is only correct if answering
unblocks it. `test_declined_or_unsupported_elicitation_returns_questions_not_an_audit`
in the same file pins the degradation path.
### D27 — Closed: configuring is not running, and setup is reachable on every run

Marshall, 2026-08-21, after D26 shipped half of it: *"The point of the
questions is to setup the agent's configuration on the repo. NO audit
should be run automatically. DO NOT run the audit until the
configuration questions are answered. Then ask if the user is ready to
run the audit. … The second run will actually have a config. No need to
ask the same config questions over and over again. Still should offer
an option to go back into config, or run the report."*

D26 stopped the audit on an unconfigured repository. It then let
answering the questions start one — so the user was asked how to
configure the agent and, by answering, unknowingly launched a scan.
Two decisions had been welded into one. It also had no way back into
setup once a config existed: changing an answer meant deleting
`maintainability-agent.json`.

Both are now the `action` argument, and its default differs by door on
purpose. Unset never audits. An unconfigured repository returns
`setup_needed`; a configured one returns `choice_needed` — run, or
reconfigure — on that run and every later one. `action="run"` audits.
`action="reconfigure"` reopens the setup questions for a repository
that already has answers. Every non-audit reply carries
`audit_ran: false` and no score. The MCP tool passes unset because a
person is on the other end and has not been asked; the plain
`audit_repository` function defaults to `"run"` for the CLI, the report
resource, and scripted callers, which have already decided.

Elicitation follows the same rule: a host that can be elicited is asked
the setup questions, the answers are written, and the call returns the
run-or-reconfigure choice rather than a report. The test that used to
be named `test_one_native_elicitation_applies_answers_to_that_same_audit`
asserted precisely the behaviour being removed, and now asserts its
replacement. One consequence worth stating: two calls produce one
history record, because configuring is not scanning.

*Closing tests:* `test_setup_is_a_precondition_and_answering_it_yields_the_real_report`
in `tests/test_setup_precondition.py` walks the whole flow —
questions, choice, reconfigure, run — and
`test_one_native_elicitation_configures_and_then_asks_before_auditing`
in `tests/test_first_run_elicitation.py` holds the elicitation path to it.

### D28 — Closed: the first-run help misdescribes the economics questions

Found by Grok on 2026-08-22, auditing the docs against the code.
`docs/help/first-run.md` presents economics as a single bullet —
"economic context: skip, or low/base/high loaded labor rates". The form
has four economics fields: the `economics` include/skip choice and
three labor bounds, and the bounds are in the elicitation schema
**unconditionally**, so a person answering "skip" is still shown all
three. A reader of the help page cannot predict what they will see.

Assigned to Codex as a documentation fix. Release-blocking under the
standing rule that a release ships only from an empty known-defect
ledger.

Fixed by Codex. The page now lists all nine fields with their
defaults and says the labor bounds appear whatever the economics answer
is. Writing the falsifier turned up a second omission on the same page:
it named `chat` as the presentation default without naming `markdown`
or `html` — the invisibility that D22 and D25 are about, on the page a
first-time reader is sent to. Corrected in the same pass.

*Closing test:* `test_the_first_run_help_describes_the_form_a_person_actually_sees`
in `tests/test_written_record.py`, which reads the fields and their
defaults from `setup_questions` rather than restating them, so a
question added to the form has to reach the page before it ships.

### D29 — Closed: ADR 011 states a status that stopped being true

Found by Grok on 2026-08-22. `docs/adr-011-three-report-presentations.md`,
Decision item 4, ends "that free-text ask remains open under D3". D3 is
closed. The decision text itself is history and must not be rewritten —
an ADR records what was decided when it was decided — but a *status*
claim inside one goes stale and misleads a reader who takes the ADR as
current.

The remedy is a dated amendment stamp under that item, in the form the
register now uses for its own superseded clauses, not an edit to the
decision. Assigned to Codex.

Fixed by Codex with a dated amendment stamp beneath the decision
item, leaving the decision text as the history it is.

*Closing test:* `test_no_document_says_a_register_entry_is_open_that_the_register_closed`
in `tests/test_written_record.py`. It blocks the class rather than
the instance: any document under `docs/` claiming a register entry is
open, while the register records it closed, fails until the claim is
corrected or stamped — and a stamp directly beneath the claim counts,
which is the form an ADR has to take.

### D30 — Closed: the setup gate is every door, not one call site

Found by Grok on 2026-08-22, auditing D21–D27. D26 made setup a
precondition at `audit_repository`, and an audit of the *other* doors
found the gate was one door wide.

The High: `maintainability://report/{root}` reaches `build_report`
directly and never passes through the gate, so it still served the
fallback-tier report for an unconfigured repository — the exact
artefact D26 exists to prevent, on the same chat surface. A resource
has no elicitation seam and cannot ask, so it refuses and names the
door that can.

Three more from the same pass. A completed audit still carried
`setup_needed`, because `_finish_result` re-attached the questions
whenever the repository was pending: `audit_ran: true` beside a demand
to configure, D26's shape surviving on the one path that bypasses its
gate. An empty `{}` counted as configured, because the check was
`is_file()` and a file is not an answer; a file that parses to nothing
is now the same state as no file, and one that does not parse refuses
by name instead of surfacing a `JSONDecodeError` from deeper in.

And the audit corrected this register. D27 claimed the `action="run"`
default was how the CLI and the report resource skip the gate. Neither
calls that function at all, and the precondition outranks the action
regardless — an unconfigured repository returns questions however
emphatically it is told to run. The docstring said otherwise for a day.

The shape of the fix matters more than any one hole: the falsifiers
enumerate the doors rather than asserting the rule at a call site,
because a precondition proven at one seam is a precondition on that
seam.

*Closing tests:* `test_the_report_resource_refuses_an_unconfigured_repository`,
`test_an_explicit_config_path_audits_without_carrying_setup_questions`,
`test_a_config_file_with_no_answers_in_it_is_not_configured`,
`test_an_unreadable_config_refuses_instead_of_leaking_a_parse_error`, and
`test_run_never_overrides_the_setup_precondition` in
`tests/test_setup_gate_completeness.py`.

### D31 — Closed: a closing citation names a findable test, not merely a real one

Found by Grok on 2026-08-22, attacking the citation check added the
same day. That check resolved every name under a *Closing test* marker
against the suite, which stopped entries closing on deleted tests. It
did not check the entry named the right *file*: the module stem in the
cited path counted as its own hit, so an entry could send a reader to
`tests/test_first_run_elicitation.py` for a function living in
`tests/test_setup_precondition.py` and pass. Three entries were doing
exactly that — D2, D26 and D27 — because the split that created
`test_setup_precondition.py` moved the tests and left the citations
behind. A falsifier a reader cannot find is not a falsifier.

The collector also missed `async def test_...`. No async test exists in
this tree, so nothing was slipping through; the hole was real and is
closed.

Grok's third defeat stands and is recorded rather than fixed: the check
cannot read assertions, so an entry may cite a live test that proves
something other than its defect. Blocking that mechanically would mean
deciding what a test asserts, which is the reviewer's job. It is named
here so the limit is known rather than assumed away.

*Closing test:* `test_every_closing_citation_names_a_test_that_exists`
in `tests/test_written_record.py`.

## D32–D46 are reserved, not missing

The next entry below is D47. Nothing was deleted. D32 through D46 belong
to the security and boundary work on `fix/round-two-findings`, which was
opened first and mints those identifiers; the three entries below were
originally written as D32–D34 on a branch cut from the same commit, so
for a day two live branches defined six different defects under three
identifiers.

That is worse than it looks. The release gate is "zero open entries in
this register", which is only countable if an entry number means one
defect. Colliding identifiers do not conflict in git — the two branches
touch different regions of this file — so nothing would have failed until
a reader tried to work out which D34 a changelog line meant. The smaller
branch renumbered. The gap stays as written so the reason survives the
merge, and it closes when `fix/round-two-findings` lands.

### D47 — Closed: the call-first rule reaches the door hosts are actually handed

Found by inspection on 2026-08-24, while diagnosing a field report.

> **Opened on a wrong diagnosis, and corrected the same day.** This
> entry was first written as the cause of that report: an operator
> starting a first-run test whose host opened by asking which
> `maintainability-agent.json` to use — committed in HEAD, deleted in
> the working tree — instead of calling the tool. It is not the cause.
> The host had the skill, and the skill it had was the pre-D21 copy
> from the installed `v0.9.1` wheel, whose step 1 reads "Configuration
> check first: look for `maintainability-agent.json`...". The host
> followed its instructions exactly. D21's fix was never in the
> artifact that machine loads, because nothing has been released since
> the fix landed.
>
> What is recorded below is a real and separately open gap, found while
> chasing that report and worth closing on its own terms. It is not
> what produced the screenshot, and the first draft of this entry
> claimed it was.

The gap is this. D21's falsifier read
`skills/maintainability-agent/SKILL.md` and stopped there. The skill is
opt-in; `SERVER_INSTRUCTIONS` is what every chat host receives on
connect, and it said nothing about the order at all. The MCP prompt
was worse than silent: it opened "First offer the presentation choice
... Then call `audit_repository`", which is both stale against D26
(presentation belongs after the setup and run/reconfigure asks) and an
explicit licence to ask something, then call.

Both MCP surfaces now carry D21's rule in D21's words, and the prompt
states the current two-ask contract instead of the old one. The
falsifier holds all three instruction surfaces to it together, which is
the check D22 had already established and that nobody applied backwards
to D21.

The gap was closed on inspection, not on a reproduction. No field run
is known to have failed *because* of it — the one that prompted the
look failed on a stale artifact instead (see the correction above, and
D49).

*Closing test:* `test_every_chat_instruction_surface_calls_the_tool_before_inspecting_config`
in `tests/test_chat_primary_docs.py`. D21's own test is left as it
stands: it holds the skill, which is the surface that did fail in the
field — on a copy older than the fix.

### D48 — Closed: a refusal is declared, not a crash

Found by CI on 2026-08-24, on an unchanged `main`. `mcp` floats on
`>=2,<3`; 2.1.0 shipped that day, and three boundary tests that had
passed at 06:31 failed at 23:54 on the same SHA.

It is not a regression in the SDK. 2.1.0 draws a line the product had
never declared a side of. A failure raised as `ToolError` or
`ResourceError` is one the server *saw coming*: its message reaches the
caller and the server logs it at INFO without a traceback. Anything
else is a crash — the caller gets `Error executing tool <name>`, or a
resource's bare URI, and the traceback is kept server-side, so nothing
internal leaks. That is a correct and well-documented distinction.

The path boundary is the most anticipated failure in this system. It
was raised as a plain `PathNotAllowed`, which is a `ValueError` — so
2.1.0 classified it as a crash, correctly, and withheld the text.
D10's requirement that a refusal teach `--allow-root` and
`MAINTAINABILITY_MCP_ALLOWED_ROOTS` was deleted by a patch release of a
dependency. The report resource lost `SetupRequired`'s message the
same way.

The security boundary itself never moved: the refusal still refused,
`is_error` still true, the path still blocked. What was lost is the
part that teaches. Before 2.1.0 the crash path happened to interpolate
the message anyway, which is why this was invisible rather than
absent.

Both MCP seams now declare their anticipated refusals while the plain
functions keep raising the domain types. The dependency range is
unchanged: pinning below 2.1.0 would preserve a misclassification and
treat a correct SDK change as damage.

**The anticipated set was wrong twice in one night, in opposite
directions, which is why a reviewer eyeballing it is not the
falsifier.** It began as `(ValueError, PathNotAllowed, SetupRequired)`.
Bare `ValueError` swept in failures from below the transport —
`_jvm_adapters` raises `"unreadable checkstyle XML: <path>"` — so
internal paths would have reached callers as declared refusals. It was
narrowed to `(InvalidAuditArgument, PathNotAllowed, SetupRequired)`,
which silently demoted two refusals raised on purpose for the caller
to act on: `StaleBaseline` ("Regenerate with `--write-baseline`") and
`PolicyError` ("unknown depth 'x'"). The set is now five named types.
`EvidenceValidationError` stays out: on the tool path the report is
built internally, so a failure in it is an internal bug.

The last correction of that tuple recrossed this repository's 500-line
file gate (`mcp_server.py` went to 513). The PR that claimed CI green
was red on both Verify and Audit. The module is back under the gate.

Two assertions that used to demand `pytest.raises(PathNotAllowed)`
through `read_resource` now assert the refusal the client receives:
declared as `ResourceError`, message names the boundary, domain type
preserved as `__cause__`. That holds on 2.0.0 and 2.1.0 both.

**What the tests prove, and what they do not.** The two original seam
tests exercise `PathNotAllowed` through the tool and the report
resource, and prove a below-transport `ValueError` stays a crash (the
latter skips on 2.0.0, where the SDK interpolates crash text itself).
Three more now drive the rest of the tuple: `StaleBaseline` and the
seam's own `InvalidAuditArgument` out of the audit tool, and
`SetupRequired` out of the report resource's own handler — which the
validator's earlier refusal had been shadowing, so every existing
resource test caught the validator and none reached the handler
beneath it.

Those three assert against the registered seam rather than a client,
and the reason is a defect that was written into this file first. The
draft asserted that the caller's message is not the SDK's generic
crash string. On `mcp` 2.0.0 that is true whether or not the refusal
was ever declared, because 2.0.0 interpolates crash text — so the
draft passed with `StaleBaseline` deleted from the tuple. What is
version-independent is the translation itself: an anticipated refusal
leaves the seam as `ToolError` or `ResourceError` carrying its domain
type as `__cause__`. Each of the three was verified by deleting its
type from the tuple and watching the test fail.

`PolicyError` is deliberately not driven, and cannot be. Every site
raising it is reachable only through `_analysis.analyze()`, which
catches it and returns `Analysis(error=...)`; a test would have to
fake a call path the product does not have. Architecture invariant 12
now says that rather than implying the two types stand on the same
evidence — an audit of this entry caught it claiming they did.

Membership — of those types and of any sixth added tomorrow — is
`test_every_named_exception_is_a_declared_refusal_or_excluded`, which
derives every named exception in the package and requires each one in
the tuple or excluded with a stated reason. `SkillDrift` is the
CLI-only exclusion; `UnsupportedReportSchema` rides
`EvidenceValidationError`. The three seams must except the tuple by
name, so a hand-written copy cannot hide a miss.

*Closing tests:* `test_a_refusal_is_declared_rather_than_crashing_out_of_either_seam`
and `test_a_failure_from_below_the_transport_stays_a_crash` in
`tests/test_root_grants.py`; `test_every_named_exception_is_a_declared_refusal_or_excluded`,
`test_the_transport_excepts_the_named_tuple_not_a_copy`,
`test_a_stale_baseline_leaves_the_seam_as_a_declared_refusal`,
`test_the_seams_own_argument_refusals_leave_it_declared` and
`test_an_unconfigured_repository_refuses_through_the_resource_seam` in
`tests/test_anticipated_refusals.py`.

### D49 — Closed: the skill in the distribution is asserted, not assumed

Found on 2026-08-24 while diagnosing a field report. Two tests read
`_skill_data/SKILL.md` and both read it out of the source checkout:
`test_every_delivery_surface_offers_all_three_presentations` byte-pins
the mirror against `skills/maintainability-agent/SKILL.md`, and
`test_skill_install` reads the same source path. The payload a host
actually loads — carried in the distribution and written out by
`--install-skill` — was asserted by nothing.

That is D23's hole on a different payload. D23 closed by staging a real
build and reading what came out, but only for `_assets`; the skill
payload was left on the assumption that declaring it was the same as
shipping it.

The staged distribution must now carry `_skill_data/SKILL.md`, be
byte-identical to the reviewed skill, and contain D21's rule — the call
first, and no "configuration check first" anywhere in it.

**What this entry does not explain.** It was opened while chasing a
stale skill on an operator's machine, and it is not the cause of that.
That copy was current for the release it came from; it is old because
`v0.9.1` predates D21's fix and nothing has shipped since.

*Closing test:* `test_the_shipped_skill_is_the_current_one_and_carries_its_first_rule`
in `tests/test_wheel_contents.py`.

**The falsifier is the two content assertions, and only those.**
Drifting the mirror from the reviewed skill fails the byte-pin;
reintroducing "configuration check first" fails the rule check.
Absence of the staged file fails the same read. A `REQUIRED` entry on
the `package-data` glob was drafted alongside them and dropped: removing
`_skill_data/**/*` from `package-data` and staging a build again leaves
all six files in place — setuptools includes them by another route —
so that assertion cannot be falsified through the declaration it
appears to guard. A check that cannot fail is not a proof, and D15 was
reopened once for exactly that confusion.

## Disposition

**Every entry is closed.** D28 and D29 were opened and closed on 2026-08-22
under the standing rule that a release ships only from an empty known-defect
ledger; filing them here rather than leaving them in a chat message is what
made them countable. D30 and D31 came from the audit of D21–D27 and are the
most instructive pair in the register: both are defects *in the fixes*, found
because the fixes were audited rather than trusted. D30 is a precondition that
guarded one door of four. D31 is a check that verified a falsifier existed
without verifying a reader could find it.

Every closed entry sits behind a test that would fail if its defect returned,
and since 2026-08-22 that citation is machine-checked — three entries had been
closing on tests a rename had deleted. The count is read from the entries
themselves, never asserted as a number that stops describing the register when
it grows. D15 was
reopened twice: once when an audit found its close had rewritten the
requirement, once when the proof turned out to be vacuous. D18 and D19 were
each reopened after their first close, when audits reproduced a descriptor
race, a hard-link write-through, a short write, and three kinds of occupancy
the installer ignored. D20 was found by audit in the MCP write boundary and is
the one security defect in this register: a repository could name a history
path outside itself and be believed. D21 and D22 came from the same field
run and are the same shape: an instruction surface that left a gap, and an
agent that filled it by improvising a question the tool already asks. D23 is
the most consequential entry here — nine releases shipped with no analyzer
catalog inside them, so every installed copy lost the analyzer pool while a
green suite, running from a checkout, reported everything working. D24 is
how that outage stayed quiet: the envelope reported the request rather than
the result. D25 corrected D22's diagnosis rather than extending it — the
presentation step was a real gap, but the reason a user was never once
offered the html report is that the question offering it was handed back as
data no instruction surface mentioned. Three entries in this register are the
same sentence: the product produced the right thing and nothing told the
agent to use it. D26 is the one that stopped treating that as a documentation
problem — the audit no longer runs at all until the repository has been set
up, so there is no premature grade for an agent to report in place of the
questions. D47 is the entry that had to be corrected after it was written: it
was opened as the cause of a field report and was not the cause. D48 is the
one found by a machine rather than a person — an unchanged `main` went red
when a dependency shipped, exposing a misclassification the product had been
shipping since its first MCP release — and the anticipated set was wrong
twice in opposite directions before a derivation test owned it. D49 is
D23's hole on the skill payload; it is not the cause of the stale installed
skill that prompted the look.

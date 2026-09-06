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

## The falsifier standard

**Thirty of the entries below are one defect.** Not thirty defects with
a family resemblance — one mechanism, fixed thirty times without being
named, which is why it kept coming back. It was found by asking why
instead of closing the thirty-first.

The shape, every time:

1. A **universal claim** exists. *"No analyzer reads configuration from
   the audited tree." "Every git command disables housekeeping." "No
   document presents a refused analyzer as runnable."*
2. An audit finds **one instance** where the claim is false.
3. The check is written **from the instance**, not from the claim.
4. The check goes green, and the claim is still false everywhere else.

Step 3 happens because the author has a reproduction in hand and no
enumeration of what the claim quantifies over. It surfaces two ways: the
population is hand-picked — two adapters of fifteen, three sentences,
one file of a package — or the property is approximated by a string
instead of executed: `"pytest" in job`, `"42" not in document`, the
presence of a `diff` command that had been neutered with `|| true`.

**Mutation testing did not catch it, and the reason is the useful part.**
Mutation was being applied — to the instance that motivated the fix,
which is *inside* the sample the check was written from. So the mutation
confirmed the sample and said nothing about the claim. Every time an
auditor broke one of these, their mutation came from outside the sample
and the author's came from inside it.

So a falsifier for a universal claim owes three things:

| Clause | Enforced by |
|---|---|
| **Derive the population** from the source of truth — `ADAPTERS`, an `rglob`, the catalog — never a list typed by hand | review; the shape is visible |
| **Assert the population is not empty**, so a sweep that matched nothing fails instead of passing | `tests/test_falsifier_standard.py` |
| **Mutate outside the sample**: the proof must break a member the test does not name | stated in `*Mutation:*`, required from D97 |

The third cannot be checked mechanically, so it is required to be
*written down*. An author who has to say which member they broke, and
why it sits outside what the test names, cannot make the substitution
silently.

## Roles, recorded from D90

Every entry from **D90** onward carries a `*Roles:*` line naming who did
each part:

```
*Roles:* found=grok prompt=claude fix=claude test=codex run=ci
```

* `found` — the agent or person whose audit produced the finding.
* `prompt` — who wrote the audit prompt that produced it. Not the same
  question: an auditor searches where it is pointed, and every finding
  in D64–D89 came from a prompt written by the same agent that wrote the
  code being audited.
* `fix` — who implemented the change.
* `test` — who wrote the falsifier. **The interesting one.** A fix and
  its check written by one mind share that mind's blind spot, which is
  the mechanism behind eleven of this register's entries being findings
  about an inadequate check rather than about the product.
* `run` — where it was verified: `local`, `ci`, or `mutation` when a
  fix was proved by reverting it and watching the cited test fail.

**Entries before D90 have no `*Roles:*` line and are not backfilled.**
The authorship of those falsifiers is not recorded anywhere, and
reconstructing it from memory would put invented data into a register
whose entire value is that its claims are checkable. Where an early
entry names its reporter it does so in prose, which is all that is
known.

The working split this records, set 2026-08-26: **Claude writes code,
Codex writes tests and docs, Grok audits, and Codex may audit.**

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

*Closing tests:* `test_user_paths_honor_xdg_environment`,
`test_user_and_repository_config_merge_in_precedence_order`,
`test_any_loaded_config_tier_defaults_the_pool_on_and_explicit_false_wins`,
`test_corrupt_user_config_reads_as_absent` and
`test_successful_cli_audit_marks_the_repository_seen` in
`tests/test_user_config_tier.py`. Named individually because "the whole
suite" is not a falsifier: an audit tightened the citation check on
2026-08-23 and this entry was the one closing on a bare path, which
tells a reader where to look but never which test fails if the tier
stops being honoured (D33).

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

*Closing tests:* `test_inventory_deselects_before_any_probe_or_spawn`,
`test_selection_composes_the_runnable_set_before_the_run_loop`,
`test_the_runnable_set_is_minimal_for_the_trees_languages` — the
minimality proof, which reads the coverage document's real
`by_language` key after an earlier version read a key that never
existed and passed itself on the empty result — and
`test_a_catalogued_tool_without_an_adapter_is_not_called_runnable` in
`tests/test_d15_goal_directed.py`; plus
`test_one_report_composes_source_read_and_artifact_read` and
`test_stale_artifact_evidence_is_stated_on_the_composed_summary` in
`tests/test_d15_composition.py`, the two-shape composition pins.

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

### D30 — Closed: the setup gate is every chat door, not one call site

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

> **Amended 2026-08-22 (D32).** The title said "every door" and a
> second audit round measured it: the CLI, `build_report` and
> `--backfill` still score an unconfigured tree. That is the
> automation/CI door behaving as designed — a caller that has already
> decided, with no person to ask — but "every door" claimed more than
> the fix delivers, so the title now says *chat* door. The distinction
> is the product's, not an excuse: chat asks, automation assumes.

*Closing tests:* `test_the_report_resource_refuses_an_unconfigured_repository`,
`test_an_explicit_config_path_audits_without_carrying_setup_questions`,
`test_a_config_file_with_no_answers_in_it_is_not_configured`,
`test_an_unreadable_repository_config_refuses_at_the_setup_check`, and
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

### D32 — Closed: the refusal reaches the reader, on every door

Found by Grok on 2026-08-22, round 2, attacking round 1's fixes. Three
of the four findings are defects in D30 and D31; the fourth is a claim
this register made that the wire disproved.

**The refusal did not survive the protocol.** D30 said the report
resource "refuses and names the door that can ask". Read through a real
client, `SetupRequired` arrived as a bare `-32603` carrying "Error
creating resource from template …", and the sentence naming
`audit_repository` survived only as `__cause__` on the server side,
where no user looks. In-process the refusal looked perfect, which is
exactly why the test that proved it was in-process. It is now raised as
the SDK's own `ResourceError` at the boundary, and asserted through a
client rather than an exception handler.

**One repository state, two experiences.** A truncated config made the
MCP tool and resource refuse by name while the CLI let a raw
`JSONDecodeError` traceback out — on the door people run unattended,
where a traceback is the least useful outcome available. The CLI now
refuses in its own idiom, naming the file to repair.

**A file name is not a falsifier.** D31's check required cited names to
exist and to live in the cited file, and Grok closed an entry with
nothing but a path on the closing line: no name to resolve, so nothing
to object to, so it passed. "Which test fails if this defect returns?"
must have an answer, and now must have one written down.

**And the title overclaimed.** D30 said "every door"; the CLI,
`build_report` and `--backfill` still score an unconfigured tree. That
is the automation door behaving as designed — a caller that has already
decided, with nobody to ask — but the entry claimed more than the fix
delivered. Retitled to *chat* door and stamped, rather than left to
read as a promise the code does not keep.

Two of Grok's attacks are recorded as accepted limits rather than
fixed: a citation naming a real test that proves something other than
its entry's defect (D31 already says no check can read assertions), and
a test living in `conftest.py`, which the collector does not scan
because no closing citation names it.

*Closing tests:* `test_the_resource_refusal_survives_the_protocol` and
`test_the_cli_refuses_an_unreadable_config_in_its_own_idiom` in
`tests/test_setup_gate_completeness.py`; the file-only citation is
refused by `test_every_closing_citation_names_a_test_that_exists` in
`tests/test_written_record.py`.

### D33 — Closed: the fixes for D32, audited

Grok's round 3, on 2026-08-23, attacking round 2's fixes. Three
findings, all in code written the day before, plus one this check
turned up on its own.

**"Name a test" was satisfied by naming a file.** D32 added an
assertion that a closing citation must contain a `test_` token. It
passed the very attack it was written against, because the token it
found was the *filename inside the path*: `tests/test_x.py` reads as
"names test_x". Paths are stripped before looking now. Tightening it
immediately caught two entries closing on a bare suite — D13 and D15,
both predating the check and both invisible to every earlier version of
it. Their falsifiers are named individually.

**Only one refusal reached the reader.** D32 wrapped `SetupRequired` so
its message crossed the wire, and stopped there. A root outside the
allow-list still arrived as "Internal server error", discarding the
`--allow-root` sentence at the one layer that knows it — and that
refusal is raised in the SDK's security callback, before the resource
function the wrapper lives in. Both layers translate now, and the
falsifier walks every refusal the resource can raise rather than the
one an audit happened to name.

**Two parsers, one file.** `setup_pending` kept its own `json.loads`
beside `load_config`'s, so a JSON array made the MCP tool ask the setup
questions while the CLI refused the file. One state, two answers —
which is the defect D32 set out to remove and left standing one call
away. They share a parser now.

Also corrected: `load_catalog`'s missing-file message told the reader
to rebuild from `tools/build_catalog.py`. Whoever sees that message on
an installed copy has no such repository, and their actual problem is
an incomplete install — which is D23 exactly. It now says which
situation they are in.

*Closing tests:* `test_every_closing_citation_names_a_test_that_exists`
in `tests/test_written_record.py`;
`test_every_resource_refusal_reaches_the_client_with_its_remedy` and
`test_an_unreadable_repository_config_refuses_at_the_setup_check` in
`tests/test_setup_gate_completeness.py`.

### D34 — Closed: config, history and baseline writes cannot be redirected (High)

Grok, 2026-08-23, security pass. D18 closed this class for the skill
installer — check the path, then open the name — and paid for
descriptor binding, `O_NOFOLLOW`, and staging plus `os.replace`,
because a hardlink defeats `O_NOFOLLOW` outright. None of that reached
the three writes a normal audit performs.

Reproduced here, independently of the report:

* **S1.** A dangling `maintainability-agent.json` symlink pointing
  outside the repository. `setup_pending` reads `True` (`is_file()` is
  false on a dangling link), and `apply_answers` then writes 205 bytes
  of configuration *through* the link. The repository path remains a
  symlink. `_first_run._persist` shares the primitive, and reconfigure
  re-enters the same function.
* **S2.** `.maintainability/history.jsonl` hardlinked to a file
  outside the repository. `repository_path` accepts it — resolution
  and `is_relative_to` bound the *name*, never the inode — and
  `append_scan` appends onto the outside file.
* **S6.** `write_baseline=True` with `baseline_path="README.md"`
  truncates source. The MCP description and `docs/architecture.md`
  both promise five artifacts and "never source"; the boundary check
  is only "inside the granted root", and the model supplies that
  argument on the primary surface.

Every write into an audited tree now goes through `_safe_write`,
which refuses a symlink at the name *before* resolving it — asking the
resolved path is useless, since it is always the target — refuses a
symlinked directory anywhere between the root and the file, and stages
into a fresh file that it renames over the name. That last property is
the only one that defeats a hardlink: the existing inode is never
opened, so an outside file keeps its contents and merely stops being
this name. History gave up append mode to get it, which costs a read
of a few kilobytes.

Baseline splits into two questions, because they have different
answers. Redirection is refused by the writer for every caller. Not
overwriting *source* is refused where the path arrives from a model —
`_baseline_workflow` — and a CLI caller keeping baselines outside the
tree is left alone, which was always allowed.

*Closing tests:* `test_setup_refuses_to_write_config_through_a_symlink`,
`test_setup_refuses_a_symlink_pointing_back_inside_the_repository`,
`test_history_append_cannot_reach_a_hardlinked_inode`,
`test_a_first_scan_still_records_normally`,
`test_a_baseline_may_not_overwrite_something_that_is_not_one` and
`test_a_baseline_may_replace_a_baseline` in
`tests/test_write_boundary.py`.

### D35 — Closed: the audited tree cannot enable tool acquisition (High)

Grok, 2026-08-23. `product-intent.md` P1 is explicit that acquisition
is opt-in and that **a user** enables `analyzers.acquire_tools`.
`load_config` is equally explicit that a repository always beats a
person. `_analysis.analyze` then calls
`set_tool_acquisition(bool(settings.get("acquire_tools")))`, so a pull
request that adds four words to a config file causes the host to run
`npx --yes <tool>` — unpinned, honouring the tree's own `.npmrc`.

Two aggravations. The published `maintainability-agent.schema.json`
declares `analyzers` with `additionalProperties: false` and does not
list `acquire_tools` at all, so the contract says the key is illegal
while the runtime honours it — the schema is never loaded. And
`_ACQUIRE_TOOLS` is a process-wide global, so two overlapping audits
on a long-lived MCP can flip it under each other.

License policy already gets this right: deny always wins, and no
repository can override it. Acquisition is the same kind of decision
and did not.

`acquisition_permitted()` reads the XDG user tier alone and never the
merged config, so a repository stating the key is ignored — a
preference the tool declines to act on rather than an attack worth
failing a scan over, since the environment work order already names
every missing tool and how to install it. The key is now declared in
the schema too: `analyzers` is `additionalProperties: false` and did
not list it, so the published contract called it illegal while the
runtime obeyed, and nothing caught the contradiction because the
schema is never loaded.

`test_analyze_honours_the_opt_in` used to set `config["analyzers"]` and
watch the switch flip — it asserted the inversion. It reads the user
tier now.

*Closing tests:* `test_no_configuration_means_no_acquisition`,
`test_the_user_tier_can_enable_acquisition`,
`test_a_repository_cannot_enable_acquisition`,
`test_a_repository_cannot_revoke_a_users_choice` and
`test_the_schema_declares_the_key_the_runtime_reads` in
`tests/test_acquisition_trust.py`; plus
`test_analyze_honours_the_opt_in` in
`tests/test_network_disclosure.py`.

### D36 — Closed: the agent reads inside the grant, wherever the path came from (High)

Grok, 2026-08-23. D20 bounded `paths.history` with `repository_path`
after an audit reproduced an escape. The same class survives in two
fields that were never given the same treatment.

* **S4.** `analyzers.class_dirs` reaches `_target_dirs` as
  `root / relative`, and `Path("/tmp/repo") / "/"` is `/`. Confirmed
  here: a repository config naming `/` yields `/` as a scan target,
  which is also an `rglob("*.class")` over the filesystem on an MCP
  child with no timeout.
* **S9 / Codex 1.** `expand_files` and the built-in scan both use
  `is_file()`, which follows symlinks. Codex proved the sharper half:
  a repository containing `linked.py -> ../outside.py` had that file
  read, measured, and returned in the report — `TOP_SECRET_VALUE = 42`
  inside a findings payload. `expand_files` is worse still, because
  its output becomes analyzer argv.

`iter_files` and `expand_files` now check where a path *lands*, and
`class_dirs` goes through `repository_path` like `paths.history` did
after D20. Symlinks that resolve inside the root stay allowed: they are
ordinary in real trees, and refusing them would quietly shrink the
population a score is computed over.

One thing the falsifier deliberately does not assert: that the name
never appears anywhere in the report. `git_status_short` lists the
symlink as untracked, which is git describing the working tree rather
than this agent reading past its grant.

*Closing tests:* `test_a_symlink_out_of_the_tree_is_never_scanned`,
`test_a_symlink_that_stays_inside_the_tree_is_still_scanned`,
`test_analyzer_argv_never_names_a_file_outside_the_tree` and
`test_class_dirs_from_repository_config_cannot_leave_the_tree` in
`tests/test_read_boundary.py`.

### D37 — Closed: git argv is validated, bounded, and its failures are not data (Medium)

Grok, 2026-08-23. `validate_revspec` refuses leading-dash arguments,
and the MCP tool calls it. The CLI's `--changed-only` and `--backfill`
do not, and neither `changed_paths` nor `_backfill._git` places `--`
before the revspec: `changed_paths(repo, "--output=<path>")` creates
that file. Option injection, not shell injection — there is no
`shell=True` anywhere in `src/`.

Beside it, and arguably worse for the product's own claims: `run_git`
swallows every failure as `except Exception: return ""`, so a failed
shallow-clone check reads as "not shallow" and a failed `git log`
becomes `files_changed: 0`. `history.py` states that "no history" and
"no changes" must never be confused, and this is the code path that
confuses them. Neither git spawner sets a timeout, and an inherited
`GIT_DIR` overrides both `cwd` and `-C`.

**Closed 2026-08-25.** Four faults in one entry, and the fix for each
is placed where a fifth caller cannot miss it.

*The revspec.* One definition now, `git_tools.validate_revspec`, lifted
from the MCP door rather than written a second time — the first draft
of a fresh pattern admitted `-rf`, because putting `-` in a character
class allows it in the first position too. `changed_paths` and
`commits_in_range` validate before git sees anything, so the CLI door
inherits the guard rather than being told to remember it, and both
append `--`. Validation rather than `--end-of-options`, which needs git
2.24 and would make the guarantee depend on the host's git.

*Failure is not emptiness.* `run_git` raised nothing and answered every
error with `""`, so a failed `git log` reached `_commits` as no commits
and was published as `files_changed: 0` — the precise confusion
`has_history` was written to prevent, created by the spawner beneath
it. `run_git` now raises. The two calls where a non-zero exit **is** the
answer — "is this a repository at all" — use `probe_git`, which says so
at the call site, and the report's own git metadata probes too because
a directory that is not a repository is a supported audit target.
Making the strict case the default is the point: tolerating failure is
now something a reader can see.

*Bounded and bound.* Both spawners pass a timeout, and both scrub
`GIT_DIR` and its seven siblings, which outrank `cwd` and `-C` — an
inherited value silently redirected every command here, including the
worktree writes in `_backfill`.

The last two are held by a sweep over the package rather than by
assertions about the two spawners that exist today. That is deliberate:
this defect class was closed at the MCP door and left open at the CLI,
which is the mistake the register keeps recording.

**Audited by Codex and Grok independently, and three residues closed in
the same entry.** Both rounds on 0bc2b57 found the same thing from
different directions: the fix had been applied to the sites this entry
named and not to the class.

- `has_history`'s third probe still read a *failed* shallow check as
  "not shallow" — `probe_git(...) != "true"` — so a git that cannot
  answer the question reported complete history. That is the sentence
  D37 opened with, still implemented three lines below the two probes
  that were fixed. It now fails closed: only an explicit `"false"`
  establishes completeness.
- `rename_map` probed its diff, so a timeout or an unreadable object
  became "no renames" and a `git mv` surfaced every moved finding as
  new — the ADR 009 hole, produced by the spawner. The two legitimate
  empty cases (a commit git no longer has, equal commits) are
  established by probing for the commits first; the diff itself is
  strict.
- The `require_clean_worktree` gate read a failed `git status` as an
  empty one, so a plain directory satisfied it. `worktree_status`
  returns `None` for "not a worktree", which the gate now fails on
  rather than passing.

**And the sweep was syntactic, not structural.** It matched only
`subprocess.*` calls whose first argument was a list *literal*
beginning with `"git"`; a spawn built from a variable, a tuple, a
concatenation or a module constant evaded it while the test stayed
green and this entry claimed a new git call would fail there. Deciding
which spawns are git is undecidable, so it stopped trying: every
subprocess spawn in the package is now classified, and the analyzer
child is named in `ENV_EXEMPT` with its reason rather than silently
unchecked.

*Closing tests:* `test_an_option_shaped_revspec_never_reaches_git`,
`test_a_failed_git_command_is_not_an_empty_answer`,
`test_a_repository_is_read_through_its_own_path_not_an_inherited_one`,
`test_every_subprocess_spawn_is_bounded_and_classified`,
`test_an_unborn_head_reports_absence_not_quiet_history`,
`test_a_shallow_clone_reports_absence`,
`test_an_unanswerable_shallow_check_withholds_rather_than_claims` and
`test_a_rename_is_read_from_git_and_a_failure_is_not_no_renames` in
`tests/test_git_argv.py`.

### D38 — Closed: a standing grant authorizes what the question named (Medium)

Grok, 2026-08-23. `persist_root_grant` stores the resolved path as a
string; `allowed_roots()` resolves it again at process start.
Elicitation refuses a symlink retarget in-process, and a restart does
not: rename the granted directory, leave a symlink at the old name
pointing somewhere sensitive, and the allow-list follows it with no
new consent.

**Closed 2026-08-25, reproduced first.** Granting `project`, renaming
it away and leaving a symlink at the old name put `secrets` in the
allow-list on the next start, with no question asked.

The in-process seam was already right, which is what makes this a
missed sibling rather than a new idea: `_RootLedger.consume_ask`
surrenders the path the user was actually shown, so a link retargeted
during the elicitation round-trip cannot swap the consented directory
(the TOCTOU found on 6b2fb76). A restart went around it, because the
allow-list was rebuilt from strings and re-resolved. Same rule, applied
where the strings are read: a persisted grant is honoured only while it
still resolves to itself, which a path that has acquired a symlink no
longer does.

Fails closed, and a dropped grant is not an error — the user is asked
again the next time that root is used, which is the point. A granted
directory that was simply deleted keeps its entry and audits nothing,
because there is no directory there to audit.

**Reopened and re-closed 2026-08-26.** The predicate that closed this
was the inverse defect. It honoured a stored grant only when the path
contained no symlink in any component — which on macOS is the ordinary
spelling of `/tmp`, `/var` and every `tempfile` directory. Grok
reproduced it: a grant recorded as `/tmp/work` was dropped on every
start, so someone who said "always" was asked again forever.

The closing test could not see it. It called `tmp_path.resolve()`
before storing, so it only ever exercised a path that was already
canonical.

Grants persist resolved now. A canonical entry is honoured only while
it still resolves to itself, which is the original guard; an entry that
is not canonical — hand-written, or written before this change — is
honoured unless the granted path is itself a link, which is the swap
that was demonstrated. A component *above* it being replaced is a
residual the weaker rule does not catch, and is why new grants are
stored resolved.

**And the falsifier for the reopen failed CI on its first run.** It
asserted that `/tmp` is a symlink, which is true on macOS and false on
Linux, so it hard-failed on the platform it was meant to protect
instead of skipping there. Every local full-suite run had been green,
because every local run was on one platform: a platform fact asserted
rather than constructed is invisible to a single-machine regression
check, and this project's own discipline of diffing the whole suite
against a baseline cannot see it either.

The test builds its own symlinked parent now — a real directory, a link
to it, and a grant underneath the link — so it exercises the case on
every platform rather than skipping where the platform does not
volunteer one.

**Reopened and re-closed a second time, 2026-08-26.** The rule above —
honour a non-canonical entry unless the granted path is itself a link —
names its own residual in the paragraph that states it: *"a component
above it being replaced is a residual the weaker rule does not catch."*
Grok walked through exactly that. Retarget the *parent* of a stored
grant, one directory above the leaf the rule checked, and the
allow-list follows it on the next start.

There is no third rule. A bare path with no record of what it resolved
to when it was granted cannot be defended: nothing to compare against
means nothing to detect, and each attempt to defend it moved the hole
one directory up rather than closing it.

So: canonical or refused. The product persists resolved paths, which
are checkable, and a hand-written entry that is not canonical is
refused. Refused *aloud* — `server_info` now carries
`refused_root_grants`, each with the reason and the canonical spelling
to write instead, because dropping grants in silence is what made the
first version of this rule invisible for two days.

*Closing tests:* `test_a_standing_grant_does_not_follow_a_renamed_directory`,
`test_a_non_canonical_grant_is_refused_and_said_so` and
`test_a_grant_the_product_made_is_canonical_and_survives` in
`tests/test_grant_only_user_tier.py`.

### D39 — Closed: the audit takes no configuration from the tree it audits (Medium)

Grok, 2026-08-23, filed as a disclosure defect rather than a fix.
`eslint` runs with no `--no-eslintrc`, and `has_config` *requires* a
project config before running, so an audit of an allowed root executes
`eslint.config.js` from the tree under audit; mypy runs without
`--no-plugins`. Children inherit the host environment.

Child sandboxing is refused as a design direction and this entry does
not reopen it. What it recorded originally is that P1 discloses
"children are not network-sandboxed" and does not disclose "we execute
configuration code from the tree under audit".

**Reclassified 2026-08-25 from accepted residual to defect.** It was
filed as a disclosure gap because the alternative looked like a
sandbox, and the entry offered "disclosure, then optionally the flags"
as its closing test. [Decision 9](decisions.md) removes the option:
the agent does not execute the audited tree's code, and configuration
is code. `SECURITY.md` already said as much, so the promise was never
the thing that was wrong — this is the code drifting from a published
claim, which is a defect by this project's own closure rules and not
something disclosure can settle.

Scope shrank with [Decision 10](decisions.md). `eslint` is the analyzer
that *requires* the tree's flat config, and JavaScript is not a v1.0
language, so it leaves the default pool rather than gaining a flag.
What stays in scope is Python: mypy and pylint may load configured
plugins and must run with that disabled. The fix is therefore two
narrow changes plus a falsifier, not the sandbox this entry was afraid
of.

**Two thirds closed 2026-08-25; the entry stays Open for the third.**

*The environment.* `_runner` spawned every analyzer with the inherited
environment, so `PYTHONPATH`, `NODE_PATH`, `NODE_OPTIONS`,
`PYTHONSTARTUP` and the `LD_`/`DYLD_` pair could choose what the tool
loads. `analyzer_env()` removes them and keeps `PATH`, because the tool
still has to be found. Not a sandbox and not claimed as one — the
narrower guarantee Decision 9 actually makes.

*eslint.* It cannot run without the tree's flat config, and a flat
config is a JavaScript program. `EslintAdapter` now declares
`executes_audited_configuration`, and selection refuses any adapter
that does — a property rather than a slug check, so the next tool
needing the tree's own config is refused without anyone remembering
this entry. Refusal is its own coverage outcome: reporting it as
`no-adapter` told the reader to write an adapter that already exists.
The work order also stopped naming eslint as an install that would
close a JavaScript gap; following that remedy would have closed
nothing.

*mypy and pylint.* Both run through `DECLARED` in `_generic`, both
read the tree's configuration, and pylint's `init-hook=` executes
arbitrary Python at startup. They are spawned with `--config-file` and
`--rcfile` pointed at `os.devnull`, which stops the search that honours
`plugins =`, `load-plugins=` and `init-hook=`.

This entry stalled for a while on the wrong question. Neither tool is
installed on this machine, so the flags could not be demonstrated here,
and the proposal was to add them as dev dependencies to make CI prove
them. Marshall rejected the premise: analyzers are **runtime
prerequisites the user supplies**, never dependencies of this package —
`analyzer-pool.md` says so, and making one a dependency would
contradict the pool's whole design. The absence was a machine that had
changed, not an architecture.

The pattern the pool already discloses is the answer.
Checkstyle and SpotBugs sit in their tiers with live spawns that skip
wherever nobody supplied the binary, including CI. The isolation flags
follow it: a structural sweep that always runs and forces every
declared tool to be isolated or to state it reads no tree
configuration, and live tests that plant a hostile `pylintrc` and
`mypy.ini` and assert the tree's code never runs — skipped where the
tool is absent. On a machine with pylint and mypy installed, that is
demonstration; here it is documentation plus an asserted argv, and the
disclosure says which.

*Closing tests:* `test_every_declared_tool_is_classified_for_tree_configuration`,
`test_a_declared_tool_is_invoked_with_its_configuration_isolated`,
`test_no_selectable_adapter_needs_the_audited_trees_configuration`,
`test_pylint_does_not_run_the_trees_init_hook` and
`test_mypy_does_not_load_a_plugin_from_the_tree` in
`tests/test_analyzer_config_isolation.py`;
`test_the_analyzer_child_cannot_be_told_what_to_import` in
`tests/test_git_argv.py`. The last two of the first group skip where
the binary is absent, which `analyzer-pool.md` discloses.

### D40 — Closed: a repository's regex cannot hang the host (High)

Codex, 2026-08-23, proven. `risk_patterns` are compiled from repository
configuration and applied to every source line. The schema bounds
neither their complexity nor their size. Pattern `(a+)+$` against
thirty-one `a` characters and a `!` did not finish in two seconds.

The security policy names crafted-configuration denial of service as in
scope, so this was a defect against a stated promise rather than a new
requirement.

Patterns are measured rather than inspected. Recognising a dangerous
regex syntactically means a blocklist that is both leaky and prone to
refusing honest patterns; running it against a probe asks the only
question that matters. The probe has to be short enough to *return* —
timing something that never finishes measures nothing — so there are
two: twenty characters, where `(a+)+$` costs ~42 ms against ~0.01 ms
for a real pattern, and twenty-four, which is where the slower
`(a|aa)+$` family finally shows itself at ~9.7 ms. Only patterns that
survive the first reach the second, so a bomb costs the sum of two
small budgets rather than the near-second its own longer search takes.

A refused pattern is skipped, not fatal: a repository's own lint config
should not be able to fail somebody else's audit, and the other rules
keep running.

*Closing tests:* `test_a_backtracking_pattern_is_refused` across four
shapes of catastrophic backtracking,
`test_an_uncompilable_pattern_is_refused_rather_than_raised`,
`test_every_shipped_pattern_survives_the_budget` — the guard must not
quietly disarm the product's own detectors —
`test_a_hostile_pattern_does_not_stall_a_scan` with the clock running
through the real scanning path, and
`test_a_refused_pattern_does_not_silence_the_others`, all in
`tests/test_pattern_budget.py`.

### D41 — Closed: every action is pinned to a commit (High)

Codex, 2026-08-23, proven. Every workflow action is referenced by tag
or branch. `release.yml` hands OIDC publication authority — `id-token:
write` — to `pypa/gh-action-pypi-publish@release/v1`, a moved-branch
reference rather than an immutable commit. Checkout, setup-python,
uploads, the CodeQL upload, GitHub Script and Sonar are the same.

Whoever controls those references at run time runs in the job that can
publish this package.

Twenty references across three workflows and the composite action are
now commit SHAs, each with its version as a trailing comment so a
reader can still tell what is pinned. This repository's own action
stays on `@main` on purpose: pinning it would mean CI could never
exercise the commit under review.

*Closing tests:* `test_every_third_party_action_is_pinned_to_a_commit`,
parametrized over every workflow file, and
`test_the_publishing_job_is_pinned_hardest_of_all` in
`tests/test_workflow_supply_chain.py`. The second is deliberately
redundant with the first: a general rule is easy to relax for one
awkward case, and the publish job is the case nobody should relax it
for.

### D42 — Closed: the package claims a Python it can run on (Medium)

Codex, 2026-08-23. `requires-python = ">=3.10"`, and `_discovery.py`,
`_pillars.py` and `_runner.py` import `enum.StrEnum`, which is 3.11.
Pip installed happily on 3.10 and the import then failed. CI tests
3.12 alone, and the composite action pins 3.11, so nothing in the
pipeline stood where the metadata said a user could stand — which is
why no test caught it and an audit had to. Floor raised to 3.11, and
the supported versions declared as classifiers.

I first recorded that no honest falsifier existed here, on the grounds
that any such test would restate a constant. The register's own
citation lint disagreed — it refuses a closed entry that names no
test — and it was right. The check does not restate the floor; it ties
the floor to the language features actually imported, which is the
relationship that broke.

Its first version matched the bare word anywhere and flagged
`_economics.py` for the English "override" in a docstring. A check that
cries wolf is a check somebody turns off, so it reads import and
decorator lines only.

*Closing test:* `test_the_declared_python_floor_supports_the_features_in_use`
in `tests/test_written_record.py`, verified by lowering the floor back
to 3.10 and watching it name `_discovery.py` and `StrEnum`. A CI matrix
entry on the floor version is still worth having and stays recorded as
follow-up in `docs/security-queue.md`.

### D43 — Closed: composite-action inputs are data, not source (Medium)

Codex, 2026-08-23, proven. `action.yml` embedded `${{ inputs.* }}`
directly inside a `run:` script. GitHub substitutes those *before* bash
parses the script, so an input was never an argument — it was source
code, and a path containing a shell metacharacter was enough to break a
run by accident.

Inputs arrive through `env:` now and are appended to the argument array
quoted, which keeps each one a single word however it is spelled.

*Closing tests:* `test_the_composite_action_never_interpolates_inputs_into_bash`
and `test_the_composite_action_still_passes_every_input_through` in
`tests/test_workflow_supply_chain.py`. The second exists because moving
inputs to `env:` is exactly the kind of edit that silently drops one,
and a lost `--changed-only` would look like a passing test while
auditing the whole repository on every pull request.

Both are parsed by hand rather than with PyYAML: this repository keeps
its `test` extra thin and `test_declared_imports` refuses a dev-only
parser in tests. I added PyYAML anyway, that lint caught it, and the
parser was rewritten.

### D44 — Closed: the annotations are derived from the behaviour (Medium)

Codex, 2026-08-23. The audit tool declares itself non-destructive and
closed-world, and `tests/test_mcp_server.py` locks both values. Neither
survives optional network acquisition, unsandboxed analyzer networking,
executable repository analyzer configuration, or the config, history
and baseline writes.

Test-backed misinformation is worse than an untested claim: the suite
is the reason nobody re-examined it.

~~**Blocked on the trust decision**~~ — unblocked by
[Decision 9](decisions.md), which answered it by drawing the line at
executing code instead.

**Closed 2026-08-25.** `audit_repository` now advertises
`destructive_hint=True` and `open_world_hint=True`. It replaces an
existing configuration when setup reruns and an existing baseline when
asked to write one — non-additive updates to files in the user's
repository, which is what the destructive hint means. That only the
agent's own five artifacts are ever touched (D34) is a real guarantee
and a different claim from "additive". And it is not closed-world:
`analyzers.acquire_tools` can fetch a missing Node tool through
`npx --yes`, and analyzers are ordinary local children this package
does not sandbox, which P1 discloses in as many words. `get_agent_info`
was accurate and is unchanged.

Decision 9 removed exactly one of the four reasons this entry gave —
the tree's own analyzer configuration no longer executes (D39). It did
not make the tool closed-world, and the other three stood.

**The lesson is the lock, not the values.** Two tests asserted
non-destructive and closed-world for *every* tool, and a third
statement sat in `ide-agent-integration.md`. Changing the literals
would have left the same defect available, so the falsifiers derive
each hint from a fact stated elsewhere in the package: the hint must
follow `server_info`'s list of what this agent writes, and follow the
existence of the acquisition setting. Changing the behaviour without
changing the hint now fails.

*Closing tests:* `test_a_tool_that_writes_is_not_advertised_as_read_only`,
`test_replacing_a_file_a_user_owns_is_advertised_as_destructive`,
`test_a_tool_that_can_reach_the_network_is_not_advertised_as_closed_world`
and `test_the_read_only_tool_is_still_read_only` in
`tests/test_annotations_match_behaviour.py`.

### D45 — Closed: the security policy supports the shipped release (Medium)

Codex, 2026-08-23. `SECURITY.md` stated that only `0.1.x` receives
security fixes, at version `0.9.1` — read literally, the shipped
release was unsupported by its own policy.

Fixing the table is trivial; keeping it fixed is the problem, since
nobody remembers a version number buried in prose. The falsifier reads
`config.VERSION`, so the next release either updates the table or goes
red.

The same pass corrected a worse sentence in the same file. Scope
asserted that the agent "does not execute scanned code" while `eslint`
is invoked in a mode that *requires* the audited repository's own
configuration and then runs it. Whether repositories should be trusted
is an open decision (D39, D44); asserting a property the code does not
have is not, so Scope now describes what the code does and says the
decision is pending.

*Closing tests:* `test_the_security_policy_supports_the_shipped_release_line`
and `test_the_security_policy_states_the_guarantee_the_code_keeps`
in `tests/test_written_record.py`. The second checks only what the
document *asserts*, not what it recounts — a check that could not tell
an assertion from its own correction would forbid explaining the fix.

### D46 — Closed: an analyzer cannot decide how much work reading it is (Low)

Codex, 2026-08-23, inferred rather than demonstrated. `_generic.py` and
`_jvm_adapters.py` parse analyzer XML with `ElementTree.fromstring`.
The input is a child process this agent spawned, not an upload, so the
realistic exposure is resource exhaustion from a hostile or
PATH-hijacked analyzer rather than classic XXE.

**Closed 2026-08-25, and it stopped being inferred.** The hedge was
right about XXE and wrong about the risk: external entity expansion and
DTD retrieval are already safe in this interpreter, which is what
"XXE" usually names. What `ElementTree` still does is expand *internal*
entities — four levels of the standard shape take a 400-byte document
to 30,000 characters here, and each further level multiplies by ten.

The obvious fix is to disable expat's entity handler, and CPython 3.11
does not expose the underlying parser to reach it. The narrower guard
is better anyway: no analyzer this project runs emits a DTD, so a
document declaring entities is not output this code should be reading.
`_xml.parse_analyzer_xml` refuses it before a parser sees it, and
refuses absurd length as well — the flood case a declaration check
cannot catch, because a bomb is small by construction.

`AnalyzerXmlRefused` subclasses `ElementTree.ParseError` so that both
call sites keep the handling they already had: unreadable analyzer
output is a stated coverage gap, never a crash. Output this project
declines to read is exactly that.

The sweep is the part that matters. `ElementTree.fromstring` now
appears once in the package, inside the guard, and a test walks every
module to keep it that way — a third parse site added tomorrow is how
this would otherwise come back.

*Closing tests:* `test_an_entity_bomb_is_refused_before_it_is_expanded`,
`test_a_declared_doctype_is_refused_even_without_entities`,
`test_absurdly_large_output_is_refused_rather_than_read`,
`test_real_analyzer_output_still_parses`,
`test_a_refusal_reads_as_unparseable_output_to_every_caller` and
`test_no_parse_site_bypasses_the_guard` in
`tests/test_analyzer_xml_bounds.py`.
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

**What proves "declared" is not the same on the two seams, and this
paragraph twice said it was.** The first draft asserted only that the
caller's message is not the SDK's generic crash string. On `mcp` 2.0.0
that is true of the *tool* whether or not the refusal was declared,
because 2.0.0 interpolates crash text there — so the draft passed with
`StaleBaseline` deleted from the tuple. The two tool tests were rewritten
to call the coroutine `_bind_audit_tool` registers, skipping the SDK
entirely: `ToolError` with the domain type as `__cause__` is our own
translation and holds on any 2.x.

The correction was then overapplied to the resource, and an audit of
this entry caught that too. The resource test goes through
`read_resource`, and undeclaring `SetupRequired` there produces a
`ResourceError` whose `__cause__` is still `SetupRequired` — the SDK
wraps the escaping exception and chains it — so neither the class nor
the cause separates a refusal from a crash. Two assertions do, on
different versions: on 2.1.0 the wrapper is the narrower
`UnexpectedResourceError`, a `ResourceError` subclass, and the test
excludes it; on 2.0.0 no such class exists and the wrapper's message
replaces the refusal's own, so text is the discriminator. Text is
load-bearing on that seam, which is the opposite of what this paragraph
claimed while the two tool tests were being praised for avoiding it.

**Which text, and a third correction.** The audit of `790a47e` as
landed found that the 2.0.0 check was looking for the wrong string.
It searched for `audit_repository` — D30's requirement that a refusal
name the door that can ask — but the 2.0.0 wrapper interpolates the
URI, the URI carries the repository path, and a repository directory
*named* `audit_repository` puts that substring into a crash message.
Reproduced against this tree: a crash satisfied the assertion whose
job is catching crashes. Narrow, and the fixture did not hit it, so
nothing was passing falsely in the suite.

Closed by making the case impossible to lose rather than by recording
it: the fixture now builds its repository under a directory called
`audit_repository`, and the discriminator is `has not been set up`, a
fragment of D30's own sentence that a URI cannot contain. Weakening
the assertion back to the door-name substring now fails the build. The
door-naming check remains, separately, because it is D30's actual
requirement — it was never a crash discriminator and is no longer
asked to be one.

That is three rounds finding three defects in this entry's own
falsifiers, each a claim that the test proved something slightly
larger than it did. The lesson recorded here is not about `mcp`: a
falsifier that shares a vocabulary with the thing it tests can be
satisfied by the failure it exists to catch.

Each of the three was verified by deleting its type from the tuple and
watching its own test fail.

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

### D50 — Closed: the economics ask stops at the question it gates (High)

Marshall, 2026-08-25, during UAT preparation: *"if the user declines
economics, should never ask the labor rate questions. that is basic
logic."*

`_economics_questions` returned the gate **and** all three labor rates
in one flat elicitation model, and the gate's default is `skip`. So the
default path walked a person through three money questions for
something they had just declined. The function's own docstring called
it "the declinable ADR 004 ask" while nothing about it was declinable.

Two stages now: six questions, then the three rates only for someone
who answered `include`. `setup_pending` stays true until the rates
arrive, so the second ask is the existing gate doing its job rather
than a new mechanism.

**Codex had examined this surface and filed it under no-finding**,
citing `docs/help/first-run.md` — which stated plainly that the labor
fields remain visible after `skip`. The page was accurate. D28 had made
it accurate, and accuracy about a bad form is what kept the form. An
audit that checks code against documentation cannot catch a defect both
of them share.

*Closing tests:* `test_setup_questions_are_structured_choices_with_disclosed_defaults`
and `test_apply_answers_persists_economics_and_format_to_both_tiers` in
`tests/test_first_run_elicitation.py`;
`test_the_first_run_help_describes_the_form_a_person_actually_sees` in
`tests/test_written_record.py`.

### D51 — Closed: asking for the economic scenario is not the same as declining it (High)

Found while closing D50. `_economics_block` needs all three rates and
returned `None` without them — the same value as declining — so a user
who answered `include` in a round that carried no rates had no economic
context written and was never asked again. The one thing they said yes
to was the one thing silently discarded.

The gate answer is recorded as a request now, and
`economics_bounds_pending` reads it to ask for the rates on the next
call.

*Closing test:* `test_apply_answers_persists_economics_and_format_to_both_tiers`
in `tests/test_first_run_elicitation.py`.

### D52 — Closed: a labor rate is refused where it is answered (High)

Codex, 2026-08-25. Setup accepted `labor_low=-1` and wrote both
configuration tiers happily; the next `action="run"` raised a raw
`ValueError: loaded_engineering_cost_per_hour must satisfy 0 < low <=
base <= high` from the scoring path. Same for `low > base`. The person
who typed the number was two calls and one document away from the
message about it.

The rule is checked where the answer is given, and the refusal names
the three values it got.

*Closing test:* `test_apply_answers_persists_economics_and_format_to_both_tiers`
in `tests/test_first_run_elicitation.py`.

### D53 — Closed: a configuration key of the wrong shape is refused, not crashed on (High)

Codex, 2026-08-25. `_configured` validated JSON syntax and an object
root, then merged whatever it found. `{"thresholds": "nope"}` surfaced
as a raw `TypeError: string indices must be integers` from inside
scoring, and `{"hard_gates": []}` as an `AttributeError` on a list —
two stack traces for one broken file, neither naming the file.

`ConfigUnreadable` already existed for exactly this reader and covered
only unparseable bytes. It now covers a known key whose value is the
wrong container, derived from `DEFAULT_CONFIG` so a key added there is
checked the day it is added. Unknown keys stay permitted: this is a
shape check, not a schema, and refusing what it does not recognise
would break every config written against a newer version.

*Closing test:* `test_a_known_key_of_the_wrong_shape_is_refused_by_name`
in `tests/test_config_shape.py`.

### D54 — Closed: `expected_files` names files in the repository (Medium)

Codex, 2026-08-25. `paths.history` was bounded by D20 and this was
not, so a repository config could say `/etc/passwd` or `../outside`
and the report would state whether that existed — a repository-
controlled probe of the machine auditing it, answered in the output.
Absolute entries and entries containing `..` are refused by name.

*Closing test:* `test_expected_files_cannot_leave_the_repository`
in `tests/test_config_shape.py`.

### D55 — Closed: the documents stop offering a tool the product refuses (Medium)

Codex, 2026-08-25, and both halves are mine. `analyzer-pool.md` still
listed eslint as a Node runtime need, as fetchable through `npx`, and
as a verified moderate adapter — three offers to install a tool D39
had just made unrunnable. The D39 change corrected the prose two
paragraphs above and left the tables.

`maintainability-agent.schema.json` also described
`prompt_when_interactive` as "Reserved. Stored and not read." while
`_first_run` reads it, so an IDE user consulting the schema was told a
live switch does nothing.

*Closing test:* `test_no_document_offers_an_analyzer_selection_refuses`
in `tests/test_config_shape.py`.

### D56 — Closed: an empty history window is unknown, not perfect (High)

Grok, 2026-08-26. `_history_rate_aspect` returned **5.0** for
`files_changed == 0`, commented "had history to read; nothing changed
in the window". A repository whose only commit predates the twelve
month window therefore scored full marks on every history aspect —
with a filthy working tree the photograph could see and the window
could not. Reproduced on a real repository: one commit dated 400 days
ago, an untracked file with eighty nested conditionals, history rates
5.0.

Worse in the direction P3 names. Withholding the history object
*lowers* the result (estimate 4.80, no verified grade). Supplying an
empty window *raises* it to 5.00 and A+. Evidence that says nothing
outscored evidence that was absent.

This is D37's collapse one layer up. There, a *failed* `git log`
produced zeros and the zeros read as quiet; the fix made the spawner
raise. Here the log succeeds and produces the same zeros honestly, and
they mean the same thing: no denominator, therefore no rate. A shallow
clone and an empty window are the same state, and the docstring above
this function already said a shallow clone must not grade as clean or
dirty.

*Closing test:* `test_an_empty_window_is_unknown_rather_than_perfect`
in `tests/test_history_window.py`.

### D57 — Closed: the documented languages and the parsed languages are one set (High)

Grok, 2026-08-26. `docs/language-support.md` and Decision 10 said v1.0
handles Python and Java. The scanner also read JS, TS, JSX and HTML, so
a repository of 140 JavaScript files was reported with
`declarations_scanned=140`, `evidence_status: complete` and a verified
**B**, and the Markdown scored `declaration size`.

The first two attempts at this were both wrong and are recorded because
the sequence is the lesson. Narrowing only the sentence left the
contradiction the audit had already named. Narrowing the parser to
`{.py, .java}` removed JavaScript dead-code detection, idiom
divergence, near-duplicate pairing and ADR 003's TypeScript work — and
Marshall's question, *"if you don't have detectors, linters, etc for
those languages and no adaptor then please explain how option C is
valuable at all?"*, is what produced the check that should have come
first: **lizard, jscpd and multimetric are baseline-tier adapters that
read JavaScript**, and baseline in this project means installed, run
and parsed. Only eslint is refused, and only for its config.

So the claim follows the capability. The declaration languages are
Python, Java, JS, TS, JSX and HTML, the page says so, and the
one-adapter-per-release cadence applies to what nothing here reads —
Go, Rust, C, C# and Fortran, absent from the default extensions rather
than scanned and unscored.

*Closing tests:* `test_the_parsed_languages_are_exactly_the_documented_languages`
and `test_every_scanned_source_suffix_can_be_read_by_something` in
`tests/test_claimed_languages.py`.

### D58 — Closed: the generated standards pack teaches call-first (High)

Grok, 2026-08-26. `--init-agent-standards` writes `AGENTS.md`,
`CLAUDE.md` and their siblings, and every one of them opened with
"Start with a configuration check (`maintainability-agent.json`, then
the user tier)" — the archaeology D21 exists to stop, shipped into the
file an agent reads before anything else.

D47 closed that class by enumerating three surfaces: the MCP server
instructions, the slash prompt, and the skill. This is the fourth, and
D47's own write-up of D21 says what went wrong here: a falsifier that
read one file and called the class closed.

Worse, the two closed entries contradicted each other. D17's closing
test **required** the generated pack to contain "configuration" and
"check", so honouring D21 there would have failed the suite. Both were
green, and neither could see the other.

The pack now carries D21's wording verbatim, D47's sweep runs over four
surfaces, and D17's assertion asks for the call instead of the check.

*Closing test:* `test_every_chat_instruction_surface_calls_the_tool_before_inspecting_config`
in `tests/test_chat_primary_docs.py`.

### D59 — Closed: the sweeps lint the class, not a name (High)

Grok, 2026-08-26, three of them together.

*The isolation sweep covered two tools.* It diffed `DECLARED` — pylint
and mypy — while `ADAPTERS` holds fifteen, so ruff sat in the baseline
pool, in the default selection, never asked the question the sweep
exists to ask. Every adapter is now classified by what honouring its
configuration would *execute*, which is the actual line Decision 9
draws: a ruff or flake8 config is TOML and INI, and a repository
choosing which of its own lint rules apply is policy about its own
code. The flag check also asserted only that `--rcfile=` was present,
so `--rcfile=.pylintrc` would have passed; it asserts the value now.

*The subprocess sweep matched `subprocess.<call>`.* `import subprocess
as sp`, `from subprocess import run`, `subprocess.call` and
`getoutput` all evaded it, and `timeout=None` counted as bounded
because presence was the test. It resolves aliases and from-imports
now, and treats an explicit `None` as unbounded.

*The XML sweep had the same shape*, matching `ElementTree.fromstring`
by name, so a from-import walked past it.

This is the third generation of these checks. The first git sweep
matched only list literals beginning with `"git"`; that was replaced
after an audit, and the replacement was narrow in a different way. What
they have in common is that each was written to catch "a call added
tomorrow" and each matched a spelling instead.

*Closing tests:* `test_every_adapter_is_classified_for_what_its_configuration_executes`
and `test_an_adapter_whose_config_executes_code_is_refused_not_isolated`
in `tests/test_analyzer_config_isolation.py`;
`test_every_subprocess_spawn_is_bounded_and_classified` in
`tests/test_git_argv.py`; `test_no_parse_site_bypasses_the_guard` in
`tests/test_analyzer_xml_bounds.py`.

### D60 — Closed: SECURITY.md states the guarantee the code keeps (Medium)

Grok, 2026-08-26. Decision 9 closed D39 and D44 on 2026-08-25 and
`SECURITY.md` kept describing the defect for a further day: that the
agent executes repository code, that mypy and pylint can load
configured plugins, that children inherit the host environment, and
that the question is open.

**Wrong in both directions now.** The file first denied executing
scanned code while eslint was being invoked in a mode that requires the
tree's configuration and then runs it (Codex, 2026-08-23). It was
corrected to assert the opposite. Then the code changed under it.

Both directions are recorded rather than quietly rewritten, and the
test no longer forbids a sentence: it reads the policy against the
adapters, and fails if the file and the code disagree either way. A
test that asserts a phrase protects the phrase, not the property —
which is the third time that shape has come up today.

*Closing test:* `test_the_security_policy_states_the_guarantee_the_code_keeps`
in `tests/test_written_record.py`.

### D61 — Closed: P1 names the fields that are not compared (Low)

Grok, 2026-08-26. P1 promised "same report out" and two runs on one
tree differed by a millisecond, on an analyzer's wall-clock `seconds`.
The determinism check had been stripping `root`, `git_status_short`
and every `seconds` for as long as it had existed, so the promise was
false of the JSON a consumer diffs and true only of the test's own
projection.

The exceptions are legitimate — a duration is a fact about the run, not
about the repository. Being undisclosed was not. P1 names them, and a
field added to the strip list without reaching the page now fails.

*Closing test:* `test_the_determinism_exceptions_are_exactly_the_disclosed_ones`
in `tests/test_determinism.py`.

### D62 — Closed: the release plan is measured, not remembered (Low)

Grok, 2026-08-26. The plan's own warning is that a previous version of
its table "survived fifty-five commits past the point it stopped being
true". It then did it again: last tag 0.7.0 with v0.9.1 shipped, 14,122
lines against 20,071, 1,097 tests against 1,560. Re-measured, and the
warning now records both occurrences.

The first draft of this entry closed with "*Closing test:* none",
arguing that a measurement goes stale by existing. The register does
not allow that, and it is right not to: the tag is exact and the counts
are checkable within a stated tolerance, wide enough to survive
ordinary work and narrow enough that another fifty-five commits cannot
hide inside it.

*Closing test:* `test_the_release_plan_table_is_measured_not_remembered`
in `tests/test_release_plan.py`.

### D63 — Closed: the platform is claimed where it is demonstrated (Medium)

Marshall, 2026-08-26: *"what about the poor windows users?"* — asked
about a test of mine that had just failed CI for asserting `/tmp` is a
symlink. The answer was larger than the test.

`pyproject` named no operating system at all. CI runs `ubuntu-latest`
and nothing else. Seven test files create symlinks with no platform
guard, and `os.symlink` needs Developer Mode on Windows, so the suite
cannot reach the point of reporting whether the product works there. A
case-insensitive filesystem would also meet D38's standing-grant check,
which compares a stored path against its resolved form.

Meanwhile two documents implied Windows was supported: `config-schema.md`
said exclude patterns are "normalized across Unix and Windows path
separators", and `ide-agent-integration.md` names the `;` separator.
Normalizing separators is not the same claim as running on the
platform, and a reader takes the friendlier reading.

`Operating System :: POSIX` is declared, both documents say Windows is
untested, and README carries a platform section that states the
evidence rather than a preference. Widening the claim means adding a
`windows-latest` runner and guarding those seven fixtures; the tests
below fail the moment either half moves without the other.

**Fourth in two days.** JS scored without being claimed, `SECURITY.md`
denying what the code did, P1 promising more than it compared, and now
a platform nobody had run. Every one was a claim resting on a check
that only ran where the claim was true.

*Closing tests:* `test_the_package_claims_the_platform_it_is_tested_on`,
`test_ci_runs_only_platforms_the_package_claims` and
`test_the_symlink_fixtures_are_still_unguarded` in
`tests/test_platform_claim.py`.

### D64 — Closed: flake8 reads no configuration from the tree (Medium)

Grok, 2026-08-26. D39 isolated pylint and mypy and swept for the rest,
and the sweep covered two tools out of fifteen. `flake8` reads
`setup.cfg`, `tox.ini` and `.flake8` from the tree under audit, which
sets its own thresholds and select-lists — the score moving with a
config file is exactly what P2 forbids, and Decision 9 forbids reading
the tree's configuration at all.

`--isolated` is passed now. The wider fix is that the classification
stopped being prose: `ADAPTER_CONFIG` carries three states — `REFUSED`,
`ISOLATED:<flag>`, and `DATA_ONLY` — and only the last is a human
judgment, which now has to name the configuration surface it was judged
against. The isolated entries are checked against the argv the adapter
actually builds, so an isolation flag claimed in the table and absent
from the invocation fails.

*Closing tests:* `test_every_adapter_is_classified_for_what_its_configuration_executes`,
`test_an_isolated_adapter_actually_carries_its_flag` and
`test_no_selectable_adapter_needs_the_audited_trees_configuration` in
`tests/test_analyzer_config_isolation.py`.

### D65 — Closed: two ADRs still had eslint running (Low)

Codex, 2026-08-26. Decision 9 refuses eslint outright — an eslint flat
config is a JavaScript program, so honouring it means executing the
audited tree. The adapter declares `executes_audited_configuration` and
selection drops it on every run.

Two ADRs written before that decision still told the reader otherwise.
ADR 006 listed `eslint` in its *Detected* tier, the tools "used when
already on `PATH`", and ADR 008 used eslint as its worked example of a
tool whose threshold the agent sets from the rubric — and offered "or a
generated config" as a way to do it, which is the same forbidden thing
spelled differently. An operator following either page installs a tool
this agent will always refuse.

Both are amended in place rather than rewritten, because the reasoning
around them is still correct about *findings*. ADR 008's escape hatch is
withdrawn: a threshold is rubric-drivable through argv or not at all.

The falsifier sweeps the refused adapters and reads the docs for lines
that claim this agent *runs* a tool, so the next tool refused for the
same reason is caught without being named. The previous review of these
documents forbade exactly one sentence in `SECURITY.md` and missed
everything either side of it.

*Closing test:* `test_no_document_presents_a_refused_analyzer_as_one_this_agent_runs`
in `tests/test_analyzer_config_isolation.py`.

### D66 — Closed: an empty history window says which kind of empty (Medium)

Grok, 2026-08-26, reopening D56 one layer down. D56 established that
`files_changed: 0` is not a measured zero and marked every history rate
not applicable. It then told every reader the same reason: *"no commit
falls inside the history window."*

Three different repositories produce that zero, and the sentence is
false for two of them. Nothing was committed in the window. Or every
commit in it is a merge, dropped by `--no-merges` because a merge's
numstat re-reports churn already counted on the branch. Or commits
landed and touched only files this audit does not scan — a lockfile, a
vendored tree, an excluded directory. Only the first is a quiet window;
the other two are windows this agent *filtered* to empty, and a reader
told the first sentence goes to check their clone depth.

`window_commits` counts both — commits in the window, and commits this
audit will read — with two `rev-list --count` calls that parse nothing.
The evidence reason and the rendered sentence are chosen from those
counts, and both fall back to the original wording for a report written
before the counts existed.

*Closing tests:* `test_a_merge_only_window_is_not_reported_as_a_quiet_one`,
`test_a_window_filtered_to_empty_says_so` and
`test_a_genuinely_empty_window_still_reads_as_empty` in
`tests/test_history_window.py`.

### D67 — Closed: the sweeps resolve dotted spellings (Medium)

Grok, 2026-08-26 — the ninth evasion of the same two sweeps, and the
third time their name resolution has been wrong.

Version one matched a literal attribute, so `import subprocess as sp`
and `from subprocess import run` walked past. Version two resolved the
*bound name*, which is right for `import subprocess` and wrong for
`import xml.etree.ElementTree`: that statement binds `xml`, and the
call is written `xml.etree.ElementTree.fromstring(...)`, whose base is
an attribute chain rather than a plain name. The sweep looked for a
`Name` and found an `Attribute`, so an unguarded XML parse — the entity
bomb D46 exists to stop — was reachable with a green suite.

Resolution is by dotted *spelling* now, matched by prefix. More
importantly the resolver has its own falsifier: ten spellings of an
unguarded parse, five of a spawn, and four unrelated calls that must
not be flagged. It earned its place immediately — it caught a
regression in the rewrite that classified every `from x import member`
as a module alias, which the two sweeps it serves would have reported
as clean.

*Closing tests:* `test_every_spelling_of_an_unguarded_parse_is_seen`,
`test_every_spelling_of_a_spawn_is_seen` and
`test_the_resolver_does_not_widen_to_unrelated_calls` in
`tests/test_ast_reading_resolves_spellings.py`.

### D68 — Closed: the declarations dimension names its source (Medium)

Grok, 2026-08-26. `DECLARATION_CRITERIA` requires cyclomatic
complexity, declaration lines **and** cognitive complexity, because the
built-in path fails a declaration on any one of the three and a rate
built from a narrower set is not comparable to it. lizard emits the
first two.

So for a JavaScript repository with lizard installed and nothing else,
`_declaration_pressure` returns `None` and the built-in brace scanner
scores the dimension — on every run, by construction. The fallback is
correct. It was silent, which P8 forbids: a declarations rate with
nothing saying what produced it.

It also made a decision page wrong. Decision 10's amendment justified
keeping JavaScript by citing lizard, jscpd and multimetric as
baseline-tier adapters that read it. Marshall's ruling — *"keep JS in
since we have a detector and can score it"* — is exactly right about
the brace scanner and was never about the pool; the page credited the
pool for work the pool cannot do here. Corrected in place.

`dimensions_declined` now rides on the coverage document with the
missing concepts named, and the coverage section renders it.

*Closing tests:* `test_lizard_alone_cannot_drive_the_declarations_dimension`,
`test_the_fallback_is_attributed_rather_than_inferred` and
`test_the_declined_dimension_reaches_the_reader` in
`tests/test_declaration_source.py`.

### D69 — Closed: P1 discloses that the history window moves (Medium)

Grok, 2026-08-26. `DEFAULT_SINCE` is `12 months ago`, resolved by git
against the wall clock at the moment the audit runs, and it is not
configurable. P1 promised "same tree, config, pinned analyzer versions
and scan history in, same evidence, findings and score out" and named
three excepted fields, none of which is this.

An unchanged tree audited a week apart reports different churn, hotspot,
coupling and ownership rates. No input changed and the grade moved.

The determinism test cannot see it and neither can the runs it is built
on: they audit the same tree seconds apart, which is precisely the
interval over which a twelve-month window cannot shift. Fifth of the
same shape — a promise kept green by a check narrower than the promise.

Disclosed rather than removed. A fixed absolute window would make every
report a different question over time, and per-repository pinning is a
config decision nobody has asked for. The falsifier holds the page to
the constant, so changing the window without changing the disclosure
fails.

*Closing test:* `test_the_history_window_is_disclosed_as_clock_relative`
in `tests/test_determinism.py`.

### D70 — Closed: the POSIX claim runs on both POSIX platforms (Medium)

Grok, 2026-08-26, reopening D63. `test_ci_runs_only_platforms_the_package_claims`
forbade `windows` in `runs-on` and was treated as demonstrating the
claim. `Operating System :: POSIX` covers macOS as well as Linux, and CI
had only ever run one Linux image, so half the declared platform was
claimed and never executed. The check was narrower than the claim it
protected — the same finding this register keeps recording.

**Why macOS was never added is the more interesting half.** Seven test
fixtures pinned `PATH=/usr/bin:/bin` when scrubbing the environment for
a child `git`. On the macOS machine this project is developed on, that
pin *is* a shim: `/usr/bin/git` is Xcode's stub, Command Line Tools are
unavailable, and every one of those fixtures dies with `xcrun: error:
invalid active developer path` before git runs.

That is the entire local baseline — 101 failures and 191 errors, diffed
run after run as "known" — from one line, and none of it says anything
about the product. A real regression landing in any of those seven files
had 292 places to hide, and this project's own discipline of diffing the
whole suite against a baseline is what made that survivable-looking.

`tests/_git_path.py` resolves the directory of the `git` actually on
PATH; the environment stays scrubbed. A `macos-latest` job runs the
suite, and the platform test now requires a runner for every family the
classifier claims rather than merely forbidding one it does not.

*Closing tests:* `test_ci_runs_only_platforms_the_package_claims` in
`tests/test_platform_claim.py`, and the suite itself on the macOS
runner.

### D71 — Closed: reading a repository does not let git rewrite it (High)

Found by the macOS CI runner on 2026-08-26, hours after that runner was
added for D70 — the second defect that runner has paid for.

Every git command this package runs is a read: `log`, `rev-list`,
`status`, `rev-parse`. But git runs housekeeping of its own after many
commands, and housekeeping repacks objects and writes commit-graphs
*inside* `.git`. So an audit that promises never to write the tree it
audits was letting git write it, on our behalf, one directory down.

It surfaced as `.git/objects/maintenance.lock` appearing between the
before and after snapshots in
`test_audit_returns_the_report_without_writing_source_or_reports` and
`test_the_tool_takes_a_format_argument_and_never_prompts`.

**Why now, on identical product code.** Auto-maintenance triggers on
accumulated loose objects rather than on every invocation. D66 added two
`rev-list --count` calls per audit and pushed a latent defect over the
threshold. Two earlier CI runs of the same code passed, which is exactly
what a probabilistic check looks like from the inside — and why the fix
is pinned to the argv rather than to a snapshot of a temporary
directory.

`gc.auto=0` and `maintenance.auto=false` are prepended to every git
command in `run_git`, the one place this package builds a git argv,
which is what makes the promise checkable at all.

**The fix was right and the test still failed.** macOS went red again on
the very next run, with the same `maintenance.lock`. Auto-maintenance
**detaches**: `git maintenance run --auto` returns immediately and the
work lands milliseconds later. The scheduler here was not the product at
all — it was the fixture's own `git commit`, which sets the repository
up before the audit is ever called, and whose maintenance then fires
inside the window between the before and after snapshots.

Same commit, three CI runs, two failures and one pass. That is the
signature of a race, and it is the second time in this entry that a
probabilistic symptom pointed at the wrong culprit.

So there are two halves. The product no longer *triggers* maintenance,
which is the real guarantee and is pinned to the argv. And the suite no
longer *schedules* it either: a session-scoped conftest fixture exports
`GIT_CONFIG_COUNT`/`KEY`/`VALUE`, which reaches every git the suite
runs, product and fixture alike. Its falsifier asks git what it resolved
rather than asserting the variables are set — the difference between
proving conftest ran and proving git listened.

*Closing tests:* `test_every_git_command_disables_gits_own_housekeeping`
in `tests/test_git_argv.py`, and
`test_the_suites_own_git_has_maintenance_disabled` in
`tests/test_git_read_only.py`.

### D72 — Closed: a refusal does not disclose where a symlink points (High)

Codex, 2026-08-26. D38's refusal carried `write_instead`: the canonical
path the entry resolved to, so the user could correct their config. It
was the more helpful message, and it told whatever host reads
`server_info` where a symlink the user named actually points — a
directory the user never put in their config, published over the
transport by the very mechanism added to make refusals visible.

D48's rule is that host paths do not cross the transport. A helpful
refusal is not an exception to it, and "we surfaced it so it would not
be silent" is not a reason to surface more than the user supplied.

The entry itself is still echoed, because the user wrote it. Its target
is not ours to publish. `repair` names the flow instead: grant the root
again through setup, which stores the path it resolved to at the moment
of consent.

*Closing test:* `test_a_non_canonical_grant_is_refused_and_said_so` in
`tests/test_grant_only_user_tier.py`, which now asserts the resolved
target appears in no field of the refusal.

### D73 — Closed: the one git spawn that is not run_git (High)

Codex, 2026-08-26, one commit after D71 closed. `_backfill._git` builds
its own argv and does not go through `run_git`, so it ran `rev-list`
without `gc.auto=0` / `maintenance.auto=false` — and
`commits_in_range()` reaches it before any worktree exists. D71's whole
claim is that reading a repository cannot let git rewrite it, and this
was a read that could.

**The closing test could not see it.** It parsed `git_tools.py` alone,
because that was where the fix lived. A rule about *every git command*,
held by a check that read one file — and there was exactly one git
command elsewhere in the package.

The sweep reads every module now: any argv whose first element is the
literal `"git"` must carry `READ_ONLY_GIT_CONFIG`, and it asserts it
found at least two spawns, because finding one is the state that hid
this.

*Closing test:* `test_every_git_command_disables_gits_own_housekeeping`
in `tests/test_git_argv.py`.

### D74 — Closed: an incoherent window explains itself as unknown (Medium)

Codex, 2026-08-26. `commits_in_window` and `commits_considered` are not
`HistoryEvidence` members, so nothing upstream validates them, and
`_empty_window_reason` asked only `isinstance(..., int)`. `True` is an
`int`. A report carrying `commits_in_window: true, commits_considered:
0` was told, confidently, that every commit in its window was a merge.
Negative counts and a subset larger than its set did the same.

D66 exists to stop a wrong reason being stated confidently, so the fix
is not a better guess: an incoherent pair earns the least specific
answer. Bools rejected, negatives rejected, and a non-merge subset that
exceeds the set it is drawn from rejected.

*Closing test:* `test_an_incoherent_pair_of_counts_earns_the_least_specific_reason`
in `tests/test_history_window.py`, seven payloads.

### D75 — Closed: the doc sweep recognises more than three sentences (Medium)

Codex, 2026-08-26. D65's closing test matched three exact phrasings,
lifted from the two sentences it was written to catch. Adding
*"maintainability-agent runs eslint whenever it is installed"* to an ADR
left it green. A check shaped like the defect it already found is not a
check — the same criticism this register has recorded five times, now
about a test written to prevent it.

Two wrong versions before the third. Matching every verb flagged nine
lines of history: the register recording the defect, the roadmap listing
tools this project does not replace, an ADR quoting an old experiment.
Then proximity exoneration turned out to be gameable in the most direct
way possible — a claim inserted directly beneath the paragraph refusing
eslint was exonerated by it, which is backwards, since a refusal nearby
is exactly where a false claim does the most damage.

What it checks now is the harm D65 actually names: *acquisition*
language beside a refused tool's name, exonerated only by the same
sentence, in operator-facing documents. The three incident records are
exempt by name and with reasons, because describing the old behaviour is
what they are for.

*Closing test:* `test_no_document_presents_a_refused_analyzer_as_one_this_agent_runs`
in `tests/test_analyzer_config_isolation.py`, verified against four
distinct phrasings.

### D76 — Closed: P1 is held to the window a report is built with (Medium)

Codex, 2026-08-26. D69's closing test compared the prose to the
`DEFAULT_SINCE` constant. Changing `history_section`'s default to
`"24 months ago"` left the constant untouched and the test green, with
the disclosure describing a window nothing used.

It now reads the *effective* window — the signature default — requires
it to equal the constant the page quotes, and checks by AST that
`report.py` does not pass a window of its own, since a call site that
overrides the default makes the disclosed value fiction.

*Closing test:* `test_the_history_window_is_disclosed_as_clock_relative`
in `tests/test_determinism.py`.

### D77 — Closed: a comment cannot stand in for an install (Medium)

Codex, 2026-08-26. The test asserting CI installs every pip-installable
adapter asked whether the slug appeared *anywhere* in the workflow file.
Deleting `flake8` from the install line and leaving
`# flake8 is installed by this step` behind kept all fourteen green
while the adapter went uninstalled.

It parses the YAML now and tokenises the actual `pip install` commands,
with comments stripped first. That immediately found a real gap the
substring version could not: `ruff` reached CI only through `.[dev]`,
so the pool step never named it. Rather than carve an exemption for it,
the claim was made literally true.

*Closing test:* `test_ci_installs_every_pip_installable_adapter` in
`tests/test_ci_installs_the_analyzer_pool.py`.

### D78 — Closed: the JS complexity number is about the code (High)

Grok, 2026-08-26. Decision 10 keeps JavaScript because this project has
a detector that can score it, and D68 made the fallback to that detector
*visible*. Grok's sentence is the finding: **visibility is not
accuracy.** D68's closer checks that the built-in scanner is attributed
and never asks whether its number means anything.

`COMPLEXITY_RE` counted every `?` character as a decision point. In
JavaScript `?` is three operators and only one is a decision. `?.` is
defensive member access. `??` is one decision written with two
characters, so a bare `\?` counted each one **twice**. `?` ternary is
the branch the rule was written for.

Reproduced at the shipped thresholds:

```javascript
function pick(u) {
  return u?.user?.profile?.settings?.theme
      ?? u?.user?.prefs?.theme
      ?? "light";
}
```

**Cyclomatic 12, status warn.** Its McCabe number is 1. An eight-way
fallback chain scored 15, one under the hard gate. It fires hardest on
exactly the modern JavaScript this project claims to score, which is P7:
a score issued where the thing measured was not the code. After the fix,
3 and 8, and genuinely branching code is unchanged.

Grok's other JS observations — regex literals unmasked, brace-free
bodies charged flat, object-literal arrows not detected as declarations
— are disclosed limitations in `_ranges` and `_cognitive` and are not
closed here. This entry closes the one that produced numbers that were
simply wrong.

*Closing tests:* `test_the_scored_complexity_is_the_functions_complexity`,
`test_a_defaulting_expression_does_not_warn` and
`test_python_complexity_is_unchanged_by_the_javascript_fix` in
`tests/test_js_complexity_operators.py`.

### D79 — Closed: a grant records what it was, not only where (High)

Grok, 2026-08-26 — the fourth predicate in three days, and the one whose
prediction was written into the finding: *"D38 is the one that will be
filed again if this round is closed by tightening `resolve()==self`
without an inode."*

Two holes, both reproduced. `Path.resolve()` is not `strict=True`, so a
directory nobody has created "resolves to itself" and was honoured —
hand-write it, get no refusal, then create it or mount over it. And
`resolve()` preserves case, so on APFS `/USERS/marshallguillory/...`
exists, resolves to itself, and was treated as a product-made grant.

**The pattern is the finding.** Four rules compared better and better
strings, and each moved the hole rather than closing it, because a path
is a *name* and names alias: symlinks, case-insensitive volumes, bind
mounts, a directory created after the question was answered. Version
three's own docstring said so — *"a bare path with no record of what it
resolved to when it was granted cannot be defended"* — and then honoured
bare paths anyway.

So this version stops comparing names. `persist_root_grant` records the
directory's device and inode at the moment of consent, and a grant is
honoured only when the directory at that path is still that directory.
A directory *swapped* for another under the granted name — identical by
name, which is why every previous rule honoured it — is refused by the
same check that refuses a swapped symlink, and so are bind mounts, case
variants and ghost paths, none of which a spelling rule could reach.

**Where identity stops, disclosed rather than implied.** Deleting a
directory and immediately recreating it is a case `(device, inode)`
cannot reliably see: ext4 hands the inode straight back, so the
recreated directory is identical by every field recorded at consent.
APFS does not reuse. The first version of the falsifier asserted a
refusal for that case, passed on macOS — including the macOS runner
added the day before — and failed on Linux CI. That is a claim wider
than its mechanism, which is this register's own recurring defect
arriving from the other side, and it was caught by infrastructure added
two days earlier for a different reason.

**A hand-written entry carries no identity and is refused.** That is the
deliberate consequence rather than an oversight: it is exactly the bare
path the rule cannot defend. Existing users are asked once more, which
D38 established is not an error.

Not claimed: that this ends the series. What is claimed is that the
thing compared is no longer a spelling.

*Closing tests:* `test_a_grant_to_a_directory_that_does_not_exist_is_refused`,
`test_a_case_variant_spelling_is_refused`,
`test_a_granted_directory_swapped_for_another_is_refused` and
`test_inode_reuse_is_the_disclosed_limit_of_identity` in
`tests/test_grant_only_user_tier.py`.

### D80 — Closed: the population floors are bounded from below (High)

Grok, 2026-08-26, in a table of "checks that cannot fail the property
they name". `test_no_calibration_member_is_unscoreable_by_the_scale_it_calibrates`
bounds the floors from *above* — a floor may not exceed the corpus
minimum. Nothing bounded them from below.

Set `files_scanned` to 1 and every check in that file stays green while
a one-file repository collects a verified grade. That is the exact
result ADR 005 exists to prevent and the one P7 names: a score issued as
a consequence of not looking.

Asserted against the behaviour rather than the constant — one file, one
declaration, no score, however the table is edited — with the invariant
also stated on the table so someone editing it sees why it has two
sides.

*Closing tests:* `test_a_hello_world_repository_is_never_scored_whatever_the_floors_say`
and `test_the_floors_are_bounded_from_below_as_well_as_above` in
`tests/test_population_floors.py`.

### D81 — Closed: the witnesses no longer share fate with what they watch (High)

Grok, 2026-08-26, reopening D71 at the layer Codex's version of the same
finding did not reach. D73 fixed the backfill argv and widened the
sweep; this is the other half.

The conftest guard exports `GIT_CONFIG_*` for the whole suite so that
fixtures cannot schedule git maintenance. It also covers the product.
So the "never writes the tree" snapshot tests — the only witnesses to
D71 — would stay green if `READ_ONLY_GIT_CONFIG` were deleted from
`run_git` tomorrow, because maintenance would not fire either way.

**Demonstrated rather than argued.** With the settings removed from
`run_git`, all 36 snapshot tests pass and the new witness fails. It
records the argv of every git a real audit spawns and asserts each
carries the settings: it watches the product, not the environment, and
is deterministic where the snapshot was probabilistic.

The same finding named D70's closer: `runs-on: macos-latest` with
`run: true` satisfied it, so POSIX could be "demonstrated" by a job that
does nothing. The macOS job now has to run the suite.

*Closing tests:* `test_a_real_audit_spawns_no_git_without_the_read_only_settings`
in `tests/test_git_read_only.py`, and
`test_the_macos_runner_actually_runs_the_suite` in
`tests/test_platform_claim.py`.

### D82 — Closed: the audit door stops naming symlink targets too (High)

Grok, UAT audit of `199fb1b`. D72 removed the resolved path from
`server_info`'s refusals because D48 forbids host paths crossing the
transport. `authorize_repository` kept doing it: the user names
`innocent`, and its `PathNotAllowed` tells the host `secret-target`.

**D72's falsifier asserted the resolved path appears in no field of the
refusal dictionary.** It never read the exception. One door was closed
and its neighbour was left open by a check shaped around the door that
had been reported — the register's recurring defect, and the second time
in three days that a fix's own closer defined the fix's scope.

The refusal echoes the spelling the user supplied, which is theirs
already, and says how to obtain a grant without resolving anything. The
sibling refusal for a non-directory is checked for the same leak.

*Closing tests:* `test_a_refusal_does_not_tell_the_host_where_a_symlink_points`
and `test_a_missing_directory_refusal_does_not_name_the_resolved_path`
in `tests/test_authorization_freshness.py`.

### D83 — Closed: a standing grant is re-checked at use, not at start-up (High)

Grok, UAT audit of `199fb1b` — and the most consequential finding of the
round, because D79 was closed without it and reads as complete.

`allowed_roots()` runs **once**, when the server is constructed, and
produces a tuple of paths. `authorize_repository` then asked one
question: is this request inside one of them? So the identity D79
records at consent was verified at start-up and never again. Swap the
granted directory afterwards and the audit keeps authorizing whatever
now sits at that path for the life of the process — and an MCP server
is long-lived, on the surface this product calls primary.

Reproduced in-process: grant `project`, rename it away, recreate it with
`pwned.txt` inside, ask again. **Authorized.** Only a restart refused it.

This is D38's original shape returning a fifth time: the in-process seam
was already right, and a later read of a stored fact went around it.
There the stored fact was a path and the read followed a symlink; here
the stored fact is an identity and the read was not happening at all.
Every version of this entry has fixed *where* the check compares and
left *when* it runs alone.

Persisted grants are re-validated at each authorization. Launch roots —
`--allow-root`, the environment, the working directory — are not: they
carry no recorded identity because they are this process's own
configuration rather than a standing consent, and re-checking them would
refuse every ordinary launch.

*Closing tests:* `test_a_swapped_directory_loses_its_grant_without_a_restart`
and `test_a_launch_root_is_not_re_checked` in
`tests/test_authorization_freshness.py`. The check lives in
`_stored_grants` beside the rule it applies, and the audit door
re-raises it as `PathNotAllowed` so the transport keeps translating a
declared refusal rather than seeing a crash (D48).

### D84 — Closed: a nested list's members are shaped too (Medium)

Codex, UAT audit of `199fb1b`. `_shaped_inside` has a branch that
validates list items and it only ever ran for a **top-level** list. So
`{"paths": {"include_extensions": [1]}}` was accepted: the value is a
list, which is all that was asked.

The audit then matched no file, exited 0, and reported a clean scan of
nothing with forty source files "unread". That is worse than a crash and
is exactly the concealment D53 exists to prevent — a type error turned
into an apparently valid empty result, which a reader cannot tell from a
repository that genuinely has no source in it.

The dict branch now recurses, so a member is checked wherever it lives.
Refused by name: `paths.include_extensions[0] must be str, not int`.

*Closing tests:* `test_a_nested_list_member_of_the_wrong_type_is_refused_by_name`
and `test_a_valid_nested_list_still_loads` in
`tests/test_config_shape.py`.

### D85 — Closed: the version string is a claim like any other (High)

Grok, UAT audit. Acceptance testing *for 1.0* was about to run against
an artifact naming itself `0.9.1` and `Development Status :: 3 - Alpha`.
A tester would report a version that is not the thing under test, and
this project already shipped nine releases whose contents did not match
what they claimed (D23).

The remedy applied was `1.0.0rc1`, `Development Status :: 4 - Beta` —
not `1.0.0`, on the reading that the release plan tags 1.0 at 8.10 and a
candidate is therefore still short of that gate. The falsifier held the
three copies of the version together and refused a bare `1.0.0` while
8.10 still said the tag waits on 8.9.

**That remedy was wrong and is reverted; see D100.** The diagnosis
stands, and so do three of its four tests: three copies of a version are
one fact, the maturity classifier is a claim about the same artifact,
and a support table that omits the shipped line reads as the shipped
line being unsupported. All three pass at `0.9.1` — they were never
about which version, only about the copies agreeing.

What did not stand is the direction. 8.8 is the acceptance run and 8.9
the hostile audit *of the artifact that passed it*; neither had happened,
so "candidate for 1.0" asserted the outcome of a gate nobody had opened.
Reading the bar as 8.10 alone is what let the promotion through. The
entry written to say a version string follows evidence rather than
intention was itself the intention.

*Closing tests:* `test_every_copy_of_the_version_says_the_same_thing`,
`test_a_final_1_0_0_is_not_claimed_before_its_gates_close`,
`test_the_maturity_classifier_matches_the_version` and
`test_security_support_covers_the_shipped_version` in
`tests/test_version_claim.py`.

### D86 — Closed: the JS scanner sees the file's actual functions (High)

Grok, UAT audit, continuing D78. That entry fixed `?` arithmetic and
left the rest disclosed; the objection is that disclosure is not a score.

Two defects, both reproduced. `function f() { return /a?b?c?d?e?/; }`
scored cyclomatic **6** — the regex literal's contents were read as
code, because masking scrubbed comments and strings and not regex
literals. And `{ onSave: (a) => {...}, onLoad: function (b) {...} }`
produced **no declarations at all**, which is how a React or Node
codebase writes most of its interesting logic: the audit scored whatever
loose `function` statements happened to sit beside the handlers and
reported the file examined.

Masking now recognises a regex literal where a *value* may begin, which
is the standard heuristic and the whole disambiguation JavaScript offers
without a parser — `a / b ? 1 : 2` is untouched. The brace scanner
detects `name:` members, a prefix that cannot be a control keyword and
so does not collide with `if (`. The example above now scores 1, and
all three declarations are found.

*Closing tests:* `test_the_scored_complexity_is_the_functions_complexity`
and the cases beside it in `tests/test_js_complexity_operators.py`.

### D87 — Closed: the macOS job runs the suite, not the word (Medium)

Grok, UAT audit. D81 required `"pytest"` in the macOS job body. `echo
pytest` satisfies that, and so does a pytest invocation naming one file
— which would let the job stop running the product's suite without
anything noticing. D77 had taught the same lesson one job over: a
comment is not an install.

The run commands are parsed now, and one of them has to *be* a
whole-suite pytest invocation rather than contain the word. Verified
against both bypasses.

*Closing test:* `test_the_macos_runner_actually_runs_the_suite` in
`tests/test_platform_claim.py`.

### D88 — Closed: why the argv recorder is the only witness (Medium)

Grok, UAT audit. D81's recorder watches the argv; the promise is about
the tree; the 36 snapshot tests still run under the suite-wide
`GIT_CONFIG_*` guard and would not notice if `READ_ONLY_GIT_CONFIG`
vanished. The objection is correct.

**Two attempts at a tree witness failed, and the second failure is the
answer.** Removing the guard was not enough — maintenance is
threshold-driven and merely *allowed* to fire. Making the environment
hostile with `gc.auto=1` was not enough either, and that one passed with
the settings deleted, which would have shipped a test that passes either
way into the entry that exists to prevent them.

The reason is that git runs housekeeping after commands that **write** —
`commit`, `merge`, `fetch` — and this package runs none of them. The
`maintenance.lock` that opened D71 was scheduled by a fixture's own
`git commit`, which is what D71's second half already concluded. No
audit of an unmodified repository can produce the write a snapshot would
catch, so a passing snapshot proves nothing in either direction.

What is checkable is the premise, and that is what is checked: every git
subcommand the audit spawns is a read, flags included. It found one the
list had missed — `git branch --show-current` — on its first run. If a
writing subcommand is ever added the reasoning stops holding and this
fails, while the argv guarantee, which does not depend on the premise,
stands on its own.

*Closing test:* `test_the_product_runs_only_git_commands_that_read` in
`tests/test_git_read_only.py`.

### D89 — Closed: gating CI pins, on the wrong platform (Medium)

Grok, UAT audit. P1's determinism is conditional on pinned analyzer
versions. The gating pipeline had installed the pool **unpinned**, on
purpose, so that an unchanged `main` going red because an analyzer
shipped is a signal rather than a silence.

That disclosure is now closed into the workflow. `constraints/analyzers.txt`
checks in the Python 3.12 resolver output for the twelve pip-installed
analyzers and their dependency closure, and the gating jobs (`verify`,
`audit`) install through it. A green PR gate therefore certifies the
pinned-input condition P1 actually states, not merely that the suite
passed against that day's analyzer releases.

The old drift signal is kept rather than deleted. The weekly scheduled
run creates a throwaway virtualenv, installs the same top-level pool
**unpinned**, freezes what pip resolved, and fails on a diff against the
checked-in constraints. Analyzer movement still turns the scheduled run
red, but the merge gate no longer floats.

**Reopened 2026-08-27, unclosed on review.** Three defects in the fix,
two of them the class D97 names:

*The drift check could never pass.* It diffed the constraints file --
eight lines of provenance comments -- against raw `pip freeze` output,
which has none, so the scheduled run went red every week whether or not
anything drifted. This file's own header says a pipeline that fails on
something advisory teaches people to ignore it.

*Its test could not see that.* It asserted the string `diff -u
constraints/analyzers.txt` was present. Appending `|| true` -- which
neuters drift detection entirely -- left it green. The second version
asserted the step mentions stripping, and replacing the helper body with
`cat` left *that* green. The third runs the workflow's own normaliser
against the real constraints file and checks its output could have come
from `pip freeze`.

*The pin does not match the platform it constrains.* The closure was
resolved on macOS arm64; `verify`, `audit` and the drift job all run
`ubuntu-latest`. The pinned install may not resolve there at all, and
the drift comparison would report platform-divergent closures as
analyzer drift, weekly, forever.

**Closed 2026-08-28.** `resolve-constraints` was dispatched against
`717da4d` and its artefact is now the checked-in file: Python 3.12.14 on
`Linux-6.17.0-1022-azure-x86_64-with-glibc2.39`, the platform `verify`,
`audit` and `analyzer-drift` actually run on. The `xfail(strict=True)`
marker did what it was put there to do — it turned into `XPASS(strict)`
the moment the file landed, so the closure could not be taken without
also removing the marker.

The residual was written on the assumption that the two closures would
diverge. They do not, and that is worth recording rather than assuming:
both platforms resolve the same forty-two packages, no entry is
platform-conditional, and the only differences are `platformdirs`
4.11.4 → 4.11.5 and `ruff` 0.16.4 → 0.16.5, two releases that shipped in
the day between the resolutions. So the weekly drift comparison was
never going to report platform divergence as analyzer drift on this
pool. That was a real risk when it was written and it is now a measured
non-risk, which is a different thing from a guess that happened to hold.

*Closing tests:* `test_the_constraints_were_resolved_on_the_platform_the_gates_run_on`,
`test_the_gating_jobs_install_through_the_constraints_file` and
`test_the_scheduled_drift_job_floats_and_can_actually_fail` in
`tests/test_analyzer_pinning.py`.

*Mutation:* the platform check was broken twice, both outside the
sample it asserts over — it reads the constraints file and the
workflow, and neither mutation touched the test. Rewriting the
provenance header to name macOS again failed it; deleting every comment
line from the constraints file failed it on the "records no provenance"
clause. Restoring the artefact passed it. The claim is about which
platform resolved the pins, and both mutations make that claim false in
the two ways it can be false: wrong platform, or no way to tell.

The platform residual was closed by claude: dispatched
`resolve-constraints`, checked in its artefact, removed the marker.

*Roles:* found=grok prompt=marshall fix=codex+claude test=codex+claude run=mutation

### D90 — Closed: a stale grant does not veto a launch root (High)

Codex, 2026-08-26, against a fix made the same day. D83 re-checks
persisted grants at use, and applied that check to any request a stale
grant happened to *cover*. So launching with `--allow-root <base>` while
holding a stale grant for `<base>/project` refused `<base>/project` —
which the launch root authorized on its own, with no consent involved.

A freshness rule that revokes access this process's own configuration
granted is not a tightening; it is a denial of service. The fix for a
security defect introduced an availability one, on the same day, in the
same function.

**And D83's closer passed throughout.** Its fixture launched on the
granted directory's *parent*, so that scenario always had independent
launch cover and never isolated the standing grant it claimed to test.
The test was green because of the over-broad behaviour rather than
despite it. Fixed here: the fixture launches on a sibling, which is what
makes the grant the only thing under test.

Authorization now separates its two sources. A launch root — the flag,
the environment, the working directory — authorizes on its own. Only
when a persisted grant is the *sole* cover does freshness decide.

*Closing tests:* `test_a_launch_root_still_authorizes_despite_a_stale_grant_beneath_it`
and `test_a_stale_grant_with_no_launch_cover_is_still_refused` in
`tests/test_authorization_freshness.py`.

*Roles:* found=codex prompt=claude fix=claude test=claude run=mutation

### D91 — Closed: the config door stops publishing paths too (High)

Codex, 2026-08-26. D82 removed the resolved path from
`authorize_repository`'s refusal. `authorize_config`, eleven lines
below it, published **two**: a caller naming `innocent.json` was told
the symlink's target and the canonical repository path.

D82's falsifier read `authorize_repository` and stopped there, so the
fix that removed one disclosure left a larger one beside it untouched.
That is the fourth door in this family — `server_info` (D72), the
repository refusal (D82), the not-a-directory refusal (D82), and now
this — and each was found only when someone looked at the next one
along.

Both refusals here name the spelling the caller supplied, which is
theirs already, and resolve nothing into the message.

*Closing test:* `test_the_config_refusals_name_no_resolved_path` in
`tests/test_authorization_freshness.py`.

*Roles:* found=codex prompt=claude fix=claude test=claude run=mutation

### D92 — Closed: an audited repository cannot run code in this process (Critical)

Grok, 2026-08-26, and the most serious defect found in this project.

Decision 9: *"this agent never executes the audited repository's code,
and its configuration is code."* That was enforced on the analyzer
adapters — eslint refused outright, pylint and mypy pointed at
`os.devnull`, and a sweep held every adapter to a classification. **Git
was never asked the question.**

`core.fsmonitor` is a repository config key naming a command git
executes. `worktree_status` runs `git status` on every git-backed
audit, which is the default path. Reproduced: a repo whose
`.git/config` sets `core.fsmonitor` to a script in its own tree ran
that script in the auditor's process, and the payload wrote a file into
the worktree — which the MCP door separately promises never happens.
The product then returned `?? PWNED` as the status string, having
created `PWNED` itself.

`READ_ONLY_GIT_CONFIG` existed and disabled *housekeeping* (D71). One
rule about git writing, none about git executing.

The list is wider than the demonstrated vector — `core.hooksPath`,
`core.pager`, `core.sshCommand`, `core.alternateRefsCommand`,
`diff.external`, `credential.helper`, `protocol.ext.allow` — because
the command set grows, and the last rule scoped to the commands of the
day missed the one spawn that lived elsewhere (D73).

**Residual, disclosed rather than closed:** content filters
(`filter.<driver>.clean`) and `diff.*.textconv` execute too and are
keyed by a driver name from the tree's own `.gitattributes`, so no
fixed `-c` disables them. Verified they fire on a worktree-content
`git diff` and not on this package's only diff, which compares two
commits by name and status.

**It also falsifies D88's reasoning.** That entry argued no tree-level
witness for the git promise could exist because "this package runs only
reads". `status` is a read that executes. The premise was wrong, not
merely the conclusion.

*Closing tests:* `test_the_audited_repository_cannot_choose_what_this_process_runs`
and `test_worktree_status_on_a_hostile_repository_changes_nothing` in
`tests/test_git_read_only.py`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=mutation

### D93 — Closed: TypeScript type members are not declarations (High)

Grok, 2026-08-26, against D86 — closed the same morning.

`_PROPERTY_RE` matches `name: (args) =>`, which is also how TypeScript
writes an interface member. So `onSave: (a: string) => void;` counted as
a one-line, complexity-1 function.

The cost is not cosmetic. Forty files of real functions scored
`insufficient` and were refused a grade. The same forty with an
`interface` of three typed arrows each reported **160 declarations**,
crossed the population floor, diluted band pressure fourfold, lifted
`declaration_size` from 1.4 to 3.0, and issued a **verified C**. The
type members are what bought the letter — P7 (a grade from a population
that is not there) and P3 (withheld evidence improving the result) in
one step.

Type blocks are skipped now: inside `interface X { … }` or
`type X = { … }`, nothing is a declaration.

*Closing tests:* `test_type_members_are_not_counted_as_declarations` and
`test_a_real_object_literal_member_is_still_found` in
`tests/test_js_declarations.py`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=mutation

### D94 — Closed: string-keyed members are declarations too (High)

Grok, 2026-08-26, the other half of D86. Masking blanks string literals
before any pattern runs, so `"onSave": (a) => {` arrives as
`        : (a) => {` and the name is gone. Quoted keys were invisible,
and a lone `function helper()` beside them still marked the file
examined — D86's original shape exactly.

**D86's closer used the unquoted instance, which is the one masking
does not destroy.** Some keys must be quoted: `"on-error"` is not a
valid identifier.

The name is recovered from the line before masking touched it.

*Closing tests:* `test_a_string_keyed_member_is_a_declaration` and
`test_a_sibling_function_does_not_stand_in_for_the_handlers` in
`tests/test_js_declarations.py`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=mutation

### D95 — Closed: a regex after a control paren is not code (Medium)

Grok, 2026-08-26, third against D86. `_VALUE_MAY_BEGIN` lists the
positions where a `/` opens a regex literal. It includes `return`,
which is the keyword D86's own closer used. It does not include `)`.

So `if (x) /a?b?c?d?e?/;` scored **complexity 7** against a McCabe
number of 2, while `return /a?b?c?d?e?/;` — the tested case — scored 1.

`)` is the one position a character cannot decide: `if (x) /re/` opens a
value and `f(x) / 2` is division. The paren is walked back to and the
token owning it is asked.

*Closing test:* `test_a_regex_literal_is_masked_wherever_a_value_may_begin`
in `tests/test_js_declarations.py`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=mutation

### D96 — Closed: the last two doors stop publishing resolved paths (High)

Grok, 2026-08-26. D72 removed a resolved path from `server_info`, D82
from `authorize_repository`, D91 from `authorize_config`. Two more were
still open: `baseline_path`, and `config.repository_path` — which runs
on an **ordinary audit** whenever the repository's own config names a
path, so a symlinked `history.jsonl` published its target to the chat
host.

Six doors, one family, and each was found only when someone looked at
the next one along. Every closer read the function it was written for.

*Closing test:* `test_no_repository_scoped_path_refusal_names_what_it_resolved_to`
in `tests/test_authorization_freshness.py`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=mutation

### D97 — Closed: the class behind thirty entries (High)

Marshall, 2026-08-27: *"have you asked WHY? these same type of defect
keep coming back so you can address the root cause? it seems like a
class of defect that is easily addressable, but you keep treating
symptoms."*

No, I had not. Thirty of the ninety-six entries above are **one
mechanism**, closed thirty times, each with a bespoke fix and no
question about why the next one arrived. The mechanism, the three
clauses that answer it, and why mutation testing was not catching it are
written up under *The falsifier standard* at the top of this file.

The short version: a check written from the instance that motivated it
rather than from the claim it defends, and a mutation drawn from the
same sample as the assertion, so the mutation confirmed the sample and
said nothing about the claim. Every time an auditor broke one of these,
they mutated a member the test did not name.

**What it cost to leave unnamed:** four adapters of fifteen swept, three
sentences of a document, one file of a package, one keyword of a value
list, a `pytest` that `echo pytest` satisfied, a `diff` that `|| true`
neutered, and a security rule enforced on every analyzer and never asked
of git.

`tests/test_falsifier_standard.py` enforces clause two over the suite:
sixteen tests derive a population by walking the filesystem, and every
one of them must now assert it found something. Four did not. Clause
three is required to be stated on every entry from D97.

**The control had the defect three times while being built**, which is
the strongest evidence that it needed to be mechanical rather than
remembered: it counted `ast.walk` as a filesystem walk and reported
twenty of thirty-three violations that were not; and it accepted *any*
population being asserted, so a test binding two populations was covered
by guarding either. That last one was found by mutating a guard the
check did not name — the clause catching its own author.

The detector's own non-empty guard is deliberately **not** cited below.
It defends the detector rather than the claim, and
`tools/prove_falsifiers.py` showed it passing at the base — correct for
a guard, wrong for a closer. A citation region that named it would be
claiming a proof it cannot give.

*Closing tests:* `test_a_sweep_asserts_its_population_is_not_empty` in
`tests/test_falsifier_standard.py` and
`test_entries_from_the_cutoff_state_what_their_mutation_broke` in
`tests/test_roles_recorded.py`.

*Roles:* found=marshall prompt=marshall fix=claude test=claude run=mutation

*Mutation:* removed the population guard from
`test_release_plan::test_the_release_plan_table_is_measured_not_remembered`
and separately from `test_written_record`. Neither is named by
`test_a_sweep_asserts_its_population_is_not_empty`, which derives its
subjects from the suite rather than listing them — so breaking either is
a member the closing test does not know about. The first draft of the
closer survived the `test_files` mutation and was fixed because of it.

### D98 — Closed: the first Codex-authored fix, reviewed (High)

Reviewed 2026-08-27, the first change under the split where Codex wrote
the code. Three defects, and what they were is more useful than that
there were three.

**The drift check could never pass.** It diffed `constraints/analyzers.txt`
— eight lines of provenance comments — against raw `pip freeze` output,
which has none. Non-empty every run, drift or no drift. The comparison
normalises both sides now.

**Its test could not see that.** It asserted the string `diff -u
constraints/analyzers.txt` appeared. Appending `|| true` neuters drift
detection entirely and left it green. My replacement asserted the step
*mentions* stripping — and replacing the helper body with `cat` left
*that* green. The third version extracts the workflow's own normaliser
and **runs** it against the real constraints file, checking the output
is something `pip freeze` could have produced.

Two string-shaped checks in a row, mine and Codex's, on the day D97
named that exact class. The standard is easy to state and hard to
apply, which is the argument for the parts of it that are mechanical.

**The pin does not match the platform it constrains** — see D89, which
this reopened.

**What the review says about the experiment.** Codex's work was good on
the parts I asked for: real resolved versions, honest provenance, the
closure decision made explicitly rather than silently, gates pinned,
drift moved rather than deleted. Its failure mode was the same as mine —
a check written from the artifact rather than the behaviour — which is
evidence that the split does not fix this class by itself. What found
all three was mutation from outside the sample, run by someone who was
not the author. That is the part that transfers.

*Closing tests:* `test_the_gating_jobs_install_through_the_constraints_file`,
`test_the_scheduled_drift_job_floats_and_can_actually_fail` and
`test_product_intent_describes_the_arrangement_the_workflow_implements`
in `tests/test_analyzer_pinning.py`.

*Roles:* found=claude prompt=marshall fix=codex+claude test=claude run=mutation

*Mutation:* appended `|| true` to the drift comparison, and separately
replaced the normaliser body with `cat`. Neither is named by the closing
tests, which locate the step by its name line and then execute what it
defines — so both break a member the tests do not enumerate. The first
two versions of the closer survived one of these each.

### D99 — Closed: every control was self-report (High)

Miles Parker, on the thread where this work was described, 2026-08-27:
*"agents are always in control over both what is being tested and the
test. An agent that introduced a bug and mutated the test to cover it up
would look no different externally from one that functioned perfectly."*

He is right, and nothing built before this addressed it. D97's standard
is enforced by tests the same agent can edit. The `*Mutation:*` line is
the author's account of what they broke. Every control in this register
was, ultimately, self-report.

**The benign version is commonplace, and I did it three times in one
day.** A test fails; I decide the test was wrong; I edit it.
`test_git_argv` pinned an exact tuple and the tuple legitimately grew.
`test_mcp_server` matched refusal text D82 changed.
`test_declaration_grading` searched a whole document for `"42"`. Each
edit was, I believe, correct. Nothing external distinguished *the test
was wrong* from *I made the test agree with me*, and that is exactly the
distinction Miles is asking for.

`tools/prove_falsifiers.py` is the first control that does not take the
author's word. For every entry added since the base commit it reads the
tests the entry cites, builds a scratch worktree, restores everything to
the base **except the files defining those tests**, and requires each
cited test to fail there. A test that passes without the change did not
need it.

Two design faults, both found by running it rather than reasoning about
it. Excluding all of `tests/` could prove no entry whose fix lives in
test code — D97 added guards to four test files, so keeping `tests/`
kept the guards and D97's own closer looked unproven. And `git checkout`
restores tracked files without deleting ones the change added, so
`constraints/analyzers.txt` survived the revert intact.

**On its first honest run it found two real problems.**
`test_there_are_sweeps_to_check` guards the detector rather than
defending the claim and passes at the base — correct for a guard, wrong
for a citation, so it is no longer cited. And
`test_entries_from_the_cutoff_state_what_their_mutation_broke` passed
*vacuously* at the base, where no entry reaches the cutoff and the list
it asserts over is empty: D97's own clause-two defect, inside D97's own
closer, invisible to every check that existed the day before.

What it does not do: it cannot stop an agent editing the prover, the
workflow, or the register. Those need enforcement outside the agent's
reach — branch protection, CODEOWNERS, a human reading a diff. It closes
the case where the code and its check are written together, which is the
case that was actually producing defects here.

*Closing tests:* `test_the_citation_region_stops_at_the_next_field`,
`test_every_citation_spelling_the_register_uses_is_read` and
`test_the_tool_is_wired_into_the_pipeline` in
`tests/test_prove_falsifiers.py`.

*Roles:* found=marshall prompt=marshall fix=claude test=claude run=mutation

*Mutation:* neutered the proving job with `|| true`, and separately
appended a `*Mutation:*` line naming a test to an entry to confirm the
citation region ignores it. Neither is a member the closing tests
enumerate — they locate the job and the region by structure — and the
tool itself was run against `bc21f4d` to confirm four cited falsifiers
fail without their changes and two do not.

### D100 — Closed: the artifact promoted itself to a 1.0 candidate (High)

Marshall, 2026-08-28: *"i never told you to create a v1.0 candidate.
ever."* He had not. D85 moved `pyproject`, `config.VERSION` and
`__init__.__version__` to `1.0.0rc1` and the classifier to Beta, added a
`1.0.x` row to `SECURITY.md` and a `1.0.0rc1 — unreleased` section to the
changelog, on 2026-08-26. No authorization for any of it is recorded
anywhere in this repository.

**The defect is not the number, it is the claim.** This project's stated
rule — in D85's own text — is that a version string is a claim like any
other and follows evidence rather than intention. The evidence for
"release candidate for 1.0" is 8.8, the acceptance run. 8.8 has not run.
So the entry written to stop a version from outrunning its evidence
promoted the version past 8.8 and 8.9 in the same commit, and passed,
because its falsifier only ever refused a bare `1.0.0`. A candidate
suffix is not a smaller claim than the release; it is the same claim
about the same gate, made more quietly.

*And the register could not say who made it.* Asked who promoted the
version, the honest answer from the record was that nobody knows: D85
carries no `*Roles:*` line. Every agent in this repository commits under
Marshall's git identity, so authorship in `git log` proves nothing about
authorization. The guess offered — *"maybe grok did it for the hostile
audit"* — is a guess, and it is the only thing the record supports.

The `*Roles:*` convention already existed. It starts at D89 and eleven
entries have carried it since, on habit alone — no check ever read it,
which is why D85 sitting four entries below the line cost nothing at the
time. Recording that without enforcing it would be the
disclosure-instead-of-a-fix that D89 itself was refused for, so the lint
now reads every entry from D89 down. The cutoff is D89 because that is
where the practice starts; choosing D100 would have picked the number
that makes the check easy. D1-D88 cannot be reconstructed from memory
and are left stated here rather than invented.

*The revert.* Every copy returns to `0.9.1` and `Development Status :: 3
- Alpha`, the state before D85; the `1.0.x` support row and the
changelog section are removed. This restores a prior state rather than
choosing a new number, because picking one would be a second release
decision nobody authorized.

*The bar is release history, not a plan row.* The first version of the
falsifier refused a 1.x claim while the release plan's 8.8 acceptance
row was open. Marshall's question killed that anchor: *"why do you keep
bring up 8.8 when 0.9.1 is the latest release"*. He is right. 8.8 is a
sentence in a document, and citing it made the bar sound like it was
about a 1.0 programme when the operative fact is far simpler — what has
actually shipped. The check now reads `git tag`: nothing may declare a
major line above the newest release, and on the day a 1.x is tagged the
bar lifts by itself. No document gets a vote.

The authorship lint — `test_entries_from_d89_record_who_did_the_work` in
`tests/test_declared_authorship.py` — is deliberately *not* cited as a
closing test. It cannot fail at the base commit, because D89 through
D99 already carry the line; it prevents the next omission rather than
proving this one. Calling it a falsifier would be the same overclaim
this entry is about.

*Closing tests:* `test_no_copy_claims_a_major_line_above_the_latest_release`
in `tests/test_version_claim.py`. The version copies are found by
sweeping `pyproject.toml` and `src/` rather than by a typed list of
three, and an empty tag list fails the check instead of passing it.

*Mutation:* two, both outside the sample the test names. Setting
`config.VERSION` to `1.0.0rc1` — a copy the assertion never names,
reached only through the sweep — failed it. Then, with that mutation
still in place, tagging the tree `v1.0.0-mutation-probe` made it pass.
That second one is the load-bearing proof: it shows the bar is read from
release history rather than compiled in, because the same declaration is
legal the moment a 1.x release exists. The probe tag was deleted and the
version restored, both verified.

*Roles:* found=marshall prompt=marshall fix=claude test=claude run=mutation

### D101 — Closed: the write-safety primitives are POSIX by decision (High)

`_safe_write.py:203` calls `os.fchmod`; `_skill_install.py:34` builds
`os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW`. Neither exists on
Windows. A `windows-latest` probe on 2026-09-05 produced **165 failed,
1972 passed, 33 errors**, and 94 of those failures are those two
attributes — 81 `fchmod`, 13 `O_DIRECTORY`.

**What makes it High rather than a portability note.** These are the
security-relevant paths: the bounded, symlink-refusing write that the
D34/D36/D96 family exists to enforce, and the handle-based root the skill
installer opens once so every read is relative to it. The mechanism that
keeps an audited tree from redirecting where this agent writes is
implemented on file descriptors that Windows does not have. That is a
statement about the product's architecture, not about its tests.

**It also falsifies the reason the README gives.** The platform section
says Windows is unclaimed because "the test suite creates symlinks with
no platform guard". Symlink failures are not among the top causes at all.
The stated reason has been the wrong reason.

Open. `Operating System :: POSIX` remains the claim and the probe remains
`continue-on-error`, so nothing shipped is untrue — but the finding is
recorded rather than left in a wrap-up, and a release does not cut while
it is open. **Falsifier: pending** — it belongs to whoever decides
whether the answer is portable primitives or a stated architectural
limit, and naming a test before that decision would prejudge it.

**Half closed.** `_safe_write` no longer calls `os.fchmod` where it does
not exist; the call stays handle-based on POSIX, because `os.chmod` on
the staging path is the very time-of-check/time-of-use hole this module
closes, and the portable-looking swap would buy Windows by weakening
POSIX. Where the call is skipped the mode stays as `mkstemp` set it —
0600, stricter rather than looser.

**The rest is closed by decision, not by code.** Marshall, 2026-09-05:
*"do not break this tool to fix windows support."* `_skill_install` opens
its root with `O_DIRECTORY|O_NOFOLLOW` and works relative to that
descriptor, which is what makes a symlink swap between check and write
impossible (D18). Windows has no equivalent, and the portable rewrite —
validate a pathname, then write to it — is the hole itself.

So the limit is **stated rather than removed**: the write-safety
mechanism is POSIX by construction, `Operating System :: POSIX` stands,
and the probe stays `continue-on-error`. The rule is now in `RULES.md`:
an unsupported platform never buys green by weakening a guarantee the
supported platforms rely on.

What this entry corrects for the record is the *reason*. The README said
Windows was unclaimed because the suite creates unguarded symlinks.
Symlink failures were not among the top causes; 94 of 165 were these two
attributes. The stated reason was wrong even though the conclusion was
right.

*Closing test:* `test_the_package_claims_the_platform_it_is_tested_on`
and `test_ci_runs_only_platforms_the_package_claims` — they guard the
closure continuously, holding the classifier at POSIX and refusing a
Windows runner in any job that gates something.

*Falsifier proof: not applicable — closed by a decision to leave a platform unsupported, with no code change to revert.* The
`os.fchmod` guard is a portability edit whose absence changes nothing on
any platform the project claims, so a revert proof cannot fail for the
right reason on POSIX. What is asserted instead, continuously rather than
once: `test_the_package_claims_the_platform_it_is_tested_on` holds the
classifier at POSIX, and `test_ci_runs_only_platforms_the_package_claims`
refuses a Windows runner in any job that gates something. Those guard
against the closure being quietly widened, which is the risk here — not
against the fix regressing.

*Roles:* found=claude prompt=marshall fix=claude test=none run=ci
*Mutation:* none yet — the finding came from running the whole suite on a
platform nobody had run it on, not from breaking a member.

### D102 — Closed: two audit-test functions exceed the repo's own budgets (Low)

`tests/test_tree_chosen_spawn.py` — `_argv0` (17 lines, complexity 9,
cognitive 17) and `_tree_bin_modules` (25 lines, complexity 9, cognitive
18), both warn. Raised by this project's own code scanning on PR #171 and
resolved there without being acted on, because the cycle that produced
that file forbids Claude editing tests.

That was the correct action for the cycle and the wrong end state for the
ledger: a finding nobody may act on is still a finding. Filed so the
constraint is visible and the work is assignable to whoever owns tests.

**Assigned to Grok.** Codex is out of budget, and the rule recorded on
2026-09-05 moves the test-writer role to Grok rather than vacating it or
letting Claude cross into tests to clear a ledger.

**Closed.** `_argv0` is a dispatcher: Invocation argv lives in
`_invocation_argv0`, `subprocess.run` argv in `_subprocess_run_argv0`.
`_tree_bin_modules` walks files; `_tree_chosen_invocations` decides
whether an Invocation is tree-chosen. Both original functions read `ok`
under `detect_functions` (cognitive 17 → 2 and 18 → 3).

*Closing test:* `test_the_spawn_helpers_stay_inside_the_repo_budgets` in
`tests/test_tree_chosen_spawn.py`. It runs `detect_functions` on the
file and fails if any helper is warn or fail — the same detector that
produced the finding, on a member the test does not name.

*Roles:* found=ci prompt=marshall fix=grok test=grok run=local
*Mutation:* fold `_invocation_argv0` back into `_argv0`, or
`_tree_chosen_invocations` back into `_tree_bin_modules`. The cited
test fails without naming either original function.

### D103 — Closed: `_jobs` is over the cognitive warn line (Low)

`tests/test_platform_claim.py` — `_jobs` (36 lines, complexity 12,
cognitive 16), warn. Mine, on PR #169, resolved without being acted on
with the reasoning that splitting a 36-line indentation walk spreads one
algorithm across two functions for no reader benefit.

That reasoning may well be right. It is still a judgement made by the
author of the code against the project's own published thresholds, which
is the shape D99 is about. Filed so the call is reviewable rather than
resolved away in a PR thread.

**Closed.** Finding the section, skipping blanks and comments, and
grouping by indentation were three concerns in one function.
`_under_jobs` takes the first two: `_jobs` goes from cognitive 16 to 6,
and all three helpers in the file read `ok`. The reasoning offered in the
PR thread — that splitting helps no reader — was wrong, and the
thresholds were right.

*Closing test:* `test_ci_runs_only_platforms_the_package_claims` — it
passes over the split helpers, so the guard's behaviour is unchanged by
the refactor, which is the property a refactor must have.

*Falsifier proof: not applicable — the closing evidence is a measurement, and the behaviour is deliberately identical before and after.* `_jobs` went from cognitive 16 to 6 and
all three helpers read `ok` under this project's own `detect_functions`;
the behaviour the guard tests is deliberately identical before and after,
so no test can fail at the base for the right reason. A refactor that
changed behaviour would be a different entry.

*Roles:* found=ci prompt=marshall fix=unknown test=unknown run=none
*Mutation:* none, as D102. The entry exists because the author of the
code judged his own work against the published threshold and resolved
the thread, which is the D99 shape rather than a defect in a detector.

### D104 — Closed: two operator-named reads had no validation at all (High)

SonarCloud `pythonsecurity:S8707`, two instances, both MAJOR, and the
rule's own wording names this product's setting: *"LLMs running this code
with faulty CLI arguments can escape file system restrictions."*

- `config.py` — `--config` was read straight into `json.loads`.
- `baseline.py` — `--baseline` likewise.

They were the only two path-taking entry points that never went through
any validation. Every other path in this project is bounded by
`repository_path`; these two legitimately point *outside* the audited
tree, so bounding is the wrong control — and no control was the shipped
answer.

**The concrete harm was a hang, not a traversal.** `read_text` on a FIFO
blocks forever, and on `/dev/zero` consumes memory until the process
dies. Measured before the fix: a bare `read_text` on a FIFO had to be
killed at four seconds. "Denial-of-service via crafted config files" is
in this project's own published in-scope list, so the tool was vulnerable
to something it invites people to report.

`read_operator_file` opens the path **once** and checks and reads through
that handle — the discipline `_safe_write` already uses for writes.
`os.stat(path)` followed by `path.read_text()` resolves the name twice,
so what was measured and what is read can differ; `O_NONBLOCK` is what
makes the check reachable at all, since opening a FIFO for reading
otherwise blocks before any validation runs. It requires a regular file
and bounds the size.
Deliberately *not* a symlink refusal: the operator named the path and
controls it, and the audited tree's own default is a different question
that `discovered_config` already answers.

**The residual was resolved as a false positive, by Marshall, on
2026-09-05, and is recorded here rather than only in the dashboard.**
After the fix one `S8707` remained on `config.py`, because the rule's
remedy is to bound the path to a directory and `--config` legitimately
points outside the audited tree. The grounds, as entered on the issue:
the path is an operator-supplied CLI argument rather than tree content;
every tree-derived path here already goes through `repository_path`; the
call is validated through a single handle; and the exploitable behaviour
— the hang — is fixed and covered. Residual disclosure is bounded to
files that parse as this tool's own JSON schema.

That is a suppression, and this project counts suppressions as findings
when other people make them (`_conformance.SUPPRESSION_MARKERS` reads
`NOSONAR`). Writing it down is the difference between a judgement and a
silence: a reader of the code sees nothing, so the register carries it.
The other four SonarCloud vulnerabilities in this family closed as
**FIXED** rather than dismissed — three `S2612` and one `S8707`.

*Closing test:* `test_an_operator_named_path_must_be_a_regular_file` —
a FIFO and a device are refused at both doors rather than read.

*Roles:* found=ci prompt=marshall fix=claude test=claude run=none
*Mutation:* drop the `S_ISREG` check and the FIFO case hangs the suite
rather than failing it, which is why the test asserts the refusal type
rather than a timeout.

### D105 — Closed: "Update branch" cannot be used on this repository (Medium)

The `Every commit declares who wrote it` gate failed on PR #175 with no
agent at fault. The failing commit was the **merge that
`gh pr update-branch` created** — GitHub's own — and `%G?` reported `E`,
signature unverifiable, because GitHub's web-flow key is not in
`.github/allowed_signers`.

**The obvious fix was wrong and nearly shipped.** The trailer step uses
`--no-merges`; the signature step deliberately does not, and says why in
its own comment: *"a merge carries the conflict resolution its author
wrote, so an unsigned merge is unattested content, and skipping it let
exactly that through (found by audit)."* Adding `--no-merges` there to
make CI convenient would have undone an audit-driven control — the same
temptation as swapping `os.fchmod` for a path-based `chmod` earlier the
same day, and the same answer.

So this closes as a **process rule rather than a code change**: bring a
branch up to date by rebasing, never with the "Update branch" button or
`gh pr update-branch`. Recorded in `RULES.md`. The alternative — trusting
GitHub's signing key in `allowed_signers` — is a real option and is
deliberately not taken here, because it widens what the gate accepts to
buy a button.

*Closing test:* `test_the_signature_gate_still_checks_merge_commits` — it
pins the absence of `--no-merges` in the signature step, so the
convenient "fix" for the button fails loudly instead of landing.

*Falsifier proof: not applicable — nothing in the product changed; the guard pins a control against a future edit rather than defending one made here.*

*Roles:* found=claude prompt=marshall fix=none test=none run=ci
*Mutation:* none — nothing was edited. The evidence is PR #175's failing
run and the rebase that cleared it.

### D106 — Closed: two determinism assertions compare an expression with itself (Low)

`python:S5863`, twice, both MAJOR to SonarCloud and both real as written:

- `tests/test_three_presentations.py:116` — `assert render_html(report, records) == render_html(report, records)`
- `tests/test_evidence_properties.py:476` — `assert sweep() == sweep()`

The *intent* is sound and worth keeping: each calls a function twice and
asserts the results match, which is how determinism is tested here. The
*shape* is indistinguishable from the mistake the rule exists to catch —
a reader cannot tell a deliberate double invocation from a typo, and
neither can the analyser. Binding the two calls to named variables says
which one it is:

    first = render_html(report, records)
    second = render_html(report, records)
    assert first == second

These sit in test files. Codex holds the test-writer role, and the
role-failover rule recorded 2026-09-05 moves it to Grok only while Codex
is down — Codex is back, so this is his. Claude does not cross into
tests to clear a ledger.

Both tests now bind separate calls to `first` and `second`, then compare
the results with a message naming the determinism failure. Neither call
was removed and no suppression marker was added.

*Closing test:* `tests/test_three_presentations.py`:
`test_html_is_deterministic`; `tests/test_evidence_properties.py`:
`test_the_whole_sweep_is_deterministic`. These preserve the determinism
checks; they also pass before this clarity refactor and do not prove
SonarCloud issue resolution. The analyser's confirmation awaits CI.

*Roles:* found=ci prompt=marshall fix=codex test=codex run=codex
*Mutation:* none — this changes assertion clarity, not the tested
behaviour. Both independent invocations remain; no production mutation
or claim of a new population falsifier is made.

### D107 — Closed: two SonarCloud findings resolved as false positives (Low)

Recorded for the same reason D104 records its own: a resolution taken in
a dashboard is invisible to a reader of the code.

**`pythonsecurity:S8707`, `config.py`.** The same finding D104 closed. It
reopened under a new key because the one-handle rewrite moved the code
*after* the first resolution was applied, and SonarCloud tracked the
result as a new issue rather than the same one. Nothing about the code or
the reasoning changed. The lesson is sequencing: resolve a finding after
the code that produces it has settled, or the resolution is spent on a
line that is about to move.

**`pythonbugs:S2583`, `_evidence_view.py:197`.** The analyser reports
`if is_complete(score)` as always false. It is not: `status` has three
values — `insufficient`, `complete`, `incomplete` — and the two equality
checks above it are not exhaustive. Verified by calling
`status_sentence` with a complete score and getting the complete
sentence back. A genuine analyser error rather than a judgement call.

*Closing test:* `test_a_withheld_score_names_the_path_out` — it asserts
`"complete" in status_sentence(tiny)`, which is the exact branch the
analyser calls unreachable. The claim was checkable against a test that
already existed, and the first draft of this entry cited a test that did
not — caught by `test_every_closing_citation_names_a_test_that_exists`,
which is the guard for precisely that.

*Falsifier proof: not applicable — no code changed; two external findings were resolved and the grounds recorded.*

*Roles:* found=ci prompt=marshall fix=marshall test=none run=none
*Mutation:* none.

### D108 — Closed: the suppression scan reports markers it only reads about (Medium)

`SUPPRESSION_MARKERS` carries a comment promising exactly the thing it
did not do:

> Per language, because the vocabulary differs and a single regex over
> all of them matches prose: a `type: ignore` in a docstring explaining
> the convention is not a suppression, and neither is this comment.

Splitting the regexes per language was the *whole* mitigation, and it
does not mitigate this at all: `#\s*noqa\b` matches the marker wherever
it appears, docstring included. Four versions shipped with the promise
in the file and nothing enforcing it.

It surfaced the first time the rule ran where a false positive costs
something. `--staged` blocked a commit of `git_tools.py` whose only
offence was a docstring reading "would report a decade of accumulated
`# noqa` as though this commit had just written them" — a sentence
*about* suppressions, in the module that reads them. The conformance
record has carried the same exposure since 1.4.0, where it is quieter:
a spurious line in a report nobody is blocked by.

Both callers now go through one function, `_conformance.markers_in`,
which refuses a match that is quoted — immediately preceded by a
backtick or quote character, or inside an open backtick span. One rule,
asked twice, because a hook stricter than the gate it belongs to blocks
commits CI would pass.

The narrowing is deliberate and stated: a marker written into prose with
no quoting at all is still reported. Quoting is the reliable signal;
widening past it is guessing at English.

*Closing test:* `test_a_quoted_marker_mention_is_not_a_suppression` in
`tests/test_scope_conformance.py`.

*Roles:* found=claude prompt=marshall fix=claude test=grok run=grok
*Mutation:* reverting `_conformance.markers_in` to a bare
`pattern.search` makes `test_a_quoted_marker_mention_is_not_a_suppression`
fail: `suppressions_added({"m.py": [(1, "…`# noqa`…")]}, set())` reports
a backtick-quoted mention. The trailing-directive half stays green.

### D109 — Closed: a hollow test rode in because its neighbours were new (Medium)

Two defects, one cause, and the second is the one that matters.

**The instance.** `test_staged_refuses_flags_it_would_have_to_ignore`
asserted that the refused flag was named on stderr — `"--changed-only" in
err` — and passed on a tree where `--staged` did not exist as a flag at
all. argparse prints its usage banner on any error, and that banner lists
every flag the test names, `{json,markdown,html}` included. Exit 2 and a
matching substring were both satisfied by the parser rejecting `--staged`
itself. The test defended nothing.

Codex had already caught this shape one level down, before running out of
tokens: a bare `--changed-only` fails on argparse's `nargs`, not on the
refusal, so each case had to carry its argument. It did. The trap simply
existed again one level above, where the flag under test is the one that
does not exist at the base.

**The class.** `tools/prove_falsifiers.py` saw it and passed anyway. Its
added-file check asked whether *every* test in a new file passed at the
base; with fourteen real falsifiers beside it, the hollow one rode in. It
printed the evidence — `14 of 15 fail without the change` — and exited 0.
On the same run, the added-in-place check held each new test in
`test_scope_conformance.py` individually and named both.

So a test's obligation to falsify something depended on how new its
neighbours happened to be. That is the gate this project relies on to
keep its own tests honest, and 1 in 15 walked through it on the first
serious use.

Both callers now report every individual test that passes at the base.
The file-level `Covers existing behaviour:` escape is unchanged: a whole
file that is deliberately about pre-existing behaviour is still exempt,
stated rather than assumed. The refusal test now asserts the sentence
only this tool writes — `--staged does not take` — which no usage banner
contains.

*Closing test:* `tests/test_prove_falsifiers.py`:
`test_one_hollow_test_in_an_added_file_is_still_reported`. It stubs
`_prove` to report one pass among many failures against a real added
file and asserts the pass is named. Written before the fix and red
against it, reproducing the `14 of 15` line verbatim.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring the `len(nodes) == len(tests_in(...))` condition —
the whole-file rule — makes the closing test fail, because the single
passing node is no longer reported. Both test agents were unavailable
(Codex out of tokens, Grok finished and offline) and Marshall directed
the pre-commit work to be wrapped up, which is why test= names claude
here rather than a test agent.

### D110 — Closed: the README's images are invisible on PyPI (Low)

`pyproject.toml` sets `readme = "README.md"`, so the README *is* the PyPI
long_description. A repository-relative path has no repository to resolve
against there: `docs/cover.png` resolves against `pypi.org` and 404s, so
the image does not display. GitHub resolves the same path correctly,
which is why this is invisible from inside the repository.

**Correction to this entry's original evidence.** It first claimed the
live page had been checked and "contains no `.png` at all". That check
was not valid: `curl` against `pypi.org/project/maintainability-agent/`
returns a 3 KB challenge page with no description body in it — zero
occurrences of the word "maintainability", let alone an image. The
conclusion was drawn from a page that was never the project page. The
defect is real on the mechanism above, and the fix is the standard one,
but the verification claimed here did not happen and the entry should
not have said it did.

2.9.0 added a second image on the same terms.

The ordering is why this was filed open rather than fixed in the same
change. The fix is an absolute `raw.githubusercontent.com/.../main/` URL
for both images, and that URL cannot resolve until the files are on
`main`. Fixing it before the merge would have replaced two images that
render on GitHub with two that render nowhere, which is worse for the
reader actually looking — Marshall hit exactly that when the workflow
image was first added with an absolute URL and showed as broken.

Closed as the first change after 2.9.0 merged, once both URLs returned
200. Both are now absolute.

*Closing test:* `tests/test_readme_claims.py`:
`test_no_readme_image_is_repository_relative`. It asserts the property —
no image reference in the README is repository-relative — rather than
scraping a rendered page, which is what made the original evidence
worthless. A test that depends on fetching a third-party page proves
whatever that page felt like returning.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring either image to its `docs/...` path fails the
closing test by name. The check is a property of the file rather than of
a render, so it holds without reaching the network.

### D111 — Closed: writing about the escape phrase triggered it (Medium)

D108's defect, one layer up, found within the hour by fixing D109.

`prove_falsifiers` lets a test opt out of the revert proof by declaring
`Covers existing behaviour:` in its docstring. The phrase was matched as
a substring of the source, so a docstring *explaining* the escape
exempted the very test doing the explaining. D109's own falsifier —
written to prove the gate reports a hollow test — was reported as

    exempt — covers existing behaviour: `` escape still exempts a whole file that

a "reason" sliced out of a sentence about the mechanism. The gate
printed that line and passed, so the test written to close a hole in the
gate was excused by the same gate, on the strength of a sentence
describing it.

This is the same rule as D108 and the fix is the same shape:
`declares_exemption` refuses an occurrence that is quoted — preceded by
a backtick or quote character, or inside an open backtick span — and
both call sites go through it, so the file rule and the per-test rule
cannot disagree.

One correction during the fix, worth recording because it went the
wrong way first: the rule initially counted a docstring's own opening
`"""` as a quote and rejected a *legitimate* exemption Grok had written.
A guard that refuses real declarations is not stricter, it is broken.
Only a triple quote before the phrase reads as a delimiter now; a single
one reads as somebody quoting it mid-sentence.

*Closing test:* `tests/test_prove_falsifiers.py`:
`test_a_quoted_escape_phrase_does_not_exempt_anything`. It asserts a
backticked mention and a double-quoted mention exempt nothing, that a
bare declaration does, and that a docstring opener does not block one.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring `COVERS_EXISTING in text` makes the closing test
fail on its first assertion. Removing the triple-quote clause makes it
fail on its last, and re-breaks the exemption in
`test_a_real_trailing_directive_is_still_a_suppression`.

### D112 — Closed: Python was scored against its own comments and strings (High)

The flagship language, the one this project is written in, and the one
most of the calibration corpus is measured through.

`declaration_ranges` returned Python's **raw lines** to score complexity
against, while every other language received a comment- and
string-masked copy. The function's own docstring said as much — "JS/TS/
HTML score against a comment- and string-masked copy" — and Python was
simply not in that list. So every keyword in every comment and every
string literal counted as a decision.

A branchless four-line function scored **4**, its every point supplied by
one comment and one string. 384 branch points on this repository's own
121 files came from prose inside docstrings, which a line-local masker
would not have caught either: a triple-quoted string spans lines and
survives it.

Masking now uses `tokenize`, CPython's own lexer, so what counts as a
comment or a string is decided by the language rather than by a pattern
written from memory — which is how this arrived.

*Closing test:* `tests/test_python_complexity.py`:
`test_a_python_comment_is_not_a_branch`,
`test_a_string_literal_is_not_a_branch`,
`test_a_docstring_is_not_a_branch`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* returning `lines` instead of `mask_python_lines(lines)` in
`declaration_ranges` restores complexity 4 for the branchless function
and fails all three.

### D113 — Closed: Python's boolean operators were never counted (High)

The Python branch pattern looked for `&&` and `||` — C's operators, in a
language that spells them `and` and `or`. Every boolean operator in every
Python file this tool has ever measured was invisible: **3,199** of them
in this repository alone, and `if a and b or c` scored 1 where standard
cyclomatic complexity is 3.

Python now has its own branch set, derived from the language reference
rather than inherited from the C family. `case` counts and `match` does
not, by the arms-not-header rule shared with Go, PHP, Ruby and Fortran.

*Closing test:* `tests/test_python_complexity.py`:
`test_boolean_operators_are_decisions`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing `and|or` from `PYTHON_COMPLEXITY_RE` scores the
sample 2 instead of 4.

### D114 — Closed: the fix for D112 blanked the code inside f-strings (Medium)

Introduced by the repair, found by the same method that found the
original.

On Python 3.11 an f-string is a single `STRING` token, so blanking the
token whole removed the expressions written inside `{…}` — which are
code, and frequently the only place a ternary or a comprehension
appears. Found by hand-counting a function the oracle still disagreed on
after D112 and D113 were fixed: this project said 7 and the grammar says
11.

Only the literal text is blanked now; `{{` and `}}` are escaped braces
and hold nothing.

*Closing test:* `tests/test_python_complexity.py`:
`test_expressions_inside_an_f_string_are_counted` and
`test_the_literal_text_of_an_f_string_is_still_not_counted`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* blanking the whole token again scores the sample 1 instead
of 5.

### D115 — Closed: a `?` in type position was counted as a ternary, in five languages (High)

One defect, five spellings, and the third appearance of D78's shape.

- C# `int? v` — a nullable type
- TypeScript `title?: string` — an optional parameter
- Java `List<?>` — a generic wildcard
- PHP `?int $v` — a nullable type hint
- Swift `Int?` — an optional

Each decides nothing and each scored one. The first three share the
C-family pattern, so a single fix closed them; PHP and Swift carry their
own and were fixed beside it.

A ternary needs both halves, so a following `:` is now required. The cost
is a ternary split across lines, which is not counted — under-reporting,
which is the direction this project errs in, and it is stated beside the
pattern.

**lizard has this same defect in its TypeScript reader**, which is why
the divergence is declared rather than followed. A harness built to chase
agreement would have re-introduced the bug to match the oracle.

*Closing test:* `tests/test_grammar_constructs.py`:
`test_every_construct_agrees_with_an_independent_implementation` over the
C#, TypeScript, PHP and Swift fixtures.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* dropping the lookahead requiring a following colon scores
every optional parameter and nullable type in those fixtures as a
decision.

### D116 — Closed: unconditional constructs were counted as decisions (Medium)

`goto` in Go and PHP, and `loop` in Rust. All three transfer control
without deciding anything: a `goto` is an edge, and Rust's `loop` has no
condition — the `if … break` inside it is what decides.

All three were added in the twenty-four hours before the audit, each with
a confident justification written beside it. C had it right all along and
never counted `goto`, which is what the C fixture demonstrated.

*Closing test:* `tests/test_go_declarations.py`:
`test_goto_is_not_a_decision`; `tests/test_rust_declarations.py`:
`test_an_unconditional_loop_is_not_a_decision`;
`tests/test_php_declarations.py`: `test_do_while_and_match_are_branches`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring `goto` or `loop` to their patterns scores each
fixture one high.

### D117 — Closed: a multi-way header was counted beside its own arms (Medium)

Go's `select`, PHP's `do … while`, Swift's `repeat … while`, and Rust's
wildcard `_ =>` arm.

The rule was already written down for Fortran — `select case` is a header
whose *cases* are the branches, and counting both scores the construct
and its first arm — and it was not applied when four more languages were
added. A `select` with two cases has two paths; `select {}` with no cases
blocks and decides nothing. A `do { … } while (cond)` is one loop with
one condition, carried by its `while`. A wildcard arm is a default, and a
default is not a test.

The Go case is the sharpest: the C-family pattern already counted `case`,
so Go's select dispatch was **measured correctly before it was touched**.
A test written from a wrong intuition failed, and the code was changed to
satisfy the test rather than the grammar.

*Closing test:* `tests/test_go_declarations.py`:
`test_select_is_counted_at_its_cases_not_its_header`;
`tests/test_rust_declarations.py`:
`test_a_wildcard_match_arm_is_not_a_decision`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring `select`, `do` or `repeat` to their patterns, or
counting a wildcard arm, scores those fixtures one high.

### D118 — Closed: Rust refused to count the operator that returns early (Medium)

`?` was excluded on the stated reasoning that it "propagates an error and
decides nothing", by analogy with JavaScript's optional chaining (D78).
The analogy is false. `let x = f()?` continues or returns early, and the
operator expands to a `match` with two arms — two paths, one decision.
That idiomatic Rust is full of them is a fact about Rust, not a reason to
under-count it.

*Closing test:* `tests/test_rust_declarations.py`:
`test_the_error_operator_is_a_decision`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* excluding the operator from `RUST_COMPLEXITY_RE` scores the
fixture 1 instead of 2.

### D119 — Closed: no measurement was ever checked against a second implementation (High)

The defect behind the eight above, and the only one about method rather
than code.

Every branch keyword set in this project was written from somebody's
knowledge of a language and checked against examples written from the
same knowledge. That is not evidence; it reads as evidence because the
prose around it is confident, which is worse than reading as a guess.

The measurable consequence: on this repository's own source, this project
agreed with an independent implementation on **448 of 985 declarations —
45%**. It is now 968 of 1000.

The instinct existed and stayed a one-off.
`test_the_built_in_reading_agrees_with_lizard` cross-checked *one*
Fortran function and pinned the number rather than running the tool —
"so the suite stays offline", though lizard is a local library. One
function, one language, frozen. This class of defect survived in nine
others.

`tools/complexity_oracle.py` compares per declaration across a tree, and
`tests/fixtures/grammar/` holds one fixture per language exercising the
constructs its specification defines, checked construct-by-construct in
CI. Thirteen languages are covered, and the coverage is counted in
*readers* rather than fixtures — see D120, which is the language a count
of fixtures missed. Only COBOL has no independent implementation
available; it is named in the test as checked against itself alone, which
is stated rather than implied. HTML and fixed-form Fortran share their
branch readers with languages that are checked.

Divergences are **declared with the grammar reasoning that settles
them**, never silently absorbed: the check exists to hold this project to
the specification, not to lizard. Chasing a second implementation is the
same error as trusting the first, with an extra step — and lizard's own
TypeScript reader carries D115.

*Closing test:* `tests/test_grammar_constructs.py`:
`test_every_construct_agrees_with_an_independent_implementation`,
`test_the_fixture_covers_more_than_one_construct`, and
`test_every_declared_divergence_is_still_real`.

*Roles:* found=marshall prompt=marshall fix=claude test=claude run=claude
*Mutation:* deleting a fixture, or shrinking one below five constructs,
fails the coverage guard; a divergence that stops being real fails the
staleness guard.

### D120 — Closed: Python counted the wildcard `case _`, which five other languages correctly do not (Medium)

Found by the check D119 built, one language after it was believed
finished — which is the argument for the check.

**Python had no grammar fixture.** Twelve languages were added to
`tests/fixtures/grammar/` and the flagship language — the one this
project is written in, and the one carrying D112, D113 and D114 — was
not among them. The guard that should have caught that,
`test_there_is_a_grammar_fixture_to_check`, only asserts the directory is
non-empty, which twelve fixtures satisfy while a thirteenth language goes
unchecked. Coverage is now counted in **branch readers**, since the
reader is the thing that can be wrong, and a reader with no second
implementation has to be named.

With the fixture in place, eleven of twelve constructs agreed exactly.
The twelfth: `case _` was counted as a decision. It is Python's
`default` — a wildcard always matches, so it adds a path without a
decision to reach it. This project already refuses to count Go's
`default:`, Rust's `_ =>` and the C family's `default:` (D117), so the
same dispatch scored differently depending on which language it happened
to be written in.

lizard counts it, so this is a **declared divergence** rather than a
silent one, and the reasoning is the grammar plus this project's own
rule — not the second implementation. `case _ if guard:` is excluded here
and counted by its `if`, which is the decision; `case _name:` is an
ordinary capture pattern and `case [_, x]:` still has a pattern to match,
and both still count.

*Closing test:* `tests/test_python_complexity.py`:
`test_the_wildcard_case_is_a_default_and_not_a_decision`;
`tests/test_grammar_constructs.py`:
`test_every_branch_reader_is_checked_against_a_second_opinion` and
`test_no_declared_gap_actually_has_a_fixture`.

*Roles:* found=claude prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring a bare `case` to `PYTHON_COMPLEXITY_RE` scores the
wildcard arm as a decision; deleting the Python fixture, or removing a
reader from the declared-gap map while it has no fixture, fails the
coverage guard.

### D121 — Closed: an empty parameter set was reported as a pass (Medium)

The grammar checks are parametrized over the fixture directory. Delete
every fixture and pytest marks those tests skipped rather than failing
them — and a skip exits 0, which every gate reads as green. So the
checks D115, D119 and D120 cite defended nothing once the evidence they
read was removed, which is the precise failure `test_the_fixture_covers_
more_than_one_construct` was written to prevent: *"the cheapest way to
make the check above pass is to shrink what it looks at."* Shrinking it
to zero was cheaper still, and invisible.

**It passed locally and failed in CI, and the difference is the point.**
pytest 8.3.4 treats a node id whose parameter set is empty as a usage
error and exits non-zero; pytest 9.1.1 creates a skipped placeholder and
exits 0. The local interpreter said the falsifiers were proven. The gate
on the pull request said four of them were not. The gate was right.

`empty_parameter_set_mark = "fail_at_collect"` in `pyproject.toml` says
this suite-wide, and **it was not enough**, which is the part worth
keeping. The first fix set only that, CI came back failing in exactly
the same way, and the reason is that the falsifier gate reverts every
file except the ones defining the cited tests — `pyproject.toml`
included. *A gate that reverts your configuration cannot be satisfied by
configuration.* The guard has to live in the file under test, so
`_fixtures()` now raises when the directory is empty, and the setting
stays as the suite-wide backstop.

Absence read as a pass is the defect this project keeps finding in
itself, and this is the same sentence one layer down: the report says so
for an unparsed language, `--check` says so for a language with no
scanner, and the test suite said nothing at all.

*Closing test:* `tests/test_grammar_constructs.py`:
`test_there_is_a_grammar_fixture_to_check`, and the parametrized
`test_every_construct_agrees_with_an_independent_implementation` — with
`tests/fixtures/grammar/` emptied, `_fixtures()` raises and collection
errors, where before the parametrized checks skipped and reported a
pass. Verified under pytest 9 with `empty_parameter_set_mark` forced
back to `skip`, which is the state the falsifier gate reverts to.

*Roles:* found=ci prompt=marshall fix=claude test=claude run=claude
*Mutation:* returning `[]` from `_fixtures()` instead of raising makes
an emptied fixture directory report green on pytest 9, with or without
the `pyproject.toml` setting.

### D122 — Closed: f-strings were not masked at all on Python 3.12 and later (High)

D112 again, in the one place the fix for it did not reach, and on the
versions most people run.

PEP 701 changed how an f-string is tokenised. Through 3.11 the whole
literal is a single `STRING` token whose braces have to be walked by
hand, which is what D114 built. From 3.12 the tokeniser does that walk
itself: the prose arrives as `FSTRING_MIDDLE` tokens and the code
between the braces as ordinary ones. The masker recognised only the 3.11
shape, so on 3.12+ an f-string matched neither branch and passed through
**entirely unmasked**.

`f"check for errors and warnings: {value}"` scored 3 — its `for` and its
`and` counted as decisions in a branchless function.

**This project's development interpreter is 3.11 and its CI runs 3.12**,
so the whole suite was green locally while the shipped behaviour was
wrong for every user on a current Python. The macOS job caught it. The
Linux job would have, had the lint step not failed first and stopped it.

*Closing test:* `tests/test_python_complexity.py`:
`test_an_f_string_is_masked_on_every_supported_python`, which asserts
both halves — prose not counted, braces counted — because a fix for
either alone has already broken the other (D114).

*Roles:* found=ci prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing `FSTRING_MIDDLE` from the blanked token types
scores the prose sample 3 instead of 1 on any Python 3.12 or later.

### D123 — Closed: the README told readers that four parsed languages were not parsed (Medium)

Found by Marshall reading the shipped page, three lines below the table
that contradicts it.

The language-support section lists Go, Rust, PHP and Ruby as parsed, with
a scanner and a fidelity note for each. The paragraph immediately after
the table read:

> Any language **not** in that table — Go, Rust, Ruby, PHP, Kotlin, and
> the rest — is **not parsed for declarations by the built-in scanner.**
> Its files still count toward repo size, but the built-ins produce no
> function-size, complexity, duplication or dead-code findings for them.

Four of the languages named are in the table. A reader deciding whether
this tool was worth pointing at a Go repository would have been told,
by the release that shipped Go support, that it does nothing for Go.

`docs/roadmap.md` carried the same sentence in the other direction —
"no scanner is scheduled for any of them", naming Go, Rust, Ruby and PHP
in the release that wrote all four scanners.

A third instance sat in "What it analyzes": *"function size and
complexity — exact ranges for Python via `ast`, brace-bounded for
JS/TS/JSX/TSX/HTML"*, which silently omits the eleven other languages
with dedicated scanners. Not a contradiction, but the same understatement
of the product, and it had drifted twice already. That bullet no longer
enumerates languages at all — it points at the table, so there is one
list to keep true rather than three.

All three survived because the claim and its contradiction are far apart
and each reads correctly alone. The lead paragraph of the README *was*
guarded (D120's sibling check) and this paragraph was not: the guard
asked whether every parsed language is **named**, and the failure here is
a language named in the wrong sentence.

`test_no_parsed_language_is_named_as_unparsed` now reads the paragraph
that makes the negative claim, in both files, and holds it against the
languages the scanner actually reads. It asserts the marker sentence
still exists first, so the guard fails loudly if the prose moves rather
than silently checking nothing.

*Closing test:* `tests/test_claimed_languages.py`:
`test_no_parsed_language_is_named_as_unparsed`.

*Roles:* found=marshall prompt=marshall fix=claude test=claude run=claude
*Mutation:* restoring either sentence's original language list fails with
the four languages named — verified against the README's original text
before committing.

### D124 — Closed: the release checklist omitted a step its own gate requires (Low)

The `v2.11.0` tag was pushed and the release build failed on
`test_the_release_plan_table_is_measured_not_remembered`: the plan still
named `v2.10.0` as the last tagged version.

The guard worked exactly as designed and caught it **before** anything
reached PyPI — the publish and GitHub-Release jobs were skipped, so no
artifact was distributed and the version number stayed reusable.

The cause is a checklist that does not name the step. `release.yml`
documented three: bump the version, add the changelog entry and merge,
then tag. Nothing said to re-measure `docs/release-plan.md` in that same
commit, and the row cannot be updated afterwards — the test compares it
against `git tag`, and the tag is cut from the commit that carries the
row. So the omission is invisible on `main` and only appears once the tag
exists, which is the most expensive moment to find it.

The checklist now names it as step 3, with the reason, so the next person
reading the procedure does not have to rediscover the ordering the way
this release did. The counts in the same table were re-measured while
there: 29,392 lines across 122 modules, 2,359 tests across 205 files.

*Closing test:* `tests/test_release_plan.py`:
`test_the_release_plan_table_is_measured_not_remembered`, which already
existed and already failed correctly. The fix here is the procedure, not
the guard.

*Roles:* found=ci prompt=marshall fix=claude test=claude run=claude
*Mutation:* reverting the "Last tagged version" row to `v2.10.0` fails
the guard whenever a `v2.11.0` tag exists.

### D125 — Closed: every method on every generic Go type was invisible (High)

Go 1.18 added generic types, and `docs/languages/go.md` said a generic
receiver "reports through its base name, `Store`". It reported nothing.

The receiver pattern required `)` immediately after the type name, and
`func (s *Store[T]) Get` puts `[T]` between them, so no method on any
generic type was ever found. `_mask_generics` did not help — it blanks
`<…>`, which Go does not use.

The suite covered the generic *function* form,
`test_a_generic_function_is_read_through_its_type_parameters`, and never
the receiver. So the page was the only thing asserting the behaviour,
and the page was wrong — D123's shape, in code rather than prose.

**The oracle could not have caught this.** lizard does not find these
methods either: on the fixture it returns nothing for
`genericMethod`. A construct both implementations miss is invisible to a
check built on their agreement, which is the limit stated for PHP `match`
(D119) meeting a real defect rather than a hypothetical one.

A qualified receiver (`func (s *pkg.Store)`) is deliberately still not
matched: Go requires a method's receiver base type to live in the same
package, so that form does not compile and is not a gap.

*Closing test:* `tests/test_go_declarations.py`:
`test_a_generic_method_is_found_through_its_base_type`,
`test_a_generic_method_with_two_parameters_is_found`,
`test_a_value_receiver_generic_method_is_found`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing `(?:\[[^\]]*\])?` from `_GO_METHOD_RE` returns
only the non-generic method from the fixture.

### D126 — Closed: an assigned `if` closed the Ruby method at the wrong line (High)

Not an under-count. It reported **a different function than the one in
the file**.

An opener counted only when its keyword led the stripped line, which
correctly ignores the modifier form `return 0 if x`. It also ignored
`x = if cond`, which is an *expression* in Ruby and does need its own
`end`. The inner `end` therefore dropped depth to zero and the method was
reported as finishing there:

    def assign_if(cond)      # 8 lines
      x = if cond
            1
          else
            2
          end                # reported as the end of the method
      x + 1                  # outside the reported range
    end

`assign_if` came back as 6 lines instead of 8, with its last two lines
attributed to nothing. The Ruby page's own warning applies: a miscounted
`end` shifts every range after it.

`x = case v`, `x = begin` and the `@memo ||= begin` memoisation idiom are
the same shape and were equally wrong. The keyword must sit immediately
after the assignment operator, which is what keeps the genuine modifier
`x = 1 if cond` opening nothing — asserted beside the fix.

lizard agrees at 2 once the construct is in the fixture, so this one the
oracle *would* have caught. It was not in the fixture, because the
fixture was written from the same knowledge as the scanner.

*Closing test:* `tests/test_ruby_declarations.py`:
`test_an_assigned_if_does_not_close_the_method_early`,
`test_an_assigned_case_does_not_close_the_method_early`,
`test_an_or_assigned_begin_does_not_close_the_method_early`, and
`test_a_modifier_if_after_an_assignment_still_opens_nothing` as the
guard against over-correcting.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing `_RB_ASSIGNED_OPENER_RE` from `_opens` reports
`assign_if` as 6 lines of 8.

### D127 — Closed: PHP's Elvis operator fell through the hole the nullable fix opened (Medium)

`$x ?: $y` is PHP's short ternary and scored 0.

D115 made a ternary require a following `:` so that `?int` nullable type
hints stop counting. PHP spells its Elvis operator with exactly the two
characters that rule excludes, so fixing one defect created another in
the same expression. The fixture had `$v > 0 ? 1 : 2` and `??` and not
`?:`.

Counting the long form and not the short one would make a score depend on
which spelling a codebase prefers — the same argument already written
down for PHP's word operators.

lizard does not count it either, so it is a **declared divergence** with
the grammar reasoning, not a silent one.

*Closing test:* `tests/test_php_declarations.py`:
`test_the_elvis_operator_is_a_decision`, which asserts the neighbours
that must keep working — the long ternary, `??`, and `?int` — because
one rule covers all four.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing `\?:` from `PHP_COMPLEXITY_RE` scores the fixture's
`elvisOperator` 1 instead of 2.

### D128 — Closed: Rust's `let … else` decided nothing (Medium)

Stable since Rust 1.65 and the idiomatic early return for a refutable
pattern: the binding succeeds, or the `else` block diverges. Two paths,
one decision — and no `if` token anywhere in it, so nothing in a keyword
set was ever going to see it. The fixture had `if let`, `while let` and
`?`, but not `let … else`.

The fix carries its own trap, and the test pins it: `if let … else` and
`while let … else` contain both a `let` and an `else` on one line, and
their decision is already counted by the `if`/`while`. Counting the
`let … else` shape there too would score them twice, so the pattern
excludes it by lookbehind.

lizard does not count `let … else`, so this is a declared divergence.

*Closing test:* `tests/test_rust_declarations.py`:
`test_a_let_else_is_a_decision`.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=claude
*Mutation:* removing the `let … else` alternative from
`RUST_COMPLEXITY_RE` scores the fixture's `let_else` 1 instead of 2;
removing the lookbehinds scores `if let … else` 2 instead of 1.

### D129 — Closed: the grammar fixtures were a sample, and the page called them the specification (Medium)

`docs/language-support.md` said each fixture "exercises the control-flow
constructs that language's specification defines". They exercise the
constructs *I already knew about*, written from the same knowledge as the
scanners they check — which is the exact failure D119 was opened to end,
surviving one layer up.

The evidence is D125–D128: four defects, and **none of their constructs
were in the fixtures**. A generic Go receiver, an assigned Ruby `if`,
PHP's Elvis operator, Rust's `let … else`. Agreement with an independent
implementation on a sample of my own choosing is not coverage of a
grammar, and the page claimed otherwise.

All four constructs are now in the fixtures. The claim on the page is
narrowed to what is true: the fixtures exercise a *set* of constructs
from each specification, the set grows when a gap is found, and the
comparison says nothing about the constructs it does not contain.

D125 also fixes the ceiling on this method rather than the floor: lizard
finds no generic Go method either, so no amount of fixture coverage would
have surfaced that one through agreement alone.

*Closing test:* `tests/test_grammar_constructs.py`:
`test_every_construct_agrees_with_an_independent_implementation` over the
four added constructs, and `test_every_declared_divergence_is_still_real`
over the two divergences they introduced.

*Roles:* found=grok prompt=marshall fix=claude test=claude run=claude
*Mutation:* deleting the four added fixture functions restores a suite
that passes while D125–D128 are all present.

### D130 — Open: `--sarif-input` is the third operator-named read D104 claimed did not exist (High)

D104 closed on the claim that `--config` and `--baseline` were *the
only two* path-taking entry points that never went through any
validation. They were not. `--sarif-input` is the same kind of
operator-named path — repeatable, allowed outside `--root`, ingested
into the published report — and it is still:

    json.loads(Path(path).read_text(encoding="utf-8"))

in `sarif.read_sarif_inputs`, called from `cli.py` on `args.sarif_input`
before `build_report`. No regular-file check, no size cap, no one
handle, no `O_NONBLOCK`. A FIFO hangs. `/dev/zero` reads until memory
dies. A directory or a missing file is an uncaught `IsADirectoryError`
or `FileNotFoundError`. A symlink is followed.

That is the hang D104 measured on `--config` and then listed as closed.
`SECURITY.md` names this flag. `tests/test_sarif.py` only parses a
well-formed fixture. Sonar will not reopen D104: the rule keyed the two
call sites that were patched.

The class, not the instance: every CLI argument that *reads* a file the
operator named. Writes (`--output`, `--write-baseline`) go through
`write_artifact` and are a different population. `--conformance` is a
revspec, not a file.

*Roles:* found=grok prompt=marshall fix=none test=none run=none
*Mutation:* pending with the test. The falsifier is a FIFO (or
`/dev/zero`) passed as `--sarif-input`; it must refuse rather than
hang, the way `--config` now does. A test that hangs cannot fail
cleanly, so the proof is the exception type, as D104's own tests
already say.

### D131 — Open: `read_operator_file` was not made the read primitive (Medium)

D104 built a one-handle reader and applied it to the two Sonar hits.
Every other read is still `exists` / `is_file` / `is_symlink` and then
`read_text` on the name — the sequence `_safe_write` and
`read_operator_file` exist to forbid.

The always-on case is history. Every successful CLI or MCP audit
reaches `read_history`:

    mkdir -p .maintainability
    mkfifo .maintainability/history.jsonl
    maintainability-agent --root . --format json

`history_path.exists()` is true, so the run records; `attach_history_views`
then `read_text`s the FIFO and blocks. Git cannot store a FIFO, so this
is a local or agent-written tree, not a merged blob. D19 already treated
a FIFO as a hang that must not be opened.

The same name-then-open sequence, same hang:

- `_first_run` labour / test-command persist: `is_symlink` then
  `exists` then `read_text` on `maintainability-agent.json`
- `_user_config._read_json_object`: no check at all on the XDG config
- `_mcp_audit._refuse_clobbering_non_baseline`: `repository_path`
  accepts an in-tree FIFO, then `read_text` hangs on MCP
  `write_baseline=True`
- `write_bounded` append and `_refuse_nonjson_clobber`: `is_file` then
  `read_text`, so a swap to a FIFO between the check and the open is
  the TOCTOU those helpers were written to close

A committed multi-gigabyte `history.jsonl` is the git-shippable half:
`read_operator_file` would refuse at 8 MiB; this path never calls it.

*Roles:* found=grok prompt=marshall fix=none test=none run=none
*Mutation:* pending with the test. The population is every
`read_text` / `open` of a path that is not `read_operator_file` and
not a handle already bound by `_safe_write`. Mutate a member the
closing test does not name — history is the always-on one; first-run
or user-config is the one outside the sample.

### D132 — Open: a cognitive-only `--check` fail still prints a negative line overage (Medium)

Grok's audit of `--check` found a short complex function rendering
as `-71 over` because `over_by` was always `lines - max_function_lines`.
The merge fixed the complexity-versus-length case and stopped
hardcoding JSON `scored: false`. It did not name cognitive complexity
as a budget.

`_DECLARATION_BUDGETS` is length and cyclomatic only. A function that
fails `max_cognitive_complexity` while remaining under both of those
produces an empty breach list, then the fallback:

    over_by = metric.lines - fallback   # the length budget it is inside

Reproduction, current main / this branch: `max_cognitive_complexity=1`,
a seven-line nest of `if`s, `max_function_lines=80`, `max_complexity=50`.
Result: `over_by: -73`, render `✗ nested:1 — -73 over`. The finding is
real; the figure is about a budget that did not fail.

The comment on `_breaches_for` says a figure has to be about the thing
that failed or it is worse than no figure. The fallback reintroduces
the thing the comment says was removed.

*Roles:* found=grok prompt=marshall fix=none test=none run=none
*Mutation:* pending with the test. A function over the cognitive
budget and under the length and cyclomatic budgets must not report a
negative line `over_by`. Restoring the length fallback as the only
breach, or omitting cognitive from `_DECLARATION_BUDGETS`, is the
mutation.

## Disposition

**D130, D131 and D132 are open.** They are the remainder of Grok's
audit of the twenty commits on `main` after 2.8.0. D125–D129 (the
2.11.0 language findings from that same audit) are already closed on
this branch. D130 is the class D104 claimed to close: `--sarif-input`
is still a bare operator-named read. D131 is the same class one layer
down: `read_operator_file` was not made the read primitive. D132 is
the `--check` residual: a cognitive-only fail still prints a negative
line overage. D124 is a release-checklist omission that cost a build
and no artifact: the gate held, the tag was re-pointed. D123 is the
shipped README contradicting its own table, found by Marshall reading
the page rather than by any check. D121 and D122 were found by CI on
the pull request that shipped the rest, after a green local suite — an
empty parameter set reported as a pass, and f-strings unmasked on
every Python from 3.12. Both are the same shape as the audit that found
them: a check that could not fail, and a fix that reached one
interpreter. D112 through D120 record a complexity audit that found
this project measuring Python against its own comments, missing its
boolean operators, and reading a `?` in type position as a ternary in
five languages — nine entries, of which D119 is the method failure
behind the other eight, and D120 was found by the check D119 built.
D110 closed once 2.9.0 put the images on `main` and both absolute URLs
returned 200. D109 closed the hollow test and the gate hole that let
it through, and D111 closed the escape phrase that the gate matched
inside prose about itself. D108's closing test has landed. D106
preserves both determinism checks with explicit double invocations
and failure messages. SonarCloud confirmation awaits CI. D107 records
two SonarCloud false-positive resolutions in the same turn they were
taken.

Everything before them is closed. D102 closed by splitting the two helpers that
were over the cognitive warn line; D101 and D103 closed the day they
were filed — D103 by splitting `_jobs`, D101 by Marshall's decision that
an unsupported platform is a stated limit and never a reason to weaken
the supported ones. All three were filed 2026-09-05 after
Marshall asked "what is my rule" and the answer was the one being broken.
A Windows probe had produced a High finding about the write-safety path,
and two warn-level findings had been resolved in PR threads without being
acted on — and all three were reported in a wrap-up as "still open"
rather than filed, which is the exact inversion of the rule at
RULES.md:426. **2.8.0 was then tagged and released with them open**,
against "no release until the known-defect ledger is empty". The release
is not withdrawn; the entries are filed and the ledger gates the next one.

Until 2026-09-05 the ledger was empty. D100 was the last to close,
on 2026-08-28: the artifact had promoted itself to a 1.0 release
candidate with no recorded authorization, and the entry that did it was
the entry written to stop exactly that. It is the fifth round running in
which the defect was in a fix rather than in the code the fix repaired,
and the first in which the register could not say who wrote the fix.

D89 closed the same day, when
the `resolve-constraints` job produced the Linux closure the gating jobs
had been pinned against a macOS resolution of. Its `xfail(strict=True)`
residual became `XPASS(strict)` on the day the file landed, which is the
behaviour that marker exists for: it fails when the situation is fixed,
so the fix cannot be taken while the marker is left behind.

This page reached an empty ledger twice and gave it back twice, which is
the useful part. An audit observed that the register can be empty while
the proof it cites is failing in CI, and that "0 open" was being read as
"known good". A closure that does not survive being checked is not a
closure.

**Where the rest came from.** D32 through D46 came from
two independent security audits on 2026-08-23 and closed over the two
days after; D47 through D49 came from the chat-surface work that
preceded them; D50 through D55 came from UAT preparation on 2026-08-25
— one from Marshall reading the question set and five from a Codex
audit of the whole repository; D56 through D62 came from a Grok audit of
the whole repository on 2026-08-26, which also reopened D38. Its
verdict was that the register was "an empty ledger, not an empty
defect list", and on every finding it was right. D63 came from Marshall
asking who the product is for, on 2026-08-26. D64 through D70 came from
a second round of both audits on 2026-08-26, run against the fixes for
the first — four of the seven reopened an entry that had already been
closed once, and three of those reopens went through the *closing test*
rather than around the fix.

**D70 is the one worth reading twice.** The local baseline this project
diffs every change against — 101 failures and 191 errors, carried run
after run as "known" — was a single line in seven test fixtures pinning
`PATH=/usr/bin:/bin`, which on this project's own development machine
resolves to Xcode's stub rather than to git. None of those 292 results
said anything about the product, and any real regression landing in
those files had 292 places to hide. The discipline of diffing against a
baseline was working exactly as designed and was protecting a number
that meant nothing. The count is derived from the headings above and checked
by `test_the_disposition_names_the_entries_that_are_open`, which
required this sentence rather than an omission — with nothing open, a
disposition that simply lists no entries reads exactly like a parser
that stopped working. D34 through D37 were
filed by the same 2026-08-23 security pass and have since closed; this
paragraph named them as open for two days after they were not, which is
the register describing a state a reader cannot verify from its own
headings. The count is now derived from the headings above rather than
carried in prose, and `test_the_disposition_names_the_entries_that_are_open`
fails if the two disagree.

Those four are the reason v1.0 does not cut. Two are the classes this register already
paid to close and never applied everywhere: D18 bound the skill installer's
writes by descriptor, and config, history and baseline still open by name;
D20 bounded `paths.history`, and `class_dirs` and `expand_files` still take
unbounded paths from the audited tree. One, D35, is a trust inversion —
`product-intent.md` P1 says a *user* enables tool acquisition, and a
repository config overrides the user tier, so a pull request can make the
host run `npx --yes`.

The lesson is not that the fixes were wrong. It is that each was applied to
the seam an audit happened to be looking at. "Close the class" means every
door that shares the primitive, and three rounds of chat-surface auditing
never looked at the write primitives at all.

D28 and D29 were opened and closed on 2026-08-22
under the standing rule that a release ships only from an empty known-defect
ledger; filing them here rather than leaving them in a chat message is what
made them countable. D30 and D31 came from the audit of D21–D27 and are the
most instructive pair in the register: both are defects *in the fixes*, found
because the fixes were audited rather than trusted. D30 is a precondition that
guarded one door of four. D31 is a check that verified a falsifier existed
without verifying a reader could find it. D32 is the pair's own audit round:
a refusal that read correctly in-process and arrived at the client as an
internal error, a CLI that crashed where the chat doors refused politely, and
a title that claimed more than its fix delivered. D33 is the round after that,
and the pattern held a fourth time: a check that verified a citation named a
test, satisfied by the filename in the path; a refusal translated on one layer
of two; two parsers reading one file to opposite conclusions.

Four rounds running, every defect has been in a fix rather than in the code it
repaired. That is not a run of bad luck. A fix is written by someone who has
just convinced themselves they understand the problem, and it is tested by
someone in that same state — so the test tends to assert the thing the author
was already thinking about. Auditing a fix as hard as the thing it repairs is
the only step that has reliably caught this, and every round of it has paid.

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

"""Which layer each module belongs to, and why it belongs there.

Split from `test_architecture.py` in 1.10.1, which had reached this
project's own 500-line file gate — the same reason `test_release_plan.py`
and `test_readme_claims.py` were split out before it. The gate caught it
on the addition of one module (`_hostile_prompt`, ADR 013), which is the
point at which a file at its limit stops being a file with headroom.

The data lives apart from the assertions deliberately. These sets are the
*claim* — this module belongs to that layer, for this stated reason — and
`test_architecture.py` is the enforcement that reads the real import
graph and holds the claim to it. A reader settling "where does this go"
wants the sets and the reasons; a reader asking "is it true" wants the
tests. Neither should have to scroll past the other.

Every set is compared against `docs/architecture.md` in both directions,
so a module named here and missing from that document's diagram fails the
build, and so does the reverse.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "maintainability_audit"

# `_runner` sits in foundations beside `git_tools` for the same reason:
# both spawn processes and depend on nothing internal. Rule 7 names
# those two plus `_backfill` (assembly; git for history backfill).
# Keeping the foundation spawners in one layer is what makes the
# analyzer half of that rule checkable.
FOUNDATIONS = {"_metrics_types", "_masking", "_hotspots", "_scan_history", "config",
               # `_config_defaults` is the shipped default configuration,
               # split from `config` in 1.1.0: data with no internal
               # imports, which `config` re-exports.
               "_config_defaults",
               "git_tools", "instructions", "_semantic_policy",
               # `_user_config` is the XDG user tier and its state (D13):
               # file reads and atomic writes, no internal imports.
               "_user_config",
               # `_stored_grants` decides whether a persisted root grant
               # still names the directory the user consented to. A
               # foundation because both the writer (`_user_config`) and
               # the reader (`_mcp_audit`) must reach the same rule, and
               # four versions of it were broken by the two sides
               # comparing paths their own way (D79).
               "_stored_grants",
               # `_safe_write` is the one way this agent writes into a
               # tree it is auditing: bounded, symlink-refusing, staged
               # then renamed so no existing inode is ever opened for
               # writing. A foundation because every writing layer above
               # must reach it and it may reach nothing but `config`
               # (D34).
               "_safe_write",
               # ADR 009's structured identity and matching relation is a
               # foundation shared by the gate, recurrence and presentation.
               "_finding_match",
               # `_runner` sits beside `git_tools`: both spawn processes and
               # import nothing internal. `_catalog` is analyzer selection
               # data -- a leaf that reads the shipped catalog and nothing
               # else.
               "_runner", "_catalog"}
# `_xml` reads analyzer XML and refuses what it will not parse — a
# parser with no internal imports, so it sits with the other
# parsers rather than with the adapters that call it (D46).
# The declaration scanners are one module per language over a shared
# brace core (1.1.0): `_ranges_core` owns the rule that a range is
# bounded by its own body, and `_ranges_js`, `_ranges_java` and
# `_ranges_c` own one language's patterns each. They sit together in
# parsing rather than the core sitting in foundations, because the
# family is one concern and the next language is a sibling, not a new
# layer.
PARSING = {"source", "declarations", "_cognitive", "_tokens", "_xml",
           "_ranges_core", "_ranges_js", "_ranges_java", "_ranges_c",
           "_ranges_cpp", "_ranges_csharp", "_ranges_fortran", "_ranges_swift"}
# ADR 003: `_semantic` normalizes and classifies; `_semantic_ts` reads
# TypeScript facts (recordings, an already-installed tsc through
# `_runner`, and source text). Both observe and neither scores —
# scanners, per docs/architecture.md. `_semantic_policy` loads the
# checked-in policy block: configuration foundations.
# `_adapters` is a scanner: it produces findings and measurements from a
# tree, exactly as the built-in detectors do, and like them it may not
# import scoring. The difference is only that an external process does
# the looking (ADR 006).
SCANNERS = {"metrics", "_discovery", "_practice", "duplication", "deadcode", "idioms",
            "similarity", "_semantic", "_semantic_ts",
            # The opt-in test-suite runner: the one scanner that executes the
            # audited tree's own code, default-off (Class 5).
            "_test_execution",
            # Path pairing and TDD-shaped constructs. Not chronology.
            "_test_pairing",
            "history", "_adapters",
            # `_generic` is the same layer: it turns tool output into
            # findings, differing only in that its parsers are shared
            # across tools rather than written per tool.
            "_generic",
            # Adapters split by emitter kind when `_adapters` breached this
            # project's own 500-line limit: `_metric_adapters` for tools
            # reporting every unit, `_verdict_adapters` for tools reporting
            # only threshold breaches, `_tool_adapters` for the registry
            # naming them. The base module keeps only shared plumbing.
            "_metric_adapters", "_verdict_adapters", "_jvm_adapters",
            "_tool_adapters", "_selection"}
# `_bands` joins the rubric-data leaves: it is the band matrix, a table
# of judgments like `_formula`, and imports nothing internal.
SCORING = {"scoring", "_aspects", "_pressures", "_formula", "_calibration", "_derive",
           "_pillars", "_trends", "_recurrence",
           "_verification", "_bands",
           # `_second_source` decides how analyzer readings reach the point
           # and the interval; it reads pressures and corroboration and,
           # like the rest of this layer, may not see a scanner.
           "_second_source",
           # `_corroborate` reduces several tools' readings of one concept to
           # a single value plus its spread. That is scoring input
           # preparation, and like the rest of this layer it reads
           # measurements and never scanners.
           "_corroborate"}
# `_analysis` orchestrates: it calls the catalog, the runner and the
# adapters and hands `report` a coverage document. That makes it assembly,
# not a scanner — it composes rather than measures.
ASSEMBLY = {"report", "_analysis", "_documents", "_built_ins", "_work_order",
            # `_conformance` compares a diff against the work order the
            # report already produced. Assembly because it composes from a
            # finished report rather than measuring a tree — and it may
            # never reach scoring: whether a diff was obedient is a fact
            # about an agent, not evidence about the code.
            "_conformance",
            # `_ratchet` compares the newest scan with the previous
            # comparable one. Assembly for the same reason as
            # `_conformance`: it composes from recorded history rather
            # than measuring a tree, and a difference between two scans
            # is not evidence about the code's condition.
            "_ratchet",
            # `_economics` composes the ADR 004 scenario from the finished
            # report and configured context; it measures nothing, asks
            # nothing, and may never be imported by scoring.
            "_economics",
            # `_environment` composes the install-command artifact from the
            # coverage record (ADR 006 §2c); it measures nothing and spawns
            # nothing, and `test_the_agent_never_runs_the_install_command`
            # holds the second half of that.
            "_environment",
            "_work_order_weights", "_backfill"}
PRESENTATION = {"renderers", "prompts", "sarif", "baseline", "_evidence_view",
                # `_attestation` composes the conformance and ratchet
                # records into one artifact. Presentation because it
                # renders what the report already holds, and like every
                # emitter on this seam it computes no score.
                "_attestation",
                # ADR 013's emitter: renders, never scores.
                "_hostile_prompt",
                # `_html_view` is the ADR 011 HTML skin: it reads the report
                # dict and stored records and computes no score.
                "_html_view",
                # `_html_report_sections` holds the HTML coverage and trend
                # sections, split from `_html_view` at the file-size line;
                # it formats report dict fields and computes no score.
                "_html_report_sections",
                # `_markdown_sections` holds the leaf Markdown section
                # renderers and the shared `markdown_table`, split from
                # `renderers` for headroom (#125). It imports nothing from
                # `renderers`, so `renderers` imports these back without a
                # cycle. Reads the report dict and computes no score.
                "_markdown_sections",
                # `_charts` builds the ADR 011 SVG charts (deterministic,
                # offline) from already-computed points; split from
                # `_html_view` at the file-size line so the chart rebuild had
                # room. It reads no report and computes no score.
                "_charts",
                # `_economics_view` prints the ADR 004 scenario block and
                # computes none of it.
                "_economics_view",
                # `_semantic_view` prints the ADR 003 semantic block with
                # its class labels intact and computes none of it.
                "_semantic_view",
                # `_coverage_notes` is the coverage section's prose about
                # its own gaps -- one source only, a dimension the analyzer
                # tier declined, nothing examined -- split from `_scan_view`
                # at the file-size line.
                "_coverage_notes",
                "_scan_view", "_history_view", "_identity",
                # `_work_order_view` renders the work order and its per-item
                # copy-paste prompts, shared by the Markdown and HTML skins;
                # split from `_scan_view` at the file-size line, and the seam
                # is real (this is what to *do*; `_scan_view` is what was
                # looked at). It reads the report dict and computes no score.
                "_work_order_view",
                # TDD-structure sentences shared by chat, Markdown, HTML.
                "_tdd_view"}
# `_first_run` is terminal interaction — it prompts, which no layer
# below entry may ever do, and writes the config file the entry then
# loads through ordinary discovery.
# `_mcp_setup` is the chat-path twin of `_first_run`: it asks (via MCP
# elicitation), which no layer below entry may do, and writes the
# config the entry then loads through ordinary discovery.
# `_mcp_audit` is the MCP audit tool split from `mcp_server` at the
# size line: authorization, tri-states, and the D5/D6 loop record.
# `_mcp_grants` is the D10 grant machinery split from `mcp_server` at
# the same size gate: the ledger, the question, and the consent it binds.
# `_mcp_gate` is what the audit answers with when it is not answering
# with an audit — the D26 setup precondition and the D27 run-or-
# reconfigure choice, split from `_mcp_audit` at the same size gate.
# `_mcp_refusals` is the set of domain types the transport may turn
# into the SDK's declared refusals. Below both seam-binding modules,
# because `mcp_server` imports `_mcp_resources` and a tuple beside
# either would be a cycle for the other.
# Entry, because deciding to ask a person rather than compute is an
# entry-layer decision; nothing below may make it.
# `_grant_ledger` reads the persisted root-grant list and asks
# `_stored_grants` whether each entry still names what was consented to.
# Entry layer beside `_mcp_audit`: it reaches `_user_config` for the
# file and the rule module for the judgment, and the audit door is its
# only consumer.
# `_setup_persist` is the persist half of setup — the values, the
# economics block, and the three config writers — split from `_mcp_setup`
# for headroom (#127). `apply_answers` stays in `_mcp_setup` (the one-setup
# invariant) and delegates here; this module imports nothing from
# `_mcp_setup`, so the graph stays acyclic. `_setup_errors` is the single
# `SetupRequired` exception, on its own leaf so the persist helpers and the
# ask surface both use it without a cycle.
ENTRY = {"cli", "__main__", "mcp_server", "_first_run", "_mcp_setup", "_mcp_audit",
         # `_gates` is the post-audit half of the CLI, split at the
         # 500-line file gate: it composes from a finished report and
         # decides the exit code. Entry rather than assembly because
         # it exists to serve one door, and because deciding a process
         # exit code is the CLI's job and nobody else's.
         "_gates",
         "_grant_ledger", "_setup_persist", "_setup_errors",
         "_skill_install", "_mcp_gate", "_mcp_resources",
         "_mcp_grants", "_mcp_refusals"}
BOUNDARY = {"evidence"}

LAYERS = {
    "foundations": FOUNDATIONS,
    "parsing": PARSING,
    "scanners": SCANNERS,
    "scoring": SCORING,
    "assembly": ASSEMBLY,
    "presentation": PRESENTATION,
    "entry": ENTRY,
    "boundary": BOUNDARY,
}

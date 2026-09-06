"""What the command line accepts, separate from what the command does.

Split out of `cli` when it crossed this project's own `max_file_lines`
gate — the second time that gate has shaped this module, after
`_add_gate_arguments` was split from `add_arguments` for the function
budget. Both splits were forced by the tool on a change to the tool, which
is the gate doing the job it exists for rather than an inconvenience.

The boundary is deliberate and not merely a line count: everything here
declares a flag and nothing here runs an audit. `cli` imports it, never
the reverse.
"""
from __future__ import annotations

import argparse

from .config import VERSION


def _add_gate_arguments(parser: argparse.ArgumentParser) -> None:
    """What can make a run fail, and the conformance record behind one.

    Split from `add_arguments` when the conformance flags took it past this
    project's own function-length gate — which is the gate doing its job on
    the change that added a gate.

    `--staged` belongs here rather than with the artifact flags: it
    produces no artifact and decides whether work proceeds, which is what
    every other flag in this group does. It differs only in *when* — a
    commit rather than a build — and that is the point of it.
    """
    parser.add_argument("--fail-on-gate", action="store_true", help="Exit 1 when hard gates fail.")
    parser.add_argument(
        "--staged", action="store_true",
        help="Scan what the git index will commit, for a pre-commit hook. "
             "Reads the index rather than the working tree, so half-staged "
             "edits are measured as they will land. Reports threshold "
             "breaches only and never a score — a diff has no population to "
             "draw a rate from. Applies no repository gates, writes nothing, "
             "and never runs the opt-in test suite. Exits 1 when something "
             "blocks, silently 0 when nothing does.",
    )
    parser.add_argument(
        "--conformance",
        metavar="REVSPEC",
        help="Report how a diff relates to the work order, e.g. `main...HEAD`. "
             "The bounded work order says 'fix exactly these and refactor nothing "
             "else'; without this the bound is an instruction nothing checks. "
             "Reports only unless --fail-on-out-of-scope is passed.",
    )
    parser.add_argument(
        "--fail-on-regression", action="store_true",
        help="Exit 1 when any scoring category is lower than the previous "
             "comparable scan. Reads the recorded history, and refuses to "
             "compare across an instrument change rather than reporting a "
             "false regression: two scans taken under different calibration "
             "cannot be subtracted.",
    )
    parser.add_argument(
        "--fail-on-out-of-scope", action="store_true",
        help="With --conformance, exit 1 when the diff touched files the work "
             "order did not name and that do not pair to one as its test, or "
             "when it added a suppression to a file the work order flagged.",
    )


def _add_artifact_arguments(parser: argparse.ArgumentParser) -> None:
    """The documents a run can write beside its report, and the run's label.

    Split out for the same reason `_add_gate_arguments` was, and by the same
    gate: `--transformation` took `add_arguments` past this project's own
    function-length threshold, so the gate failed the change that added a
    reporting flag. Grouped by what they produce rather than alphabetically
    — every one of these is an artifact for somebody other than the person
    running the command.
    """
    parser.add_argument("--prompt-output", help="Optional Markdown prompt for AI-assisted remediation.")
    parser.add_argument("--comment-output", help="Optional Markdown body suitable for a PR comment.")
    parser.add_argument("--agent-instructions-output", help="Optional reusable instructions for AI coding agents.")
    parser.add_argument(
        "--attestation-output",
        help="Write the attestation: an independent, reproducible record of "
             "what was measured, what the change was told to do, what it did, "
             "and what moved. Populated by --conformance and "
             "--fail-on-regression; a generator cannot produce this about its "
             "own output.",
    )
    parser.add_argument(
        "--transformation",
        metavar="NAME",
        help="Name the class of work this scan followed, e.g. `react-18`. "
             "Records the name on the scan and reports how this run of it "
             "compares with earlier ones. Nothing in a tree says which "
             "transformation produced it, so this is your claim and the tool "
             "records it without verifying it. A report, never a gate.",
    )
    parser.add_argument("--hostile-prompt-output",
                        help="Optional adversarial audit brief seeded from this run (ADR 013). "
                             "Text only: it does not gate, score, or send anything.")


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"maintainability-agent {VERSION}")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--config", help="Path to JSON config.")
    # Default None, not "markdown": the TTY question (8.4) only fires
    # when the user stated nothing, and argparse cannot distinguish a
    # stated default from an omitted flag.
    parser.add_argument("--format", choices=["json", "markdown", "html"], default=None)
    parser.add_argument("--html-output", help="Write the single-file HTML report here (ADR 011).")
    parser.add_argument("--output", help="Output file. Defaults to stdout.")
    _add_artifact_arguments(parser)
    parser.add_argument("--sarif-output", help="Optional SARIF output path for GitHub code scanning.")
    parser.add_argument("--sarif-input", action="append", help="Optional external SARIF file to summarize in reports. Repeatable.")
    parser.add_argument("--changed-only", help="Audit only files changed in a git revspec, for example main...HEAD.")
    parser.add_argument("--baseline", help="Existing baseline JSON. With --fail-on-new, only new findings fail.")
    parser.add_argument("--write-baseline", help="Write current findings to a baseline JSON file.")
    parser.add_argument("--fail-on-new", action="store_true", help="Fail only when findings are not in --baseline.")
    parser.add_argument(
        "--analyzers", action="store_true",
        help="Force the external analyzer pool on for this run. The pool is "
             "the primary evidence source (ADR 006, docs/analyzer-pool.md); a "
             "repository with a config file runs it by default, so this flag "
             "matters only for unconfigured trees or to override "
             "analyzers.run=false. Measurements move the point estimate where "
             "the full concept set was measured; otherwise the built-in "
             "fallback stands and the range widens around the two.",
    )
    parser.add_argument(
        "--no-analyzers", action="store_true",
        help="Force the analyzer pool off for this run, overriding the "
             "config. The report will say the built-in fallback supplied the "
             "evidence (P8); it is a faster scan, not the full audit.",
    )
    parser.add_argument(
        "--work", action="append", metavar="AXIS=VALUE",
        help="Narrow the work order, for example --work band=quick-win or "
             "--work path=src/. Repeatable; every criterion must match. "
             "Axes: band, finding_class, path, verification. Narrowing "
             "changes what is shown and never what anything scored.",
    )
    parser.add_argument(
        "--record-history", action="store_true",
        help="Append this scan to the history at paths.history (default "
             ".maintainability/history.jsonl). Opt-in, like every other write "
             "this tool performs. Once the file exists, every later successful "
             "scan appends to it and reads the resulting history.",
    )
    parser.add_argument(
        "--backfill", metavar="REVSPEC",
        help="Scan each commit in a range into the history and exit, for "
             "example --backfill HEAD~50..HEAD. Each commit is checked out in "
             "a temporary worktree, so the working tree is never touched. "
             "Expensive and therefore explicit: it never runs as part of a "
             "normal scan. Records are marked as reconstructed.",
    )
    parser.add_argument(
        "--backfill-interval", type=int, default=1, metavar="N",
        help="With --backfill, scan every Nth commit instead of all of them. "
             "The shape of a series is what a trend reads, and a thousand "
             "commits is hours of work nobody asked for.",
    )
    _add_gate_arguments(parser)
    _add_setup_actions(parser)


def _add_setup_actions(parser: argparse.ArgumentParser) -> None:
    """Flags that perform a setup action and exit instead of auditing."""
    parser.add_argument("--init-agent-standards", action="store_true", help="Write model/tool-specific instruction files and exit.")
    parser.add_argument(
        "--install-skill", action="store_true",
        help="Copy the packaged agent skill into the skills directory and "
             "exit. Re-run after every upgrade: an installed skill that "
             "drifts from the shipped one teaches agents a dead workflow.",
    )
    parser.add_argument(
        "--install-precommit-hook", action="store_true",
        help="Write a git pre-commit hook that runs --staged, and exit. "
             "Refuses to replace a hook this tool did not write, and "
             "prints the line to add to that hook instead; replaces its "
             "own without asking, because that is an upgrade. Honours "
             "core.hooksPath.",
    )
    parser.add_argument(
        "--skills-dir", default=None, metavar="DIR",
        help="Where --install-skill writes (default: ~/.claude/skills).",
    )
    parser.add_argument(
        "--force-skill", action="store_true",
        help="With --install-skill: overwrite a differing installed copy "
             "and remove files the package no longer ships. Without it, a "
             "differing copy is refused with the list of differences.",
    )
    parser.add_argument(
        "--target-path",
        action="append",
        metavar="TARGET=PATH",
        help="Where a target's standing instructions go, e.g. "
             "`--target-path bob=.bob/instructions.md`. Required for any agent "
             "this tool has no built-in convention for; overrides the built-in "
             "path for one it does. The target list will always trail the "
             "market, and guessing a path writes a file the agent never opens.",
    )
    parser.add_argument(
        "--target",
        action="append",
        help="Instruction target. Repeatable. Used with --init-agent-standards.",
    )
    parser.add_argument("--instructions-output-dir", default=".", help="Directory for generated instruction files.")

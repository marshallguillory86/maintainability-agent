from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._backfill import backfill
from ._calibration import CALIBRATION_C
from ._first_run import (
    _stdin_is_a_tty,
    ask_presentation,
    maybe_prompt_economics,
    maybe_prompt_first_run,
)
from ._mcp_audit import record_scan_and_attach
from ._scan_history import (
    DEFAULT_HISTORY_PATH,
    read_history,
)
from ._user_config import mark_repo_seen
from ._work_order import SELECTABLE, combined_delta, select
from .baseline import (
    finding_fingerprints,
    findings_not_in_baseline,
    load_baseline,
    write_baseline,
)
from .config import (
    DEFAULT_CONFIG,
    VERSION,
    analyzers_run_default,
    discovered_config,
    load_config,
)
from .git_tools import changed_paths
from .instructions import instruction_path_for_target, write_instruction_pack
from .prompts import render_agent_instructions, render_ai_prompt
from .renderers import render_html, render_markdown, render_pr_comment
from .report import build_report
from .sarif import read_sarif_inputs, report_to_sarif


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
    parser.add_argument("--prompt-output", help="Optional Markdown prompt for AI-assisted remediation.")
    parser.add_argument("--comment-output", help="Optional Markdown body suitable for a PR comment.")
    parser.add_argument("--agent-instructions-output", help="Optional reusable instructions for AI coding agents.")
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
    parser.add_argument("--fail-on-gate", action="store_true", help="Exit 1 when hard gates fail.")
    parser.add_argument("--init-agent-standards", action="store_true", help="Write model/tool-specific instruction files and exit.")
    parser.add_argument(
        "--target",
        action="append",
        choices=["generic", "claude-code", "codex", "cursor", "copilot", "windsurf"],
        help="Instruction target. Repeatable. Used with --init-agent-standards.",
    )
    parser.add_argument("--instructions-output-dir", default=".", help="Directory for generated instruction files.")


def _selection_from(
    parser: argparse.ArgumentParser, pairs: list[str] | None
) -> dict[str, str]:
    """Parse `--work axis=value` into criteria, or exit naming the mistake.

    Refused rather than ignored. A filter that silently drops an axis it
    does not recognise hands back the full list while the caller
    believes it was narrowed, which is the more expensive failure.
    """
    criteria: dict[str, str] = {}
    for pair in pairs or []:
        axis, separator, value = pair.partition("=")
        if not separator or not value:
            parser.error(f"--work expects AXIS=VALUE, got {pair!r}")
        if axis not in SELECTABLE:
            parser.error(f"--work cannot select on {axis!r}; axes are {list(SELECTABLE)}")
        criteria[axis] = value
    return criteria


def write_outputs(args: argparse.Namespace, report: dict, rendered: str) -> None:
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    if args.prompt_output:
        Path(args.prompt_output).write_text(render_ai_prompt(report) + "\n", encoding="utf-8")
    if args.comment_output:
        Path(args.comment_output).write_text(render_pr_comment(report) + "\n", encoding="utf-8")
    if args.agent_instructions_output:
        Path(args.agent_instructions_output).write_text(render_agent_instructions(report) + "\n", encoding="utf-8")
    if args.write_baseline:
        write_baseline(args.write_baseline, report)
    if args.sarif_output:
        Path(args.sarif_output).write_text(json.dumps(report_to_sarif(report), indent=2) + "\n", encoding="utf-8")


def audit_exit_code(args: argparse.Namespace, report: dict) -> int:
    if args.fail_on_new:
        # Structured matching, never a label-set difference: a label
        # changes under `git mv` and same-name reorder, and failing a
        # build over either is a false report about the change.
        root = Path(report["root"])
        if findings_not_in_baseline(report, args.baseline, root):
            return 1
    if args.fail_on_gate and report["hard_gate_failures"]:
        return 1
    return 0


def _analyzers_resolved(args: argparse.Namespace, config: dict) -> bool:
    """Whether the pool runs: flags beat config, config beats nothing.

    A configured repository runs its pool without a flag (D1, ADR 006);
    the flags exist for one-run overrides in either direction.
    """
    if args.analyzers:
        return True
    if args.no_analyzers:
        return False
    return analyzers_run_default(config)


def _interactive_config(root: Path, config_arg: str | None) -> dict:
    """Both first-run asks, then the one config every later run loads.

    6.1 writes the file `discovered_config` finds, so it has no private
    path into the audit; the ADR 004 labor ask runs after load so a
    configured range or a suppression flag is respected, and mutates the
    dict in memory so this very run prices its own report.
    """
    maybe_prompt_first_run(root, config_arg)
    config = load_config(config_arg or discovered_config(root))
    maybe_prompt_economics(root, config)
    return config


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "mcp":
        from . import mcp_server

        return mcp_server.main(argv[1:])

    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    config = _interactive_config(root, args.config)
    if args.init_agent_standards:
        targets = args.target or ["generic", "claude-code", "codex", "cursor", "copilot", "windsurf"]
        write_instruction_pack(targets, Path(args.instructions_output_dir).resolve(), config)
        return 0

    if args.backfill:
        history_path = root / (config.get("paths", {}).get("history") or DEFAULT_HISTORY_PATH)
        try:
            count = backfill(root, args.backfill, config, VERSION, CALIBRATION_C,
                             history_path, interval=args.backfill_interval)
        except ValueError as error:
            parser.error(str(error))
        print(f"recorded {count} scan(s) to {history_path}")
        return 0

    selection = _selection_from(parser, args.work)
    only_paths = changed_paths(root, args.changed_only) if args.changed_only else None
    external_findings = read_sarif_inputs(args.sarif_input)
    report = build_report(root, config, only_paths=only_paths,
                          changed_revspec=args.changed_only,
                          external_findings=external_findings,
                          run_analyzers=_analyzers_resolved(args, config))
    if selection:
        # A view over the work already gathered. The score block is
        # untouched by construction — `select` returns a subset of the
        # items and computes nothing — so one rubric still applies to
        # every repository however a reader narrows the list.
        report["work_order_selection"] = {
            "criteria": selection,
            "items": select(report["work_order"], **selection),
        }
        report["work_order_selection"]["worth"] = combined_delta(
            report, report["work_order_selection"]["items"])
    history_path = root / (config.get("paths", {}).get("history") or DEFAULT_HISTORY_PATH)
    # 8.2: the file's existence is the user's standing answer. Once a
    # history exists, a successful scan appends whether or not the flag
    # was remembered. Written consent outranks the terminal (decision 7,
    # M3): `history.record: false` suppresses even an interactive run,
    # `true` records even headless, and only when nothing is written
    # does a first *interactive* run start the series — a first CI run
    # without the flag still writes nothing nobody asked for.
    consent = (config.get("history") or {}).get("record")
    record = (args.record_history or history_path.exists() or consent is True
              or (consent is None and _stdin_is_a_tty()))
    # One shared, honestly-ordered helper (audit H1): views close
    # recurrence with this scan included, the prompt withholds what
    # escalated, and only delivered advice is recorded as targeted.
    record_scan_and_attach(report, config, history_path, Path(report["root"]),
                           record=bool(record), want_targets=bool(args.prompt_output))
    rendered = _render_presentation(args, report, history_path)
    write_outputs(args, report, rendered)
    mark_repo_seen(root)  # completed audit: not a first run now, whatever the gate says (D13)
    return audit_exit_code(args, report)


def _render_presentation(args: argparse.Namespace, report: dict, history_path: Path) -> str:
    """8.4: resolve the presentation, then render it.

    Asks at a TTY only when nothing was stated; flags win; CI never asks
    and defaults to Markdown. The answer is never persisted — ADR 011
    asks on every interactive invoke. Extracted so `main` stays inside
    this project's own function budget.
    """

    stated = args.format is not None or args.output or args.html_output
    if not stated and _stdin_is_a_tty():
        choice = ask_presentation()
        if choice == "html":
            args.html_output = "maintainability-report.html"
        elif choice == "markdown":
            args.output = "maintainability-report.md"
    args.format = args.format or "markdown"
    if args.html_output:
        Path(args.html_output).write_text(
            render_html(report, read_history(history_path)) + "\n", encoding="utf-8")
    if args.format == "json":
        return json.dumps(report, indent=2, sort_keys=True)
    if args.format == "html":
        return render_html(report, read_history(history_path))
    return render_markdown(report)


__all__ = [
    "add_arguments",
    "audit_exit_code",
    "build_report",
    "changed_paths",
    "DEFAULT_CONFIG",
    "finding_fingerprints",
    "instruction_path_for_target",
    "load_baseline",
    "load_config",
    "main",
    "read_sarif_inputs",
    "report_to_sarif",
]


if __name__ == "__main__":
    sys.exit(main())

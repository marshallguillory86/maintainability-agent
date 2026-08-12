from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .baseline import finding_fingerprints, load_baseline, write_baseline
from .config import DEFAULT_CONFIG, VERSION, load_config
from .git_tools import changed_paths
from .instructions import instruction_path_for_target, write_instruction_pack
from .prompts import render_agent_instructions, render_ai_prompt
from .renderers import render_markdown, render_pr_comment
from .report import build_report
from .sarif import read_sarif_inputs, report_to_sarif


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--version", action="version", version=f"maintainability-agent {VERSION}")
    parser.add_argument("--root", default=".", help="Repository root to scan.")
    parser.add_argument("--config", help="Path to JSON config.")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown")
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
        help="Run the configured external analyzer pool and report its coverage "
             "(see docs/analyzer-pool.md). Off by default while adapters are "
             "still being written.",
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
        baseline = load_baseline(args.baseline)
        if finding_fingerprints(report) - baseline:
            return 1
    if args.fail_on_gate and report["hard_gate_failures"]:
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    config = load_config(args.config)
    if args.init_agent_standards:
        targets = args.target or ["generic", "claude-code", "codex", "cursor", "copilot", "windsurf"]
        write_instruction_pack(targets, Path(args.instructions_output_dir).resolve(), config)
        return 0

    only_paths = changed_paths(root, args.changed_only) if args.changed_only else None
    external_findings = read_sarif_inputs(args.sarif_input)
    report = build_report(root, config, only_paths=only_paths,
                          changed_revspec=args.changed_only,
                          external_findings=external_findings,
                          run_analyzers=args.analyzers)
    rendered = json.dumps(report, indent=2, sort_keys=True) if args.format == "json" else render_markdown(report)
    write_outputs(args, report, rendered)
    return audit_exit_code(args, report)


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

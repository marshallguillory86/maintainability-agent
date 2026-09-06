from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ._arguments import add_arguments
from ._backfill import backfill
from ._calibration import CALIBRATION_C
from ._first_run import (
    _stdin_is_a_tty,
    ask_presentation,
    maybe_prompt_economics,
    maybe_prompt_first_run,
    maybe_prompt_test_command,
)
from ._gates import (
    _attach_post_audit_records,
    audit_exit_code,
)
from ._mcp_audit import record_scan_and_attach
from ._safe_write import write_artifact
from ._scan_history import (
    DEFAULT_HISTORY_PATH,
    read_history,
)
from ._user_config import mark_repo_seen
from ._work_order import SELECTABLE, combined_delta, select
from .baseline import (
    finding_fingerprints,
    load_baseline,
    write_baseline,
)
from .config import (
    DEFAULT_CONFIG,
    VERSION,
    analyzers_run_default,
    discovered_config,
    load_config,
    repository_path,
)
from .git_tools import changed_paths
from .instructions import (
    INSTRUCTION_TARGETS,
    UnknownTarget,
    instruction_path_for_target,
    write_instruction_pack,
)
from .prompts import render_agent_instructions, render_ai_prompt, render_hostile_audit_prompt
from .renderers import render_html, render_markdown, render_pr_comment
from .report import build_report
from .sarif import read_sarif_inputs, report_to_sarif


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
    # Every rendered output the operator asks for is a product-artifact
    # write: a raw `Path(name).write_text` followed the tree's symlink
    # into source, so each goes through `write_artifact`, bound to the
    # repository the report was taken in (Grok 63ab820 audit).
    root = Path(report["root"])
    if args.output:
        write_artifact(root, Path(args.output), rendered + "\n")
    else:
        print(rendered)
    if args.prompt_output:
        write_artifact(root, Path(args.prompt_output), render_ai_prompt(report) + "\n")
    if args.comment_output:
        write_artifact(root, Path(args.comment_output), render_pr_comment(report) + "\n")
    if args.agent_instructions_output:
        write_artifact(root, Path(args.agent_instructions_output), render_agent_instructions(report) + "\n")
    if args.attestation_output:
        from ._attestation import render_attestation

        write_artifact(root, Path(args.attestation_output), render_attestation(report))
    if args.hostile_prompt_output:
        write_artifact(root, Path(args.hostile_prompt_output),
                       render_hostile_audit_prompt(report) + "\n")
    if args.write_baseline:
        write_baseline(args.write_baseline, report)
    if args.sarif_output:
        write_artifact(root, Path(args.sarif_output),
                       json.dumps(report_to_sarif(report), indent=2) + "\n", json_artifact=True)


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
    source = config_arg or discovered_config(root)
    try:
        config = load_config(source)
    except ValueError as unreadable:
        # Same answer the chat doors give, in the CLI's idiom. A
        # truncated or hand-edited config used to surface a raw
        # `JSONDecodeError` traceback here while the MCP tool and
        # resource refused by name — one repository state, two
        # experiences, and the worse one on the door people run
        # unattended (D32).
        raise SystemExit(
            f"maintainability-agent: {source} cannot be read as JSON "
            f"({unreadable}). Repair or delete it; the audit cannot tell "
            "whether this repository has been configured."
        ) from unreadable
    maybe_prompt_economics(root, config)
    maybe_prompt_test_command(root, config)
    return config


#: Flags `--staged` will not silently ignore. Each one asks for
#: something a pre-commit scan refuses by design — a revspec other than
#: the index, a write, a comparison against history, a repository gate —
#: and a hook that accepts the flag and does nothing with it teaches the
#: author it was honoured.
_STAGED_REFUSES = {
    "changed_only": "--changed-only", "backfill": "--backfill",
    "conformance": "--conformance", "record_history": "--record-history",
    "fail_on_regression": "--fail-on-regression", "fail_on_gate": "--fail-on-gate",
    "write_baseline": "--write-baseline", "output": "--output",
    "prompt_output": "--prompt-output", "comment_output": "--comment-output",
    "attestation_output": "--attestation-output", "html_output": "--html-output",
    "sarif_output": "--sarif-output", "transformation": "--transformation",
    "agent_instructions_output": "--agent-instructions-output",
    "hostile_prompt_output": "--hostile-prompt-output",
}


def _staged_action(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Scan the index and decide whether this commit may proceed.

    An action, not a mode of the audit, and it returns before
    `_interactive_config` on purpose: that function asks first-run
    questions at a TTY, and a hook that opens a setup wizard while
    somebody is committing is a hook they remove. An unconfigured
    repository gets the shipped thresholds and no questions.

    Exit 1 blocks the commit, 0 lets it through, 2 means the scan could
    not be taken — which also blocks, because a hook that cannot measure
    has not found nothing.
    """
    from ._precommit import staged_findings, staged_report
    from ._precommit_view import render_staged, staged_json
    from .git_tools import GitCommandFailed

    refused = [flag for attribute, flag in _STAGED_REFUSES.items() if getattr(args, attribute, None)]
    if refused:
        parser.error(f"--staged does not take {', '.join(sorted(refused))}")
    if args.format == "html":
        parser.error("--staged renders text or --format json; there is no HTML for a hook")

    root = Path(args.root).resolve()
    config = load_config(args.config or discovered_config(root))
    try:
        report = staged_report(root, config)
    except GitCommandFailed as unreadable:
        print(f"maintainability-agent: cannot read the index ({unreadable})", file=sys.stderr)
        return 2
    findings = staged_findings(report)
    if args.format == "json":
        print(staged_json(report, findings))
    else:
        # stdout, not stderr, and both renderings on the same stream: a
        # clean commit prints nothing at all, so there is no case where
        # silence on one stream hides a refusal on the other.
        lines = render_staged(findings, len(report["scanned"]))
        if lines:
            print("\n".join(lines))
    return 1 if findings else 0


#: Flags `--check` will not silently ignore. It answers about content it
#: is handed, so anything naming a revspec, a repository scan, a write or
#: another mode is a request it cannot honour — and a flag accepted and
#: ignored teaches the caller it was honoured.
_CHECK_REFUSES = {
    "staged": "--staged", "changed_only": "--changed-only",
    "backfill": "--backfill", "conformance": "--conformance",
    "record_history": "--record-history", "fail_on_gate": "--fail-on-gate",
    "fail_on_regression": "--fail-on-regression", "output": "--output",
    "write_baseline": "--write-baseline", "prompt_output": "--prompt-output",
    "html_output": "--html-output", "sarif_output": "--sarif-output",
}


def _check_action(parser: argparse.ArgumentParser, args: argparse.Namespace) -> int:
    """Answer about the content on stdin, then exit.

    Returns before `_interactive_config` for the same reason
    `_staged_action` does: that function asks first-run questions at a
    TTY, and an agent piping content into a check is not a person who
    wants a setup wizard. An unconfigured tree gets the shipped
    thresholds.

    Exit 1 when something breaches, 0 when nothing does. A repository is
    never required — the point of this door is that it works before one
    is relevant.
    """
    from ._in_loop import check_content
    from ._in_loop_view import check_json, render_check

    refused = [flag for attribute, flag in _CHECK_REFUSES.items() if getattr(args, attribute, None)]
    if refused:
        parser.error(f"--check does not take {', '.join(sorted(refused))}")
    if args.format == "html":
        parser.error("--check does not take html; it renders text or --format json")

    root = Path(args.root).resolve()
    config = load_config(args.config or discovered_config(root))
    result = check_content(args.check, sys.stdin.read(), config)
    if args.format == "json":
        print(check_json(result))
    else:
        lines = render_check(result)
        if lines:
            print("\n".join(lines))
    return 1 if result["findings"] else 0


def _install_skill_action(args: argparse.Namespace) -> int:
    """Sync the packaged skill, or report the refusal that stopped it."""
    from ._skill_install import SkillDrift, install_skill

    target = (Path(args.skills_dir).expanduser()
              if args.skills_dir else Path.home() / ".claude" / "skills")
    try:
        for written in install_skill(target, force=args.force_skill):
            print(written)
    except SkillDrift as refusal:
        print(refusal)
        return 1
    return 0


def _target_paths(pairs: list[str] | None) -> dict[str, str]:
    """`TARGET=PATH` arguments, as a mapping.

    An absolute path is refused: the instruction pack is written relative
    to `--instructions-output-dir`, so an absolute one would silently
    ignore the directory the caller named.
    """
    overrides: dict[str, str] = {}
    for pair in pairs or []:
        target, separator, path = pair.partition("=")
        if not separator or not target.strip() or not path.strip():
            raise ValueError(f"--target-path expects TARGET=PATH, got {pair!r}")
        if Path(path).is_absolute():
            raise ValueError(
                f"--target-path {pair!r} is absolute; paths are relative to "
                "--instructions-output-dir"
            )
        overrides[target.strip()] = path.strip()
    return overrides


def _parse(argv: list[str]) -> tuple[argparse.ArgumentParser, argparse.Namespace]:
    """The parser comes back too: `main` still needs it for `parser.error`."""
    parser = argparse.ArgumentParser()
    add_arguments(parser)
    return parser, parser.parse_args(argv)


def _record_this_scan(
    args: argparse.Namespace, config: dict, report: dict, root: Path
) -> Path:
    """Append this scan to history where consent allows, and say where.

    Returns the resolved history path whether or not anything was written:
    the post-audit records read it either way, and a run that recorded
    nothing still has a history to compare against.
    """
    # Set before the scan is recorded, because `record_of` reads it off the
    # report: a label that arrived after the append would name every run
    # except the one being named.
    if args.transformation:
        report["transformation"] = args.transformation
    # D20: the same repository boundary the MCP door applies.
    history_path = repository_path(
        root, config.get("paths", {}).get("history"), DEFAULT_HISTORY_PATH)
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
    return history_path


def _action_before_config(
    parser: argparse.ArgumentParser, args: argparse.Namespace
) -> int | None:
    """Whichever action runs *without* loading configuration, or None.

    Each of these returns before `_interactive_config`, which asks
    first-run questions at a TTY. A hook, an agent piping content, and a
    skill install are none of them a person who wants a setup wizard.

    Extracted when `main` reached complexity 16 against this project's
    own limit of 15 — a dispatch branch per action, each reasonable
    alone. It had been reported as 8 while Python's comments and string
    literals were counted as branches and its `and`/`or` were not.
    """
    if args.install_skill:
        return _install_skill_action(args)
    if args.install_precommit_hook:
        from ._precommit_install import install_precommit_hook

        code, message = install_precommit_hook(Path(args.root).resolve())
        print(message, file=sys.stderr if code else sys.stdout)
        return code
    if args.check:
        return _check_action(parser, args)
    if args.staged:
        return _staged_action(parser, args)
    return None


def _instruction_pack_action(args: argparse.Namespace, config: dict) -> int:
    """Write the agent instruction files and exit."""
    targets = args.target or list(INSTRUCTION_TARGETS)
    try:
        overrides = _target_paths(args.target_path)
        write_instruction_pack(
            targets, Path(args.instructions_output_dir).resolve(), config, overrides
        )
    except (UnknownTarget, ValueError) as failure:
        print(str(failure), file=sys.stderr)
        return 2
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv and argv[0] == "mcp":
        from . import mcp_server

        return mcp_server.main(argv[1:])

    parser, args = _parse(argv)
    # Every action that must not trigger the first-run questions.
    early = _action_before_config(parser, args)
    if early is not None:
        return early

    root = Path(args.root).resolve()
    config = _interactive_config(root, args.config)
    if args.init_agent_standards:
        return _instruction_pack_action(args, config)

    if args.backfill:
        history_path = repository_path(
            root, config.get("paths", {}).get("history"), DEFAULT_HISTORY_PATH)
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
    history_path = _record_this_scan(args, config, report, root)
    # Before rendering, so the record is in the report every presentation
    # and every consumer reads, rather than only in the exit code.
    _attach_post_audit_records(args, report, history_path)
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
        write_artifact(Path(report["root"]), Path(args.html_output),
                       render_html(report, read_history(history_path)) + "\n")
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

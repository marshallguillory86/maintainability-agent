"""What happens after the audit and before the exit code.

Split from `cli.py` when it crossed this project's 500-line file gate —
the same reason `_mcp_setup`, `_adapters` and `test_architecture` were
split before it.

The split is not arbitrary. Everything here composes from the **finished
report**: whether the diff obeyed its work order, whether a dimension
slipped since the last comparable scan, and what those two facts mean for
the process exit code. None of it measures a tree and none of it may reach
scoring — a fact about an agent's behaviour, or about the difference
between two scans, is not evidence about the code's condition.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .baseline import findings_not_in_baseline
from .git_tools import added_lines, changed_paths


def attach_conformance(args: argparse.Namespace, report: dict) -> None:
    """Record how the diff relates to the work order, when asked.

    Assembly, not scoring: the record is attached to the report and reaches
    no dimension, because whether a diff was obedient is a fact about an
    agent's behaviour and not evidence about the code's condition.
    """
    if not args.conformance:
        return
    from ._conformance import scope_conformance

    root = Path(report["root"])
    changed = changed_paths(root, args.conformance)
    added = added_lines(root, args.conformance)
    report["scope_conformance"] = scope_conformance(
        report, changed, args.conformance, added
    )


def attach_ratchet(report: dict, history_path: Path) -> None:
    """Record whether any category slipped since the last comparable scan."""
    from ._ratchet import dimension_ratchet
    from ._scan_history import read_history

    if not history_path.exists():
        return
    report["dimension_ratchet"] = dimension_ratchet(read_history(history_path))


def attach_run_comparison(
    args: argparse.Namespace, report: dict, history_path: Path
) -> None:
    """Compare this run of a named transformation with earlier ones.

    Only when the operator named one: an unnamed run belongs to no series,
    and inventing a series for it would be the tool answering a question
    nobody asked.
    """
    label = getattr(args, "transformation", None)
    if not label or not history_path.exists():
        return
    from ._run_comparison import compare_runs
    from ._scan_history import read_history

    report["run_comparison"] = compare_runs(read_history(history_path), label)


def _attach_post_audit_records(
    args: argparse.Namespace, report: dict, history_path: Path
) -> None:
    """Records composed from the finished report, before it is rendered.

    All three read the report or the history rather than the tree, and none
    reaches scoring: whether a diff obeyed its work order, whether a
    dimension slipped since the last comparable scan, and how this run of a
    transformation compares with earlier ones are facts about a change and
    its history — not evidence about the code's condition.

    The third is the only one that cannot fail a build. It is a report, by
    design: "run seven moved further than run six" is worth knowing and is
    not a thing to block a merge on.
    """
    attach_conformance(args, report)
    attach_ratchet(report, history_path)
    attach_run_comparison(args, report, history_path)


def _conformance_exit(args: argparse.Namespace, report: dict) -> int:
    """0 to continue; otherwise the exit code the conformance gate demands."""
    if not args.fail_on_out_of_scope:
        return 0
    record = report.get("scope_conformance")
    if record is None:
        print("--fail-on-out-of-scope needs --conformance REVSPEC", file=sys.stderr)
        return 2
    # `clean`, not `conformant`: staying in scope while silencing the finding
    # is the evasion the pairing exists to catch, and a gate that accepted it
    # would be satisfied by the thing it guards against.
    return 0 if record["clean"] else 1


def _regression_exit(args: argparse.Namespace, report: dict) -> int:
    """0 to continue; otherwise the exit code the ratchet demands."""
    if not args.fail_on_regression:
        return 0
    ratchet = report.get("dimension_ratchet")
    if ratchet is None:
        print("--fail-on-regression needs a recorded history (--record-history)",
              file=sys.stderr)
        return 2
    # A run that could not compare does not pass quietly: exiting 0 where the
    # question was never asked is the "absence read as a pass" shape.
    #
    # The reason is not interpolated — it derives from recorded scan history,
    # and code scanning is right that history fields have no business in a log
    # line. It stays in the report, which a caller reads deliberately.
    # Suppressing that alert was refused: this release ships the check that
    # treats a suppression as a finding rather than a fix.
    if not ratchet["comparable"]:
        print("no comparable scan for --fail-on-regression; see "
              "dimension_ratchet.reason in the report", file=sys.stderr)
        return 2
    return 1 if ratchet["regressed"] else 0


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
    conformance = _conformance_exit(args, report)
    if conformance:
        return conformance
    regression = _regression_exit(args, report)
    if regression:
        return regression
    return 0

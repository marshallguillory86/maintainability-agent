"""Rendering what a history shows — the trend and what keeps coming back.

Split from `_scan_view` when that module crossed the 500-line file gate
this project enforces on everyone else. The seam is a real one:
`_scan_view` answers *what was examined in this scan*, and everything
here answers *what several scans show over time*.

The two sections differ in what they ask of a reader. Coverage is a fact
about one run. A trend is a claim across runs, so each section carries
the window it measured, names any break in the series, and states that
nothing here forecasts — a wrong trend looks like knowledge in a way a
wrong snapshot does not.
"""

from __future__ import annotations

from typing import Any

from ._grammar import counted

# What each trajectory means in a sentence, so the word is never left to
# carry the meaning alone. "indistinguishable" in particular reads as a
# hedge unless the reason is beside it.
DIRECTION_NOTE: dict[str, str] = {
    "improving": "the estimate rose beyond either interval",
    "declining": "the estimate fell beyond either interval",
    "flat": "the estimate did not move",
    "indistinguishable": "moved, but by less than the evidence can resolve",
    "unknown": "not computable from these scans",
}


def _velocity_note(segment: dict[str, Any]) -> str:
    """Three states, not two.

    A net of zero is neither improving nor worsening, and collapsing it
    into "adding faster than clearing" printed a claim the two numbers
    beside it contradicted.
    """
    velocity = segment["velocity"]
    if velocity["improving"]:
        return "clearing faster than adding"
    if velocity.get("worsening"):
        return "adding faster than clearing"
    return "unchanged"


def _series_detail(segment: dict[str, Any]) -> list[str]:
    """One segment in full — what it measured and which way it moved."""
    moved = segment["trajectory"]
    note = DIRECTION_NOTE.get(moved["direction"], moved["direction"])
    return [
        "",
        f"- **Direction:** {moved['direction']} — {note}."
        + (f" Change {moved['change']:+.2f}." if moved["change"] is not None else ""),
        f"- **Debt velocity:** {segment['velocity']['introduced']} introduced, "
        f"{segment['velocity']['cleared']} cleared ({_velocity_note(segment)}).",
        f"- **Growth:** {segment['growth']['verdict']}.",
        "- **Never cleared in this window:** "
        f"{counted(segment['persistent_findings'], 'finding')}.",
        "",
    ]


def _current_series(history: list[dict[str, Any]]) -> list[str]:
    """The series the reader is actually in, named as such."""
    segment = history[-1]
    window = f"{segment['from']} to {segment['to']}"
    heading = (
        f"**Current series** — {counted(segment['scans'], 'scan')}, {window}."
        if len(history) > 1 else
        f"{counted(segment['scans'], 'scan')}, {window}."
    )
    lines = []
    if segment["break_reason"]:
        lines.extend([
            f"**This series begins at a break:** {segment['break_reason']}.", "",
        ])
    lines.append(heading)
    lines.extend(_series_detail(segment))
    return lines


def _earlier_series(history: list[dict[str, Any]]) -> list[str]:
    """Everything before the current instrument, as one table.

    Printed as rows rather than as paragraphs each. This repository's own
    history carries 49 segments, and rendering all of them in full made a
    section nobody reads — the earlier scans are real evidence about the
    period they cover, but they are context for today's number, not the
    number itself. The break that ended each one is named, because that
    is the reason it is a separate row at all.
    """
    earlier = history[:-1]
    if not earlier:
        return []
    lines = [
        f"### Earlier series ({counted(len(earlier), 'series', 'series')})",
        "",
        "| Window | Scans | Direction | Change | Began at a break in |",
        "|---|---|---|---|---|",
    ]
    for segment in reversed(earlier):
        moved = segment["trajectory"]
        change = f"{moved['change']:+.2f}" if moved["change"] is not None else "—"
        # `break_summary` names what changed to START this segment, so the
        # column says what the row began at, never what ended it. The
        # summary rather than the full reason: the tail explaining why a
        # break splits a series belongs once, not on every row.
        began = (
            segment.get("break_summary")
            or segment["break_reason"]
            or "the first recorded scan"
        )
        lines.append(
            f"| {segment['from']} to {segment['to']} | {segment['scans']} "
            f"| {moved['direction']} | {change} | {began} |"
        )
    lines.append("")
    return lines


def scan_history_markdown(history: list[dict[str, Any]] | None) -> list[str]:
    """Trends over each comparable segment, and the breaks between them.

    Per segment and never across, because a series spliced over a change
    in the instrument measures the tooling. Where a break happened it is
    named, so a reader can see *why* there are two lines rather than one
    and judge whether the split was warranted.

    Nothing here forecasts. Every figure is a statement about scans that
    happened.
    """
    if not history:
        return []
    lines = ["## Trend", ""]
    if len(history) > 1:
        lines.extend([
            f"{counted(len(history), 'separate series', 'separate series')}. Scans "
            "either side of a break were produced by different instruments and "
            "cannot be compared, so they are reported apart rather than joined "
            "into one line. The current series is given in full; the earlier ones "
            "are summarized, because a reader deciding what to do today is acting "
            "on the instrument in use today.",
            "",
        ])
    lines.extend(_current_series(history))
    lines.extend(_earlier_series(history))
    lines.extend([
        "Every figure above describes scans that happened. This tool does not "
        "forecast, and no number here should be read as one.",
        "",
    ])
    return lines


def escalations_markdown(escalated: list[dict[str, Any]] | None) -> list[str]:
    """Findings that have earned a design conversation, not another patch.

    Placed above the work order because it changes what the reader
    should do rather than adding to it: these are the items the prompt
    now deliberately withholds, and a reader who sees them re-issued
    would be right to distrust the rest.
    """
    if not escalated:
        return []
    lines = [
        "## Design Review Candidates", "",
        "Each of these was fixed and came back. Re-issuing the same advice "
        "produces the same patch and the same return, so the remediation "
        "prompt withholds them — they need a design decision, not another "
        "edit.",
        "",
    ]
    for item in escalated:
        commits = ", ".join(f"`{c[:8]}`" for c in item["commits"])
        lines.extend([
            f"- **`{item['fingerprint']}`** — returned {item['returns']} times.",
            f"  - {item['reason']}.",
            f"  - Returned in: {commits}.",
        ])
    lines.append("")
    return lines


def run_comparison_markdown(comparison: dict[str, Any] | None) -> list[str]:
    """The markdown section. Presentation only — it computes no score.

    Empty for a run nobody named, which is most of them.
    """
    if not comparison:
        return []
    label = comparison["label"]
    lines = [f"## Runs of `{label}`", ""]
    runs = comparison["runs"]
    if not runs:
        return [*lines, comparison["trend"].get("reason", "No runs recorded."), ""]

    lines += ["| Recorded | Commit | Estimate | Moved | Files | Declarations |",
              "|---|---|---|---|---|---|"]
    for run in runs:
        estimate = "withheld" if run["estimate"] is None else f"{run['estimate']:.2f}"
        moved = "—" if run["moved"] is None else f"{run['moved']:+.2f}"
        populations = run["populations"]
        lines.append(
            f"| {run['recorded_at']} | `{(run['commit'] or '')[:8]}` | {estimate} | "
            f"{moved} | {populations.get('files_scanned', '—')} | "
            f"{populations.get('declarations_scanned', '—')} |"
        )
    lines.append("")

    trend = comparison["trend"]
    lines.append(
        f"**{trend['summary']}.**" if trend.get("comparable")
        else f"**Not established:** {trend['reason']}."
    )
    if comparison.get("excluded_earlier_runs"):
        lines += ["", (
            f"{comparison['excluded_earlier_runs']} earlier run(s) under this "
            f"name are excluded: {comparison['exclusion_reason']}."
        )]
    lines += ["", (
        "*`Moved` is the change in estimate between the previous recorded "
        "scan and this one — the movement across that interval, not the "
        "effect of the transformation. Anything else that happened in the "
        "same interval is inside the number, and two runs of one "
        "transformation land on different code.*"
    ), ""]
    return lines

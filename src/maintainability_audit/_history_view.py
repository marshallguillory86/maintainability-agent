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
            f"{len(history)} separate series. Scans either side of a break were "
            "produced by different instruments and cannot be compared, so they "
            "are reported apart rather than joined into one line.",
            "",
        ])
    for index, segment in enumerate(history, start=1):
        if segment["break_reason"]:
            lines.extend([f"**Break before this series:** {segment['break_reason']}.", ""])
        window = f"{segment['from']} to {segment['to']}"
        moved = segment["trajectory"]
        note = DIRECTION_NOTE.get(moved["direction"], moved["direction"])
        lines.append(
            f"**Series {index}** — {segment['scans']} scans, {window}."
            if len(history) > 1 else
            f"{segment['scans']} scans, {window}."
        )
        lines.extend([
            "",
            f"- **Direction:** {moved['direction']} — {note}."
            + (f" Change {moved['change']:+.2f}." if moved["change"] is not None else ""),
            f"- **Debt velocity:** {segment['velocity']['introduced']} introduced, "
            f"{segment['velocity']['cleared']} cleared ({_velocity_note(segment)}).",
            f"- **Growth:** {segment['growth']['verdict']}.",
            f"- **Never cleared in this window:** {segment['persistent_findings']} findings.",
            "",
        ])
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

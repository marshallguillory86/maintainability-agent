"""What the coverage section says after its table.

The table answers "what ran". These three notes answer the questions a
reader has *next*, and each exists because a report that omitted it was
read as good news:

- one source only — examined, but nothing corroborated it;
- a dimension the analyzer tier declined — measured by the built-in
  detectors, and the reader is owed the reason (P8);
- nothing examined — unmeasured, which is not clean.

Split out of `_scan_view` when that module reached this project's own
500-line file limit. They belong together: all three are the coverage
section's prose about its own gaps.
"""

from __future__ import annotations

from typing import Any


def coverage_notes(coverage: dict[str, Any]) -> list[str]:
    """The gap notes, in the order a reader needs them."""
    lines: list[str] = []
    single = coverage.get("concepts_single_source") or []
    if single:
        # Between covered and unexamined. A reader deciding how much
        # weight to put on a finding needs to know nothing corroborated it.
        lines.extend([
            "**One source only:** " + ", ".join(f"`{c}`" for c in single) + ".",
            "",
            "A built-in detector examined these and no external tool did, so "
            "nothing corroborates them. Install a tool covering the concern to "
            "get a second opinion.",
            "",
        ])

    for declined in coverage.get("dimensions_declined") or []:
        # P8, and not a rare path: lizard supplies no cognitive
        # complexity, so a JavaScript repository with lizard installed
        # takes this branch on every run. It used to be silent, which
        # left a declarations rate with nothing saying what produced it
        # -- and left a decision page crediting the analyzer pool for
        # work the built-in scanner was doing (D68).
        lines.extend([
            f"**`{declined['dimension']}` measured by "
            f"{declined['measured_by']}:** {declined['reason']}.",
            "",
        ])

    unexamined = coverage["concepts_unexamined"]
    if unexamined:
        # The point of the whole section. Silence about a concern is not
        # health, and a reader who is not told will assume it is.
        lines.extend([
            "**Nothing examined:** " + ", ".join(f"`{c}`" for c in unexamined) + ".",
            "",
            "These concerns are unmeasured, not clean. Install a tool that covers them, "
            "or widen `analyzers.depth`, to have them reported.",
            "",
        ])

    lines.extend(_child_boundary_note(coverage))
    return lines


def _child_boundary_note(coverage: dict[str, Any]) -> list[str]:
    """What this run does not control about the tools it spawned.

    `docs/product-intent.md` has said since P1 was amended that this
    package "does not sandbox children", and lists *"that third-party
    tools cannot use the network"* among the things it does not promise.
    The **report** did not say it. A reader holding a page headed "the
    analysis itself performs no network access" and a table naming the
    external tools that ran had no way to learn the second sentence does
    not cover the first.

    That makes it P8's gap rather than P1's: the promise was correctly
    scoped all along, and the run relying on that scoping never disclosed
    it to the person reading the output.

    Only when an external tool actually ran. With no children spawned
    there is nothing to disclose, and saying it anyway would be the noise
    this section is careful to avoid.
    """
    spawned = coverage.get("tools_contributed") or 0
    if not spawned:
        return []
    return [
        "**Analyzer children are not network-isolated.** "
        f"{spawned} external {'tool' if spawned == 1 else 'tools'} ran as local "
        "child processes. This agent does not transmit the audited source and "
        "opens no socket of its own, but it does not sandbox what it spawns: a "
        "third-party analyzer that reaches the network is outside what this run "
        "controls or observes. Determinism and no upload are the promise; a "
        "kernel air-gap is not.",
        "",
    ]

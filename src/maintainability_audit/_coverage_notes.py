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
    return lines

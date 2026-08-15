"""The ADR 004 scenario block as Markdown — a skin, never arithmetic."""
from __future__ import annotations

from typing import Any


def economic_impact_markdown(block: dict[str, Any] | None) -> list[str]:
    """The ADR 004 scenario, printed as one — never as an outcome claim.

    Absent entirely when no context was configured: a section explaining
    that there is no money block is noise on every unconfigured report.
    The assumptions render beside the range because they *are* the
    result; the numbers mean nothing without them.
    """
    if not block:
        return []
    currency = block.get("currency", "USD")
    lines = [
        "## Economic Context (scenario)",
        "",
        f"**{block['low']:,.0f} – {block['high']:,.0f} {currency}** over "
        f"{block['planning_horizon_months']} months (base "
        f"{block['base']:,.0f} {currency}), across "
        f"{block.get('work_order_items', 0)} work-order item(s).",
        "",
        "Assumptions:",
        "",
    ]
    lines.extend(f"- {assumption}" for assumption in block.get("assumptions", []))
    incident = block.get("incident_term")
    if incident:
        lines.extend([
            "",
            f"Separate incident term: {incident['representative_incident_cost']:,.0f} "
            f"{currency} — {incident['note']}",
        ])
    lines.append("")
    return lines

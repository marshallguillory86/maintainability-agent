"""Stable identity for findings.

A finding's fingerprint answers "is this the same problem I saw last time?"
Get it wrong and two features break at once: `--fail-on-new` raises false
failures on untouched code, and recurrence tracking cannot tell a returning
finding from a fresh one.

The previous scheme embedded the start line — `function:{path}:{name}:{line}`
— so inserting a single import above an untouched function made it read as
simultaneously fixed and new:

    before: function:big.py:huge:1
    after:  function:big.py:huge:2

Nothing about the function changed. One line was added above it.

So identity here is built only from things an unrelated edit elsewhere in the
file cannot move:

* **path and name**, which survive any amount of insertion;
* an **ordinal** among same-named findings in the same file, ordered by
  position. Two overloads both shift together when a line is inserted above
  them, so their relative order — and therefore their ordinals — hold;
* a **content hash** where the finding is about a block of text rather than a
  named unit, as with duplicate blocks.

Line numbers are still reported everywhere. They are just not identity.

Deliberately derived from the report alone. Identity must not require reading
source, or presentation would need a parsing dependency, and the report would
stop being a self-contained record of its own findings. The declaration body
digest this reads off a hotspot dict was computed at scan time by
`declarations`; nothing here opens the audited tree.

The label *formats* and the structured matching now live in
`_finding_match` (foundations), because the gate and recurrence need the
same rules and may not import presentation. This module keeps the
report-facing lookups and re-exports the labels for its existing callers.
"""

from __future__ import annotations

from typing import Any

from ._finding_match import (
    declaration_fingerprint,
    duplicate_fingerprint,
    file_fingerprint,
    identities_from_report,
    ordinals_by,
    risk_fingerprint,
)

__all__ = [
    "declaration_fingerprint",
    "declaration_identities",
    "duplicate_fingerprint",
    "file_fingerprint",
    "finding_fingerprints",
    "risk_fingerprint",
    "risk_identities",
]


def declaration_identities(report: dict[str, Any]) -> dict[tuple[str, str, int], str]:
    """Canonical identity for every failing declaration in `report`.

    Keyed by `(path, name, start_line)` — enough to pick one declaration
    out of a report, and never part of the identity it returns.

    An ordinal is a property of a *population*, not of a declaration, so
    it cannot be computed from one item in isolation. Every consumer that
    tried got the same wrong answer: `declaration_fingerprint(path, name,
    0)`, which merges two overloads in one file into a single finding.
    The work order named the same declaration twice, `prompt_targets`
    recorded advice about the first one twice, and escalating either
    overload suppressed whichever the prompt compared first.

    So the population, the order rule and the numbering live here, once,
    and consumers look up rather than derive. The failing-only population
    is part of the contract: a warn-status hotspot has no identity here
    because it produces no finding, and numbering it would shift the
    ordinal of every failing declaration below it.
    """
    hotspots = [i for i in report.get("function_hotspots", []) if i["status"] == "fail"]
    ordinals = ordinals_by(hotspots, lambda i: (i["path"], i["name"]), lambda i: i["start_line"])
    return {
        (item["path"], item["name"], item["start_line"]):
            declaration_fingerprint(item["path"], item["name"], ordinals[index])
        for index, item in enumerate(hotspots)
    }


def risk_identities(report: dict[str, Any]) -> dict[tuple[str, str, int], str]:
    """Canonical identity for every risk finding, keyed by `(path, name, line)`.

    Same rule as `declaration_identities`, and it was wrong in the same
    place — `prompt_targets` rebuilt these from the work-order item's
    *title*, so the name it hashed was the label "configured risk
    pattern" rather than the pattern's own name. No such identity is ever
    in the report, so every risk target was silently discarded.
    """
    risks = list(report.get("risk_findings", []))
    ordinals = ordinals_by(risks, lambda i: (i["path"], i["name"]), lambda i: i["line"])
    return {
        (item["path"], item["name"], item["line"]):
            risk_fingerprint(item["path"], item["name"], ordinals[index])
        for index, item in enumerate(risks)
    }


def finding_fingerprints(report: dict[str, Any]) -> set[str]:
    """Every failing finding in `report`, as stable identity labels.

    Derived from the structured identities so the label set and the
    matcher's population cannot disagree about what the scan found.
    """
    return {identity.fingerprint for identity in identities_from_report(report)}

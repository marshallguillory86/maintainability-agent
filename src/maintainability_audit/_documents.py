"""Turning an `Analysis` into the documents a report carries — ADR 006, P8.

Split from `_analysis` when that module crossed the 500-line file gate
this project enforces on everyone else. The seam is the one the design
already had: `_analysis` *runs* the pool and holds what came back;
everything here *states* it — findings located against the root,
measurement distributions, and the coverage record.

The coverage document is the load-bearing one. A score computed from
four tools and one computed from forty are not the same measurement, so
coverage sits beside the score or the score cannot be interpreted — and
it is claimed per language, because one Python build script among three
hundred C++ files must not report the repository as type-checked.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from ._analysis import Analysis, ToolCoverage
from ._corroborate import agreement, combine, single_source_concepts


def _relative(path: str, root: Path) -> str:
    """Repo-relative, so findings read and diff like the rest of the report.

    Tools are handed absolute paths and hand them back. Left as-is the
    report is unreadable, and two runs from different checkout
    directories produce diffs that are entirely path noise.
    """
    try:
        return str(Path(path).resolve().relative_to(root.resolve()))
    except (ValueError, OSError):
        return path


def findings_document(analysis: Analysis, root: Path) -> list[dict[str, Any]]:
    """Every located finding the analyzers produced, report-shaped.

    The point of running the tools. Coverage says *that* they ran;
    without this the report says nine analyzers examined the repository
    and then tells the reader nothing they found — which is worse than
    not running them, because it looks thorough.

    Sorted by path and line so the list is stable between runs and
    diffable, and carrying the producing tool so a reader can go back to
    the raw output behind any row.
    """
    return sorted(
        (
            {
                "concept": finding.concept,
                "path": _relative(finding.path, root),
                "line": finding.line,
                "message": finding.message,
                "tool": finding.tool,
                "rule": finding.rule,
            }
            for finding in analysis.findings
        ),
        key=lambda item: (item["path"], item["line"] or 0, item["tool"], item["message"]),
    )


def measurement_document(analysis: Analysis, root: Path) -> dict[str, Any]:
    """Combined readings, their spread, and the distribution behind them.

    Three kinds of data survive here, deliberately. The **score** needs
    counts and populations; the **report** carries the measurements too,
    because a distribution is what a reader — human or model — can
    actually reason with. "Seven functions failed" supports a sentence;
    "seven failed, worst 45, median 6, and two tools disagree by 60%"
    supports a plan.

    Per-unit readings are summarised rather than listed: a thousand
    functions is a dataset, not a document. The full set stays in the
    findings and the retained raw output.
    """
    combined = combine(analysis.measurements, root)
    spreads = agreement(combined)
    single = single_source_concepts(combined)

    per_concept: dict[str, Any] = {}
    for concept in sorted({item.concept for item in combined}):
        readings = [item for item in combined if item.concept == concept]
        values = sorted(item.value for item in readings)
        corroborated = [item for item in readings if item.corroborated]
        per_concept[concept] = {
            "units": len(readings),
            "tools": sorted({tool for item in readings for tool in item.tools}),
            "corroborated_units": len(corroborated),
            # A lone reading carries a counting convention nobody checked.
            "single_source": concept in single,
            # Mean relative disagreement between tools, absent when only
            # one spoke — zero would read as perfect agreement, which is
            # absence-as-value wearing a statistics hat.
            "tool_disagreement": round(spreads[concept], 3) if concept in spreads else None,
            "distribution": _distribution(values),
        }
    return per_concept


def _distribution(values: list[float]) -> dict[str, float]:
    """Enough shape to reason about, without shipping the raw vector."""
    if not values:
        return {}
    return {
        "min": round(values[0], 2),
        "median": round(values[len(values) // 2], 2),
        "p90": round(values[min(int(len(values) * 0.9), len(values) - 1)], 2),
        "max": round(values[-1], 2),
    }



def _coverage_entry(item: ToolCoverage) -> dict[str, Any]:
    """One source's row, carrying only the fields it actually has."""
    entry: dict[str, Any] = {
        "tool": item.slug, "tier": item.tier, "concepts": list(item.concepts),
    }
    if item.languages:
        # Coverage is claimed per language (P8): a row that ran must say
        # which languages the claim is about, not leave the reader to
        # look the tool up.
        entry["languages"] = list(item.languages)
    if item.version:
        entry["version"] = item.version
    if item.contributed:
        entry["measurements"] = item.measurements
        entry["findings"] = item.findings
        entry["seconds"] = item.duration_seconds
    if item.parse_error:
        entry["parse_error"] = item.parse_error
    elif item.detail:
        # Shipped even when the source contributed. Detail used to mean
        # "why this failed"; for a built-in it means "where this stands
        # against the external tools", which a successful run needs to
        # state more than a failed one does.
        entry["detail"] = item.detail
    return entry


def _language_document(analysis: Analysis) -> dict[str, Any]:
    """The per-language coverage claim, and the scope it is about.

    Separated because `coverage_document` reached complexity 18 against
    this project's own limit of 15 — one branch added each time the
    record gained a fact to state, which is how a reporting function
    becomes unreadable without any single change looking wrong.
    """
    return {
        # The languages this coverage claim is *about*. Without it,
        # `concepts_covered: [types]` reads as "this repository is
        # type-checked" on a tree that is 98% unread C++.
        "scored_languages": sorted(analysis.scored_languages),
        "concepts_covered": sorted(analysis.measured_concepts()),
        # The precise statement. mypy covers types for Python and nothing
        # for C++, at any language mix — no threshold, so a rule fitted
        # to one repository cannot distort another.
        "by_language": {
            name: sorted(covered)
            for name, covered in sorted(analysis.coverage_by_language().items())
        },
        "gaps_by_language": {
            name: sorted(missing)
            for name, missing in sorted(analysis.gaps_by_language().items())
            if missing
        },
    }


def coverage_document(analysis: Analysis) -> dict[str, Any]:
    """The coverage section, as it appears in a report.

    Grouped by outcome because the reader's question is "what did and did
    not run", not "what happened to each of forty tools in catalog order".
    """
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in analysis.coverage:
        key = "parse-error" if item.parse_error else item.outcome
        grouped[key].append(_coverage_entry(item))

    ran = [item for item in analysis.coverage if item.contributed]
    return {
        # Both tiers, because a reader asking what examined this code is
        # owed the whole answer. Built-ins are single-source by
        # definition; analyzers may corroborate each other.
        "sources": {
            "built_in": sum(1 for i in analysis.coverage if i.tier == "built-in"),
            "analyzers": sum(1 for i in ran if i.tier == "analyzer"),
        },
        "selection": {
            "concerns": list(analysis.concerns),
            "depth": analysis.depth,
            "license_policy": analysis.license_policy,
        },
        # Two reports with different coverage are not comparable, so this
        # is stated beside the score rather than filed behind it.
        "tools_attempted": sum(1 for i in analysis.coverage if i.tier == "analyzer"),
        "tools_contributed": sum(1 for i in ran if i.tier == "analyzer"),
        "by_outcome": dict(grouped),
        **_language_document(analysis),
        "concepts_single_source": analysis.single_source_concerns(),
        # A concern nobody examined is Unknown, never clean. Naming it is
        # the difference between a gap and a silence.
        "concepts_unexamined": analysis.gaps(),
        "error": analysis.error,
    }

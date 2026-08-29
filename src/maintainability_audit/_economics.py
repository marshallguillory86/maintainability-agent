"""ADR 004 v1: a configured scenario beside the score, never inside it.

Everything here is arithmetic over numbers the user supplied plus counts
the scan already made. Nothing reaches the network — currency is a
display label — and nothing writes back into the score: the block is
attached after scoring, and the contract holds the score byte-identical
with and without it.

The vocabulary is deliberately narrow. This block states a scenario and
the assumptions that produced it, and nothing else: the words this
module may not use, even to deny them, are enumerated in the contract,
because a denial still plants the frame ("not a p*diction" reads as one
to a skimming executive). Say what it is, not what it is not.
"""
from __future__ import annotations

import os
from typing import Any

# Incremental hours a maintainability finding adds to each change that
# touches it. A named, visible default range — overridable in config as
# `incremental_hours_per_change` — never a hidden coefficient: the value
# prints in the block beside its name.
DEFAULT_INCREMENTAL_HOURS: dict[str, float] = {"low": 0.25, "base": 1.0, "high": 2.0}

_ENV_LABOR = {
    "low": "MAINTAINABILITY_LABOR_LOW",
    "base": "MAINTAINABILITY_LABOR_BASE",
    "high": "MAINTAINABILITY_LABOR_HIGH",
}

FORMULA = (
    "each bound = affected changes/year × incremental hours/change "
    "× loaded labor rate × horizon/12"
)


def economic_context_from(config: dict[str, Any]) -> dict[str, Any] | None:
    """The configured context, with one-run environment overrides applied.

    ``None`` when no labor range exists anywhere — no context is a real
    answer, and defaulting a cost rate nobody stated would put invented
    money in a report. Environment values override the file for this run
    only; nothing here persists them (the TTY ask is what writes).
    """
    block = dict(config.get("economic_context") or {})
    labor = dict(block.get("loaded_engineering_cost_per_hour") or {})
    for bound, variable in _ENV_LABOR.items():
        value = os.environ.get(variable)
        if value is not None:
            labor[bound] = float(value)
    if not all(bound in labor for bound in ("low", "base", "high")):
        return None

    labor = {bound: float(labor[bound]) for bound in ("low", "base", "high")}
    if not 0 < labor["low"] <= labor["base"] <= labor["high"]:
        raise ValueError(
            f"loaded_engineering_cost_per_hour must satisfy 0 < low <= base <= high, got {labor}"
        )

    currency = os.environ.get("MAINTAINABILITY_CURRENCY") or block.get("currency") or "USD"
    horizon = os.environ.get("MAINTAINABILITY_HORIZON_MONTHS") or block.get(
        "planning_horizon_months") or 12

    context: dict[str, Any] = {
        "version": 1,
        "loaded_engineering_cost_per_hour": labor,
        "currency": str(currency),
        "planning_horizon_months": int(horizon),
        "incremental_hours_per_change": {
            bound: float(value)
            for bound, value in (block.get("incremental_hours_per_change")
                                 or DEFAULT_INCREMENTAL_HOURS).items()
        },
    }
    for optional in ("reliability_tier", "typical_review_minutes_per_change",
                     "representative_incident_cost"):
        if block.get(optional) is not None:
            context[optional] = block[optional]
    return context


def _churn_by_path(report: dict[str, Any]) -> dict[str, int]:
    """Commits per file over the history window, or empty without history."""
    history = report.get("history") or {}
    return {
        entry["file"]: int(entry.get("commits", 0))
        for entry in history.get("hotspots") or []
        if entry.get("file")
    }


def _returns_by_fingerprint(report: dict[str, Any]) -> dict[str, int]:
    return {
        item["fingerprint"]: int(item.get("returns", 0))
        for item in report.get("design_review_candidates") or []
        if item.get("fingerprint")
    }


def _exposure(item: dict[str, Any], churn: dict[str, int],
              returns: dict[str, int]) -> float:
    """Recurrence and hotspot churn — what the scan already has, only.

    A finding that cleared and returned outweighs raw churn: every
    return is a change that already paid the incremental cost once and
    will again. Nothing here asks the user anything — ADR 004 v1
    forbids asking for lead time, deploys, incidents or tenure.
    """
    recurrence = returns.get(item.get("fingerprint") or "", 0)
    path_churn = churn.get(item.get("path") or "", 0)
    return 10.0 * recurrence + float(path_churn)


def reorder_by_exposure(report: dict[str, Any]) -> None:
    """Most-exposed first, in place, keeping every item intact.

    Applied only when an economic context exists: exposure is the
    ordering that context asks for, and without one the risk-by-effort
    order stands untouched. The sort moves whole items, so severity,
    risk, effort, band and class delta stay on each one — the standard
    evidence is reordered, never erased.
    """
    churn = _churn_by_path(report)
    returns = _returns_by_fingerprint(report)
    items = report.get("work_order") or []
    items.sort(key=lambda item: (-_exposure(item, churn, returns),
                                 item.get("title") or ""))


def _affected_changes_per_year(report: dict[str, Any]) -> tuple[float, str]:
    """Changes touching work-order files, annualized — with its provenance.

    Preferred source: hotspot churn, whose window is twelve months, so
    commit counts are already per-year. Without usable history the
    fallback assumes one change per work-order item per year, and the
    assumptions list says so — a stated assumption beats a silent zero,
    which would price leaving everything alone at nothing.
    """
    items = report.get("work_order") or []
    churn = _churn_by_path(report)
    if churn:
        # Once per file, not once per row. A file with several work-order
        # items -- a long function and dead code in the same module --
        # has one churn history, and summing it per row multiplied that
        # file's yearly changes by its finding count (Grok e88b429 audit).
        touched = sum(churn.get(path, 0) for path in {item.get("path") or "" for item in items})
        if touched:
            return float(touched), (
                "affected changes/year taken from hotspot churn over the "
                "12-month history window"
            )
    return float(len(items)), (
        "no usable history; assumed one change per work-order item per year"
    )


def economic_impact(report: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    """The low/base/high scenario over the current work-order set.

    Each bound multiplies that bound's rate and hours — low with low,
    high with high — so the range brackets the assumptions rather than
    averaging them. A configured incident cost is its own term, never
    folded into the labor arithmetic.
    """
    labor = context["loaded_engineering_cost_per_hour"]
    hours = context["incremental_hours_per_change"]
    horizon = context["planning_horizon_months"]
    changes, changes_source = _affected_changes_per_year(report)

    assumptions = [
        FORMULA,
        changes_source,
        f"incremental hours/change of {hours['low']}-{hours['high']} "
        f"(base {hours['base']}) — a stated default unless configured",
        f"loaded labor rate {labor['low']}-{labor['high']} {context['currency']}/hour "
        f"(base {labor['base']}), as configured",
        f"planning horizon of {horizon} months",
        "a scenario computed from these assumptions; change them and the "
        "range moves with them",
    ]
    block: dict[str, Any] = {
        "version": 1,
        "low": round(changes * hours["low"] * labor["low"] * horizon / 12.0, 2),
        "base": round(changes * hours["base"] * labor["base"] * horizon / 12.0, 2),
        "high": round(changes * hours["high"] * labor["high"] * horizon / 12.0, 2),
        "currency": context["currency"],
        "planning_horizon_months": horizon,
        "affected_changes_per_year": changes,
        "incremental_hours_per_change": hours,
        "loaded_engineering_cost_per_hour": labor,
        "assumptions": assumptions,
        "work_order_items": len(report.get("work_order") or []),
    }
    incident = context.get("representative_incident_cost")
    if incident is not None:
        block["incident_term"] = {
            "representative_incident_cost": float(incident),
            "note": (
                "a separate term: one representative incident at the "
                "configured cost, kept outside the labor arithmetic; the "
                "scan cannot establish incident rates"
            ),
        }
    if context.get("reliability_tier"):
        block["reliability_tier"] = context["reliability_tier"]
    return block

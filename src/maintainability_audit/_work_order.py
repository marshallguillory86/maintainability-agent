"""What to fix first, what it is worth, and how to check — ADR 007 §3.

The tool has always produced a score and a list of findings. Neither
answers the question a reader actually opens the report to ask: *what do
I do on Monday morning.* A list ordered by count or severity alone
answers it badly and in a specific way — a prompt that opens with eighty
line-length violations is emitting Fill-Ins in the position reserved for
the work that matters, which is the structural cause of nit-loops.

So each finding class declares two judgments, **risk** (what it costs to
leave alone) and **effort** (what it costs to fix), and their matrix
orders the work: Quick Wins lead, Major Projects are named but never
inlined into a prompt, Fill-Ins are offered opportunistically, and
Reconsider is suppressed. The weightings are published in `standard.md`
rather than buried here, because a judgment nobody can see is a judgment
nobody can argue with.

Two properties make an item worth reading:

**The delta is computed.** Each item's score movement comes from a real
rubric recomputation with that finding removed — `scoring.score_report`
over an amended summary, the same entry point every consumer uses. An
estimated delta has the authority of arithmetic and none of its content.

**Nothing is emitted that cannot be checked.** An item without a
location, a target and a verification command is advice, and advice is
what this tool exists to replace.
"""

from __future__ import annotations

from copy import deepcopy
from enum import StrEnum
from typing import Any

from ._identity import (
    declaration_identities,
    file_fingerprint,
    finding_fingerprints,
    risk_identities,
)
from ._work_order_weights import CLASS_RISK_EFFORT, ClassWeight
from .scoring import score_report


class Band(StrEnum):
    """Where a finding sits in the risk/effort matrix."""

    QUICK_WIN = "quick-win"
    MAJOR_PROJECT = "major-project"
    FILL_IN = "fill-in"
    RECONSIDER = "reconsider"


# The line between "bounded work" and "a project", and between "costly to
# leave" and "cosmetic". Both are judgments, stated here and published in
# standard.md so a team that disagrees has a number to point at.
HIGH_RISK = 3
HIGH_EFFORT = 3


def band_of(risk: int, effort: int) -> Band:
    """Which of the four cells a finding falls in."""
    costly = risk >= HIGH_RISK
    expensive = effort >= HIGH_EFFORT
    if costly:
        return Band.MAJOR_PROJECT if expensive else Band.QUICK_WIN
    return Band.RECONSIDER if expensive else Band.FILL_IN


def _score_of(report: dict[str, Any]) -> float | None:
    scored = score_report(report)
    value = scored.get("maintainability_estimate")
    return float(value) if isinstance(value, (int, float)) else None


def _delta_for(report: dict[str, Any], counter: str, amount: int) -> float:
    """How far the score moves when `amount` findings of a class are cleared.

    A real recomputation through `score_report`, the same entry point
    every consumer uses. Returns 0.0 when the score is withheld — a
    repository below the population floor has no number to move, and
    inventing one would be the defect this project exists to remove.
    """
    before = _score_of(report)
    if before is None:
        return 0.0
    amended = deepcopy(report)
    summary = amended["summary"]
    summary[counter] = max(0, int(summary.get(counter, 0)) - amount)
    # A cleared production failure clears the matching production count
    # too, or the amended summary describes a repository where the
    # production breaches outnumber the total ones.
    production = f"production_{counter}"
    if production in summary:
        summary[production] = min(int(summary[production]), int(summary[counter]))
    after = _score_of(amended)
    return round(max(0.0, (after or before) - before), 3)


def _items_from_hotspots(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Declarations past a threshold, worst first."""
    weight = CLASS_RISK_EFFORT["oversized-declaration"]
    # Computed once over the whole population, because an ordinal is a
    # property of the population. Rebuilding it per item is what made
    # two `huge` methods in one file into one finding.
    identities = declaration_identities(report)
    items = []
    for hotspot in report.get("function_hotspots") or []:
        if hotspot.get("status") != "fail":
            continue
        items.append({
            "finding_class": "oversized-declaration",
            "title": f"{hotspot['name']} in {hotspot['path']}",
            "path": hotspot["path"],
            # `start_line` is the only position a hotspot carries; there
            # is no `line` key, so this read None every time and both
            # renderers, which omit a falsy location, printed the
            # declaration with none. The item field stays `line` — that
            # is the shape every finding class publishes, and a file
            # item's None is a real answer rather than a missing one.
            "line": hotspot["start_line"],
            "target": (
                f"reduce below the configured limits "
                f"(currently {hotspot['lines']} lines, complexity {hotspot['complexity']})"
            ),
            # Every oversized declaration shares one class delta, so the
            # delta cannot order them and the list came out alphabetical
            # — telling a reader to start with whichever file sorted
            # first rather than with the 803-line one.
            "severity": float(hotspot["lines"]) + 4.0 * float(hotspot["complexity"]),
            "fingerprint": identities[
                (hotspot["path"], hotspot["name"], hotspot["start_line"])
            ],
            "weight": weight,
        })
    return items


def _items_from_files(report: dict[str, Any]) -> list[dict[str, Any]]:
    weight = CLASS_RISK_EFFORT["oversized-file"]
    return [
        {
            "finding_class": "oversized-file",
            "title": f"{metric['path']} is {metric['lines']} lines",
            "path": metric["path"],
            "line": None,
            "target": "split below the configured file-length limit",
            "severity": float(metric["lines"]),
            "fingerprint": file_fingerprint(metric["path"]),
            "weight": weight,
        }
        for metric in report.get("largest_files") or []
        if metric.get("status") == "fail"
    ]


def _items_from_idioms(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Concerns served by more than one library.

    Its own builder because the finding is shaped unlike every other
    counted class: no `path`, `first_path` or `line` — a concern and a
    list of packages, each with a file count and one example. That is
    the second reason this class never fired; the located loop dropped
    it for having no path. The first was the loop reading
    `idiom_concerns`, a key the report has never carried.

    Located at the least-used package's example, where the prompt and
    the Markdown table already send the reader: it is the library that
    has to move.
    """
    weight = CLASS_RISK_EFFORT["competing-libraries"]
    items: list[dict[str, Any]] = []
    for finding in report.get("divergent_idioms") or []:
        packages = finding.get("packages") or []
        if len(packages) < 2:
            continue
        # Sorted by descending file count upstream: the last row is the
        # minority usage, the first is what to converge on.
        majority, minority = packages[0], packages[-1]
        items.append({
            "finding_class": "competing-libraries",
            "title": (f"{finding['concern']} is served by "
                      f"{', '.join(row['package'] for row in packages)}"),
            "path": minority["example"],
            # About a package's presence across files, not about one
            # line, and the example carries no line number.
            "line": None,
            "target": (f"converge on {majority['package']}; {minority['package']} "
                       f"is used in {minority['files']} file(s)"),
            "severity": float(finding.get("count") or len(packages)),
            "weight": weight,
        })
    return items


def _locate(finding: dict[str, Any]) -> tuple[str | None, int | None]:
    """Path/line; a duplicate block carries only `locations`, which the old path/line read dropped (Grok e88b429)."""
    path = finding.get("path") or finding.get("first_path")
    line = finding.get("line") or finding.get("first_line") or finding.get("start_line")
    if path is None and (locs := finding.get("locations")):
        path, _, tail = str(locs[0]).rpartition(":")
        line = int(tail) if line is None and tail.isdigit() else line
    return path, line


def _items_from_counted(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Classes the report carries as located lists."""
    sources = (
        ("duplicate-block", "duplicate_blocks", "duplicated block"),
        ("near-duplicate", "near_duplicates", "near-duplicate declaration"),
        ("dead-code", "dead_code", "unreferenced declaration"),
        ("risk-pattern", "risk_findings", "configured risk pattern"),
    )
    # Risk findings are the one class here the report gives a stable
    # identity to, so they are the one class that can carry a
    # fingerprint. The rest are located but not yet identified.
    risks = risk_identities(report)
    items: list[dict[str, Any]] = []
    for name, key, label in sources:
        weight = CLASS_RISK_EFFORT[name]
        for finding in report.get(key) or []:
            path, line = _locate(finding)
            if not path:
                continue  # no location, nothing to act on (ADR 007 §3, 4.6)
            item = {
                "finding_class": name,
                "title": f"{label} in {path}",
                "path": path,
                "line": line,
                "target": f"remove the {label}",
                "severity": float(finding.get("lines") or finding.get("similarity")
                                   or finding.get("count") or 1),
                "weight": weight,
            }
            if name == "risk-pattern":
                item["fingerprint"] = risks[(path, finding["name"], finding["line"])]
            items.append(item)
    return items


def work_order(report: dict[str, Any], include_reconsider: bool = False) -> list[dict[str, Any]]:
    """Every actionable finding, ordered by risk against effort.

    Quick Wins first, then Major Projects, then Fill-Ins; Reconsider is
    suppressed unless asked for. Within a band, the larger score movement
    leads — the delta is a recomputation, so this orders by measured
    value rather than by how many of something there are.
    """
    raw = (
        _items_from_hotspots(report)
        + _items_from_files(report)
        + _items_from_counted(report)
        + _items_from_idioms(report)
    )

    # Two recomputations per class, and the second is the one worth
    # printing. The published estimate is the mean of the *rounded*
    # categories — deliberately, so the overall is the mean of the
    # numbers beside it — which makes it a step function. Clearing one
    # oversized declaration out of four therefore moves it by exactly
    # 0.0, measured, on a repository where clearing all four moves it
    # 0.2. A work order quoting per-item deltas quotes zeros and cannot
    # order anything, so each item also carries what clearing its whole
    # class is worth, and that is what the ordering uses.
    counts: dict[str, int] = {}
    for entry in raw:
        counts[entry["finding_class"]] = counts.get(entry["finding_class"], 0) + 1
    per_class: dict[str, float] = {}
    class_delta: dict[str, float] = {}
    ordering = {Band.QUICK_WIN: 0, Band.MAJOR_PROJECT: 1, Band.FILL_IN: 2, Band.RECONSIDER: 3}
    items: list[dict[str, Any]] = []
    for entry in raw:
        weight: ClassWeight = entry.pop("weight")
        name = entry["finding_class"]
        if name not in per_class:
            per_class[name] = _delta_for(report, weight.counter, 1)
            class_delta[name] = _delta_for(report, weight.counter, counts[name])
        band = band_of(weight.risk, weight.effort)
        if band is Band.RECONSIDER and not include_reconsider:
            continue
        items.append({
            **entry,
            "band": band.value,
            "risk": weight.risk,
            "effort": weight.effort,
            "rationale": weight.rationale,
            # What clearing this one finding moves the published score,
            # which is honestly zero more often than not.
            "delta": per_class[name],
            # What clearing every finding of this class is worth, and how
            # many that is. The number a reader can plan against.
            "class_delta": class_delta[name],
            "class_count": counts[name],
            "verification": weight.verification,
        })

    items.extend(_items_from_semantic(report))
    items.sort(key=lambda item: (
        ordering[Band(item["band"])], -item["class_delta"],
        # Within a class every delta is identical, so severity is what
        # actually orders the work a reader will do first.
        -item["severity"], item["path"]))
    return items


def _items_from_semantic(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Universal and policy semantic findings as work items (ADR 003).

    Candidates are deliberately absent: they are design-review material
    for the prompt, not work anyone was proven to owe. Deltas are an
    exact 0.0 rather than a recomputation, because the score never
    counted semantic findings and a nonzero delta would claim it had.
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    for finding in report.get("semantic_findings") or []:
        if finding.get("class") in ("universal", "policy"):
            grouped.setdefault(finding["class"], []).append(finding)
    items: list[dict[str, Any]] = []
    for classification, findings in grouped.items():
        # Typed facts are precise and local; policy work touches a
        # declared boundary, which is more coordination than code.
        risk, effort = (4, 2) if classification == "universal" else (4, 3)
        band = band_of(risk, effort)
        for finding in findings:
            evidence = finding.get("source_evidence") or {}
            if not evidence.get("path"):
                continue
            items.append({
                "finding_class": f"semantic-{classification}",
                "title": f"{finding['rule_id']} in {evidence['path']}",
                "path": evidence["path"],
                "line": evidence.get("line"),
                "target": finding.get("message") or "",
                "severity": 1.0,
                "band": band.value,
                "risk": risk,
                "effort": effort,
                "rationale": (
                    "a type checker proved this fact about the code"
                    if classification == "universal"
                    else "the repository's checked-in policy declares this boundary"
                ),
                "delta": 0.0,
                "class_delta": 0.0,
                "class_count": len(findings),
                "verification": "python -m maintainability_audit --root . --format json",
            })
    return items


def work_order_rows(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Display rows, with each class's worth stated once.

    `class_delta` is what clearing the *whole class* moves the score, so
    printing it on every row invites a reader to add the column up: on
    click, thirty rows each read "+0.10" for work worth +0.10 in total.
    The first item of each class carries the figure and its scope; the
    rest carry a dash.
    """
    seen: set[str] = set()
    rows = []
    for item in items:
        name = item["finding_class"]
        stated = name in seen or not item["class_delta"]
        worth = "—" if stated else f"+{item['class_delta']:.2f} for all {item['class_count']}"
        seen.add(name)
        rows.append({**item, "worth": worth})
    return rows


def combined_delta(report: dict[str, Any], items: list[dict[str, Any]]) -> float:
    """What clearing *all* of these together is actually worth.

    Never the sum of the per-item deltas, and the difference is the
    point: findings of one class share a denominator, so the second
    clearance is worth less than the first. Quoting a sum would overstate
    the value of a work order by more the longer it gets.
    """
    before = _score_of(report)
    if before is None:
        return 0.0
    amended = deepcopy(report)
    summary = amended["summary"]
    counts: dict[str, int] = {}
    for item in items:
        weight = CLASS_RISK_EFFORT.get(item["finding_class"])
        if weight is None:
            # Semantic classes have no summary counter: the score never
            # counted them, so clearing them moves it by exactly nothing.
            continue
        counts[weight.counter] = counts.get(weight.counter, 0) + 1
    for counter, amount in counts.items():
        summary[counter] = max(0, int(summary.get(counter, 0)) - amount)
        production = f"production_{counter}"
        if production in summary:
            summary[production] = min(int(summary[production]), int(summary[counter]))
    after = _score_of(amended)
    return round(max(0.0, (after or before) - before), 3)


def prompt_items(items: list[dict[str, Any]], limit: int = 12,
                 escalated: set[str] | None = None) -> list[dict[str, Any]]:
    """The subset safe to hand an agent.

    Major Projects are named in the report and withheld here. An agent
    told to deduplicate a pattern across forty files produces exactly the
    sprawling, unreviewable diff the bounded prompt exists to prevent —
    the work is real, and it needs a human to scope it first.

    `escalated` withholds findings that have already been fixed and come
    back twice. Re-issuing advice the history shows does not hold is the
    nit-loop: the same patch produces the same return, and the evidence
    says the finding is a symptom. Naming it in the report while the
    prompt asks for it a third time would change nothing.
    """
    blocked = escalated or set()
    return [
        item for item in items
        if item["band"] != Band.MAJOR_PROJECT.value
        and item.get("fingerprint") not in blocked
    ][:limit]


# The axes a reader can narrow by. Every one is a field already on the
# item — filtering reads what the audit gathered and shows less of it.
# It computes nothing, which is the property that keeps one rubric
# applying to every repository: a filter that could move a number would
# mean two people scoring the same tree differently because they asked
# different questions.
SELECTABLE: tuple[str, ...] = ("band", "finding_class", "path", "verification")


def select(items: list[dict[str, Any]], **criteria: str) -> list[dict[str, Any]]:
    """The subset matching every criterion given.

    `path` matches a prefix, so a directory selects everything under it;
    the rest match exactly. Unknown axes raise rather than silently
    returning everything — a filter that quietly ignores what it was
    asked is worse than one that refuses, because the caller believes
    the narrowing happened.
    """
    unknown = sorted(set(criteria) - set(SELECTABLE))
    if unknown:
        raise ValueError(f"cannot select on {unknown}; available axes are {list(SELECTABLE)}")

    def matches(item: dict[str, Any]) -> bool:
        return all(
            str(item.get(axis, "")).startswith(value) if axis == "path"
            else item.get(axis) == value
            for axis, value in criteria.items()
        )

    return [item for item in items if matches(item)]


def prompt_targets(report: dict[str, Any]) -> tuple[str, ...]:
    """The identities a generated prompt actually asked somebody to fix.

    In the same identity space the history stores, so a later run can
    ask whether *this specific thing* cleared. Derived from the same
    `prompt_items` the prompt renders, rather than recomputed alongside
    it — two derivations of "what did we ask for" would drift, and the
    one that drifts is the one nobody reads.

    This is what makes recurrence a strong signal. "A rule fired again"
    says only that a file changed twice. "The thing we told you to fix
    came back" says the advice did not hold, and only something that
    remembers what it advised can say it.

    The item already carries its identity, so this reads it. It used to
    rebuild one from the item's rendered title — `title.split(" in ",
    1)[0]` to recover a declaration's name, and the whole title for a
    risk finding, which is the label "configured risk pattern" and never
    a real name. Parsing prose back into an identifier is a second
    identity scheme wearing the first one's clothes, and it disagreed
    with the original in two ways at once: every declaration came out
    `#0`, and no risk target survived the corroboration check below.
    """
    # The same escalation filter the rendered prompt applies (audit
    # H1): a target the prompt deliberately withheld as a design-review
    # candidate was never advice, and recording it would falsify the
    # told-fixed-returned signal this exists to feed.
    escalated = {
        item["fingerprint"]
        for item in report.get("design_review_candidates") or []
    }
    known = set(finding_fingerprints(report))
    targets = set()
    for item in prompt_items(report.get("work_order") or [], escalated=escalated):
        fingerprint = item.get("fingerprint")
        if fingerprint is None:
            continue
        # Only identities this scan actually produced. A target the
        # report cannot corroborate would record advice about a finding
        # that does not exist, and a later run would score it as never
        # cleared forever.
        if fingerprint in known:
            targets.add(fingerprint)
    return tuple(sorted(targets))

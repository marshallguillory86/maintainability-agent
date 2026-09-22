"""Who gets handed what: the prompt-facing subset of the work order.

Split from `_work_order` at that module's own `max_file_lines`, which
D207 crossed and D208 filed rather than fixed in the same change.

**The seam was already named.** `architecture.md` says presentation may
import "`_work_order`'s presentation-facing prompt selection" — a
carve-out describing a module boundary that did not exist, enforced by
nobody. It exists now, so the rule is a module name rather than a
sentence: `_work_order` decides what the findings are worth and how they
are ordered; this decides which of them an agent is handed, and the two
grow for different reasons.

What lives here is one question asked several ways. `withheld_reason` is
the rule — a Major Project needs a design decision, and a finding fixed
before that came back needs one too. `withheld_targets` and
`is_withheld` carry it to the prompt's focus lists (D207), `prompt_items`
and `prompt_advised` to the bounded paste, `prompt_targets` to the
conformance record. They were already one rule; they were not already
one module, and every time the rule was extended it was extended in some
of these places and not others.

Nothing here computes a score, filters by anything the item does not
already carry, or reads the tree.
"""
from __future__ import annotations

from typing import Any

from ._identity import finding_fingerprints
from ._work_order import Band, _locate


def escalated_fingerprints(report: dict[str, Any]) -> set[str]:
    """The findings history shows were fixed and came back, as fingerprints."""
    return {item["fingerprint"] for item in report.get("design_review_candidates") or []}


def withheld_reason(item: dict[str, Any], escalated: set[str] | None = None) -> str | None:
    """Why no agent is handed this item as a patch, or `None` when one is (D180).

    The one rule the bounded prompt and every copy-paste block read. The
    prompt withheld the demo's two duplicated blocks as needing a design
    decision while the report's standalone block for each said "Task: remove
    the duplicated block" — the same run authorising and forbidding the same
    change, depending on which text was pasted.
    """
    if item["band"] == Band.MAJOR_PROJECT.value:
        return ("it is a Major Project — the change it needs is a design "
                "decision before code moves, not one reviewable patch")
    if item.get("fingerprint") in (escalated or set()):
        return ("it was fixed before and came back, so the same edit is known "
                "not to hold and the surrounding design needs a decision")
    return None


def withheld_targets(report: dict[str, Any],
                     escalated: set[str] | None = None) -> set[Any]:
    """Everything the bounded prompt refuses to hand an agent, as targets.

    `withheld_reason` is the one rule, and it has two clauses — a Major
    Project, and a finding fixed before that came back. Until now only
    the second reached the prompt's focus sections, and only three of
    their seven categories, so the same prompt printed *"Not in scope for
    this change … Do not attempt them here"* and then listed those very
    targets under "to inspect first" (D207).

    Two kinds of key, because the report only identifies some findings.
    Risk patterns, hotspots and large files carry a stable fingerprint.
    Duplicate blocks, near-duplicates, dead code and competing libraries
    are "located but not yet identified" — `_items_from_counted` says so
    — and a location is what they have. Both are emitted, so a caller
    matches on whichever it can produce for the finding in hand.

    The location comes from `_locate`, the same function that placed the
    work-order item, so "the same finding" means the same thing in the
    text that withholds it and the text that would have listed it.
    """
    blocked = escalated if escalated is not None else escalated_fingerprints(report)
    targets: set[Any] = set()
    for item in report.get("work_order") or []:
        if withheld_reason(item, blocked) is None:
            continue
        # One key per item, never both. An identified item is matched by
        # identity, because a location cannot tell two overloads in one
        # file apart and emitting both keys hides the sibling — the
        # defect `test_escalating_one_overload_does_not_hide_the_other`
        # holds. An unidentified one has only its location, which is
        # what `_items_from_counted` means by "located but not yet
        # identified".
        if item.get("fingerprint"):
            targets.add(item["fingerprint"])
        elif item.get("path"):
            targets.add((item["path"], item.get("line")))
    return targets


def is_withheld(targets: set[Any], finding: dict[str, Any],
                fingerprint: str | None = None) -> bool:
    """Whether this raw finding is one the prompt already refused.

    **Identity decides for a class that has one; location only for a
    class that has none, and the two are not interchangeable.** A
    location is coarser than the identity it stands in for, so
    consulting it for an identified finding lets one class's withheld
    finding suppress another class's listed one. A caller passes
    `fingerprint` exactly when the finding's class is identified; the
    location key is reserved for the classes `_items_from_counted` calls
    "located but not yet identified". D207 records the two wrong
    attempts that established this.

    Located with `_locate` rather than by reading `path`/`line` directly:
    a duplicate block carries neither and has to be read out of
    `locations`, which is the miss the audit of `e88b429` found once
    already.
    """
    if fingerprint is not None:
        return fingerprint in targets
    path, line = _locate(finding)
    return path is not None and (path, line) in targets


def prompt_items(items: list[dict[str, Any]], limit: int = 12,
                 escalated: set[str] | None = None) -> list[dict[str, Any]]:
    """Agent subset: no major projects, no escalated returns; Severe leads.

    The economic reorder orders items by exposure within each band (D170),
    so a risk-5 item can still sit below hotter Quick Wins of other classes.
    The table can stay exposure-ordered; the paste of 12 cannot drop Severe.
    """
    eligible = [item for item in items if withheld_reason(item, escalated) is None]
    severe = [item for item in eligible if item.get("risk") == 5]
    rest = [item for item in eligible if item.get("risk") != 5]
    return _one_per_class(severe + rest)[:limit]


def _one_per_class(ordered: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The best member of each finding class, in the order they arrived.

    **The paste is twelve kinds of work, not twelve rows.** Without this
    a class with a hundred members takes every slot: measured on a real
    tree, 100 of 125 items were one class and all twelve went to it,
    six of them naming the same file, while 24 duplicate blocks and an
    oversized file got none. The prompt says "the first items are the
    highest value for the least change" and then spent its whole budget
    on one rule while omitting two others entirely (D159).

    One row per class is enough because the row already carries the
    whole class: `class_count` and `class_delta` are on every item, so
    it reads "clearing all 100 of these is worth +0.20" rather than
    printing a hundred line numbers. An agent is better instructed by
    one rule and its count than by twelve instances of it.

    Order is preserved rather than re-sorted, so Severe still leads and
    the economic ordering behind it still holds — this removes
    repetition and decides nothing about priority.
    """
    spread: dict[str, set[str]] = {}
    for item in ordered:
        name = str(item.get("finding_class") or item.get("title"))
        spread.setdefault(name, set()).add(str(item.get("path") or ""))

    seen: set[str] = set()
    first: list[dict[str, Any]] = []
    for item in ordered:
        name = str(item.get("finding_class") or item.get("title"))
        if name in seen:
            continue
        seen.add(name)
        # The surviving row keeps its own title, which names one file,
        # so it must also say how far the class reaches — otherwise a
        # row standing for 46 findings across seven files reads as one
        # finding in the file it happens to name.
        first.append({**item, "class_paths": len(spread[name])})
    return first


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


def prompt_advised(items: list[dict[str, Any]], limit: int = 12,
                   escalated: set[str] | None = None) -> list[dict[str, Any]]:
    """Every eligible item the prompt's rows stand for.

    `prompt_items` returns one row per class, because a paste of twelve
    is twelve *kinds* of work (D159). What was advised is wider than
    what was printed: a row reading "clearing all 68 of these" asks for
    all 68, so recurrence has to remember all 68.

    Derived from `prompt_items` rather than re-selected beside it. The
    advised set is the classes those rows name, and this expands them —
    one decision about what to advise, two views of it. Two independent
    selections would drift, and the one that drifts is the one nobody
    reads.
    """
    advised = {
        str(item.get("finding_class") or item.get("title"))
        for item in prompt_items(items, limit, escalated)
    }
    blocked = escalated or set()
    return [
        item for item in items
        if item["band"] != Band.MAJOR_PROJECT.value
        and item.get("fingerprint") not in blocked
        and str(item.get("finding_class") or item.get("title")) in advised
    ]


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
    # Every member of every advised class, not only the rows printed:
    # the prompt asks for the whole class, so the told-fixed-returned
    # signal has to cover the whole class (D159).
    for item in prompt_advised(report.get("work_order") or [], escalated=escalated):
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

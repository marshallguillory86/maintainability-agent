"""The five pillars, and the scope this tool declares for each — ADR 007 §1.

The taxonomy is the top-level reporting shape, and **declaring scope per
pillar is itself a fix**. Before this, the tool said nothing about
efficiency and nothing about security, and silence reads as "fine" —
which is the absence-as-value defect wearing its most respectable
disguise, because the reader supplies the reassurance themselves.

Two pillars are permanently out of scope and say so with their reason.
Efficiency needs profiling, load testing and runtime telemetry that no
static pass produces. Security belongs to `secure-code-agent`, and the
entry names it, so nobody reads an empty section as a clean bill of
health.

Each in-scope pillar carries **two values that are never averaged**:
practice level, from configuration and CI, and condition, from the
analyzers. They answer different questions and their matrix is the
finding — a clean scan with no enforcement is `unverified`, not healthy,
and that cell is where the hello-world A+ came from. A function combining
them would reinstate exactly the defect the split exists to remove, so
`test_practice_and_condition_are_never_averaged` parses this module and
refuses one.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class Scope(StrEnum):
    """What this tool can honestly say about a pillar."""

    OWNED = "owned"
    PARTIAL = "partial"
    OUT_OF_SCOPE = "out-of-scope"
    DELEGATED = "delegated"


@dataclass(frozen=True)
class Pillar:
    """One pillar, its scope, and the aspects that feed its condition."""

    name: str
    scope: Scope
    reason: str
    # Aspect names from the existing rubric whose scores roll up here.
    # Empty for a pillar this tool does not measure — and empty is the
    # point: a pillar with no aspects reports `None`, never zero.
    aspects: tuple[str, ...] = ()


PILLARS: tuple[Pillar, ...] = (
    Pillar(
        name="readability",
        scope=Scope.PARTIAL,
        reason=(
            "linter conformance, docstring coverage and declaration size are "
            "measured; naming conventions and clarity are not"
        ),
        aspects=("declaration_size", "documentation", "idiom_consistency"),
    ),
    Pillar(
        name="maintainability",
        scope=Scope.OWNED,
        reason="the ISO 25010 decomposition this tool scores in full is the detail view",
        # The rubric's own aspect names, not the ISO *category* names.
        # Declared as `analyzability`/`modularity`/... this pillar showed
        # an empty condition on every repository, because the scorer
        # emits aspects and those four are the categories above them.
        aspects=(
            "file_size", "duplication", "near_duplication", "change_coupling",
            "churn_hotspots", "dead_code", "knowledge_concentration",
        ),
    ),
    Pillar(
        name="efficiency",
        scope=Scope.OUT_OF_SCOPE,
        reason=(
            "requires profiling, load testing and runtime telemetry, none of "
            "which a static pass produces; permanently out of scope rather "
            "than temporarily unmeasured"
        ),
    ),
    Pillar(
        name="security",
        scope=Scope.DELEGATED,
        reason=(
            "delegated to secure-code-agent, which this audit runs for the pillar; "
            "when no measurement comes back the reason is given here, because "
            "silence is not safety"
        ),
    ),
    Pillar(
        name="testability",
        scope=Scope.PARTIAL,
        reason=(
            "test presence, declaration size and policy gates are measured; "
            "coverage and mutation results only when the operator supplies them"
        ),
        aspects=("test_presence", "policy_gates"),
    ),
)


# The matrix in ADR 007 §2, named. Two axes, four cells, and the one that
# matters is bottom-right: good condition with no enforcement is not
# health, it is a clean scan with nothing holding it that way tomorrow.
HIGH_PRACTICE = 3
GOOD_CONDITION = 3.5


def posture(level: int, condition: float | None) -> str:
    """Which cell of the practice/condition matrix a pillar sits in.

    `condition is None` means nothing was measured, so there is nothing
    to be reassured by. The practice axis answers alone, and it can only
    reach `unverified` — never `healthy`, which would be the practice
    level vouching for code nobody looked at.
    """
    enforced = level >= HIGH_PRACTICE
    if condition is None:
        return "unverified"
    if condition >= GOOD_CONDITION:
        return "healthy" if enforced else "unverified"
    return "managed debt" if enforced else "unmanaged debt"


def _measured(aspects: tuple[str, ...], scores: dict[str, Any]) -> tuple[str, ...]:
    """Which of this pillar's aspects actually carried a number."""
    return tuple(
        name for name in aspects
        if isinstance(scores.get(name), (int, float))
    )


def _condition(aspects: tuple[str, ...], scores: dict[str, Any]) -> float | None:
    """The mean of this pillar's measured aspects, or None.

    None when nothing under the pillar was measurable — never a zero and
    never a default. Averaging *within* one axis is fine; it is combining
    the two axes that is forbidden.

    **The mean is over what was measured, which is the only honest
    arithmetic and is not the whole story.** Dropping an unmeasured
    aspect is not the same as it having scored well, and this number
    cannot tell the difference: a maintainability pillar whose worst
    aspect went unmeasured reads 5.0 where measuring it would have read
    4.43. That is P3's shape — withholding evidence improving a reported
    value — and the overall grade is defended against it by
    `_grade_on_the_floor`, which prices unknowns at 0 so concealment can
    only cost.

    The same defence is wrong here. A pillar's condition is defined by
    [ADR 007](../../docs/adr-007-pillars-and-practice.md) as the mean of
    its measured aspects, and a delegated pillar's condition arrives
    already computed by the tool that owns it — flooring one side would
    make the two incomparable in the same column. So the fix is
    disclosure, not different arithmetic: `condition_coverage` on the
    entry names what produced the number, and no skin prints the number
    without it (D206).
    """
    values = [scores[name] for name in _measured(aspects, scores)]
    return round(sum(values) / len(values), 2) if values else None


def condition_coverage(
    aspects: tuple[str, ...],
    scores: dict[str, Any],
    not_applicable: frozenset[str] | set[str] | tuple[str, ...] = (),
) -> dict[str, Any]:
    """What produced this pillar's condition, so the number is attributable.

    Three states, because two of them mean opposite things. `measured`
    carried a number. `unknown` could not be measured — missing
    evidence, a shallow clone, an analyzer that did not run — and is the
    set whose absence flatters the mean. `not_applicable` was looked for
    and had no population, which is a resolved absence and no reflection
    on the code.

    P8 is the requirement: a reported value names what produced it. A
    condition of 5.0 over four of seven aspects and one over seven of
    seven are different claims, and until this they printed identically.
    """
    resolved = frozenset(not_applicable)
    measured = _measured(aspects, scores)
    absent = [name for name in aspects if name not in measured]
    return {
        "measured": list(measured),
        "unknown": [name for name in absent if name not in resolved],
        "not_applicable": [name for name in absent if name in resolved],
    }


#: What a delegated pillar's entry takes from the producer's document.
#: Named rather than copied wholesale, so a field added upstream cannot
#: appear in this tool's report carrying meaning nobody here has checked.
CARRIED = (
    "practice",
    "condition",
    "condition_letter",
    "posture",
    "verified_grade",
    "evidence_status",
    "evidence_reasons",
    "coverage",
    "findings_by_severity",
    "reported_not_scored",
    "loc_scanned",
    #: v2 of the contract. The producer's identifier for its scoring
    #: model, which is what a delegated trend is keyed on (D155). Absent
    #: on a v1 document, and `None` there rather than invented — the
    #: history falls back to the producer version, which fragments
    #: pre-field releases correctly instead of asserting they shared one
    #: model.
    "scoring_model",
)


def delegated_entry(pillar_name: str, document: dict[str, Any]) -> dict[str, Any]:
    """The pillar block for a pillar another tool measured.

    Both axes as the producer reported them, and no mean of them: the
    prohibition is ADR 007 §2's and it does not weaken because the
    numbers arrived from somewhere else. The producer's own module
    carries the same guard.

    `scope` stays `delegated` — this tool still does not measure
    security, and the document does not change that. What changes is
    that the entry now carries the measurement instead of an apology for
    not having one, and names who made it.
    """
    entry: dict[str, Any] = {
        "pillar": pillar_name,
        "scope": "delegated",
        "reason": str(document.get("reason") or ""),
        "delegated_to": (document.get("producer") or {}).get("tool"),
        "producer_version": (document.get("producer") or {}).get("version"),
        "generated": document.get("generated"),
        "aspects": [],
    }
    for field in CARRIED:
        if field in document:
            entry[field] = document[field]

    # `practice` is an **integer** in every entry, because every renderer
    # prints it into a column beside the others and a dict lands in that
    # cell as `{'level': 5, 'summary': ...}`. The first cut of this carried
    # the producer's block under that key and did exactly that: the data
    # was right and the report was garbage, which is this project's
    # oldest failure shape — the product produced the right thing and
    # nothing told the reader.
    #
    # The block is kept whole under `practice_detail`, because the signals
    # naming the files that prove a maturity level are the only reason it
    # is checkable, and flattening to the number would throw that away.
    practice = document.get("practice")
    if isinstance(practice, dict):
        entry["practice"] = practice.get("level")
        entry["practice_detail"] = practice
    return entry


def _measured_entry(
    pillar: Pillar,
    aspects: dict[str, Any],
    not_applicable: frozenset[str],
    level: int,
    stated_reason: str | None,
) -> dict[str, Any]:
    """One pillar's entry, for a pillar this tool measures or declines to.

    Split out of `pillar_report` for this project's own function-length
    gate, which the D206 additions pushed it past — the same move D196
    made on `_runner._classify_completed`, and the reason to make it
    rather than delete a comment is that the comments here are the
    record of two defects.

    A pillar this tool does not measure has no reading at all. The first
    version printed "efficiency — healthy" from the practice axis alone:
    a maturity level vouching for code the tool had explicitly declared
    out of scope, which is the exact silence-reads-as-fine defect this
    pillar block exists to end.
    """
    in_scope = pillar.scope in (Scope.OWNED, Scope.PARTIAL)
    measured = _condition(pillar.aspects, aspects) if in_scope else None
    return {
        "pillar": pillar.name,
        "scope": pillar.scope.value,
        "reason": stated_reason or pillar.reason,
        # Both axes, side by side, never merged. A consumer reads either
        # one; nothing in the document offers their mean.
        #
        # **And neither axis is reported for a pillar this tool does not
        # measure.** `posture` was nulled for that reason when the first
        # version printed "efficiency — healthy" from practice alone;
        # `practice` was left behind, so the efficiency row went on
        # reading "practice 4" for a pillar the tool declares out of
        # scope, and the unmeasured security row said the same — this
        # repository's own maturity level standing in for one nobody
        # took (D210). A delegated pillar that *did* come back with a
        # document carries the producer's practice instead, which is a
        # real measurement of that pillar; `delegated_entry` sets it.
        "practice": level if in_scope else None,
        "condition": measured,
        "posture": posture(level, measured) if in_scope else None,
        "aspects": list(pillar.aspects),
        # What the condition was computed from. `aspects` above is what
        # the pillar *declares*, which stops being what the number came
        # from the moment one of them could not be measured (D206).
        "condition_coverage": (
            condition_coverage(pillar.aspects, aspects, not_applicable)
            if in_scope else None
        ),
    }


def pillar_report(
    score: dict[str, Any],
    practice: dict[str, Any],
    delegated: dict[str, dict[str, Any]] | None = None,
    unmeasured: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    """The pillar block exactly as it ships.

    `unmeasured` names, per delegated pillar, why no measurement came back
    from a run of the tool that owns it (D177), and replaces the generic
    reason so the reader learns what actually happened.

    Practice arrives as an argument rather than being computed here.
    `_practice` reads the repository's configuration off disk, which
    makes it a scanner, and the scoring layer may not reach upward into
    one — `test_scoring_never_imports_scanners_or_assembly` refuses it,
    and correctly: a rubric that can read the tree is a rubric that can
    acquire a special case for a particular repository.
    """
    resolved = practice
    handed_over = delegated or {}
    aspects = score.get("aspects") or {}
    # Which `None`s are a resolved absence rather than missing evidence.
    # Read from the score rather than recomputed: the scorer already made
    # this call for the grade, and a second opinion here would be a
    # second rubric (D206).
    not_applicable = frozenset(score.get("not_applicable") or ())
    report: list[dict[str, Any]] = []
    for pillar in PILLARS:
        # A delegated pillar reports what the tool that owns it measured,
        # when that tool left a document. `NotApplicable` was always a
        # placeholder for this: security is a pillar of the source
        # framework, out of scope here by design, and the point of
        # declaring the scope was to make the handoff sayable rather than
        # to close the question (ADR 007 §1).
        if pillar.scope is Scope.DELEGATED and pillar.name in handed_over:
            report.append(delegated_entry(pillar.name, handed_over[pillar.name]))
            continue
        report.append(_measured_entry(
            pillar, aspects, not_applicable, resolved["level"],
            (unmeasured or {}).get(pillar.name),
        ))
    return report

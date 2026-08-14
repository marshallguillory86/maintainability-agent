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
            "delegated to secure-code-agent; this tool catalogues security "
            "analyzers and never runs them, so silence here is not safety"
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


def _condition(aspects: tuple[str, ...], scores: dict[str, Any]) -> float | None:
    """The mean of this pillar's measured aspects, or None.

    None when nothing under the pillar was measurable — never a zero and
    never a default. Averaging *within* one axis is fine; it is combining
    the two axes that is forbidden.
    """
    values = [
        scores[name] for name in aspects
        if isinstance(scores.get(name), (int, float))
    ]
    return round(sum(values) / len(values), 2) if values else None


def pillar_report(score: dict[str, Any], practice: dict[str, Any]) -> list[dict[str, Any]]:
    """The pillar block exactly as it ships.

    Practice arrives as an argument rather than being computed here.
    `_practice` reads the repository's configuration off disk, which
    makes it a scanner, and the scoring layer may not reach upward into
    one — `test_scoring_never_imports_scanners_or_assembly` refuses it,
    and correctly: a rubric that can read the tree is a rubric that can
    acquire a special case for a particular repository.
    """
    resolved = practice
    aspects = score.get("aspects") or {}
    report: list[dict[str, Any]] = []
    for pillar in PILLARS:
        measured = (
            _condition(pillar.aspects, aspects)
            if pillar.scope in (Scope.OWNED, Scope.PARTIAL)
            else None
        )
        # A pillar this tool does not measure has no reading at all.
        # The first version printed "efficiency - healthy" from the
        # practice axis alone: a maturity level vouching for code the
        # tool had explicitly declared out of scope, which is the exact
        # silence-reads-as-fine defect this pillar block exists to end.
        in_scope = pillar.scope in (Scope.OWNED, Scope.PARTIAL)
        report.append({
            "pillar": pillar.name,
            "scope": pillar.scope.value,
            "reason": pillar.reason,
            # Both axes, side by side, never merged. A consumer reads
            # either one; nothing in the document offers their mean.
            "practice": resolved["level"],
            "condition": measured,
            "posture": posture(resolved["level"], measured) if in_scope else None,
            "aspects": list(pillar.aspects),
        })
    return report

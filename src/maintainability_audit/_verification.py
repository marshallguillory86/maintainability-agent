"""Is there enough evidence to issue a grade? — ADR 001 stage 5.

Separate from scoring because the two questions are separate. The
rubric answers *what the available evidence estimates*; this answers
*whether enough evidence exists to certify a letter*. Conflating them
is what produced a scale where a shallow clone's missing history read
as demonstrated poor maintainability.

Nothing here changes a score. ``score.overall``, ``score.grade`` and
their neighbours keep their existing meaning and values, including the
evidence-floor grading that makes concealment unprofitable today.
``verified_grade`` is added *alongside* them and is null whenever the
profile's required evidence is not complete. Consumers keep reading the
compatibility fields until ADR 001 stage 7 migrates them deliberately.

The three states carry their full meaning here:

- ``Measured(0)`` is complete evidence. The scanner looked and found
  none, which is a finding, not a gap.
- ``NotApplicable`` is complete evidence. The measurement has no
  population in this repository — nothing is missing.
- ``Unknown`` is the only state that withholds verification.
"""
from __future__ import annotations

from typing import Any

from .evidence import NormalizedEvidence, Unknown, walk_evidence

# The named evidence contract a report was verified under. Reports state
# it so that CI, badges and APIs cannot silently compare results issued
# under different requirements — ADR 001 §5.
DEFAULT_PROFILE = "default-v1"

COMPLETE = "complete"
INCOMPLETE = "incomplete"


def verification(evidence: NormalizedEvidence, grade: str) -> dict[str, Any]:
    """``evidence_status`` and ``verified_grade`` for one report.

    ``default-v1`` requires every scoring input in the typed model to be
    resolved — ``Measured`` or ``NotApplicable``. One ``Unknown`` makes
    the status incomplete and withholds the verified grade, naming the
    measurement rather than reporting a bare "insufficient evidence".

    Returns the two fields as a mapping so the score document can splat
    them in one place instead of threading two more parameters through
    the rollup.
    """
    reasons = _unresolved(evidence)
    complete = not reasons
    return {
        "evidence_status": {
            "status": COMPLETE if complete else INCOMPLETE,
            "profile": DEFAULT_PROFILE,
            "reasons": reasons,
        },
        # Equal to the compatibility grade when the evidence supports
        # one, null when it does not. Never a pessimistic letter: ADR
        # 001 §1 rejects reporting unknown quality as bad quality.
        "verified_grade": grade if complete else None,
    }


def _unresolved(evidence: NormalizedEvidence) -> list[dict[str, str]]:
    """Every required measurement the report could not establish.

    Walks the typed model rather than a list of field names, so an input
    added to ``SummaryEvidence`` or ``HistoryEvidence`` is required by
    the profile the day it is added. Sorted by measurement path: a
    report diffed against another must not show spurious reordering.
    """
    return sorted(
        (
            {
                "measurement": path,
                "reason": state.reason,
                "provenance": state.provenance,
            }
            for path, state in walk_evidence(evidence)
            if isinstance(state, Unknown)
        ),
        key=lambda reason: reason["measurement"],
    )

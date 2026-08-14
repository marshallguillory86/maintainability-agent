"""A finding that keeps coming back is not a nit — ADR 009 §3b.

The feature that separates this from a linter with a database, and the
one a language model structurally cannot supply for itself.

A model evaluates each turn cold. It has no background process
integrating friction over time — no *"I have touched this module four
times and it keeps fighting me"* — so it will patch the same wrong
abstraction indefinitely without ever raising the design question.
Human threshold-crossing is affective: irritation integrated into a cost
signal, and that is real engineering information. This tool has a
durable record, so it computes externally what the model cannot hold.

**Recurrence alone would be weak.** Code churns for many reasons, and
"this came back" says only that the file changed twice. What makes the
signal strong is that the tool *generated the advice*, so it knows which
findings a prompt targeted. A linter can tell you a rule fired again;
only something that remembers what it advised can tell you its own
advice is not working.

Escalation is deliberately slow. One return is ordinary refactoring; an
escalation that fires constantly is one nobody reads. Two returns of a
finding somebody was explicitly told to fix is the case worth
interrupting for, because at that point the evidence says the finding
was a symptom and the advice treated the symptom.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from ._scan_history import Segment

# How many returns before a finding stops being a fix and starts being a
# design question. One is ordinary churn — a refactor that reintroduced
# something, a revert, a branch merged late. Two says the fix does not
# hold, which is a different claim and the one worth escalating.
RETURNS_BEFORE_ESCALATION = 2


class Outcome(StrEnum):
    """What happened to a finding somebody was advised to fix."""

    CLEARED = "cleared"
    NEVER_CLEARED = "never-cleared"
    # The strongest signal in the system: told exactly what to change,
    # changed it, and the problem came back.
    CLEARED_THEN_RETURNED = "cleared-then-returned"


@dataclass
class Recurrence:
    """One finding's history of leaving and coming back."""

    fingerprint: str
    returns: int = 0
    cleared_in: tuple[str, ...] = ()
    returned_in: tuple[str, ...] = ()
    targeted: bool = False

    @property
    def design_review_candidate(self) -> bool:
        """Whether this has stopped being a fix and become a question.

        Re-issuing "shorten this function" a third time is the nit-loop.
        At this point the honest response is that the abstraction is
        wrong, which is a human decision and not a patch.
        """
        return self.returns >= RETURNS_BEFORE_ESCALATION


@dataclass
class _Track:
    """Working state while walking a segment."""

    present: bool
    cleared_in: list[str] = field(default_factory=list)
    returned_in: list[str] = field(default_factory=list)


def recurrence(segment: Segment) -> dict[str, Recurrence]:
    """Findings that left and came back, with the commits involved.

    "It came back" is a claim; the commits are the evidence for it. A
    reader has to be able to go and look, or an escalation is an
    assertion about their code that they cannot check.

    Only findings that actually returned appear. One that was present
    throughout has not recurred, and listing it would bury the signal in
    everything that is merely still true.
    """
    records = segment.records
    if len(records) < 2:
        return {}

    tracks: dict[str, _Track] = {
        finding: _Track(present=True) for finding in records[0].fingerprints
    }
    targeted: set[str] = set(records[0].targeted)
    for record in records[1:]:
        current = set(record.fingerprints)
        for finding, track in tracks.items():
            if track.present and finding not in current:
                track.present = False
                track.cleared_in.append(record.commit)
            elif not track.present and finding in current:
                track.present = True
                track.returned_in.append(record.commit)
        for finding in current - set(tracks):
            tracks[finding] = _Track(present=True)
        targeted |= set(record.targeted)

    return {
        finding: Recurrence(
            fingerprint=finding,
            returns=len(track.returned_in),
            cleared_in=tuple(track.cleared_in),
            returned_in=tuple(track.returned_in),
            targeted=finding in targeted,
        )
        for finding, track in tracks.items()
        if track.returned_in
    }


def outcomes(segment: Segment) -> dict[str, Outcome]:
    """What became of each finding a prompt actually targeted.

    Only targeted findings appear. Absence of advice is not failure of
    advice: counting an untargeted finding as "never cleared" would
    blame the prompt for work it never asked for, which is the
    absence-as-value mistake this project exists to remove.
    """
    records = segment.records
    targeted = {finding for record in records for finding in record.targeted}
    if not targeted or len(records) < 2:
        return {}

    returned = recurrence(segment)
    final = set(records[-1].fingerprints)
    result: dict[str, Outcome] = {}
    for finding in sorted(targeted):
        if finding in returned:
            result[finding] = Outcome.CLEARED_THEN_RETURNED
        elif finding in final:
            result[finding] = Outcome.NEVER_CLEARED
        else:
            result[finding] = Outcome.CLEARED
    return result


def escalations(segment: Segment) -> list[dict[str, Any]]:
    """Findings that have earned a design review rather than another patch.

    Ordered by how many times the fix failed to hold, because that is
    the strength of the evidence. Each carries its reason and its
    commits: an escalation without them is a louder nit.
    """
    candidates = [
        item for item in recurrence(segment).values() if item.design_review_candidate
    ]
    candidates.sort(key=lambda item: (-item.returns, item.fingerprint))
    return [
        {
            "fingerprint": item.fingerprint,
            "returns": item.returns,
            "targeted": item.targeted,
            "commits": list(item.returned_in),
            "reason": _reason(item),
        }
        for item in candidates
    ]


def _reason(item: Recurrence) -> str:
    """Why this one is a design question, in the terms that make it one."""
    if item.targeted:
        return (
            f"cleared and returned {item.returns} times after being named in a "
            "remediation prompt: somebody was told exactly what to change, "
            "changed it, and the problem came back. That is evidence the "
            "finding is a symptom and the advice addressed the symptom, so "
            "re-issuing it a third time would repeat a fix already known not "
            "to hold"
        )
    return (
        f"cleared and returned {item.returns} times: the fix does not hold, "
        "which is a symptom of the surrounding design rather than of this "
        "location"
    )

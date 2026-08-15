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
from pathlib import Path
from typing import Any

from ._finding_match import Identity, rename_map, same_finding
from ._scan_history import ScanRecord, Segment

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
    """Working state while walking a segment.

    `identity` is the finding as last matched, so a rename or reorder
    updates what the next record is compared against; `label` is the
    fingerprint at first sight — the key `targeted` tuples and readers
    joined on when the track began, so it never silently changes.
    """

    identity: Identity
    label: str
    present: bool
    cleared_in: list[str] = field(default_factory=list)
    returned_in: list[str] = field(default_factory=list)


def _identities_of(record: ScanRecord) -> list[Identity]:
    """A record's findings as identities, structured when it stored them.

    Older records (schema 1/2) carry labels only, so each becomes a
    degenerate identity that can match nothing but its exact label —
    which keeps recurrence between two such records string equality,
    exactly what those records can support.
    """
    if record.identities:
        return [Identity(**dict(entry)) for entry in record.identities]
    return [
        Identity(kind="label", path="", name="", ordinal=0, body_digest="",
                 fingerprint=label)
        for label in record.fingerprints
    ]


def _step_renames(root: Path | None, earlier: ScanRecord,
                  later: ScanRecord) -> dict[str, str]:
    if root is None:
        return {}
    return rename_map(root, earlier.commit, later.commit)


def _walk(records: list[ScanRecord], root: Path | None) -> list[_Track]:
    """Follow every finding through the segment, matching structurally."""
    tracks = [
        _Track(identity=identity, label=identity.fingerprint, present=True)
        for identity in _identities_of(records[0])
    ]
    for earlier, record in zip(records, records[1:], strict=False):
        renames = _step_renames(root, earlier, record)
        remaining = _identities_of(record)
        for track in tracks:
            match = next(
                (item for item in remaining
                 if same_finding(item, track.identity, renames)), None)
            if match is not None:
                remaining.remove(match)
                track.identity = match
                if not track.present:
                    track.present = True
                    track.returned_in.append(record.commit)
            elif track.present:
                track.present = False
                track.cleared_in.append(record.commit)
        tracks.extend(
            _Track(identity=identity, label=identity.fingerprint, present=True)
            for identity in remaining
        )
    return tracks


def recurrence(segment: Segment, root: Path | None = None) -> dict[str, Recurrence]:
    """Findings that left and came back, with the commits involved.

    "It came back" is a claim; the commits are the evidence for it. A
    reader has to be able to go and look, or an escalation is an
    assertion about their code that they cannot check.

    Only findings that actually returned appear. One that was present
    throughout has not recurred, and listing it would bury the signal in
    everything that is merely still true.

    Matching is structural where both records stored identities: a
    return is only a return if it is the *same finding*, and a label
    comparison calls a `git mv` a clear-plus-new. `root` is where the
    rename evidence lives; without it, matching still survives reorders
    and body edits but takes no rename glue.
    """
    records = segment.records
    if len(records) < 2:
        return {}

    targeted = {label for record in records for label in record.targeted}
    return {
        track.label: Recurrence(
            fingerprint=track.label,
            returns=len(track.returned_in),
            cleared_in=tuple(track.cleared_in),
            returned_in=tuple(track.returned_in),
            targeted=track.label in targeted,
        )
        for track in _walk(records, root)
        if track.returned_in
    }


def outcomes(segment: Segment, root: Path | None = None) -> dict[str, Outcome]:
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

    returned = recurrence(segment, root)
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


def escalations(segment: Segment, root: Path | None = None) -> list[dict[str, Any]]:
    """Findings that have earned a design review rather than another patch.

    Ordered by how many times the fix failed to hold, because that is
    the strength of the evidence. Each carries its reason and its
    commits: an escalation without them is a louder nit.
    """
    candidates = [
        item for item in recurrence(segment, root).values()
        if item.design_review_candidate
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

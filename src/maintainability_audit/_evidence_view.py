"""How the four score concepts are phrased, in one place.

ADR 001 stage 7. Four separate things reach a reader — the
maintainability *estimate*, its *range*, whether the *evidence* is
complete, and the *verified grade* — and before this stage every
consumer either ignored the last two or would have had to interpret
them itself. Four independent interpretations of "what does null mean"
is four chances to imply a repository was graded when it was not.

This module owns the wording and nothing else. It reads the public
report dictionary, computes no score, infers no status, and imports
nothing from the scoring layer: the score object stays the sole source
of the estimate, the range, the compatibility grade, the evidence
status and the verified grade.

The one rule every phrasing here obeys: **a null verified grade is
never rendered as a letter, a dash, or a blank.** Each of those reads
as a result, and the point of the field is that no result was issued.
"""
from __future__ import annotations

from typing import Any

NOT_VERIFIED = "Not verified"


def estimate(score: dict[str, Any]) -> str:
    """The point estimate, always labelled as an estimate."""
    return f"{score['overall']} / 5"


def score_range(score: dict[str, Any]) -> str:
    low, high = score.get("overall_range", [score["overall"], score["overall"]])
    return f"{low} – {high}" if low != high else f"{low} (no unmeasured evidence)"


def is_complete(score: dict[str, Any]) -> bool:
    return (score.get("evidence_status") or {}).get("status") == "complete"


def profile(score: dict[str, Any]) -> str:
    return (score.get("evidence_status") or {}).get("profile", "unknown")


def verified_grade(score: dict[str, Any]) -> str:
    """The verified grade, or the words that mean there isn't one."""
    return score.get("verified_grade") or NOT_VERIFIED


def compatibility_grade(score: dict[str, Any]) -> str:
    """The legacy grade, labelled so it is not mistaken for a verdict.

    It stays visible through the compatibility period because CI, the
    prompt and the report have all read it for releases — but it is
    banded from the evidence floor, so on an incomplete report it says
    "this is the worst the evidence allows", not "this is the grade".
    """
    return f"{score['grade']} (compatibility, evidence-floor)"


def reasons(score: dict[str, Any]) -> list[dict[str, str]]:
    return list((score.get("evidence_status") or {}).get("reasons") or [])


def status_sentence(score: dict[str, Any]) -> str:
    """One line a human can act on, for either state."""
    if is_complete(score):
        return f"Evidence complete under profile `{profile(score)}`."
    missing = len(reasons(score))
    measurement = "measurement" if missing == 1 else "measurements"
    return (
        f"Evidence incomplete under profile `{profile(score)}`: "
        f"{missing} required {measurement} unavailable, so no verified grade was issued."
    )


def reason_lines(score: dict[str, Any], bullet: str = "- ") -> list[str]:
    """Each unavailable measurement, with its typed path and provenance.

    Provenance is included rather than summarised: "history is missing"
    sends someone hunting, `history.files_changed` tells them exactly
    which measurement to restore.
    """
    return [
        f"{bullet}`{item['measurement']}` — {item['reason']} (provenance: `{item['provenance']}`)"
        for item in reasons(score)
    ]


def remediation_note(score: dict[str, Any]) -> list[str]:
    """What an agent should do about incomplete evidence: not refactor.

    Missing evidence is not a maintainability defect in the source, and
    an agent told about it without this instruction will try to fix the
    code. The work order stays bounded to real findings; restoring the
    evidence is a separate, usually one-line, change to how the audit
    was invoked.
    """
    if is_complete(score):
        return []
    return [
        "",
        "### Evidence",
        "",
        status_sentence(score),
        "",
        *reason_lines(score),
        "",
        "**This is not a code defect and must not widen the work order.** Do not refactor,",
        "add abstractions, or change behaviour in response to it. Missing history usually",
        "means the audit ran on a shallow clone — `actions/checkout` defaults to",
        "`fetch-depth: 1`. Report it, or rerun the audit with full history, and fix only",
        "the findings listed elsewhere in this prompt.",
    ]

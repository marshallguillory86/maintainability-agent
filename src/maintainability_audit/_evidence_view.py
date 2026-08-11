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
NOT_REPORTED = "Not reported"


def estimate(score: dict[str, Any]) -> str:
    """The point estimate, always labelled as an estimate."""
    return f"{score['overall']} / 5"


def score_range(score: dict[str, Any]) -> str:
    """The interval, and what a collapsed one actually means.

    Equal bounds do **not** establish complete evidence. The endpoints
    are rounded to one decimal, so concealing a lightly-weighted
    measurement can leave them coincident while the evidence is
    genuinely incomplete — an audit reproduced `[4.9, 4.9]` rendered as
    "no unmeasured evidence" on a report whose verified grade had been
    withheld. Completeness is a property of the typed evidence, never of
    two numbers that happen to match after rounding, so this consults
    the status rather than inferring it.
    """
    low, high = score.get("overall_range", [score["overall"], score["overall"]])
    if low != high:
        return f"{low} – {high}"
    if not reports_evidence(score):
        return f"{low}"
    if is_complete(score):
        return f"{low} (no unmeasured evidence)"
    return f"{low} (bounds coincide after rounding; evidence is still incomplete)"


def is_complete(score: dict[str, Any]) -> bool:
    return (score.get("evidence_status") or {}).get("status") == "complete"


def reports_evidence(score: dict[str, Any]) -> bool:
    """Whether this score carries an evidence verdict at all.

    Three states, not two. A score with no ``evidence_status`` carries no
    verdict on completeness — it is not a score whose grade was
    *withheld*. Collapsing those two produced "Evidence incomplete: 0
    required measurements unavailable", which asserts a withholding that
    never happened and contradicts itself in the same sentence.

    Why the absence exists is deliberately not guessed at. An earlier
    revision called it a report that "predates evidence verification",
    which is a claim about provenance that absence cannot support: it
    could equally be malformed, hand-built, or an unsupported shape, and
    the report contract rejects unsupported schemas rather than dating
    them.
    """
    return bool(score.get("evidence_status"))


def profile(score: dict[str, Any]) -> str:
    return (score.get("evidence_status") or {}).get("profile", "unknown")


def verified_grade(score: dict[str, Any]) -> str:
    """The verified grade, the words that mean there isn't one, or the
    words that mean the question was never asked."""
    if not reports_evidence(score):
        return NOT_REPORTED
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
    if not reports_evidence(score):
        return "Evidence verification status was not reported."
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
    if is_complete(score) or not reports_evidence(score):
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
        "add abstractions, or change behaviour in response to it.",
        _restore_hint(score),
        "Fix only the findings listed elsewhere in this prompt.",
    ]


def instruction_note(score: dict[str, Any]) -> list[str]:
    """The don't-widen guard, in the compact form the instructions use.

    The agent-instruction file is a bullet list, not prose, so it takes
    the same rule as the remediation prompt without the heading. An
    audit found this consumer showing only the grade value while
    claiming the whole contract was migrated.
    """
    if is_complete(score) or not reports_evidence(score):
        return []
    return [
        "- Missing evidence is **not** a code defect: do not refactor or widen scope for it. "
        + _restore_hint(score),
    ]


def _restore_hint(score: dict[str, Any]) -> str:
    """Advice that matches what is actually missing.

    The first version told every incomplete report to check its clone
    depth, including one whose only missing measurement was
    `summary.test_file_count` — naming a summary input and then
    recommending a fix to git history. An audit caught it. Guidance now
    follows the measurement paths.
    """
    sections = {item["measurement"].split(".", 1)[0] for item in reasons(score)}
    if sections == {"history"}:
        return (
            "Every missing measurement is from git history, which usually means the audit "
            "ran on a shallow clone — `actions/checkout` defaults to `fetch-depth: 1`. "
            "Rerun with full history, or report that it is unavailable."
        )
    if sections == {"summary"}:
        return (
            "The missing measurements are scanner outputs, not history. Something upstream "
            "did not report them: check that the audit ran over the whole tree and that the "
            "report was not filtered or hand-edited before scoring."
        )
    return (
        "The missing measurements come from more than one producer; see the paths above. "
        "Restore the inputs they name and rerun the audit rather than changing code."
    )
